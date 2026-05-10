"""
reporters/weekly.py — Weekly Wrap builder (~800 mots, 7 sections + tableaux).

Sections (REPT-02) :
  1. Executive Summary  — narration vue d'ensemble (~120 mots)
  2. Macro Watch        — tableau taux/inflation + narration
  3. ETF Performance    — tableau performance + narration
  4. Crypto Recap       — tableau coins + Fear & Greed + narration
  5. PEA Wrap           — tableau PEA + alerte éligibilité
  6. News Digest        — bullets top headlines
  7. Outlook            — narration semaine à venir (~120 mots)

Threat model :
  T-03-09 : dégradation totale — data={} retourne 7 sections "[Section indisponible.]"
             via filet try/except global dans build_weekly_report.
"""
from __future__ import annotations

from config import Config
from reporters.base import synthesize_section, build_section, format_pct, format_currency
from logging_setup import get_logger

logger = get_logger(__name__)

WEEKLY_SYSTEM_PROMPT = (
    "Tu es un analyste financier français. Réponds en français, ton sobre et factuel. "
    "Sections de ~100-120 mots chacune. Pas de conseil financier explicite."
)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    """Construit un tableau Markdown."""
    if not rows:
        return ""
    head = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join(["---"] * len(headers)) + "|"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return f"{head}\n{sep}\n{body}"


def _executive_summary(data: dict, config: Config) -> str:
    meta = data.get("_meta", {}) or {}
    prompt = (
        f"Rédige le résumé exécutif (~120 mots) de la semaine financière. "
        f"Sources OK: {meta.get('sources_ok', [])}. "
        f"Sources failed: {meta.get('sources_failed', [])}."
    )
    body = synthesize_section(prompt, config=config, system=WEEKLY_SYSTEM_PROMPT)
    return build_section("Executive Summary", body)


def _macro_watch(data: dict, config: Config) -> str:
    macro = data.get("macro") or {}
    if macro.get("source_failed"):
        return build_section("Macro Watch", "Données macro indisponibles cette semaine.")
    series = macro.get("series", {})
    rows = [[k, str(s.get("value", "n/a")), str(s.get("date", "n/a"))]
            for k, s in series.items() if isinstance(s, dict)]
    table = _table(["Série", "Valeur", "Date"], rows)
    prompt = f"Commentaire macro ~100 mots à partir des séries: {list(series.keys())}."
    body = synthesize_section(prompt, config=config, system=WEEKLY_SYSTEM_PROMPT)
    return build_section("Macro Watch", f"{table}\n\n{body}" if table else body)


def _etf_performance(data: dict, config: Config) -> str:
    etf = data.get("etf") or {}
    if etf.get("source_failed"):
        return build_section("ETF Performance", "Données ETF indisponibles.")
    tickers = etf.get("tickers", {})
    rows = []
    for sym, t in tickers.items():
        if t.get("price") is not None:
            rows.append([sym, format_currency(t["price"]),
                         format_pct(t.get("pct_change", 0.0))])
    table = _table(["Ticker", "Prix", "Variation"], rows)
    prompt = f"Commentaire ETF ~100 mots. Tickers couverts: {list(tickers.keys())}."
    body = synthesize_section(prompt, config=config, system=WEEKLY_SYSTEM_PROMPT)
    return build_section("ETF Performance", f"{table}\n\n{body}" if table else body)


def _crypto_recap(data: dict, config: Config) -> str:
    crypto = data.get("crypto") or {}
    if crypto.get("source_failed"):
        return build_section("Crypto Recap", "Données crypto indisponibles.")
    coins = crypto.get("coins", {})
    fg = crypto.get("fear_greed", {}) or {}
    rows = []
    for cid, c in coins.items():
        if c.get("price") is not None:
            rows.append([c.get("symbol", cid), format_currency(c["price"]),
                         format_pct(c.get("pct_change_24h", 0.0))])
    table = _table(["Coin", "Prix", "24h"], rows)
    prompt = (f"Commentaire crypto ~100 mots. Fear & Greed: {fg.get('label', 'n/a')} "
              f"({fg.get('value', 'n/a')}). Coins: {list(coins.keys())}.")
    body = synthesize_section(prompt, config=config, system=WEEKLY_SYSTEM_PROMPT)
    return build_section("Crypto Recap", f"{table}\n\n{body}" if table else body)


def _pea_wrap(data: dict, config: Config) -> str:
    pea = data.get("pea") or {}
    if pea.get("source_failed"):
        return build_section("PEA Wrap", "Données PEA indisponibles.")
    prices = pea.get("prices", {})
    rows = []
    for sym, p in prices.items():
        if p.get("price") is not None:
            rows.append([sym, format_currency(p["price"], symbol="€"),
                         format_pct(p.get("pct_change", 0.0))])
    table = _table(["Ticker", "Prix", "Variation"], rows)
    alert = ""
    if pea.get("eligibility_changed"):
        alert = "ALERTE — changement d'éligibilité PEA détecté.\n\n"
    prompt = f"Commentaire PEA France ~100 mots. Tickers: {list(prices.keys())}."
    body = synthesize_section(prompt, config=config, system=WEEKLY_SYSTEM_PROMPT)
    return build_section("PEA Wrap", f"{alert}{table}\n\n{body}" if table else f"{alert}{body}")


def _news_digest(data: dict, _config: Config) -> str:
    news = data.get("news") or {}
    if news.get("source_failed"):
        return build_section("News Digest", "Headlines indisponibles cette semaine.")
    headlines = news.get("headlines", [])[:10]
    if not headlines:
        return build_section("News Digest", "Aucun titre récent disponible.")
    bullets = "\n".join(f"- **{h.get('source', '?')}** — {h.get('title', 'titre manquant')}"
                        for h in headlines)
    return build_section("News Digest", bullets)


def _outlook(data: dict, config: Config) -> str:
    prompt = (
        "Rédige les perspectives (~120 mots) pour la semaine financière à venir. "
        "Mentionne 2-3 points d'attention pour un investisseur particulier français "
        "exposé ETF mondiaux, crypto et PEA."
    )
    body = synthesize_section(prompt, config=config, system=WEEKLY_SYSTEM_PROMPT)
    return build_section("Outlook", body)


def build_weekly_report(data: dict, config: Config) -> str:
    """
    Construit le Weekly Wrap (~800 mots, 7 sections + tableaux).

    Args:
        data: dict produit par collect_all() (peut être vide ou partiel)
        config: Config avec anthropic_api_key et anthropic_model

    Returns:
        Rapport Markdown complet — toujours 7 sections, jamais lève.
    """
    try:
        sections = [
            _executive_summary(data, config),
            _macro_watch(data, config),
            _etf_performance(data, config),
            _crypto_recap(data, config),
            _pea_wrap(data, config),
            _news_digest(data, config),
            _outlook(data, config),
        ]
        return "\n".join(sections)
    except Exception as e:
        logger.error("build_weekly_report failed: %s", e)
        return "\n".join(
            build_section(t, "[Section indisponible.]")
            for t in ("Executive Summary", "Macro Watch", "ETF Performance",
                      "Crypto Recap", "PEA Wrap", "News Digest", "Outlook")
        )
