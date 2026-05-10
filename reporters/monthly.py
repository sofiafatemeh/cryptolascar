"""
reporters/monthly.py — Monthly Close builder (~2000 mots, 7 sections, ≥ 2 tableaux).

Sections (REPT-03) :
  1. Month in Review              — narration ~250 mots (synthèse mensuelle)
  2. Macro Backdrop               — tableau FRED + narration
  3. ETF Monthly Performance      — tableau ETF + narration
  4. Crypto Monthly               — tableau coins + Fear & Greed + narration
  5. PEA Monthly                  — tableau PEA + alerte éligibilité
  6. News & Themes                — bullets + narration thèmes du mois
  7. Forward Look                 — narration ~250 mots (perspectives mois suivant)

Threat model :
  T-03-09 (mensuel) : dégradation totale — data={} retourne 7 sections formatées
                      via filet try/except global dans build_monthly_report.
  T-03-13 : les logs n'exposent jamais la config complète (clé API).
"""
from __future__ import annotations

from config import Config
from reporters.base import synthesize_section, build_section, format_pct, format_currency
from logging_setup import get_logger

logger = get_logger(__name__)

MONTHLY_SYSTEM_PROMPT = (
    "Tu es un analyste financier français senior. Réponds en français, ton sobre et factuel. "
    "Sections de ~250 mots pour la narration centrale, ~150 mots pour les commentaires de tableau. "
    "Pas de conseil financier explicite."
)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    """Construit un tableau Markdown."""
    if not rows:
        return ""
    head = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join(["---"] * len(headers)) + "|"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return f"{head}\n{sep}\n{body}"


def _month_in_review(data: dict, config: Config) -> str:
    """Section 1 — Month in Review : synthèse narrative du mois écoulé (~250 mots)."""
    meta = data.get("_meta", {}) or {}
    prompt = (
        "Rédige 'Month in Review' (~250 mots) — synthèse du mois écoulé pour un investisseur "
        f"particulier français exposé ETF mondiaux, crypto et PEA. "
        f"Sources OK: {meta.get('sources_ok', [])}. "
        f"Failed: {meta.get('sources_failed', [])}."
    )
    body = synthesize_section(prompt, config=config, system=MONTHLY_SYSTEM_PROMPT, max_tokens=600)
    return build_section("Month in Review", body)


def _macro_backdrop(data: dict, config: Config) -> str:
    """Section 2 — Macro Backdrop : tableau séries FRED + narration mensuelle."""
    macro = data.get("macro") or {}
    if macro.get("source_failed"):
        return build_section("Macro Backdrop", "Données macro indisponibles ce mois.")
    series = macro.get("series", {})
    rows = [
        [k, str(s.get("value", "n/a")), str(s.get("date", "n/a"))]
        for k, s in series.items()
        if isinstance(s, dict)
    ]
    table = _table(["Série", "Valeur", "Date"], rows)
    prompt = f"Commentaire macro mensuel ~150 mots. Séries disponibles : {list(series.keys())}."
    body = synthesize_section(prompt, config=config, system=MONTHLY_SYSTEM_PROMPT)
    return build_section("Macro Backdrop", f"{table}\n\n{body}" if table else body)


def _etf_monthly(data: dict, config: Config) -> str:
    """Section 3 — ETF Monthly Performance : tableau ETF + narration mensuelle."""
    etf = data.get("etf") or {}
    if etf.get("source_failed"):
        return build_section("ETF Monthly Performance", "Données ETF indisponibles ce mois.")
    rows = []
    for sym, t in etf.get("tickers", {}).items():
        if t.get("price") is not None:
            rows.append([
                sym,
                format_currency(t["price"]),
                format_pct(t.get("pct_change", 0.0)),
            ])
    table = _table(["Ticker", "Prix", "Variation"], rows)
    prompt = (
        f"Commentaire ETF mensuel ~150 mots. "
        f"Tickers couverts : {list(etf.get('tickers', {}).keys())}."
    )
    body = synthesize_section(prompt, config=config, system=MONTHLY_SYSTEM_PROMPT)
    return build_section("ETF Monthly Performance", f"{table}\n\n{body}" if table else body)


def _crypto_monthly(data: dict, config: Config) -> str:
    """Section 4 — Crypto Monthly : tableau coins + Fear & Greed + narration."""
    crypto = data.get("crypto") or {}
    if crypto.get("source_failed"):
        return build_section("Crypto Monthly", "Données crypto indisponibles ce mois.")
    rows = []
    for cid, c in crypto.get("coins", {}).items():
        if c.get("price") is not None:
            rows.append([
                c.get("symbol", cid),
                format_currency(c["price"]),
                format_pct(c.get("pct_change_24h", 0.0)),
            ])
    table = _table(["Coin", "Prix", "30j"], rows)
    fg = crypto.get("fear_greed", {}) or {}
    prompt = (
        f"Commentaire crypto mensuel ~150 mots. "
        f"Fear & Greed : {fg.get('label', 'n/a')} ({fg.get('value', 'n/a')}). "
        f"Coins : {list(crypto.get('coins', {}).keys())}."
    )
    body = synthesize_section(prompt, config=config, system=MONTHLY_SYSTEM_PROMPT)
    return build_section("Crypto Monthly", f"{table}\n\n{body}" if table else body)


