"""
tests/test_weekly.py — Tests TDD pour reporters/weekly.py (build_weekly_report).

RED phase : ces tests doivent échouer (ImportError) tant que reporters/weekly.py
n'est pas implémenté.

Couverture :
  Test 1 — test_build_weekly_report_returns_seven_sections
  Test 2 — test_build_weekly_report_word_count_in_target_range
  Test 3 — test_build_weekly_report_contains_markdown_tables
  Test 4 — test_build_weekly_report_etf_table_lists_all_tickers
  Test 5 — test_build_weekly_report_calls_synthesize_section_at_least_three_times
  Test 6 — test_build_weekly_report_handles_partial_data
  Test 7 — test_build_weekly_report_uses_configured_anthropic_model
  Test 8 — test_build_weekly_report_never_raises
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from config import Config
from db.cache import init_db

# Import à tester — provoquera ImportError (RED gate) jusqu'à l'implémentation
from reporters.weekly import build_weekly_report


# ---------------------------------------------------------------------------
# Données mock (réutilisées depuis tests/test_integration.py)
# ---------------------------------------------------------------------------

MOCK_ETF_OK = {
    "tickers": {
        "SPY": {
            "price": 500.0,
            "prev_close": 495.0,
            "pct_change": 1.01,
            "volume": 1_000_000,
        }
    },
    "alpha_vantage_failed": False,
    "partial": False,
    "source_used": "yfinance_etf",
}

# Fixture ETF étendue pour Test 4 (5 tickers)
MOCK_ETF_EXTENDED = {
    "tickers": {
        "SPY": {"price": 500.0, "prev_close": 495.0, "pct_change": 1.01, "volume": 1_000_000},
        "QQQ": {"price": 420.0, "prev_close": 415.0, "pct_change": 1.20, "volume": 800_000},
        "IWDA.AS": {"price": 90.0, "prev_close": 89.0, "pct_change": 1.12, "volume": 50_000},
        "EIMI.AS": {"price": 35.0, "prev_close": 34.5, "pct_change": 1.45, "volume": 20_000},
        "CSPX.AS": {"price": 55.0, "prev_close": 54.0, "pct_change": 1.85, "volume": 30_000},
    },
    "alpha_vantage_failed": False,
    "partial": False,
    "source_used": "yfinance_etf",
}

MOCK_CRYPTO_OK = {
    "coins": {
        "bitcoin": {
            "price": 60000.0,
            "market_cap": 1_200_000_000_000,
            "volume_24h": 30_000_000_000,
            "pct_change_24h": 2.5,
            "symbol": "BTC",
        }
    },
    "fear_greed": {"value": 65, "label": "Greed"},
    "coingecko_failed": False,
    "fear_greed_failed": False,
    "partial": False,
    "source_used": "coingecko",
}

MOCK_PEA_OK = {
    "prices": {
        "CW8.PA": {
            "price": 350.0,
            "prev_close": 348.0,
            "pct_change": 0.57,
            "volume": 10_000,
        }
    },
    "eligibility": {
        "CW8.PA": {"eligible": True, "isin": "LU1681043599"}
    },
    "eligibility_changed": False,
    "partial": False,
    "source_used": "yfinance_pea",
}

MOCK_MACRO_OK = {
    "series": {
        "DGS10": {
            "value": 4.45,
            "date": "2026-05-09",
            "series_id": "DGS10",
        }
    },
    "fred_failed": False,
    "partial": False,
    "source_used": "fred",
}

MOCK_NEWS_OK = {
    "headlines": [
        {
            "title": "BTC up",
            "url": "https://x.com",
            "source": "Test",
            "published_at": "2026-05-09T06:00:00Z",
        }
    ],
    "count": 1,
    "newsapi_failed": False,
    "scrape_failed": False,
    "partial": False,
    "source_used": "news",
}

MOCK_DATA_FULL = {
    "etf": MOCK_ETF_OK,
    "crypto": MOCK_CRYPTO_OK,
    "pea": MOCK_PEA_OK,
    "macro": MOCK_MACRO_OK,
    "news": MOCK_NEWS_OK,
}


# ---------------------------------------------------------------------------
# Fixture : Config minimale pour les tests
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_config():
    """Crée une Config avec un db_path temporaire initialisé."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path)
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
# Test 1 — Le rapport contient exactement 7 sections ##
# ---------------------------------------------------------------------------


