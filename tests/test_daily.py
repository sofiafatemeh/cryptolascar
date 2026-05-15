"""
tests/test_daily.py — Tests TDD pour reporters/daily.py (build_daily_report).

RED phase : ces tests doivent échouer (ImportError) tant que reporters/daily.py
n'est pas implémenté.

Couverture :
  Test 1 — Retourne une chaîne avec les 6 titres de section exacts
  Test 2 — Compte de mots dans la fourchette cible [250, 400]
  Test 3 — synthesize_section est appelé au moins une fois (pas de texte hardcodé)
  Test 4 — La Config passée à synthesize_section a le bon modèle (LLM-02)
  Test 5 — Dégradation gracieuse si synthesize_section retourne FALLBACK_TEMPLATE
  Test 6 — Gestion des subsections manquantes (source_failed)
  Test 7 — PEA Alert contient un mot-clé d'alerte si eligibility_changed=True
"""
from __future__ import annotations

import copy
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from config import Config
from db.cache import init_db

# Import à tester — provoquera ImportError (RED gate) jusqu'à l'implémentation
from reporters.daily import build_daily_report
from reporters.base import FALLBACK_TEMPLATE

# ---------------------------------------------------------------------------
# Fixtures de données — reprises des mocks de test_integration.py
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

MOCK_META = {
    "sources_ok": ["etf", "crypto", "pea", "macro", "news"],
    "sources_failed": [],
    "collected_at": "2026-05-09T06:00:00Z",
}


# ---------------------------------------------------------------------------
# Fixture : Config avec DB temporaire initialisée
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_config():
    """Crée une Config avec db_path temporaire et tables initialisées."""
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


@pytest.fixture
def data_complete():
    """Dict de données complet combinant les 5 mocks + _meta."""
    return {
        "etf": copy.deepcopy(MOCK_ETF_OK),
        "crypto": copy.deepcopy(MOCK_CRYPTO_OK),
        "pea": copy.deepcopy(MOCK_PEA_OK),
        "macro": copy.deepcopy(MOCK_MACRO_OK),
        "news": copy.deepcopy(MOCK_NEWS_OK),
        "_meta": copy.deepcopy(MOCK_META),
    }


# ---------------------------------------------------------------------------
# Test 1 — Retourne une chaîne avec les 6 titres de section exacts
# ---------------------------------------------------------------------------


def test_build_daily_report_returns_string_with_six_sections(tmp_config, data_complete):
    """
    Avec synthesize_section mocké, build_daily_report doit retourner une chaîne
    contenant exactement les 6 titres de section définis par REPT-01.
    """
    with patch("reporters.daily.synthesize_section", return_value="NARRATION OK"), \
         patch("reporters.daily.generate_etf_chart", return_value=None), \
         patch("reporters.daily.generate_crypto_sparklines", return_value=None), \
         patch("reporters.daily.generate_fear_greed_gauge", return_value=None), \
         patch("reporters.daily.generate_pea_table", return_value=None):
        result = build_daily_report(data_complete, tmp_config)

    report = result.plain_text
    assert isinstance(report, str), "build_daily_report doit retourner un ReportOutput avec plain_text str"

    expected_sections = [
        "## Macro Snapshot",
        "## ETF Radar",
        "## Crypto Pulse",
        "## PEA Alert",
        "## News Feed",
        "## One Signal",
    ]
    for section_title in expected_sections:
        assert section_title in report, (
            f"Section '{section_title}' absente du rapport.\n"
            f"Rapport produit:\n{report}"
        )


# ---------------------------------------------------------------------------
# Test 2 — Compte de mots dans la fourchette cible [250, 400]
# ---------------------------------------------------------------------------


