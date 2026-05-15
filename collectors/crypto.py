"""
collectors/crypto.py — Collecte des prix crypto via CoinGecko + Fear & Greed Index.

Collecte les données de prix, capitalisation, volume et variation 24h pour 8 coins
via l'API CoinGecko (batch unique), plus l'indice Fear & Greed via Alternative.me.
Cache SQLite 1h. Sleep 1.5s après l'appel batch CoinGecko (respect du rate limit).

Usage:
    from collectors.crypto import collect_crypto
    from config import get_config

    config = get_config()
    result = collect_crypto(config)
    # result["coins"]["bitcoin"]["price"]  -> float
    # result["fear_greed"]["value"]        -> int
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from config import Config
from db.cache import get_connection
from logging_setup import get_logger

logger = get_logger(__name__)

CRYPTO_IDS = [
    "bitcoin",
    "ethereum",
    "binancecoin",
    "solana",
    "ripple",
    "cardano",
    "avalanche-2",
    "dogecoin",
]
CACHE_SOURCE = "coingecko"
FNG_SOURCE = "fear_greed"
CACHE_TTL_HOURS = 1
CG_SLEEP_SECONDS = 1.5
CG_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
FNG_URL = "https://api.alternative.me/fng/?limit=1"
CG_MARKET_CHART_URL = "https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
SPARKLINE_SOURCE = "coingecko_sparkline"
SPARKLINE_COINS = ["bitcoin", "ethereum"]


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expires_iso(hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _get_cached(conn, source: str, symbol: str) -> dict | None:
    """Retourne les données du cache si valides (expires_at > maintenant)."""
    now = _utcnow_iso()
    row = conn.execute(
        "SELECT data_json FROM market_cache WHERE source=? AND symbol=? AND expires_at > ?",
        (source, symbol, now),
    ).fetchone()
    return json.loads(row["data_json"]) if row else None


def _upsert_cache(conn, source: str, symbol: str, data: dict) -> None:
    """Insère ou remplace une entrée dans market_cache."""
    conn.execute(
        "INSERT OR REPLACE INTO market_cache "
        "(source, symbol, data_json, fetched_at, expires_at) VALUES (?,?,?,?,?)",
        (
            source,
            symbol,
            json.dumps(data),
            _utcnow_iso(),
            _expires_iso(CACHE_TTL_HOURS),
        ),
    )
    conn.commit()


def _all_coins_cached(conn) -> dict[str, dict] | None:
    """Retourne tous les 8 coins depuis le cache si tous sont valides, sinon None."""
    result = {}
    for coin_id in CRYPTO_IDS:
        data = _get_cached(conn, CACHE_SOURCE, coin_id)
        if data is None:
            return None
        result[coin_id] = data
    return result


def _fetch_fear_greed(conn) -> dict | None:
    """Récupère l'indice Fear & Greed depuis le cache ou Alternative.me.

    Retourne None si la collecte échoue (dégradation gracieuse).
    """
    cached = _get_cached(conn, FNG_SOURCE, "index")
    if cached:
        logger.debug("Cache hit pour Fear & Greed index")
        return cached
    try:
        resp = httpx.get(FNG_URL, timeout=10)
        resp.raise_for_status()
        raw = resp.json()
        data = {
            "value": int(raw["data"][0]["value"]),
            "label": raw["data"][0]["value_classification"],
        }
        _upsert_cache(conn, FNG_SOURCE, "index", data)
        logger.info("Fear & Greed index: %d (%s)", data["value"], data["label"])
        return data
    except Exception as exc:
        logger.error("Fear & Greed fetch failed: %s", exc)
        return None


def _fetch_sparkline(conn, coin_id: str, config: Config) -> list[float]:
    """
    Récupère l'historique des prix sur 7 jours pour coin_id via CoinGecko market_chart.
    Vérifie d'abord le cache (source='coingecko_sparkline', TTL 1h).
    Retourne une liste de floats ou [] en cas d'échec.

    Sécurité T-08-02 : timeout=15, exception capturée → [] retourné.
    Sécurité T-08-03 : coingecko_api_key transmis en query param uniquement, jamais loggué.
    Sécurité T-08-04 : float() cast dans la list comprehension ; ValueError capturé par le except.
    """
    cached = _get_cached(conn, SPARKLINE_SOURCE, coin_id)
    if cached:
        logger.debug("Cache hit pour sparkline %s", coin_id)
        return cached.get("prices", [])

    try:
        url = CG_MARKET_CHART_URL.format(coin_id=coin_id)
        params: dict = {"vs_currency": "usd", "days": "7", "interval": "daily"}
        if config.coingecko_api_key:
            params["x_cg_demo_api_key"] = config.coingecko_api_key
        resp = httpx.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        prices = [float(price) for _, price in data.get("prices", [])]
        _upsert_cache(conn, SPARKLINE_SOURCE, coin_id, {"prices": prices})  # WR-03: cache before sleep
        logger.info("Sparkline %s: %d points", coin_id, len(prices))
        time.sleep(CG_SLEEP_SECONDS)  # rate-limit courtesy — last before return
        return prices
    except Exception as exc:
        logger.error("Sparkline fetch failed for %s: %s", coin_id, exc)
        return []


def collect_crypto(config: Config) -> dict:
    """Collecte les prix pour 8 coins crypto + l'indice Fear & Greed.

    Args:
        config: Configuration avec db_path et coingecko_api_key (optionnelle).

    Returns:
        dict avec les clés :
          - coins: dict[coin_id, {price, market_cap, volume_24h, pct_change_24h, symbol}]
          - fear_greed: {value, label} ou None si échec
          - coingecko_failed: bool
          - fear_greed_failed: bool
          - partial: bool (True si CoinGecko a échoué)
          - source_used: str ("coingecko")

    Ne lève jamais d'exception — retourne un dict partiel avec les flags d'erreur.
    """
    conn = get_connection(config.db_path)
    coins_data: dict[str, Any] = {}
    cg_failed = False
    fg_failed = False
    fg_data = None  # CR-01: initialize before try so return is always safe

    try:
        # Vérifier si tous les coins sont en cache
        cached_all = _all_coins_cached(conn)
        if cached_all:
            logger.debug("Cache hit pour tous les %d coins crypto", len(CRYPTO_IDS))
            coins_data = cached_all
        else:
            try:
                params: dict[str, Any] = {
                    "vs_currency": "usd",
                    "ids": ",".join(CRYPTO_IDS),
                    "order": "market_cap_desc",
                    "per_page": 250,
                    "page": 1,
                    "sparkline": "false",
                }
                if config.coingecko_api_key:
                    params["x_cg_demo_api_key"] = config.coingecko_api_key
                resp = httpx.get(CG_MARKETS_URL, params=params, timeout=15)
                resp.raise_for_status()
                items = resp.json()
                time.sleep(CG_SLEEP_SECONDS)
                for item in items:
                    coin_id = item["id"]
                    data = {
                        "price": item["current_price"],
                        "market_cap": item["market_cap"],
                        "volume_24h": item["total_volume"],
                        "pct_change_24h": item["price_change_percentage_24h"],
                        "symbol": item["symbol"].upper(),
                    }
                    _upsert_cache(conn, CACHE_SOURCE, coin_id, data)
                    coins_data[coin_id] = data
                    logger.info(
                        "Fetched %s: price=%.2f, 24h=%.2f%%",
                        coin_id,
                        data["price"],
                        data["pct_change_24h"] or 0,
                    )
            except Exception as exc:
                logger.error("CoinGecko fetch failed: %s", exc)
                cg_failed = True

        # Enrichissement sparkline pour bitcoin et ethereum (indépendant du résultat batch)
        if not cg_failed:
            for coin_id in SPARKLINE_COINS:
                if coin_id in coins_data:
                    coins_data[coin_id]["history"] = _fetch_sparkline(conn, coin_id, config)

        # Fear & Greed (indépendant de CoinGecko)
        fg_data = _fetch_fear_greed(conn)
        if fg_data is None:
            fg_failed = True
    except Exception as e:  # CR-01: outer except to enforce "never raises" contract
        logger.error("Unexpected error in collect_crypto: %s", e)
        cg_failed = True
        fg_failed = True
    finally:
        conn.close()
    return {
        "coins": coins_data,
        "fear_greed": fg_data,
        "coingecko_failed": cg_failed,
        "fear_greed_failed": fg_failed,
        "partial": cg_failed,
        "source_used": CACHE_SOURCE,
    }
