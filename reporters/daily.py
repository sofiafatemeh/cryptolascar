"""
reporters/daily.py — Daily Report builder (~300 mots, 6 sections).

Sections (ordre figé par REPT-01) :
  1. Macro Snapshot   — taux & inflation
  2. ETF Radar        — performance ETFs
  3. Crypto Pulse     — top coins + Fear & Greed
  4. PEA Alert        — PEA France + alerte éligibilité
  5. News Feed        — top headlines
  6. One Signal       — point d'attention du jour

Threat model :
  T-03-06 : dégradation gracieuse — chaque sous-fonction _xxx_section
             checke source_failed et retourne un message "indisponible"
             plutôt que de planter.
  T-03-07 : les logs n'exposent jamais la config complète (clé API).
"""
from __future__ import annotations

import datetime as _dt
import html as _html

from config import Config
from reporters.base import (
    build_section, format_currency, format_pct, synthesize_section,
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

_PEA_NAMES = {
    "^FCHI":    "CAC 40",
    "^SBF120":  "SBF 120",
    "CW8.PA":   "Amundi MSCI World",
    "PAEEM.PA": "Amundi MSCI EM",
    "PANX.PA":  "Amundi Nasdaq-100",
}
_PEA_ELIGIBILITY = {
    "CW8.PA":   True,
    "PAEEM.PA": True,
    "PANX.PA":  True,
    "^FCHI":    None,
    "^SBF120":  None,
}

DAILY_SYSTEM_PROMPT = (
    "Tu es un analyste financier français. Réponds en français, ton sobre et factuel, "
    "synthèse d'environ 50 mots par section. Pas de conseil financier explicite."
)


def _macro_section(data: dict, config: Config) -> str:
    """Section 1 — Macro Snapshot : taux DGS10/DGS2, inflation CPI, masse M2."""
    macro = data.get("macro") or {}
    if macro.get("source_failed"):
        return build_section(
            "Macro Snapshot",
            "Données macro indisponibles ce matin (source FRED en échec).",
        )
    series = macro.get("series", {})
    facts = []
    for key in ("DGS10", "DGS2", "CPIAUCSL", "M2SL"):
        s = series.get(key)
        if s and s.get("value") is not None:
            facts.append(f"{key}={s['value']}")
    prompt = (
        f"Résume en ~50 mots la situation macro ce matin. "
        f"Données: {', '.join(facts) or 'aucune donnée'}."
    )
    body = synthesize_section(prompt, config=config, system=DAILY_SYSTEM_PROMPT)
    return build_section("Macro Snapshot", body)


def _etf_section(data: dict, config: Config) -> str:
    """Section 2 — ETF Radar : prix et variations des ETFs principaux."""
    etf = data.get("etf") or {}
    if etf.get("source_failed"):
        return build_section("ETF Radar", "Données ETF indisponibles ce matin.")
    tickers = etf.get("tickers", {})
    facts = []
    for sym, t in tickers.items():
        if t.get("price") is not None and t.get("pct_change") is not None:
            facts.append(
                f"{sym} {format_currency(t['price'])} ({format_pct(t['pct_change'])})"
            )
    prompt = (
        f"Résume en ~50 mots la performance ETFs. "
        f"Données: {', '.join(facts) or 'aucune donnée'}."
    )
    body = synthesize_section(prompt, config=config, system=DAILY_SYSTEM_PROMPT)
    return build_section("ETF Radar", body)


def _crypto_section(data: dict, config: Config) -> str:
    """Section 3 — Crypto Pulse : top coins + Fear & Greed index."""
    crypto = data.get("crypto") or {}
    if crypto.get("source_failed"):
        return build_section("Crypto Pulse", "Données crypto indisponibles ce matin.")
    coins = crypto.get("coins", {})
    fg = crypto.get("fear_greed") or {}
    facts = []
    for cid, c in coins.items():
        if c.get("price") is not None and c.get("pct_change_24h") is not None:
            facts.append(
                f"{c.get('symbol', cid)} {format_currency(c['price'])} "
                f"({format_pct(c['pct_change_24h'])})"
            )
    fg_label = fg.get("label", "n/a")
    prompt = (
        f"Résume en ~50 mots la dynamique crypto. "
        f"Fear & Greed: {fg_label}. "
        f"Données: {', '.join(facts) or 'aucune'}."
    )
    body = synthesize_section(prompt, config=config, system=DAILY_SYSTEM_PROMPT)
    return build_section("Crypto Pulse", body)


def _pea_section(data: dict, config: Config) -> str:
    """Section 4 — PEA Alert : variations PEA + alerte si eligibility_changed."""
    pea = data.get("pea") or {}
    if pea.get("source_failed"):
        return build_section("PEA Alert", "Données PEA indisponibles ce matin.")
    prices = pea.get("prices", {})
    eligibility_changed = pea.get("eligibility_changed", False)
    facts = []
    for sym, p in prices.items():
        if p.get("price") is not None and p.get("pct_change") is not None:
            facts.append(
                f"{sym} {format_currency(p['price'], symbol='€')} "
                f"({format_pct(p['pct_change'])})"
            )
    alert = "ALERTE: changement d'éligibilité PEA détecté." if eligibility_changed else ""
    prompt = (
        f"Résume en ~50 mots la situation PEA France. "
        f"{alert} Données: {', '.join(facts) or 'aucune'}."
    )
    body = synthesize_section(prompt, config=config, system=DAILY_SYSTEM_PROMPT)
    # T-03-06 : garantir le mot-clé 'alerte' ou 'changement' si eligibility_changed
    # même si Claude ne l'a pas inclus dans sa narration (preuve test 7)
    if (
        eligibility_changed
        and "alerte" not in body.lower()
        and "changement" not in body.lower()
    ):
        body = "ALERTE — changement d'éligibilité PEA détecté. " + body
    return build_section("PEA Alert", body)


def _news_section(data: dict, config: Config) -> str:
    """Section 5 — News Feed : top 5-7 titres financiers."""
    news = data.get("news") or {}
    if news.get("source_failed"):
        return build_section("News Feed", "Headlines indisponibles ce matin.")
    headlines = news.get("headlines", [])[:7]
    if not headlines:
        return build_section("News Feed", "Aucun titre récent disponible.")
    bullets = "\n".join(
        f"- {h.get('title', 'titre manquant')} ({h.get('source', '?')})"
        for h in headlines
    )
    prompt = (
        f"Liste structurée des titres financiers du matin :\n{bullets}\n"
        f"Résume en ~40 mots les 2-3 thèmes dominants."
    )
    body = synthesize_section(prompt, config=config, system=DAILY_SYSTEM_PROMPT)
    return build_section("News Feed", f"{bullets}\n\n{body}")


def _one_signal_section(data: dict, config: Config) -> str:
    """Section 6 — One Signal : point d'attention principal du jour."""
    meta = data.get("_meta", {})
    prompt = (
        "Identifie LE point d'attention principal du matin pour un investisseur particulier "
        "français exposé ETF/crypto/PEA. Réponse en ~40 mots, ton analyste, "
        "sans conseil financier explicite. "
        f"Sources OK: {meta.get('sources_ok', [])}. "
        f"Sources failed: {meta.get('sources_failed', [])}."
    )
    body = synthesize_section(prompt, config=config, system=DAILY_SYSTEM_PROMPT)
    return build_section("One Signal", body)


def _build_chart_panel(data: dict, date_str: str) -> str:
    """Build 2x2 chart panel HTML (D-11 / UI-SPEC §Chart Panel). Never raises."""
    crypto_data = data.get("crypto") or {}
    # CHART-03: coerce None fear_greed to {} before .get("value") to avoid AttributeError
    fg_score = ((data.get("crypto") or {}).get("fear_greed") or {}).get("value")

    # CHART-01: transform collector ETF dict to {ticker: {"1d": float, "1w": float}}
    etf_raw = data.get("etf") or {}
    etf_chart_data = {
        sym: {
            "1d": t.get("pct_change") or 0.0,
            "1w": t.get("pct_change_1w") or 0.0,
        }
        for sym, t in (etf_raw.get("tickers") or {}).items()
        if t.get("pct_change") is not None
    }

    try:
        etf_b64 = generate_etf_chart(etf_chart_data, date_str)
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

    # CHART-04: transform collector PEA dict to list[dict] with standard keys
    pea_raw = data.get("pea") or {}
    pea_list = [
        {
            "ticker":       sym,
            "name":         _PEA_NAMES.get(sym, sym),
            "price":        t.get("price"),
            "change_1d":    t.get("pct_change"),
            "change_1w":    t.get("pct_change_1w"),
            "pea_eligible": _PEA_ELIGIBILITY.get(sym),
        }
        for sym, t in (pea_raw.get("prices") or {}).items()
        if t.get("price") is not None
    ]

    try:
        pea_html = generate_pea_table(pea_list)
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
            f'font-size:14px;line-height:1.6;white-space:pre-wrap;">{body_escaped}</p>'
        )
        parts.append(html_section(title_s, p_body))
    return "".join(parts)


