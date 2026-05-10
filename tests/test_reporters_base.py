"""
tests/test_reporters_base.py — Tests TDD pour reporters/base.py (client Claude partagé).

RED phase : ces tests doivent échouer (ImportError) tant que reporters/base.py
n'est pas implémenté.

Couverture :
  Test 1 — synthesize_section appelle Claude avec le modèle lu depuis Config
  Test 2 — synthesize_section retourne le texte du contenu Claude
  Test 3 — synthesize_section retourne un fallback gracieux si l'API échoue
  Test 4 — synthesize_section ne logue jamais la clé API (T-03-01)
  Test 5 — format_pct et format_currency respectent les contrats de formatage
  Test 6 — build_section assemble titre en-tête et corps
"""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config import Config

# Import à tester — provoquera ImportError (RED gate) jusqu'à l'implémentation
from reporters.base import synthesize_section, build_section, format_pct, format_currency


# ---------------------------------------------------------------------------
# Fixture : Config minimale avec clé Anthropic de test
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_config():
    """Crée une Config minimale pour les tests reporters."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    cfg = Config(
        smtp_host="localhost",
        smtp_port=587,
        smtp_user="user@example.com",
        smtp_password="password",
        recipient_list=["dest@example.com"],
        anthropic_api_key="test-anthropic-key",
        anthropic_model="claude-sonnet-4-6",
        coingecko_api_key="",
        alpha_vantage_key="",
        fred_api_key="",
        newsapi_key="",
        db_path=Path(db_path),
        log_level="DEBUG",
        log_file="",
    )
    yield cfg
    os.unlink(db_path)


# ---------------------------------------------------------------------------
# Test 1 — synthesize_section appelle Claude avec le modèle lu depuis Config
# ---------------------------------------------------------------------------

def test_synthesize_section_calls_claude_with_configured_model(tmp_config):
    """
    synthesize_section doit appeler messages.create avec model=cfg.anthropic_model
    (valeur lue depuis Config, pas une constante hardcodée).
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Narrative text")]
    mock_client.messages.create.return_value = mock_response

    with patch("reporters.base.Anthropic", return_value=mock_client):
        result = synthesize_section("test prompt", config=tmp_config)

    # Vérifier que messages.create a été appelé avec le modèle depuis Config
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == tmp_config.anthropic_model


# ---------------------------------------------------------------------------
# Test 2 — synthesize_section retourne le texte généré par Claude
# ---------------------------------------------------------------------------

def test_synthesize_section_returns_text_content(tmp_config):
    """
    synthesize_section doit retourner exactement la chaîne response.content[0].text.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Synthesized narrative")]
    mock_client.messages.create.return_value = mock_response

    with patch("reporters.base.Anthropic", return_value=mock_client):
        result = synthesize_section("test prompt", config=tmp_config)

    assert result == "Synthesized narrative"


# ---------------------------------------------------------------------------
# Test 3 — Dégradation gracieuse si l'API Claude échoue
# ---------------------------------------------------------------------------

def test_synthesize_section_graceful_fallback_on_api_failure(tmp_config):
    """
    Si l'API Claude échoue, synthesize_section doit retourner un fallback non vide
    contenant 'indisponible', sans lever d'exception (T-03-02).
    """
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API down")

    with patch("reporters.base.Anthropic", return_value=mock_client):
        result = synthesize_section("test prompt", config=tmp_config)

    assert isinstance(result, str)
    assert len(result) > 0
    assert "indisponible" in result.lower()


# ---------------------------------------------------------------------------
# Test 4 — La clé API n'apparaît jamais dans les logs (T-03-01)
# ---------------------------------------------------------------------------

def test_synthesize_section_never_logs_api_key(tmp_config, caplog):
    """
    Même en cas d'échec API, la clé anthropic_api_key ne doit jamais
    apparaître dans les logs (T-03-01).
    """
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("network error")

    with patch("reporters.base.Anthropic", return_value=mock_client):
        with caplog.at_level(logging.DEBUG, logger="reporters.base"):
            synthesize_section("test prompt", config=tmp_config)

    assert tmp_config.anthropic_api_key not in caplog.text


# ---------------------------------------------------------------------------
# Test 5 — format_pct et format_currency respectent les contrats
# ---------------------------------------------------------------------------

def test_format_pct_format_currency():
    """
    format_pct : signe explicite + 2 décimales
    format_currency : symbole $ + séparateur milliers + pas de décimales
    """
    assert format_pct(1.234) == "+1.23%"
    assert format_pct(-0.5) == "-0.50%"
    assert format_pct(0.0) == "+0.00%"
    assert format_currency(60000.0) == "$60,000"
    assert format_currency(1000000.0) == "$1,000,000"


# ---------------------------------------------------------------------------
# Test 6 — build_section assemble le titre et le corps
# ---------------------------------------------------------------------------

def test_build_section_assembles_header_and_body():
    """
    build_section("Title", "Body text") doit retourner une chaîne contenant
    '## Title' et 'Body text'.
    """
    result = build_section("Macro Snapshot", "Body text")
    assert "## Macro Snapshot" in result
    assert "Body text" in result
