"""
tests/test_macro.py — Tests TDD pour collectors/macro.py (collect_macro).

RED phase : ces tests doivent échouer (ImportError) tant que collectors/macro.py
n'est pas implémenté.

Couverture :
  Test 1 — Cache hit : httpx.get non appelé si données en cache valide pour toutes les séries
  Test 2 — Cache miss : FRED appelé pour chaque série, résultat mis en cache
  Test 3 — Clé FRED manquante → fred_failed=True, series={}
  Test 4 — Échec d'une série → partial=True, autres séries présentes
  Test 5 — collect_macro ne propage jamais d'exception
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from db.cache import get_connection, init_db
from config import Config

# Import à tester — provoquera ImportError (RED gate) jusqu'à l'implémentation
from collectors.macro import collect_macro


# ---------------------------------------------------------------------------
# Données de mock FRED
# ---------------------------------------------------------------------------

MOCK_FRED_RESPONSE = {
    "observations": [
        {"date": "2026-05-09", "value": "4.45"},
        {"date": "2026-05-08", "value": "4.44"},
    ]
}


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
        fred_api_key="FAKE_KEY",
        newsapi_key="",
        db_path=Path(db_path),
        log_level="DEBUG",
        log_file="",
    )
    yield cfg
    os.unlink(db_path)


def _insert_fred_cache_row(
    db_path: Path,
    series_id: str,
    data: dict,
    expires_in_hours: float = 25.0,
) -> None:
    """Insère une ligne dans market_cache pour les tests de cache hit."""
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc)
    fetched_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    expires_at = (now + timedelta(hours=expires_in_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT OR REPLACE INTO market_cache (source, symbol, data_json, fetched_at, expires_at) "
        "VALUES (?,?,?,?,?)",
        ("fred", series_id, json.dumps(data), fetched_at, expires_at),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Test 1 — Cache hit : httpx.get ne doit PAS être appelé
# ---------------------------------------------------------------------------

def test_cache_hit_skips_fred(tmp_config):
    """
    Toutes les séries en cache valide : httpx.get ne doit jamais être appelé.
    """
    series_values = {
        "DGS10": {"value": 4.45, "date": "2026-05-09", "series_id": "DGS10"},
        "DGS2": {"value": 4.10, "date": "2026-05-09", "series_id": "DGS2"},
        "CPIAUCSL": {"value": 313.5, "date": "2026-04-01", "series_id": "CPIAUCSL"},
        "M2SL": {"value": 21500.0, "date": "2026-04-01", "series_id": "M2SL"},
    }
    for series_id, data in series_values.items():
        _insert_fred_cache_row(tmp_config.db_path, series_id, data, expires_in_hours=25.0)

    with patch("httpx.get") as mock_get:
        mock_get.side_effect = AssertionError("httpx.get should not be called on cache hit")
        result = collect_macro(tmp_config)

    assert result["series"]["DGS10"]["value"] == 4.45
    mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2 — Cache miss : FRED appelé, résultat écrit en cache
# ---------------------------------------------------------------------------

def test_cache_miss_fetches_fred_and_writes_cache(tmp_config):
    """Sans cache, httpx.get doit être appelé 4 fois (une fois par série)."""
    mock_response = MagicMock()
    mock_response.json.return_value = MOCK_FRED_RESPONSE

    with patch("httpx.get", return_value=mock_response) as mock_get, \
         patch("collectors.macro.time.sleep"):
        result = collect_macro(tmp_config)

    # Valeur extraite de MOCK_FRED_RESPONSE["observations"][0]["value"]
    assert result["series"]["DGS10"]["value"] == 4.45

    # httpx.get appelé 4 fois (une par série FRED)
    assert mock_get.call_count == 4

    # Ligne écrite en cache pour DGS10
    conn = get_connection(tmp_config.db_path)
    row = conn.execute(
        "SELECT data_json, expires_at FROM market_cache WHERE source='fred' AND symbol='DGS10'"
    ).fetchone()
    conn.close()
    assert row is not None
    row_data = json.loads(row["data_json"])
    assert row_data["value"] == 4.45

    # expires_at > maintenant (TTL 24h bien appliqué)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert row["expires_at"] > now


# ---------------------------------------------------------------------------
# Test 3 — Clé FRED manquante → fred_failed=True, series={}
# ---------------------------------------------------------------------------

def test_missing_fred_key_sets_flag(tmp_config):
    """Si fred_api_key est vide, fred_failed=True et aucun appel httpx n'est émis."""
    tmp_config.fred_api_key = ""

    with patch("httpx.get") as mock_get:
        mock_get.side_effect = AssertionError("httpx.get should not be called when key is missing")
        result = collect_macro(tmp_config)

    assert result["fred_failed"] is True
    assert result["series"] == {}
    mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4 — Échec d'une série individuelle → partial=True
# ---------------------------------------------------------------------------

def test_single_series_failure_sets_partial(tmp_config):
    """Si DGS10 échoue, partial=True mais les autres séries sont présentes."""
    mock_response = MagicMock()
    mock_response.json.return_value = MOCK_FRED_RESPONSE

    def _side_effect(url, params=None, timeout=None):
        if params and params.get("series_id") == "DGS10":
            raise Exception("FRED network error for DGS10")
        return mock_response

    with patch("httpx.get", side_effect=_side_effect), \
         patch("collectors.macro.time.sleep"):
        result = collect_macro(tmp_config)

    assert result["partial"] is True
    # DGS10 en échec — value=None
    assert result["series"]["DGS10"]["value"] is None
    # Les autres séries doivent être présentes avec leurs valeurs
    assert "DGS2" in result["series"]
    assert result["series"]["DGS2"]["value"] == 4.45


# ---------------------------------------------------------------------------
# Test 5 — collect_macro ne propage jamais d'exception
# ---------------------------------------------------------------------------

def test_collect_macro_never_raises(tmp_config):
    """collect_macro doit toujours retourner un dict, même si tout échoue."""
    with patch("httpx.get", side_effect=Exception("total FRED failure")):
        result = collect_macro(tmp_config)

    assert isinstance(result, dict)
    assert "series" in result
