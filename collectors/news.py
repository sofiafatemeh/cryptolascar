"""
collectors/news.py — Collecte de titres financiers via NewsAPI + scraping BS4.

Sources :
- NewsAPI (~10 articles) : https://newsapi.org/v2/everything
- CoinDesk, CoinTelegraph, Boursorama, AMF (5 titres chacun)

Cache SQLite 2h — source="news", symbol="headlines".
Dégradation gracieuse : jamais d'exception propagée.

Threat model (T-02-17 à T-02-21) :
- La clé API NewsAPI n'est jamais loguée (T-02-17)
- HTML scrapé traité comme données uniquement, pas exécuté (T-02-18)
- Sleep 1.0s entre chaque domaine scraped (T-02-19)
- Cache via requêtes paramétrées (T-02-21)
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup

from config import Config
from db.cache import get_connection
from logging_setup import get_logger

logger = get_logger(__name__)

CACHE_SOURCE = "news"
CACHE_SYMBOL = "headlines"
CACHE_TTL_HOURS = 2
SCRAPE_SLEEP_SECONDS = 1.0
MAX_HEADLINES = 35
MAX_PER_SCRAPED_SOURCE = 5
NEWSAPI_PAGE_SIZE = 10

NEWSAPI_URL = "https://newsapi.org/v2/everything"
SCRAPE_SOURCES = {
    "CoinDesk": "https://www.coindesk.com/",
    "CoinTelegraph": "https://cointelegraph.com/",
    "Boursorama": "https://www.boursorama.com/bourse/actualites/",
    "AMF": "https://www.amf-france.org/fr/espace-epargnants/actualites-et-alertes",
}


def _utcnow_iso() -> str:
    """Retourne l'heure UTC actuelle au format ISO 8601."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expires_iso(hours: int) -> str:
    """Retourne l'heure UTC dans `hours` heures au format ISO 8601."""
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_cached(conn: Any) -> list | None:
    """
    Recherche les headlines en cache valide.
    Retourne la liste de dicts ou None si pas de cache valide.
    """
    now = _utcnow_iso()
    row = conn.execute(
        "SELECT data_json FROM market_cache WHERE source=? AND symbol=? AND expires_at > ?",
        (CACHE_SOURCE, CACHE_SYMBOL, now),
    ).fetchone()
    return json.loads(row["data_json"]) if row else None


def _upsert_cache(conn: Any, headlines: list) -> None:
    """
    Upsert les headlines dans market_cache (source="news", symbol="headlines").
    TTL = CACHE_TTL_HOURS heures. Requête paramétrée (T-02-21).
    """
    conn.execute(
        "INSERT OR REPLACE INTO market_cache "
        "(source, symbol, data_json, fetched_at, expires_at) VALUES (?,?,?,?,?)",
        (
            CACHE_SOURCE,
            CACHE_SYMBOL,
            json.dumps(headlines),
            _utcnow_iso(),
            _expires_iso(CACHE_TTL_HOURS),
        ),
    )
    conn.commit()


def _fetch_newsapi(api_key: str) -> list[dict]:
    """
    Récupère ~10 headlines depuis NewsAPI.
    La clé API n'est jamais loguée (T-02-17).
    Retourne une liste vide en cas d'échec.
    """
    params = {
        "q": "ETF OR crypto OR bourse OR CAC",
        "language": "fr",
        "sortBy": "publishedAt",
        "pageSize": NEWSAPI_PAGE_SIZE,
        "apiKey": api_key,
    }
    resp = httpx.get(NEWSAPI_URL, params=params, timeout=10)
    if resp.status_code != 200:
        # Log status code only — never the URL which contains apiKey (T-02-17)
        raise ValueError(f"NewsAPI returned HTTP {resp.status_code}")
    articles = resp.json().get("articles", [])
    return [
        {
            "title": a["title"],
            "url": a["url"],
            "source": a["source"]["name"],
            "published_at": a["publishedAt"],
        }
        for a in articles[:NEWSAPI_PAGE_SIZE]
        if a.get("title") and a.get("url")
    ]


