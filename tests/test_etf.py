"""
tests/test_etf.py — Tests TDD pour collectors/etf.py (collect_etf).

RED phase : ces tests doivent échouer (ImportError) tant que collectors/etf.py
n'est pas implémenté.

Couverture :
  Test 1 — Cache hit : yfinance non appelé si donnée en cache valide
  Test 2 — Cache miss : yfinance appelé, résultat mis en cache
  Test 3 — Quota Alpha Vantage épuisé → alpha_vantage_failed=True
  Test 4 — Exception yfinance pour un ticker → partial=True
  Test 5 — collect_etf ne propage jamais d'exception
"""
from __future__ import annotations

import json
import tempfile
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from db.cache import init_db, get_connection
from config import Config

# Import à tester — provoquera ImportError (RED gate) jusqu'à l'implémentation
from collectors.etf import collect_etf


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


def _insert_cache_row(db_path: Path, symbol: str, data: dict, expires_in_hours: float = 5.0) -> None:
    """Insère une ligne dans market_cache pour les tests de cache hit."""
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc)
    fetched_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    expires_at = (now + timedelta(hours=expires_in_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT OR REPLACE INTO market_cache (source, symbol, data_json, fetched_at, expires_at) VALUES (?,?,?,?,?)",
        ("yfinance_etf", symbol, json.dumps(data), fetched_at, expires_at),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Test 1 — Cache hit : yfinance ne doit PAS être appelé pour le ticker en cache
# ---------------------------------------------------------------------------

def test_cache_hit_skips_yfinance(tmp_config):
    """
    Un ticker en cache valide doit être retourné sans appel yfinance POUR CE TICKER.
    On met tous les tickers en cache afin de vérifier qu'aucun appel yfinance n'est émis.
    """
    cached_data = {"price": 500.0, "prev_close": 495.0, "pct_change": 1.01, "volume": 1_000_000}
    # Pré-remplir le cache pour TOUS les tickers ETF
    from collectors.etf import ETF_TICKERS
    for ticker in ETF_TICKERS:
        ticker_data = dict(cached_data)
        if ticker == "SPY":
            ticker_data["price"] = 500.0
        _insert_cache_row(tmp_config.db_path, ticker, ticker_data, expires_in_hours=5.0)

    with patch("collectors.etf.yf") as mock_yf:
        mock_yf.Ticker.side_effect = AssertionError("yfinance should not be called on cache hit")
        result = collect_etf(tmp_config)

    assert result["tickers"]["SPY"]["price"] == 500.0
    mock_yf.Ticker.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2 — Cache miss : yfinance appelé, résultat écrit en cache
# ---------------------------------------------------------------------------

def test_cache_miss_fetches_yfinance_and_writes_cache(tmp_config):
    """Sans cache, yfinance doit être consulté et le résultat sauvegardé."""
    mock_fast_info = MagicMock()
    mock_fast_info.lastPrice = 550.0
    mock_fast_info.previousClose = 540.0
    mock_fast_info.regularMarketVolume = 2_000_000

    mock_ticker = MagicMock()
    mock_ticker.fast_info = mock_fast_info

    # alpha_vantage_key vide — pas d'appel AV
    tmp_config.alpha_vantage_key = ""

    with patch("collectors.etf.yf") as mock_yf:
        mock_yf.Ticker.return_value = mock_ticker
        result = collect_etf(tmp_config)

    assert result["tickers"]["SPY"]["price"] == 550.0

    # Vérifie que la ligne a été écrite en base
    conn = get_connection(tmp_config.db_path)
    row = conn.execute(
        "SELECT data_json FROM market_cache WHERE source='yfinance_etf' AND symbol='SPY'"
    ).fetchone()
    conn.close()
    assert row is not None
    row_data = json.loads(row["data_json"])
    assert "price" in row_data


# ---------------------------------------------------------------------------
# Test 3 — Quota Alpha Vantage épuisé → alpha_vantage_failed=True
# ---------------------------------------------------------------------------

def test_alpha_vantage_quota_sets_flag(tmp_config):
    """Si AV retourne {'Note': ...}, alpha_vantage_failed doit être True."""
    mock_fast_info = MagicMock()
    mock_fast_info.lastPrice = 550.0
    mock_fast_info.previousClose = 540.0
    mock_fast_info.regularMarketVolume = 2_000_000

    mock_ticker = MagicMock()
    mock_ticker.fast_info = mock_fast_info

    tmp_config.alpha_vantage_key = "FAKE_KEY"

    av_response = MagicMock()
    av_response.json.return_value = {
        "Note": "Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day."
    }

    with patch("collectors.etf.yf") as mock_yf, \
         patch("collectors.etf.httpx.get", return_value=av_response):
        mock_yf.Ticker.return_value = mock_ticker
        result = collect_etf(tmp_config)

    assert result["alpha_vantage_failed"] is True
    assert result["tickers"]["SPY"]["price"] is not None


# ---------------------------------------------------------------------------
# Test 4 — yfinance lève une exception pour SPY → partial=True
# ---------------------------------------------------------------------------

def test_yfinance_failure_sets_partial(tmp_config):
    """Si yfinance échoue sur un ticker, partial=True et price=None pour ce ticker."""
    tmp_config.alpha_vantage_key = ""

    def _ticker_factory(symbol):
        if symbol == "SPY":
            raise Exception("network error")
        mock_fast_info = MagicMock()
        mock_fast_info.lastPrice = 300.0
        mock_fast_info.previousClose = 295.0
        mock_fast_info.regularMarketVolume = 500_000
        t = MagicMock()
        t.fast_info = mock_fast_info
        return t

    with patch("collectors.etf.yf") as mock_yf:
        mock_yf.Ticker.side_effect = _ticker_factory
        result = collect_etf(tmp_config)

    assert result["partial"] is True
    assert "SPY" in result["tickers"]
    assert result["tickers"]["SPY"]["price"] is None


# ---------------------------------------------------------------------------
# Test 5 — collect_etf ne propage jamais d'exception
# ---------------------------------------------------------------------------

def test_collect_etf_never_raises(tmp_config):
    """collect_etf doit toujours retourner un dict, même si tout échoue."""
    tmp_config.alpha_vantage_key = ""

    with patch("collectors.etf.yf") as mock_yf:
        mock_yf.Ticker.side_effect = Exception("total failure")
        result = collect_etf(tmp_config)

    assert isinstance(result, dict)
    assert "tickers" in result