def build_daily_report(data: dict, config: Config) -> ReportOutput:
    """
    Construit le Daily Report (~300 mots, 6 sections).

    Returns:
        ReportOutput(html_body, plain_text) — toujours 6 sections, jamais lève.
    """
    try:
        sections = [
            _macro_section(data, config),
            _etf_section(data, config),
            _crypto_section(data, config),
            _pea_section(data, config),
            _news_section(data, config),
            _one_signal_section(data, config),
        ]
        plain_text = "\n".join(sections)
        chart_panel = _build_chart_panel(data, _dt.date.today().strftime("%Y-%m-%d"))
        html_body = chart_panel + _sections_to_html(sections)
        return ReportOutput(html_body=html_body, plain_text=plain_text)
    except Exception as e:
        # T-03-07 : on logue uniquement le message d'erreur, JAMAIS la config (clé API)
        logger.error("build_daily_report failed: %s", e)
        fallback_plain = "\n".join(
            build_section(t, "[Section indisponible.]")
            for t in ("Macro Snapshot", "ETF Radar", "Crypto Pulse",
                      "PEA Alert", "News Feed", "One Signal")
        )
        fallback_html = "".join(
            html_section(t, '<p style="color:#e0e0e0;">[Section indisponible.]</p>')
            for t in ("Macro Snapshot", "ETF Radar", "Crypto Pulse",
                      "PEA Alert", "News Feed", "One Signal")
        )
        return ReportOutput(html_body=fallback_html, plain_text=fallback_plain)