def _pea_monthly(data: dict, config: Config) -> str:
    """Section 5 — PEA Monthly : tableau PEA + alerte éligibilité si applicable."""
    pea = data.get("pea") or {}
    if pea.get("source_failed"):
        return build_section("PEA Monthly", "Données PEA indisponibles ce mois.")
    rows = []
    for sym, p in pea.get("prices", {}).items():
        if p.get("price") is not None:
            rows.append([
                sym,
                format_currency(p["price"], symbol="€"),
                format_pct(p.get("pct_change", 0.0)),
            ])
    table = _table(["Ticker", "Prix", "Variation"], rows)
    # Alerte éligibilité — garantie même si Claude ne l'inclut pas
    alert = ""
    if pea.get("eligibility_changed"):
        alert = "ALERTE — changement d'éligibilité PEA détecté ce mois.\n\n"
    prompt = "Commentaire PEA France mensuel ~150 mots. Bilan du mois pour les titres PEA."
    body = synthesize_section(prompt, config=config, system=MONTHLY_SYSTEM_PROMPT)
    out = f"{alert}{table}\n\n{body}" if table else f"{alert}{body}"
    return build_section("PEA Monthly", out)


def _news_themes(data: dict, config: Config) -> str:
    """Section 6 — News & Themes : bullets headlines + narration thèmes du mois."""
    news = data.get("news") or {}
    if news.get("source_failed"):
        return build_section("News & Themes", "Headlines indisponibles ce mois.")
    headlines = news.get("headlines", [])[:15]
    if not headlines:
        return build_section("News & Themes", "Aucun titre récent disponible.")
    bullets = "\n".join(
        f"- **{h.get('source', '?')}** — {h.get('title', 'titre manquant')}"
        for h in headlines
    )
    prompt = (
        f"Identifie les 3 thèmes financiers dominants du mois (~150 mots) "
        f"à partir de ces titres :\n{bullets}"
    )
    body = synthesize_section(prompt, config=config, system=MONTHLY_SYSTEM_PROMPT)
    return build_section("News & Themes", f"{bullets}\n\n{body}")


def _forward_look(data: dict, config: Config) -> str:
    """Section 7 — Forward Look : perspectives pour le mois à venir (~250 mots)."""
    prompt = (
        "Rédige 'Forward Look' (~250 mots) — perspectives pour le mois à venir. "
        "Mentionne 3-4 points d'attention pour un investisseur particulier français "
        "exposé ETF mondiaux, crypto et PEA."
    )
    body = synthesize_section(prompt, config=config, system=MONTHLY_SYSTEM_PROMPT, max_tokens=600)
    return build_section("Forward Look", body)


def build_monthly_report(data: dict, config: Config) -> str:
    """
    Construit le Monthly Close (~2000 mots, 7 sections, ≥ 2 tableaux).

    Sections dans l'ordre REPT-03 :
      1. Month in Review              — narration ~250 mots
      2. Macro Backdrop               — tableau FRED + narration
      3. ETF Monthly Performance      — tableau ETF + narration
      4. Crypto Monthly               — tableau coins + narration
      5. PEA Monthly                  — tableau PEA + alerte éligibilité
      6. News & Themes                — bullets + narration thèmes
      7. Forward Look                 — narration ~250 mots

    Args:
        data: dict produit par collect_all() — clés etf/crypto/pea/macro/news/_meta.
              Chaque sous-dict peut avoir source_failed=True (dégradation gracieuse).
        config: Config (utilisé pour anthropic_model et anthropic_api_key).
                Le modèle n'est JAMAIS hardcodé dans ce module (LLM-02).

    Returns:
        Rapport Markdown complet (chaîne) — toujours 7 sections, jamais lève.

    Ne lève jamais — filet de sécurité global en cas d'erreur inattendue.
    """
    try:
        sections = [
            _month_in_review(data, config),
            _macro_backdrop(data, config),
            _etf_monthly(data, config),
            _crypto_monthly(data, config),
            _pea_monthly(data, config),
            _news_themes(data, config),
            _forward_look(data, config),
        ]
        return "\n".join(sections)
    except Exception as e:
        # T-03-13 : on logue uniquement le message d'erreur, JAMAIS la config (clé API)
        logger.error("build_monthly_report failed: %s", e)
        # Filet de sécurité — retourner les 7 titres en mode dégradé total
        return "\n".join(
            build_section(t, "[Section indisponible.]")
            for t in (
                "Month in Review",
                "Macro Backdrop",
                "ETF Monthly Performance",
                "Crypto Monthly",
                "PEA Monthly",
                "News & Themes",
                "Forward Look",
            )
        )
