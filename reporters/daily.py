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

from config import Config
from reporters.base import build_section, format_currency, format_pct, synthesize_section
from logging_setup import get_logger

logger = get_logger(__name__)

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
    fg = crypto.get("fear_greed", {})
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


def build_daily_report(data: dict, config: Config) -> str:
    """
    Construit le Daily Report (~300 mots, 6 sections).

    Sections dans l'ordre REPT-01 :
      1. Macro Snapshot — taux & inflation
      2. ETF Radar      — performance ETFs
      3. Crypto Pulse   — top coins + Fear & Greed
      4. PEA Alert      — PEA France + alerte éligibilité
      5. News Feed      — top headlines
      6. One Signal     — point d'attention du jour

    Args:
        data: dict produit par collect_all() — clés etf/crypto/pea/macro/news/_meta.
              Chaque sous-dict peut avoir source_failed=True (dégradation gracieuse).
        config: Config (utilisé pour anthropic_model et anthropic_api_key).
                Le modèle n'est JAMAIS hardcodé dans ce module (LLM-02).

    Returns:
        Rapport Markdown complet (chaîne) — toujours 6 sections, jamais lève.

    Ne lève jamais (T-03-06) — filet de sécurité global en cas d'erreur inattendue.
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
        return "\n".join(sections)
    except Exception as e:
        # T-03-07 : on logue uniquement le message d'erreur, JAMAIS la config (clé API)
        logger.error("build_daily_report failed: %s", e)
        # Filet de sécurité — retourner les 6 titres en mode dégradé total
        return "\n".join(
            build_section(t, "[Section indisponible.]")
            for t in (
                "Macro Snapshot",
                "ETF Radar",
                "Crypto Pulse",
                "PEA Alert",
                "News Feed",
                "One Signal",
            )
        )