def test_build_daily_report_word_count_in_target_range(tmp_config, data_complete):
    """
    Le rapport doit avoir entre 250 et 400 mots (cible ~300).
    Le mock retourne ~50 mots par section pour atteindre la fourchette.
    """
    filler_50_words = (
        "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod "
        "tempor incididunt ut labore et dolore magna aliqua ut enim ad minim veniam "
        "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo "
        "consequat duis aute irure dolor reprehenderit voluptate velit esse cillum "
        "dolore eu fugiat nulla pariatur excepteur sint occaecat cupidatat non proident"
    )

    with patch("reporters.daily.synthesize_section", return_value=filler_50_words), \
         patch("reporters.daily.generate_etf_chart", return_value=None), \
         patch("reporters.daily.generate_crypto_sparklines", return_value=None), \
         patch("reporters.daily.generate_fear_greed_gauge", return_value=None), \
         patch("reporters.daily.generate_pea_table", return_value=None):
        result = build_daily_report(data_complete, tmp_config)

    report = result.plain_text
    word_count = len(report.split())
    assert 250 <= word_count <= 400, (
        f"Compte de mots hors fourchette [250, 400] : {word_count} mots.\n"
        f"Rapport produit:\n{report}"
    )


# ---------------------------------------------------------------------------
# Test 3 — synthesize_section est appelé au moins une fois
# ---------------------------------------------------------------------------


def test_build_daily_report_calls_synthesize_section(tmp_config, data_complete):
    """
    synthesize_section doit être appelé au moins une fois — preuve que la narration
    passe par le client Claude et non du texte hardcodé.
    """
    with patch("reporters.daily.synthesize_section", return_value="NARRATION OK") as mock_synth:
        build_daily_report(data_complete, tmp_config)

    assert mock_synth.call_count >= 1, (
        f"synthesize_section doit être appelé au moins 1 fois, "
        f"got {mock_synth.call_count} appels"
    )


# ---------------------------------------------------------------------------
# Test 4 — La Config passée à synthesize_section a le bon modèle (LLM-02)
# ---------------------------------------------------------------------------


def test_build_daily_report_uses_configured_model_via_config(tmp_config, data_complete):
    """
    La Config passée à synthesize_section doit avoir anthropic_model='claude-sonnet-4-6'
    (preuve LLM-02 : le modèle est configurable, jamais hardcodé dans daily.py).
    """
    with patch("reporters.daily.synthesize_section", return_value="NARRATION OK") as mock_synth:
        build_daily_report(data_complete, tmp_config)

    assert mock_synth.call_count >= 1, "synthesize_section non appelé"

    # Vérifier chaque appel : la config passée doit avoir le bon modèle
    for call in mock_synth.call_args_list:
        # synthesize_section(prompt, config=config, system=...) — config en kwarg
        kwargs = call.kwargs
        args = call.args
        # config peut être en position 1 (arg positionnel) ou en kwarg
        if "config" in kwargs:
            cfg_passed = kwargs["config"]
        elif len(args) >= 2:
            cfg_passed = args[1]
        else:
            pytest.fail(f"config non trouvé dans les args de l'appel: {call}")

        assert cfg_passed.anthropic_model == "claude-sonnet-4-6", (
            f"anthropic_model attendu 'claude-sonnet-4-6', got '{cfg_passed.anthropic_model}'"
        )


# ---------------------------------------------------------------------------
# Test 5 — Dégradation gracieuse si synthesize_section retourne FALLBACK_TEMPLATE
# ---------------------------------------------------------------------------


def test_build_daily_report_graceful_when_synthesize_returns_fallback(tmp_config, data_complete):
    """
    Si synthesize_section retourne FALLBACK_TEMPLATE (API Claude en échec),
    build_daily_report ne doit pas lever d'exception et doit retourner
    un rapport avec les 6 sections structurées.
    """
    with patch("reporters.daily.synthesize_section", return_value=FALLBACK_TEMPLATE), \
         patch("reporters.daily.generate_etf_chart", return_value=None), \
         patch("reporters.daily.generate_crypto_sparklines", return_value=None), \
         patch("reporters.daily.generate_fear_greed_gauge", return_value=None), \
         patch("reporters.daily.generate_pea_table", return_value=None):
        result = build_daily_report(data_complete, tmp_config)

    report = result.plain_text
    assert isinstance(report, str), "plain_text doit être une chaîne"

    expected_sections = [
        "## Macro Snapshot",
        "## ETF Radar",
        "## Crypto Pulse",
        "## PEA Alert",
        "## News Feed",
        "## One Signal",
    ]
    for section_title in expected_sections:
        assert section_title in report, (
            f"Section '{section_title}' absente même en mode fallback.\n"
            f"Rapport produit:\n{report}"
        )


