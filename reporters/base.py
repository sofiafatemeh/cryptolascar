"""
reporters/base.py — Client Claude partagé et helpers de formatage.

Threat model :
  T-03-01 : la clé Anthropic n'est jamais loggée — seuls section_name et str(e)
             apparaissent dans les logs en cas d'échec.
  T-03-02 : dégradation gracieuse — synthesize_section() retourne un fallback
             lisible plutôt que de lever en cas d'échec API.
"""
from __future__ import annotations

from anthropic import Anthropic
from config import Config
from logging_setup import get_logger

logger = get_logger(__name__)

DEFAULT_MAX_TOKENS = 1024
FALLBACK_TEMPLATE = "[Section indisponible — synthèse Claude temporairement indisponible.]"


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
        return response.content[0].text
    except Exception as e:
        # T-03-01 : on logue le type d'erreur, JAMAIS la clé API
        logger.warning("Claude synthesis failed: %s", e)
        return FALLBACK_TEMPLATE


def build_section(title: str, body: str) -> str:
    """Assemble une section au format Markdown : '## {title}\\n\\n{body}\\n'."""
    return f"## {title}\n\n{body}\n"


def format_pct(value: float) -> str:
    """Formate un pourcentage avec signe explicite : 1.234 -> '+1.23%', -0.5 -> '-0.50%'."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def format_currency(value: float, symbol: str = "$") -> str:
    """Formate un montant en devise : 60000.0 -> '$60,000'."""
    return f"{symbol}{value:,.0f}"
