"""
tests/test_monthly.py — Tests TDD pour reporters/monthly.py (build_monthly_report).

RED phase : ces tests doivent échouer (ImportError) tant que reporters/monthly.py
n'est pas implémenté.

Couverture (REPT-03) :
  Test 1 — Retourne une chaîne avec les 7 titres de section exacts
  Test 2 — Compte de mots dans la fourchette cible [1700, 2300]
  Test 3 — Contient au moins 2 tableaux Markdown distincts
  Test 4 — synthesize_section est appelé au moins 4 fois
  Test 5 — La Config passée à synthesize_section a le bon modèle
  Test 6 — Dégradation gracieuse si data = {} (pas d'exception, 7 sections)
  Test 7 — Section PEA Monthly contient alerte si eligibility_changed=True
"""
from __future__ import annotations

import copy
import os
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from config import Config
from db.cache import init_db

# Import à tester — provoquera ImportError (RED gate) jusqu'à l'implémentation
from reporters.monthly import build_monthly_report

# ---------------------------------------------------------------------------
# Données mock — reprises depuis test_daily.py / test_integration.py
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
            "title": "BTC dépasse 60 000 USD",
            "url": "https://x.com",
            "source": "CoinDesk",
            "published_at": "2026-05-09T06:00:00Z",
        },
        {
            "title": "La Fed maintient ses taux",
            "url": "https://y.com",
            "source": "Bloomberg",
            "published_at": "2026-05-09T07:00:00Z",
        },
    ],
    "count": 2,
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
# Test 1 — Retourne une chaîne avec les 7 titres de section exacts
# ---------------------------------------------------------------------------


def test_build_monthly_report_returns_seven_sections(tmp_config, data_complete):
    """
    Avec synthesize_section mocké, build_monthly_report doit retourner un ReportOutput
    contenant exactement les 7 titres de section définis par REPT-03 dans plain_text.
    """
    with patch("reporters.monthly.synthesize_section", return_value="NARRATION OK"):
        result = build_monthly_report(data_complete, tmp_config)

    report = result.plain_text
    assert isinstance(report, str), "plain_text doit être une chaîne"

    expected_sections = [
        "## Month in Review",
        "## Macro Backdrop",
        "## ETF Monthly Performance",
        "## Crypto Monthly",
        "## PEA Monthly",
        "## News & Themes",
        "## Forward Look",
    ]
    for section_title in expected_sections:
        assert section_title in report, (
            f"Section '{section_title}' absente du rapport mensuel.\n"
            f"Rapport produit:\n{report}"
        )


# ---------------------------------------------------------------------------
# Test 2 — Compte de mots dans la fourchette cible [1700, 2300]
# ---------------------------------------------------------------------------


