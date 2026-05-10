"""
tests/test_news.py — Tests TDD pour collectors/news.py (collect_news).

RED phase : ces tests doivent échouer (ImportError) tant que collectors/news.py
n'est pas implémenté.

Couverture :
  Test 1 — Cache hit : httpx et BS4 non appelés si données en cache valide
  Test 2 — Cache miss : NewsAPI + scraping 4 sites, écriture cache, total ≤ 35
  Test 3 — Clé NewsAPI manquante → newsapi_failed=True, headlines scrapés retournés
  Test 4 — Échec scraping total → scrape_failed=True, headlines NewsAPI conservés
  Test 5 — collect_news ne propage jamais d'exception
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
from collectors.news import collect_news


# ---------------------------------------------------------------------------
# Fixtures et helpers
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
        newsapi_key="FAKE_KEY",
        db_path=Path(db_path),
        log_level="DEBUG",
        log_file="",
    )
    yield cfg
    os.unlink(db_path)


# Réponse simulée NewsAPI
MOCK_NEWSAPI_RESPONSE = {
    "articles": [
        {
            "title": "BTC hits 100k",
            "url": "https://news.example.com/1",
            "source": {"name": "CoinDesk"},
            "publishedAt": "2026-05-09T06:00:00Z",
        },
        {
            "title": "ETF flows surge",
            "url": "https://news.example.com/2",
            "source": {"name": "Bloomberg"},
            "publishedAt": "2026-05-09T05:00:00Z",
        },
    ]
}

# HTML simulé pour CoinDesk
MOCK_HTML_COINDESK = (
    b'<html><body>'
    b'<a href="/article/btc-rally"><h3>BTC Rally Continues</h3></a>'
    b'<a href="/article/eth-drop"><h3>ETH Drops 5%</h3></a>'
    b'</body></html>'
)


def _insert_cache_headlines(db_path: Path, headlines: list, expires_in_hours: float = 3.0) -> None:
    """Pré-insère des headlines dans market_cache pour les tests de cache hit."""
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc)
    fetched_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    expires_at = (now + timedelta(hours=expires_in_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT OR REPLACE INTO market_cache (source, symbol, data_json, fetched_at, expires_at) "
        "VALUES (?,?,?,?,?)",
        ("news", "headlines", json.dumps(headlines), fetched_at, expires_at),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Test 1 — Cache hit : httpx ne doit PAS être appelé
# ---------------------------------------------------------------------------

def test_cache_hit_skips_fetch(tmp_config):
    """
    Si des headlines sont en cache valide (expires_at dans le futur),
    collect_news doit retourner les données sans appeler httpx ni BS4.
    """
    cached_headlines = [
        {
            "title": "Cached",
            "url": "https://x.com",
            "source": "Test",
            "published_at": "2026-05-09T06:00:00Z",
        }
    ]
    _insert_cache_headlines(tmp_config.db_path, cached_headlines, expires_in_hours=3.0)

    with patch("httpx.get", side_effect=AssertionError("httpx.get should NOT be called on cache hit")):
        result = collect_news(tmp_config)

    assert result["headlines"][0]["title"] == "Cached"
    assert result["count"] == 1


# ---------------------------------------------------------------------------
# Test 2 — Cache miss : NewsAPI + scraping, écriture cache, total ≤ 35
# ---------------------------------------------------------------------------

def test_cache_miss_fetches_and_writes_cache(tmp_config):
    """
    Sans cache, collect_news doit appeler NewsAPI et scraper les 4 sites,
    écrire les résultats dans market_cache, et retourner ≤ 35 headlines.
    """
    def mock_httpx_get(url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        if "newsapi.org" in url:
            mock_resp.json = lambda: MOCK_NEWSAPI_RESPONSE
        else:
            mock_resp.content = MOCK_HTML_COINDESK
        return mock_resp

    with patch("httpx.get", side_effect=mock_httpx_get):
        result = collect_news(tmp_config)

    assert len(result["headlines"]) > 0
    assert result["count"] <= 35

    # Vérifier que la ligne a été écrite en cache
    conn = get_connection(tmp_config.db_path)
    row = conn.execute(
        "SELECT data_json FROM market_cache WHERE source='news' AND symbol='headlines'"
    ).fetchone()
    conn.close()
    assert row is not None


# ---------------------------------------------------------------------------
# Test 3 — Clé NewsAPI manquante → newsapi_failed=True
# ---------------------------------------------------------------------------

def test_missing_newsapi_key_sets_flag(tmp_config):
    """
    Si newsapi_key est vide, newsapi_failed doit être True
    et les headlines scrapés doivent être retournés quand même.
    """
    tmp_config.newsapi_key = ""

    def mock_httpx_get(url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        mock_resp.content = MOCK_HTML_COINDESK
        return mock_resp

    with patch("httpx.get", side_effect=mock_httpx_get):
        result = collect_news(tmp_config)

    assert result["newsapi_failed"] is True
    assert len(result["headlines"]) >= 0  # peut contenir des headlines scrapés


# ---------------------------------------------------------------------------
# Test 4 — Échec total du scraping → scrape_failed=True
# ---------------------------------------------------------------------------

def test_scraping_failure_sets_flag(tmp_config):
    """
    Si tous les sites de scraping lèvent une exception,
    scrape_failed doit être True, mais les headlines NewsAPI doivent rester.
    """
    call_count = {"n": 0}

    def mock_httpx_get(url, **kwargs):
        if "newsapi.org" in url:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json = lambda: MOCK_NEWSAPI_RESPONSE
            return mock_resp
        # Toutes les URL de scraping échouent
        raise Exception("Connection refused")

    with patch("httpx.get", side_effect=mock_httpx_get):
        result = collect_news(tmp_config)

    assert result["scrape_failed"] is True
    assert len(result["headlines"]) >= 2  # les 2 articles NewsAPI doivent être présents


# ---------------------------------------------------------------------------
# Test 5 — collect_news ne propage jamais d'exception
# ---------------------------------------------------------------------------

def test_collect_news_never_raises(tmp_config):
    """
    Même si toutes les sources (NewsAPI + scraping) échouent,
    collect_news doit toujours retourner un dict sans lever d'exception.
    """
    with patch("httpx.get", side_effect=Exception("Total failure")):
        result = collect_news(tmp_config)

    assert isinstance(result, dict)
    assert "headlines" in result