# ---------------------------------------------------------------------------
# Test 6 — Gestion des subsections manquantes (source_failed)
# ---------------------------------------------------------------------------


def test_build_daily_report_handles_missing_subsections(tmp_config, data_complete):
    """
    Quand data['macro'] indique une source en échec (source_failed=True),
    la section Macro Snapshot doit quand même apparaître avec un texte
    indiquant l'indisponibilité des données. Les autres sections restent normales.
    """
    data_complete["macro"] = {"error": "FRED down", "source_failed": True}

    with patch("reporters.daily.synthesize_section", return_value="NARRATION OK"), \
         patch("reporters.daily.generate_etf_chart", return_value=None), \
         patch("reporters.daily.generate_crypto_sparklines", return_value=None), \
         patch("reporters.daily.generate_fear_greed_gauge", return_value=None), \
         patch("reporters.daily.generate_pea_table", return_value=None):
        result = build_daily_report(data_complete, tmp_config)

    report = result.plain_text
    assert "## Macro Snapshot" in report, (
        "La section Macro Snapshot doit être présente même si source_failed=True"
    )

    # Le texte doit indiquer l'indisponibilité
    macro_section_start = report.find("## Macro Snapshot")
    next_section = report.find("## ETF Radar")
    macro_content = report[macro_section_start:next_section] if next_section != -1 else report[macro_section_start:]
    assert "indisponible" in macro_content.lower() or "échec" in macro_content.lower(), (
        f"La section Macro Snapshot doit indiquer l'indisponibilité. Contenu:\n{macro_content}"
    )

    # Les autres sections sont présentes et normales
    for section in ("## ETF Radar", "## Crypto Pulse", "## PEA Alert", "## News Feed", "## One Signal"):
        assert section in report, f"Section '{section}' manquante malgré macro en échec"


# ---------------------------------------------------------------------------
# Test 7 — PEA Alert contient un mot-clé d'alerte si eligibility_changed=True
# ---------------------------------------------------------------------------


def test_build_daily_report_includes_pea_alert_when_eligibility_changed(tmp_config, data_complete):
    """
    Si data['pea']['eligibility_changed'] = True, la section PEA Alert doit
    contenir le mot-clé 'alerte' ou 'changement' (signal explicite à l'utilisateur).
    """
    data_complete["pea"]["eligibility_changed"] = True

    with patch("reporters.daily.synthesize_section", return_value="NARRATION OK"), \
         patch("reporters.daily.generate_etf_chart", return_value=None), \
         patch("reporters.daily.generate_crypto_sparklines", return_value=None), \
         patch("reporters.daily.generate_fear_greed_gauge", return_value=None), \
         patch("reporters.daily.generate_pea_table", return_value=None):
        result = build_daily_report(data_complete, tmp_config)

    report = result.plain_text

    assert "## PEA Alert" in report, "Section PEA Alert absente"

    # Extraire le contenu de la section PEA Alert
    pea_start = report.find("## PEA Alert")
    next_section = report.find("## News Feed")
    pea_content = report[pea_start:next_section] if next_section != -1 else report[pea_start:]

    assert "alerte" in pea_content.lower() or "changement" in pea_content.lower(), (
        f"La section PEA Alert doit contenir 'alerte' ou 'changement' quand "
        f"eligibility_changed=True. Contenu PEA:\n{pea_content}"
    )
