"""
tests/test_integration.py — Tests d'intégration pour l'orchestration collect_all().

Couverture :
  Test 1 — test_collect_all_all_sources_ok : tous les collecteurs OK, _meta correcte
  Test 2 — test_collect_all_one_collector_raises : dégradation gracieuse, etf en echec
  Test 3 — test_collect_all_pea_eligibility_change_propagates : eligibility_changed=True accessible

RED phase : ces tests échouent jusqu'à ce que collect_all() soit implémenté dans main.py.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from config import Config
from db.cache import init_db

# Import à tester — provoquera ImportError (RED gate) jusqu'à l'implémentation
from main import collect_all


# ---------------------------------------------------------------------------
# Données mock pour les 5 collecteurs
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


# ---------------------------------------------------------------------------
# Test 1 — Tous les collecteurs OK
# ---------------------------------------------------------------------------


def test_collect_all_all_sources_ok(tmp_config):
    """
    Quand tous les collecteurs réussissent, collect_all retourne un dict avec
    les 6 clés attendues et sources_failed vide.
    """
    with (
        patch("main.collect_etf", return_value=MOCK_ETF_OK),
        patch("main.collect_crypto", return_value=MOCK_CRYPTO_OK),
        patch("main.collect_pea", return_value=MOCK_PEA_OK),
        patch("main.collect_macro", return_value=MOCK_MACRO_OK),
        patch("main.collect_news", return_value=MOCK_NEWS_OK),
    ):
        result = collect_all(tmp_config)

    # Toutes les clés attendues sont présentes
    for key in ("etf", "crypto", "pea", "macro", "news", "_meta"):
        assert key in result, f"Clé '{key}' absente du résultat collect_all"

    # Aucune source en échec
    assert result["_meta"]["sources_failed"] == [], (
        f"sources_failed devrait être vide, got: {result['_meta']['sources_failed']}"
    )

    # La source ETF est dans sources_ok
    assert "etf" in result["_meta"]["sources_ok"], (
        f"'etf' devrait être dans sources_ok: {result['_meta']['sources_ok']}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Un collecteur lève une exception → dégradation gracieuse
# ---------------------------------------------------------------------------


def test_collect_all_one_collector_raises(tmp_config):
    """
    Quand collect_etf lève une exception, le run continue.
    sources_failed contient 'etf', result['etf']['source_failed'] est True,
    et les autres sources sont dans sources_ok.
    """
    with (
        patch("main.collect_etf", side_effect=Exception("ETF network failure")),
        patch("main.collect_crypto", return_value=MOCK_CRYPTO_OK),
        patch("main.collect_pea", return_value=MOCK_PEA_OK),
        patch("main.collect_macro", return_value=MOCK_MACRO_OK),
        patch("main.collect_news", return_value=MOCK_NEWS_OK),
    ):
        result = collect_all(tmp_config)

    # ETF en échec
    assert "etf" in result["_meta"]["sources_failed"], (
        f"'etf' devrait être dans sources_failed: {result['_meta']['sources_failed']}"
    )
    assert result["etf"]["source_failed"] is True, (
        "result['etf']['source_failed'] devrait être True"
    )

    # Au moins une autre source est OK
    assert len(result["_meta"]["sources_ok"]) > 0, (
        "sources_ok ne devrait pas être vide quand d'autres collecteurs réussissent"
    )
    assert "crypto" in result["_meta"]["sources_ok"] or any(
        s in result["_meta"]["sources_ok"] for s in ("pea", "macro", "news")
    ), f"Aucune source non-etf dans sources_ok: {result['_meta']['sources_ok']}"


# ---------------------------------------------------------------------------
# Test 3 — eligibility_changed=True propagé depuis collect_pea
# ---------------------------------------------------------------------------


def test_collect_all_pea_eligibility_change_propagates(tmp_config):
    """
    Quand collect_pea retourne eligibility_changed=True, le résultat de
    collect_all doit préserver cette information dans result['pea'].
    """
    mock_pea_changed = {**MOCK_PEA_OK, "eligibility_changed": True}

    with (
        patch("main.collect_etf", return_value=MOCK_ETF_OK),
        patch("main.collect_crypto", return_value=MOCK_CRYPTO_OK),
        patch("main.collect_pea", return_value=mock_pea_changed),
        patch("main.collect_macro", return_value=MOCK_MACRO_OK),
        patch("main.collect_news", return_value=MOCK_NEWS_OK),
    ):
        result = collect_all(tmp_config)

    assert result["pea"]["eligibility_changed"] is True, (
        "eligibility_changed=True devrait être préservé dans result['pea']"
    )
