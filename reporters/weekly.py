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

import html as _html

from config import Config
from reporters.base import (
    synthesize_section, build_section, format_pct, format_currency,
    ReportOutput, html_section,
    ETF_FALLBACK, CRYPTO_FALLBACK, GAUGE_FALLBACK, PEA_FALLBACK,
)
from charts import (
    generate_etf_chart,
    generate_crypto_sparklines,
    generate_fear_greed_gauge,
    generate_pea_table,
)
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
    # Garantir le mot-clé alerte si eligibility_changed (même si Claude l'a omis)
    if (
        pea.get("eligibility_changed")
        and "alerte" not in body.lower()
        and "changement" not in body.lower()
    ):
        body = "ALERTE — changement d'éligibilité PEA détecté. " + body
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


def _build_chart_panel(data: dict, date_str: str) -> str:
    """Build 2x2 chart panel HTML (D-11 / UI-SPEC §Chart Panel). Never raises."""
    etf_data = data.get("etf") or {}
    crypto_data = data.get("crypto") or {}
    pea_data = data.get("pea") or {}
    fg_score = (data.get("crypto") or {}).get("fear_greed", {}).get("value")

    try:
        etf_b64 = generate_etf_chart(etf_data, date_str)
    except Exception:
        etf_b64 = None
    etf_cell = (
        f'<img src="data:image/png;base64,{etf_b64}" alt="ETF Chart"'
        f' style="display:block;max-width:100%;height:auto;margin:16px 0;" />'
        if etf_b64 else ETF_FALLBACK
    )

    try:
        btc_hist = (crypto_data.get("coins") or {}).get("bitcoin", {}).get("history", [])
        eth_hist = (crypto_data.get("coins") or {}).get("ethereum", {}).get("history", [])
        crypto_b64 = generate_crypto_sparklines(btc_hist, eth_hist)
    except Exception:
        crypto_b64 = None
    crypto_cell = (
        f'<img src="data:image/png;base64,{crypto_b64}" alt="Crypto Sparklines"'
        f' style="display:block;max-width:100%;height:auto;margin:16px 0;" />'
        if crypto_b64 else CRYPTO_FALLBACK
    )

    try:
        gauge_b64 = generate_fear_greed_gauge(fg_score) if fg_score is not None else None
    except Exception:
        gauge_b64 = None
    gauge_cell = (
        f'<img src="data:image/png;base64,{gauge_b64}" alt="Fear &amp; Greed Gauge"'
        f' style="display:block;max-width:100%;height:auto;margin:16px 0;" />'
        if gauge_b64 else GAUGE_FALLBACK
    )

    try:
        pea_html = generate_pea_table(pea_data)
    except Exception:
        pea_html = None
    pea_cell = pea_html if pea_html else PEA_FALLBACK

    return (
        '<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">'
        '<tr>'
        f'<td class="chart-cell" width="50%" style="vertical-align:top;padding:8px;">{etf_cell}</td>'
        f'<td class="chart-cell" width="50%" style="vertical-align:top;padding:8px;">{crypto_cell}</td>'
        '</tr>'
        '<tr>'
        f'<td class="chart-cell" width="50%" style="vertical-align:top;padding:8px;">{gauge_cell}</td>'
        f'<td class="chart-cell" width="50%" style="vertical-align:top;padding:8px;">{pea_cell}</td>'
        '</tr>'
        '</table>'
    )


def _sections_to_html(sections: list[str]) -> str:
    """Convert Markdown sections list to html_section() card HTML."""
    parts = []
    for md_section in sections:
        lines_s = md_section.strip().split("\n", 2)
        title_s = lines_s[0].lstrip("# ").strip() if lines_s else "Section"
        body_md = lines_s[2].strip() if len(lines_s) > 2 else ""
        body_escaped = _html.escape(body_md)
        p_body = (
            f'<p style="color:#e0e0e0;font-family:\'Courier New\',monospace;'
            f'font-size:14px;line-height:1.6;">{body_escaped}</p>'
        )
        parts.append(html_section(title_s, p_body))
    return "".join(parts)


def build_weekly_report(data: dict, config: Config) -> ReportOutput:
    """
    Construit le Weekly Wrap (~800 mots, 7 sections + tableaux).

    Args:
        data: dict produit par collect_all() (peut être vide ou partiel)
        config: Config avec anthropic_api_key et anthropic_model

    Returns:
        ReportOutput(html_body, plain_text) — toujours 7 sections, jamais lève.
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
        plain_text = "\n".join(sections)
        chart_panel = _build_chart_panel(data, "")
        html_body = chart_panel + _sections_to_html(sections)
        return ReportOutput(html_body=html_body, plain_text=plain_text)
    except Exception as e:
        logger.error("build_weekly_report failed: %s", e)
        fallback_plain = "\n".join(
            build_section(t, "[Section indisponible.]")
            for t in ("Executive Summary", "Macro Watch", "ETF Performance",
                      "Crypto Recap", "PEA Wrap", "News Digest", "Outlook")
        )
        fallback_html = "".join(
            html_section(t, '<p style="color:#e0e0e0;">[Section indisponible.]</p>')
            for t in ("Executive Summary", "Macro Watch", "ETF Performance",
                      "Crypto Recap", "PEA Wrap", "News Digest", "Outlook")
        )
        return ReportOutput(html_body=fallback_html, plain_text=fallback_plain)
