"""
tests/test_pea.py — Tests TDD pour collectors/pea.py (collect_pea).

RED phase : ces tests doivent échouer (ImportError) tant que collectors/pea.py
n'est pas implémenté.

Couverture :
  Test 1 — Cache hit : yfinance non appelé si donnée en cache valide
  Test 2 — Cache miss : yfinance appelé, résultat mis en cache
  Test 3 — Premier run éligibilité : pas d'alerte (première insertion)
  Test 4 — Éligibilité inchangée : eligibility_changed=False
  Test 5 — Éligibilité changée : eligibility_changed=True, warning loggué
  Test 6 — Échec yfinance pour un ticker : partial=True, pas d'exception
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
from collectors.pea import collect_pea


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_price_cache(db_path: Path, symbol: str, data: dict, expires_in_hours: float = 5.0) -> None:
    """Insère une ligne de prix dans market_cache pour les tests de cache hit."""
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc)
    fetched_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    expires_at = (now + timedelta(hours=expires_in_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT OR REPLACE INTO market_cache (source, symbol, data_json, fetched_at, expires_at) VALUES (?,?,?,?,?)",
        ("yfinance_pea", symbol, json.dumps(data), fetched_at, expires_at),
    )
    conn.commit()
    conn.close()


def insert_eligibility(conn, ticker: str, eligible: bool) -> None:
    """Insère ou remplace un statut d'éligibilité dans market_cache."""
    conn.execute(
        "INSERT OR REPLACE INTO market_cache (source, symbol, data_json, fetched_at, expires_at) VALUES (?,?,?,?,?)",
        (
            "pea_eligibility",
            ticker,
            json.dumps({"eligible": eligible}),
            "2026-01-01T00:00:00Z",
            "2099-01-01T00:00:00Z",
        ),
    )
    conn.commit()


def _make_mock_fast_info() -> MagicMock:
    """Retourne un MagicMock simulant yfinance fast_info."""
    mock_fi = MagicMock()
    mock_fi.lastPrice = 7800.0
    mock_fi.previousClose = 7700.0
    mock_fi.regularMarketVolume = 500000
    return mock_fi


def _make_mock_ticker(fast_info: MagicMock | None = None) -> MagicMock:
    mock_t = MagicMock()
    mock_t.fast_info = fast_info or _make_mock_fast_info()
    return mock_t


# ---------------------------------------------------------------------------
# Test 1 — Cache hit : yfinance ne doit PAS être appelé
# ---------------------------------------------------------------------------


def test_price_cache_hit_skips_yfinance(tmp_config):
    """
    Un ticker en cache valide doit être retourné sans appel yfinance.
    On pré-insère uniquement ^FCHI et vérifie que son prix est retourné
    sans que yfinance ne soit appelé pour ce ticker.
    Pour que le test soit déterministe on pré-insère tous les tickers.
    """
    from collectors.pea import PEA_TICKERS

    cached_data = {"price": 7800.0, "prev_close": 7700.0, "pct_change": 1.30, "volume": 500000}
    for ticker in PEA_TICKERS:
        _insert_price_cache(tmp_config.db_path, ticker, cached_data, expires_in_hours=5.0)

    with patch("collectors.pea.yf") as mock_yf:
        mock_yf.Ticker.side_effect = AssertionError("yfinance should not be called on cache hit")
        result = collect_pea(tmp_config)

    assert result["prices"]["^FCHI"]["price"] == 7800.0
    mock_yf.Ticker.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2 — Cache miss : yfinance appelé, résultat écrit en cache
# ---------------------------------------------------------------------------


