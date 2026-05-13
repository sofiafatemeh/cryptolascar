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

# Répertoire racine du projet (ancré au fichier, indépendant du cwd) (WR-03)
_PROJECT_ROOT = Path(__file__).parent.parent
_TWEETS_DIR = _PROJECT_ROOT / "tweets"

# Validation des paramètres d'entrée pour prévenir le path traversal (CR-02)
_SAFE_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SAFE_TYPE_RE = re.compile(r"^(daily|weekly|monthly)$")

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

    Raises:
        ValueError: si report_type ou date ne respectent pas le format attendu (CR-02)

    Note:
        Monthly Close → retourne None sans écriture (TWEET-04).
        Longueur hors [240, 270] → warning loggé mais fichier écrit quand même.
    """
    # TWEET-04 : Monthly Close — aucun tweet
    if report_type == "monthly":
        logger.info("Tweet skipped: report_type=monthly (TWEET-04)")
        return None

    # Validation des paramètres pour prévenir le path traversal (CR-02)
    if not _SAFE_TYPE_RE.match(report_type):
        raise ValueError(f"Invalid report_type: {report_type!r}")
    if not _SAFE_DATE_RE.match(date):
        raise ValueError(f"Invalid date format: {date!r}")

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
        # Vérification défensive de la réponse Claude (WR-02)
        if not response.content:
            raise ValueError(
                f"Claude returned empty content list (stop_reason={response.stop_reason!r})"
            )
        content_block = response.content[0]
        if content_block.type != "text":
            raise ValueError(
                f"Unexpected content block type: {content_block.type!r}"
            )
        tweet_text = content_block.text.strip()
    except Exception as e:
        # T-04-05 : api_key JAMAIS loggé
        from anthropic import AuthenticationError as _AuthErr
        if isinstance(e, _AuthErr):
            logger.warning(
                "Tweet skipped: ANTHROPIC_API_KEY invalide ou absent — "
                "le run continue sans fichier tweet"
            )
            return None
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

    # Écriture dans /tweets/YYYY-MM-DD.txt (STOR-02) — chemin ancré au projet (WR-03)
    dest = _TWEETS_DIR / f"{date}.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(tweet_text, encoding="utf-8")
    logger.info(
        "Tweet written: report_type=%s date=%s path=%s length=%d",
        report_type, date, dest, tweet_len,
    )
    return None