def test_build_weekly_report_returns_seven_sections(tmp_config):
    """
    Avec des données mock complètes et synthesize_section mocké,
    le rapport doit contenir au moins 7 sections Markdown (## ).
    """
    # Retourne ~100 mots pour chaque appel narratif
    mock_narration = " ".join(["mot"] * 100)

    with patch("reporters.weekly.synthesize_section", return_value=mock_narration):
        report = build_weekly_report(MOCK_DATA_FULL, tmp_config)

    # Compter les titres de section ##
    lines = report.splitlines()
    section_lines = [l for l in lines if l.startswith("## ")]
    assert len(section_lines) >= 7, (
        f"Attendu >= 7 sections ##, trouvé {len(section_lines)}: {section_lines}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Le nombre de mots est dans la fourchette 650-1000
# ---------------------------------------------------------------------------


def test_build_weekly_report_word_count_in_target_range(tmp_config):
    """
    Avec synthesize_section retournant ~100 mots par section narrative,
    le compte total doit rester entre 650 et 1000 mots.
    """
    mock_narration = " ".join(["mot"] * 100)

    with patch("reporters.weekly.synthesize_section", return_value=mock_narration):
        report = build_weekly_report(MOCK_DATA_FULL, tmp_config)

    word_count = len(report.split())
    assert 650 <= word_count <= 1000, (
        f"Nombre de mots hors fourchette: {word_count} (attendu 650-1000)"
    )


# ---------------------------------------------------------------------------
# Test 3 — Le rapport contient au moins un tableau Markdown
# ---------------------------------------------------------------------------


def test_build_weekly_report_contains_markdown_tables(tmp_config):
    """
    Le rapport doit contenir au moins UNE ligne avec le pattern |...|...|
    (tableau Markdown pour les données chiffrées).
    """
    mock_narration = " ".join(["mot"] * 100)

    with patch("reporters.weekly.synthesize_section", return_value=mock_narration):
        report = build_weekly_report(MOCK_DATA_FULL, tmp_config)

    has_table = any('|' in line and line.count('|') >= 2 for line in report.splitlines())
    assert has_table, "Le rapport doit contenir au moins un tableau Markdown (lignes |...|...|)"


# ---------------------------------------------------------------------------
# Test 4 — La table ETF liste tous les tickers de MOCK_ETF_EXTENDED
# ---------------------------------------------------------------------------


def test_build_weekly_report_etf_table_lists_all_tickers(tmp_config):
    """
    Avec 5 tickers ETF dans les données, chacun doit apparaître dans le rapport.
    """
    mock_narration = " ".join(["mot"] * 100)
    data = {**MOCK_DATA_FULL, "etf": MOCK_ETF_EXTENDED}

    with patch("reporters.weekly.synthesize_section", return_value=mock_narration):
        report = build_weekly_report(data, tmp_config)

    expected_tickers = ["SPY", "QQQ", "IWDA.AS", "EIMI.AS", "CSPX.AS"]
    for ticker in expected_tickers:
        assert ticker in report, f"Ticker {ticker} absent du rapport ETF"


# ---------------------------------------------------------------------------
# Test 5 — synthesize_section est appelé au moins 3 fois
# ---------------------------------------------------------------------------


def test_build_weekly_report_calls_synthesize_section_at_least_three_times(tmp_config):
    """
    Les sections narratives (Executive Summary, Macro, ETF, Crypto, PEA, Outlook)
    doivent toutes passer par synthesize_section — au minimum 3 appels.
    """
    mock_narration = " ".join(["mot"] * 100)

    with patch("reporters.weekly.synthesize_section", return_value=mock_narration) as mock_synth:
        build_weekly_report(MOCK_DATA_FULL, tmp_config)

    assert mock_synth.call_count >= 3, (
        f"synthesize_section appelé {mock_synth.call_count} fois, attendu >= 3"
    )


# ---------------------------------------------------------------------------
# Test 6 — Dégradation gracieuse avec données PEA partielles
# ---------------------------------------------------------------------------


def test_build_weekly_report_handles_partial_data(tmp_config):
    """
    Si data["pea"] contient source_failed=True, la section PEA Wrap
    doit afficher un message d'indisponibilité sans planter.
    Les autres sections doivent rester normales.
    """
    mock_narration = " ".join(["mot"] * 100)
    data = {
        **MOCK_DATA_FULL,
        "pea": {"error": "connexion échouée", "source_failed": True},
    }

    with patch("reporters.weekly.synthesize_section", return_value=mock_narration):
        report = build_weekly_report(data, tmp_config)

    lines = report.splitlines()
    section_lines = [l for l in lines if l.startswith("## ")]
    assert len(section_lines) >= 7, (
        f"Attendu >= 7 sections même avec PEA partiel, trouvé {len(section_lines)}"
    )

    # La section PEA Wrap doit exister
    assert "## PEA Wrap" in report, "La section '## PEA Wrap' doit exister même en mode dégradé"

    # La section PEA doit indiquer l'indisponibilité
    report_lower = report.lower()
    assert "indisponible" in report_lower or "unavailable" in report_lower or "error" in report_lower, (
        "La section PEA doit indiquer l'indisponibilité des données"
    )


# ---------------------------------------------------------------------------
# Test 7 — Le modèle Anthropic configuré est transmis à synthesize_section
# ---------------------------------------------------------------------------


def test_build_weekly_report_uses_configured_anthropic_model(tmp_config):
    """
    Tous les appels à synthesize_section doivent recevoir la config contenant
    anthropic_model == 'claude-sonnet-4-6' (preuve LLM-02, pas de hardcode).
    """
    mock_narration = " ".join(["mot"] * 100)

    with patch("reporters.weekly.synthesize_section", return_value=mock_narration) as mock_synth:
        build_weekly_report(MOCK_DATA_FULL, tmp_config)

    assert mock_synth.call_count >= 1, "synthesize_section doit être appelé au moins une fois"

    for c in mock_synth.call_args_list:
        # synthesize_section(prompt, config=config, system=...)
        # Vérifier que config est passé et contient le bon modèle
        config_arg = c.kwargs.get("config") or (c.args[1] if len(c.args) > 1 else None)
        assert config_arg is not None, "synthesize_section doit recevoir un argument config"
        assert config_arg.anthropic_model == "claude-sonnet-4-6", (
            f"Modèle hardcodé ou incorrect: {config_arg.anthropic_model}"
        )


# ---------------------------------------------------------------------------
# Test 8 — Dégradation totale : data={} ne lève jamais et retourne 7 sections
# ---------------------------------------------------------------------------


def test_build_weekly_report_never_raises(tmp_config):
    """
    Avec data={} (totalement vide), build_weekly_report ne doit jamais lever
    et doit retourner un rapport avec 7 sections ## .
    """
    with patch("reporters.weekly.synthesize_section", return_value="Section indisponible."):
        try:
            report = build_weekly_report({}, tmp_config)
        except Exception as e:
            pytest.fail(f"build_weekly_report a levé une exception avec data={{}}: {e}")

    lines = report.splitlines()
    section_lines = [l for l in lines if l.startswith("## ")]
    assert len(section_lines) >= 7, (
        f"Avec data={{}}, attendu >= 7 sections ##, trouvé {len(section_lines)}"
    )