def _scrape_coindesk(html: bytes, base_url: str) -> list[dict]:
    """
    Scrape jusqu'à MAX_PER_SCRAPED_SOURCE headlines de CoinDesk.
    Cherche les <a> contenant des balises <h3> ou <h4>.
    """
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for a_tag in soup.find_all("a", href=True):
        h_tag = a_tag.find(["h3", "h4"])
        if h_tag and h_tag.get_text(strip=True):
            href = a_tag["href"]
            if href.startswith("/"):
                href = "https://www.coindesk.com" + href
            results.append(
                {
                    "title": h_tag.get_text(strip=True),
                    "url": href,
                    "source": "CoinDesk",
                    "published_at": _utcnow_iso(),
                }
            )
        if len(results) >= MAX_PER_SCRAPED_SOURCE:
            break
    return results


def _scrape_cointelegraph(html: bytes, base_url: str) -> list[dict]:
    """
    Scrape jusqu'à MAX_PER_SCRAPED_SOURCE headlines de CoinTelegraph.
    Cherche les <span class="*title*"> dans des balises <a>.
    """
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for span in soup.find_all("span", class_=lambda c: c and "title" in c):
        parent_a = span.find_parent("a", href=True)
        title = span.get_text(strip=True)
        if parent_a and title:
            href = parent_a["href"]
            if href.startswith("/"):
                href = "https://cointelegraph.com" + href
            results.append(
                {
                    "title": title,
                    "url": href,
                    "source": "CoinTelegraph",
                    "published_at": _utcnow_iso(),
                }
            )
        if len(results) >= MAX_PER_SCRAPED_SOURCE:
            break
    return results


def _scrape_boursorama(html: bytes, base_url: str) -> list[dict]:
    """
    Scrape jusqu'à MAX_PER_SCRAPED_SOURCE headlines de Boursorama.
    Cherche les <a> pointant vers des articles d'actualité (URL contenant "actu" ou "article").
    """
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for a_tag in soup.find_all("a", href=True):
        title = a_tag.get_text(strip=True)
        href = a_tag["href"]
        if (
            title
            and len(title) > 20
            and ("actu" in href or "article" in href or "actualite" in href)
        ):
            if href.startswith("/"):
                href = "https://www.boursorama.com" + href
            results.append(
                {
                    "title": title[:200],
                    "url": href,
                    "source": "Boursorama",
                    "published_at": _utcnow_iso(),
                }
            )
        if len(results) >= MAX_PER_SCRAPED_SOURCE:
            break
    return results


def _scrape_amf(html: bytes, base_url: str) -> list[dict]:
    """
    Scrape jusqu'à MAX_PER_SCRAPED_SOURCE communiqués de l'AMF.
    Cherche les <a> avec des titres substantiels pointant vers amf-france.org.
    """
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for a_tag in soup.find_all("a", href=True):
        title = a_tag.get_text(strip=True)
        href = a_tag["href"]
        if title and len(title) > 20 and (
            "amf-france.org" in href or href.startswith("/")
        ):
            if href.startswith("/"):
                href = "https://www.amf-france.org" + href
            results.append(
                {
                    "title": title[:200],
                    "url": href,
                    "source": "AMF",
                    "published_at": _utcnow_iso(),
                }
            )
        if len(results) >= MAX_PER_SCRAPED_SOURCE:
            break
    return results


# Registre des parsers par source
SCRAPE_PARSERS = {
    "CoinDesk": _scrape_coindesk,
    "CoinTelegraph": _scrape_cointelegraph,
    "Boursorama": _scrape_boursorama,
    "AMF": _scrape_amf,
}


def _scrape_all() -> tuple[list[dict], bool]:
    """
    Scrape les 4 sources. Retourne (headlines, all_failed).
    Sleep SCRAPE_SLEEP_SECONDS entre chaque domaine (T-02-19).
    En cas d'échec sur une source : log warning, continue vers les autres.
    """
    all_headlines: list[dict] = []
    any_success = False
    first_request = True

    for source_name, url in SCRAPE_SOURCES.items():
        if not first_request:
            time.sleep(SCRAPE_SLEEP_SECONDS)
        first_request = False
        try:
            resp = httpx.get(
                url,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0 (compatible; CryptoLascar/1.0)"},
            )
            resp.raise_for_status()
            parser = SCRAPE_PARSERS[source_name]
            items = parser(resp.content, url)
            all_headlines.extend(items)
            logger.info("Scraped %d headlines from %s", len(items), source_name)
            any_success = True
        except Exception as exc:
            logger.warning("Scraping failed for %s: %s", source_name, exc)

    return all_headlines, not any_success


