"""
reporters/base.py — Client Claude partagé et helpers de formatage.

Threat model :
  T-03-01 : la clé Anthropic n'est jamais loggée — seuls section_name et str(e)
             apparaissent dans les logs en cas d'échec.
  T-03-02 : dégradation gracieuse — synthesize_section() retourne un fallback
             lisible plutôt que de lever en cas d'échec API.
"""
from __future__ import annotations

import html as _html_stdlib
from typing import NamedTuple

from anthropic import Anthropic
from config import Config
from logging_setup import get_logger

logger = get_logger(__name__)

DEFAULT_MAX_TOKENS = 1024
FALLBACK_TEMPLATE = "[Section indisponible — synthèse Claude temporairement indisponible.]"

# Chart fallback HTML strings (CHART-05 / D-15) — use exactly; from Phase 6 UI-SPEC Copywriting Contract
ETF_FALLBACK    = '<p style="color:#888;font-style:italic;">[Graphique ETF indisponible]</p>'
CRYPTO_FALLBACK = '<p style="color:#888;font-style:italic;">[Graphique crypto indisponible]</p>'
GAUGE_FALLBACK  = '<p style="color:#888;font-style:italic;">[Gauge Fear &amp; Greed indisponible]</p>'
PEA_FALLBACK    = '<p style="color:#888;font-style:italic;">[Tableau PEA indisponible]</p>'


class ReportOutput(NamedTuple):
    """Dual output from reporter build functions (D-02).

    html_body: Rich HTML string — chart <img> tags + PEA table + section <div> cards.
               Passed to Jinja2 template with | safe filter.
    plain_text: Unchanged Markdown narrative — fed to MIME text/plain part (D-05).
    """
    html_body: str
    plain_text: str


def synthesize_section(
    prompt: str,
    config: Config,
    system: str = "",
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """
    Appelle l'API Claude et retourne la chaîne narrative générée.

    Args:
        prompt: contenu utilisateur (données structurées + consigne narrative)
        config: Config avec anthropic_api_key et anthropic_model
        system: prompt système optionnel (rôle, ton, contraintes)
        max_tokens: budget tokens (défaut 1024)

    Returns:
        str non vide — soit la narration Claude, soit FALLBACK_TEMPLATE en cas d'échec.

    Ne lève jamais — T-03-02.
    """
    try:
        client = Anthropic(api_key=config.anthropic_api_key)
        kwargs = {
            "model": config.anthropic_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)
        if not response.content:
            logger.warning(
                "Claude returned empty content list for section (stop_reason=%s)",
                response.stop_reason,
            )
            return FALLBACK_TEMPLATE
        return response.content[0].text
    except Exception as e:
        # T-03-01 : on logue le type d'erreur, JAMAIS la clé API
        logger.warning("Claude synthesis failed: %s", type(e).__name__)
        return FALLBACK_TEMPLATE


def build_section(title: str, body: str) -> str:
    """Assemble une section au format Markdown : '## {title}\\n\\n{body}\\n'."""
    return f"## {title}\n\n{body}\n"


def html_section(title: str, body_html: str) -> str:
    """Assemble une section HTML dark-mode card (D-10, UI-SPEC §Narrative Sections).

    Args:
        title: section title — HTML-escaped inside this function (XSS prevention)
        body_html: pre-built HTML content — caller is responsible for escaping

    Returns:
        str: <div> card with background:#111111, orange h2 heading, Courier New font
    """
    safe_title = _html_stdlib.escape(title)
    return (
        '<div style="background:#111111;border:1px solid #2a2a2a;'
        'padding:16px;margin-bottom:8px;">'
        f'<h2 style="color:#FF6B35;font-family:\'Courier New\',monospace;'
        f'font-size:18px;font-weight:700;margin-top:0;margin-bottom:12px;'
        f'line-height:1.2;">{safe_title}</h2>'
        f'{body_html}'
        '</div>'
    )


def format_pct(value: float) -> str:
    """Formate un pourcentage avec signe explicite : 1.234 -> '+1.23%', -0.5 -> '-0.50%'."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def format_currency(value: float, symbol: str = "$") -> str:
    """Formate un montant en devise : 60000.0 -> '$60,000'."""
    return f"{symbol}{value:,.0f}"