def test_price_cache_miss_fetches_yfinance(tmp_config):
    """Sans cache, yfinance doit être consulté et le résultat sauvegardé."""
    mock_ticker = _make_mock_ticker()

    with patch("collectors.pea.yf") as mock_yf:
        mock_yf.Ticker.return_value = mock_ticker
        result = collect_pea(tmp_config)

    assert result["prices"]["^FCHI"]["price"] == 7800.0

    # Vérifie que la ligne a été écrite en base
    conn = get_connection(tmp_config.db_path)
    row = conn.execute(
        "SELECT data_json FROM market_cache WHERE source='yfinance_pea' AND symbol='^FCHI'"
    ).fetchone()
    conn.close()
    assert row is not None
    row_data = json.loads(row["data_json"])
    assert "price" in row_data


# ---------------------------------------------------------------------------
# Test 3 — Premier run éligibilité : pas d'alerte, upsert effectué
# ---------------------------------------------------------------------------


def test_first_run_eligibility_no_alert(tmp_config):
    """
    Premier run : aucune ligne d'éligibilité en cache.
    Résultat attendu : eligibility_changed=False + ligne insérée pour CW8.PA.
    """
    mock_ticker = _make_mock_ticker()

    with patch("collectors.pea.yf") as mock_yf:
        mock_yf.Ticker.return_value = mock_ticker
        result = collect_pea(tmp_config)

    assert result["eligibility_changed"] is False

    # Vérifie que la ligne d'éligibilité a été insérée
    conn = get_connection(tmp_config.db_path)
    row = conn.execute(
        "SELECT data_json FROM market_cache WHERE source='pea_eligibility' AND symbol='CW8.PA'"
    ).fetchone()
    conn.close()
    assert row is not None


# ---------------------------------------------------------------------------
# Test 4 — Éligibilité inchangée : eligibility_changed=False
# ---------------------------------------------------------------------------


def test_eligibility_unchanged_no_alert(tmp_config):
    """
    Les statuts d'éligibilité pré-insérés correspondent au statut actuel.
    Résultat attendu : eligibility_changed=False.
    """
    conn = get_connection(tmp_config.db_path)
    insert_eligibility(conn, "CW8.PA", True)
    insert_eligibility(conn, "PAEEM.PA", True)
    insert_eligibility(conn, "PANX.PA", True)
    conn.close()

    mock_ticker = _make_mock_ticker()

    with patch("collectors.pea.yf") as mock_yf:
        mock_yf.Ticker.return_value = mock_ticker
        result = collect_pea(tmp_config)

    assert result["eligibility_changed"] is False


# ---------------------------------------------------------------------------
# Test 5 — Éligibilité changée : eligibility_changed=True, warning loggué
# ---------------------------------------------------------------------------


def test_eligibility_changed_sets_flag(tmp_config):
    """
    CW8.PA était inéligible (False en cache) mais PEA_ELIGIBILITY_STATUS dit True.
    Résultat attendu : eligibility_changed=True.
    """
    conn = get_connection(tmp_config.db_path)
    insert_eligibility(conn, "CW8.PA", False)  # Mismatch avec PEA_ELIGIBILITY_STATUS=True
    conn.close()

    mock_ticker = _make_mock_ticker()

    with patch("collectors.pea.yf") as mock_yf:
        mock_yf.Ticker.return_value = mock_ticker
        result = collect_pea(tmp_config)

    assert result["eligibility_changed"] is True


# ---------------------------------------------------------------------------
# Test 6 — Échec yfinance pour un ticker : partial=True, jamais d'exception
# ---------------------------------------------------------------------------


def test_yfinance_failure_sets_partial(tmp_config):
    """
    yfinance lève une exception pour ^FCHI uniquement.
    Résultat attendu : partial=True, les autres tickers sont présents, pas d'exception.
    """

    def _ticker_factory(symbol):
        if symbol == "^FCHI":
            raise Exception("yfinance network error for ^FCHI")
        return _make_mock_ticker()

    with patch("collectors.pea.yf") as mock_yf:
        mock_yf.Ticker.side_effect = _ticker_factory
        result = collect_pea(tmp_config)

    assert result["partial"] is True
    assert isinstance(result, dict)
