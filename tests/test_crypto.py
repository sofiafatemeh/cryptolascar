"""
tests/test_crypto.py — Tests TDD pour collectors/crypto.py (collect_crypto).

RED phase : ces tests doivent échouer (ImportError) tant que collectors/crypto.py
n'est pas implémenté.

Couverture :
  Test 1 — Cache hit : httpx.get non appelé si données en cache valides
  Test 2 — Cache miss : CoinGecko appelé, résultat écrit en cache
  Test 3 — Echec CoinGecko → coingecko_failed=True, Fear & Greed toujours collecté
  Test 4 — Echec Fear & Greed → fear_greed_failed=True, coins toujours populés
  Test 5 — collect_crypto ne propage jamais d'exception
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config import Config
from db.cache import get_connection, init_db

# Import à tester — provoquera ImportError (RED gate) jusqu'à l'implémentation
from collectors.crypto import collect_crypto


# ---------------------------------------------------------------------------
# Mock responses
# ---------------------------------------------------------------------------

MOCK_CG_RESPONSE = [
    {
        "id": "bitcoin",
        "symbol": "btc",
        "current_price": 60000.0,
        "market_cap": 1200000000000,
        "total_volume": 30000000000,
        "price_change_percentage_24h": 2.5,
    },
    {
        "id": "ethereum",
        "symbol": "eth",
        "current_price": 3500.0,
        "market_cap": 420000000000,
        "total_volume": 15000000000,
        "price_change_percentage_24h": -1.2,
    },
]

MOCK_FNG_RESPONSE = {"data": [{"value": "65", "value_classification": "Greed"}]}


# ---------------------------------------------------------------------------
# Fixture : Config pointant vers un DB temporaire
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


def _insert_cache_row(
    db_path: Path,
    source: str,
    symbol: str,
    data: dict,
    expires_in_hours: float = 5.0,
) -> None:
    """Insère une ligne dans market_cache pour les tests de cache hit."""
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc)
    fetched_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    expires_at = (now + timedelta(hours=expires_in_hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    conn.execute(
        "INSERT OR REPLACE INTO market_cache (source, symbol, data_json, fetched_at, expires_at) "
        "VALUES (?,?,?,?,?)",
        (source, symbol, json.dumps(data), fetched_at, expires_at),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Test 1 — Cache hit : httpx.get ne doit PAS être appelé
# ---------------------------------------------------------------------------


def test_cache_hit_skips_coingecko(tmp_config):
    """
    Si toutes les données crypto sont en cache valide, httpx.get ne doit pas
    être appelé. On pré-insère bitcoin + Fear & Greed pour couvrir les deux sources.
    """
    from collectors.crypto import CRYPTO_IDS

    # Pré-remplir le cache pour TOUS les coins
    for coin_id in CRYPTO_IDS:
        price = 55000.0 if coin_id == "bitcoin" else 3000.0
        _insert_cache_row(
            tmp_config.db_path,
            source="coingecko",
            symbol=coin_id,
            data={
                "price": price,
                "market_cap": 1000000000000,
                "volume_24h": 20000000000,
                "pct_change_24h": 1.0,
                "symbol": coin_id[:3].upper(),
            },
            expires_in_hours=5.0,
        )

    # Pré-remplir Fear & Greed
    _insert_cache_row(
        tmp_config.db_path,
        source="fear_greed",
        symbol="index",
        data={"value": 70, "label": "Greed"},
        expires_in_hours=5.0,
    )

    with patch("collectors.crypto.httpx.get") as mock_get:
        mock_get.side_effect = AssertionError("httpx.get should not be called on cache hit")
        result = collect_crypto(tmp_config)

    assert result["coins"]["bitcoin"]["price"] == 55000.0
    mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2 — Cache miss : CoinGecko et Fear & Greed appelés, cache écrit
# ---------------------------------------------------------------------------


def test_cache_miss_fetches_coingecko_and_writes_cache(tmp_config):
    """Sans cache, httpx.get doit être appelé et le résultat sauvegardé."""

    def _mock_get(url, **kwargs):
        mock_resp = MagicMock()
        if "coingecko.com" in url:
            mock_resp.json.return_value = MOCK_CG_RESPONSE
        else:
            mock_resp.json.return_value = MOCK_FNG_RESPONSE
        return mock_resp

    with patch("collectors.crypto.httpx.get", side_effect=_mock_get), \
         patch("collectors.crypto.time.sleep"):
        result = collect_crypto(tmp_config)

    assert result["coins"]["bitcoin"]["price"] == 60000.0

    # Vérifie que les lignes ont été écrites en base
    conn = get_connection(tmp_config.db_path)
    row_cg = conn.execute(
        "SELECT data_json FROM market_cache WHERE source='coingecko' AND symbol='bitcoin'"
    ).fetchone()
    row_fg = conn.execute(
        "SELECT data_json FROM market_cache WHERE source='fear_greed' AND symbol='index'"
    ).fetchone()
    conn.close()

    assert row_cg is not None
    assert row_fg is not None


# ---------------------------------------------------------------------------
# Test 3 — Echec CoinGecko → coingecko_failed=True, Fear & Greed toujours collecté
# ---------------------------------------------------------------------------


def test_coingecko_failure_sets_flag(tmp_config):
    """Si CoinGecko échoue, coingecko_failed=True et Fear & Greed est quand même collecté."""

    def _mock_get(url, **kwargs):
        if "coingecko.com" in url:
            raise Exception("connection refused")
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_FNG_RESPONSE
        return mock_resp

    with patch("collectors.crypto.httpx.get", side_effect=_mock_get), \
         patch("collectors.crypto.time.sleep"):
        result = collect_crypto(tmp_config)

    assert result["coingecko_failed"] is True
    assert result["fear_greed"] is not None
    assert result["fear_greed"]["value"] == 65


# ---------------------------------------------------------------------------
# Test 4 — Echec Fear & Greed → fear_greed_failed=True, coins toujours populés
# ---------------------------------------------------------------------------


def test_fear_greed_failure_sets_flag(tmp_config):
    """Si Alternative.me échoue, fear_greed_failed=True et les coins sont quand même collectés."""

    def _mock_get(url, **kwargs):
        if "alternative.me" in url:
            raise Exception("connection refused")
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_CG_RESPONSE
        return mock_resp

    with patch("collectors.crypto.httpx.get", side_effect=_mock_get), \
         patch("collectors.crypto.time.sleep"):
        result = collect_crypto(tmp_config)

    assert result["fear_greed_failed"] is True
    assert result["coins"]["bitcoin"]["price"] == 60000.0


# ---------------------------------------------------------------------------
# Test 5 — collect_crypto ne propage jamais d'exception
# ---------------------------------------------------------------------------


def test_collect_crypto_never_raises(tmp_config):
    """collect_crypto doit toujours retourner un dict, même si tout échoue."""
    with patch("collectors.crypto.httpx.get") as mock_get, \
         patch("collectors.crypto.time.sleep"):
        mock_get.side_effect = Exception("total failure")
        result = collect_crypto(tmp_config)

    assert isinstance(result, dict)
    assert "coins" in result