def collect_news(config: Config) -> dict:
    """
    Collecte des titres financiers depuis NewsAPI et 4 sites scrapés.

    Flux :
    1. Vérifie le cache SQLite (TTL 2h, source="news", symbol="headlines")
    2. Cache hit → retourne les données sans appels réseau
    3. Cache miss →
       a. Fetch NewsAPI si config.newsapi_key est défini
       b. Scrape CoinDesk, CoinTelegraph, Boursorama, AMF (1s entre chaque)
       c. Fusion, déduplication par URL, cap à MAX_HEADLINES=35
       d. Upsert cache

    Dégradation gracieuse :
    - NewsAPI indisponible → newsapi_failed=True, scraping seul
    - Site de scraping indisponible → log warning, continue
    - Tout échoue → retourne dict avec listes vides et flags d'erreur

    Args:
        config: Config avec newsapi_key (optionnel) et db_path

    Returns:
        dict contenant :
        - "headlines": list[dict] (max 35) avec title, url, source, published_at
        - "count": int
        - "newsapi_failed": bool
        - "scrape_failed": bool  — True si TOUS les sites de scraping ont échoué
        - "partial": bool
        - "source_used": str

    Never raises.
    """
    try:
        conn = get_connection(config.db_path)
        cached = _get_cached(conn)
        if cached is not None:
            logger.debug("Cache hit for news headlines (%d items)", len(cached))
            conn.close()
            return {
                "headlines": cached,
                "count": len(cached),
                "newsapi_failed": False,
                "scrape_failed": False,
                "partial": False,
                "source_used": CACHE_SOURCE,
            }
    except Exception as exc:
        logger.error("Cache read error: %s", exc)
        # On continue sans cache en cas d'erreur DB
        conn = None

    headlines: list[dict] = []
    newsapi_failed = False
    scrape_failed = False

    # Couche 1 : NewsAPI
    if config.newsapi_key:
        try:
            api_headlines = _fetch_newsapi(config.newsapi_key)
            headlines.extend(api_headlines)
            logger.info("Fetched %d headlines from NewsAPI", len(api_headlines))
        except Exception as exc:
            # Clé jamais loguée (T-02-17) — uniquement str(exc)
            logger.error("NewsAPI fetch failed: %s", exc)
            newsapi_failed = True
    else:
        logger.warning("NEWSAPI_KEY not configured — skipping NewsAPI")
        newsapi_failed = True

    # Couche 2 : Scraping BS4
    try:
        scraped, scrape_failed = _scrape_all()
        headlines.extend(scraped)
    except Exception as exc:
        logger.error("Scraping layer error: %s", exc)
        scrape_failed = True

    # Déduplication par URL
    seen_urls: set[str] = set()
    deduped: list[dict] = []
    for h in headlines:
        if h.get("url") and h["url"] not in seen_urls:
            seen_urls.add(h["url"])
            deduped.append(h)

    # Cap à MAX_HEADLINES
    final = deduped[:MAX_HEADLINES]

    # Écriture cache
    if conn is not None:
        try:
            _upsert_cache(conn, final)
            conn.close()
        except Exception as exc:
            logger.error("Cache write error: %s", exc)
    elif conn is None:
        # Tentative de reconnexion pour écrire le cache
        try:
            conn2 = get_connection(config.db_path)
            _upsert_cache(conn2, final)
            conn2.close()
        except Exception as exc:
            logger.error("Cache reconnect/write error: %s", exc)

    return {
        "headlines": final,
        "count": len(final),
        "newsapi_failed": newsapi_failed,
        "scrape_failed": scrape_failed,
        "partial": newsapi_failed or scrape_failed,
        "source_used": CACHE_SOURCE,
    }