def test_build_monthly_report_word_count_in_target_range(tmp_config, data_complete):
    """
    Le rapport mensuel doit avoir entre 1700 et 2300 mots (cible ~2000).
    Le mock retourne ~250 mots par section narrative pour atteindre la fourchette.
    """
    filler_250_words = " ".join(["lorem"] * 250)

    with patch("reporters.monthly.synthesize_section", return_value=filler_250_words):
        result = build_monthly_report(data_complete, tmp_config)

    report = result.plain_text
    word_count = len(report.split())
    assert 1700 <= word_count <= 2300, (
        f"Compte de mots hors fourchette [1700, 2300] : {word_count} mots.\n"
        f"Rapport produit (extrait):\n{report[:500]}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Contient au moins 2 tableaux Markdown distincts
# ---------------------------------------------------------------------------


def test_build_monthly_report_contains_at_least_two_tables(tmp_config, data_complete):
    """
    Le rapport mensuel doit contenir au moins 2 tableaux Markdown distincts.
    Un tableau est détecté comme un bloc de lignes consécutives commençant par '|'.
    """
    with patch("reporters.monthly.synthesize_section", return_value="NARRATION OK"):
        result = build_monthly_report(data_complete, tmp_config)

    report = result.plain_text
    # Compter les blocs de lignes consécutives contenant '|...|...|'
    lines = report.split("\n")
    table_count = 0
    in_table = False
    for line in lines:
        if re.match(r"\|.*\|.*\|", line):
            if not in_table:
                table_count += 1
                in_table = True
        else:
            in_table = False

    assert table_count >= 2, (
        f"Le rapport mensuel doit contenir au moins 2 tableaux Markdown, "
        f"trouvé {table_count}.\n"
        f"Rapport produit:\n{report}"
    )


# ---------------------------------------------------------------------------
# Test 4 — synthesize_section est appelé au moins 4 fois
# ---------------------------------------------------------------------------


def test_build_monthly_report_calls_synthesize_section_at_least_four_times(
    tmp_config, data_complete
):
    """
    synthesize_section doit être appelé au moins 4 fois pour les sections narratives
    du Monthly Close (Month in Review, Macro, ETF, Crypto, PEA, News, Forward Look).
    """
    with patch(
        "reporters.monthly.synthesize_section", return_value="NARRATION OK"
    ) as mock_synth:
        build_monthly_report(data_complete, tmp_config)

    assert mock_synth.call_count >= 4, (
        f"synthesize_section doit être appelé au moins 4 fois, "
        f"got {mock_synth.call_count} appels"
    )


# ---------------------------------------------------------------------------
# Test 5 — La Config passée à synthesize_section a le bon modèle (LLM-02)
# ---------------------------------------------------------------------------


def test_build_monthly_report_uses_configured_anthropic_model(tmp_config, data_complete):
    """
    La Config passée à synthesize_section doit avoir anthropic_model='claude-sonnet-4-6'
    (preuve LLM-02 : le modèle est configurable, jamais hardcodé dans monthly.py).
    """
    with patch(
        "reporters.monthly.synthesize_section", return_value="NARRATION OK"
    ) as mock_synth:
        build_monthly_report(data_complete, tmp_config)

    assert mock_synth.call_count >= 1, "synthesize_section non appelé"

    for call in mock_synth.call_args_list:
        kwargs = call.kwargs
        args = call.args
        if "config" in kwargs:
            cfg_passed = kwargs["config"]
        elif len(args) >= 2:
            cfg_passed = args[1]
        else:
            pytest.fail(f"config non trouvé dans les args de l'appel: {call}")

        assert cfg_passed.anthropic_model == "claude-sonnet-4-6", (
            f"anthropic_model attendu 'claude-sonnet-4-6', "
            f"got '{cfg_passed.anthropic_model}'"
        )


# ---------------------------------------------------------------------------
# Test 6 — Dégradation gracieuse si data = {} (aucune donnée disponible)
# ---------------------------------------------------------------------------


def test_build_monthly_report_handles_missing_data_gracefully(tmp_config):
    """
    Avec data = {} (aucune donnée disponible), build_monthly_report ne doit
    pas lever d'exception et doit retourner un ReportOutput avec les 7 sections.
    """
    with patch("reporters.monthly.synthesize_section", return_value="NARRATION OK"):
        result = build_monthly_report({}, tmp_config)

    report = result.plain_text
    assert isinstance(report, str), "plain_text doit être une chaîne même avec data={}"

    expected_sections = [
        "## Month in Review",
        "## Macro Backdrop",
        "## ETF Monthly Performance",
        "## Crypto Monthly",
        "## PEA Monthly",
        "## News & Themes",
        "## Forward Look",
    ]
    for section_title in expected_sections:
        assert section_title in report, (
            f"Section '{section_title}' absente du rapport en mode dégradé (data={{}}).\n"
            f"Rapport produit:\n{report}"
        )


# ---------------------------------------------------------------------------
# Test 7 — PEA Monthly contient alerte si eligibility_changed=True
# ---------------------------------------------------------------------------


def test_build_monthly_report_includes_pea_eligibility_alert(tmp_config, data_complete):
    """
    Si data['pea']['eligibility_changed'] = True, la section PEA Monthly doit
    contenir le mot-clé 'alerte' ou 'changement' (signal explicite à l'utilisateur).
    """
    data_complete["pea"]["eligibility_changed"] = True

    with patch("reporters.monthly.synthesize_section", return_value="NARRATION OK"):
        result = build_monthly_report(data_complete, tmp_config)

    report = result.plain_text
    assert "## PEA Monthly" in report, "Section PEA Monthly absente"

    # Extraire le contenu de la section PEA Monthly
    pea_start = report.find("## PEA Monthly")
    next_section = report.find("## News & Themes")
    pea_content = (
        report[pea_start:next_section] if next_section != -1 else report[pea_start:]
    )

    assert "alerte" in pea_content.lower() or "changement" in pea_content.lower(), (
        f"La section PEA Monthly doit contenir 'alerte' ou 'changement' quand "
        f"eligibility_changed=True. Contenu PEA:\n{pea_content}"
    )
