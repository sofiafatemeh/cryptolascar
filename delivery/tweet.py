"""
delivery/tweet.py — Générateur de fichiers tweet depuis le rapport ONE SIGNAL.

Threat model:
  T-04-05 : anthropic_api_key jamais loggé — seuls report_type, date, str(e)
             apparaissent dans les logs en cas d'échec (D-12).
  T-04-06 : Le fichier tweet est écrit même si la longueur est hors [240, 270]
             (dégradation gracieuse — log warning, pas de raise).

Routing (D-11) :
  "daily"   → extraction ## One Signal → Claude → tweets/YYYY-MM-DD.txt
  "weekly"  → rapport complet → Claude → tweets/YYYY-MM-DD.txt
  "monthly" → aucun fichier (TWEET-04)
"""
from __future__ import annotations

import re
from pathlib import Path

from anthropic import Anthropic

from config import Config
from logging_setup import get_logger

logger = get_logger(__name__)

# Pool de hashtags — Claude choisit 3-4 selon le contenu (D-10)
HASHTAG_POOL: list[str] = [
    "#Bourse",
    "#ETF",
    "#Crypto",
    "#Finance",
    "#CAC40",
    "#Bitcoin",
    "#Investissement",
    "#Marchés",
]

# Contrainte de longueur tweet (TWEET-03)
TWEET_MIN_CHARS = 240
TWEET_MAX_CHARS = 270

_SYSTEM_PROMPT = (
    "Tu es un analyste financier francophone qui rédige des tweets percutants pour "
    "une audience d'investisseurs particuliers. Ton style est concis, factuel, et professionnel."
)


def extract_one_signal(report: str) -> str:
    """Extrait le texte sous '## One Signal' du rapport daily (D-08).

    Args:
        report: texte brut du rapport (sortie reporters/daily.py)

    Returns:
        str: contenu de la section One Signal, stripped. Chaîne vide si absent.
    """
    # Cherche "## One Signal" (case-insensitive sur "One Signal") puis capture
    # jusqu'au prochain header "##" ou fin de chaîne
    pattern = r"##\s*One Signal\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, report, re.DOTALL | re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def _build_prompt(report_type: str, source_text: str) -> str:
    """Construit le prompt utilisateur pour Claude (TWEET-03, D-09)."""
    hashtags_str = ", ".join(HASHTAG_POOL)
    return (
        f"Rédige un tweet en français basé sur cette analyse financière.\n\n"
        f"CONTRAINTES OBLIGATOIRES :\n"
        f"- Exactement {TWEET_MIN_CHARS} à {TWEET_MAX_CHARS} caractères (espaces inclus)\n"
        f"- Ton analyste, factuel, professionnel\n"
        f"- Termine avec 3 ou 4 hashtags choisis parmi : {hashtags_str}\n"
        f"- Aucun guillemet, aucune explication, seulement le texte du tweet\n\n"
        f"Analyse source ({report_type}) :\n{source_text}"
    )


def write_tweet(
    report_type: str,
    date: str,
    report: str,
    config: Config,
) -> None:
    """Génère et écrit un fichier tweet pour daily ou weekly (D-11).

    Args:
        report_type: "daily" | "weekly" | "monthly"
        date: date ISO YYYY-MM-DD (ex: "2026-05-10")
        report: texte brut du rapport (sortie reporters/dispatch.py)
        config: Config avec anthropic_api_key et anthropic_model

    Returns:
        None — écrit le fichier ou lève une exception.

    Note:
        Monthly Close → retourne None sans écriture (TWEET-04).
        Longueur hors [240, 270] → warning loggé mais fichier écrit quand même.
    """
    # TWEET-04 : Monthly Close — aucun tweet
    if report_type == "monthly":
        logger.info("Tweet skipped: report_type=monthly (TWEET-04)")
        return None

    # Extraction du texte source selon le type de rapport
    if report_type == "daily":
        source_text = extract_one_signal(report)
        if not source_text:
            logger.warning(
                "write_tweet: ## One Signal section not found in daily report — using full report"
            )
            source_text = report
    else:
        # Weekly : rapport complet (résumé exécutif + outlook)
        source_text = report

    prompt = _build_prompt(report_type, source_text)

    try:
        client = Anthropic(api_key=config.anthropic_api_key)
        response = client.messages.create(
            model=config.anthropic_model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
            system=_SYSTEM_PROMPT,
        )
        tweet_text = response.content[0].text.strip()
    except Exception as e:
        # T-04-05 : api_key JAMAIS loggé
        logger.error(
            "Tweet generation failed: report_type=%s date=%s error=%s",
            report_type, date, str(e),
        )
        raise

    # Vérification de longueur (TWEET-03) — warning si hors plage, écriture quand même
    tweet_len = len(tweet_text)
    if not (TWEET_MIN_CHARS <= tweet_len <= TWEET_MAX_CHARS):
        logger.warning(
            "Tweet length %d is outside [%d, %d] for report_type=%s date=%s — writing anyway",
            tweet_len, TWEET_MIN_CHARS, TWEET_MAX_CHARS, report_type, date,
        )

    # Écriture dans /tweets/YYYY-MM-DD.txt (STOR-02)
    dest = Path("tweets") / f"{date}.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(tweet_text, encoding="utf-8")
    logger.info(
        "Tweet written: report_type=%s date=%s path=%s length=%d",
        report_type, date, dest, tweet_len,
    )
    return None
