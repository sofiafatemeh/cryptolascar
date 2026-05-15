"""
collectors/etf.py — Collecte des prix ETF avec cache SQLite et fallback Alpha Vantage.

Fonctionnalité principale :
  collect_etf(config: Config) -> dict
    - Collecte SPY, QQQ, IWDA.AS, EIMI.AS, CSPX.AS via yfinance (source primaire)
    - Cache SQLite 4h : un deuxième appel dans la fenêtre ne touche pas yfinance
    - Alpha Vantage GLOBAL_QUOTE en supplément si config.alpha_vantage_key défini
    - Dégradation gracieuse : ne lève jamais d'exception non gérée

Menaces couvertes (STRIDE — cf. 02-01-PLAN.md) :
  T-02-01 : api_key jamais loggée — seuls symbol et message d'erreur
  T-02-02 : requêtes SQLite paramétrées uniquement (pas de f-string)
  T-02-03 : sleep 0.5s entre appels AV, quota géré gracieusement
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import yfinance as yf

from config import Config
from db.cache import get_connection
from logging_setup import get_logger

logger = get_logger(__name__)

ETF_TICKERS = ["SPY", "QQQ", "IWDA.AS", "EIMI.AS", "CSPX.AS"]
CACHE_SOURCE = "yfinance_etf"
CACHE_TTL_HOURS = 4
AV_SLEEP_SECONDS = 0.5
AV_BASE_URL = "https://www.alphavantage.co/query"


# ---------------------------------------------------------------------------
# Fonctions utilitaires — horodatage UTC
# ---------------------------------------------------------------------------

def _utcnow_iso() -> str:
    """Retourne l'heure UTC actuelle au format ISO 8601."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expires_iso(hours: int) -> str:
    """Retourne l'heure d'expiration UTC (maintenant + hours)."""
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Fonctions de cache SQLite
# ---------------------------------------------------------------------------

def _get_cached(conn, source: str, symbol: str) -> dict | None:
    """
    Lit la ligne de cache non expirée pour (source, symbol).
    Retourne le dict désérialisé ou None si absence / expiration.
    """
    now = _utcnow_iso()
    row = conn.execute(
        "SELECT data_json FROM market_cache WHERE source=? AND symbol=? AND expires_at > ?",
        (source, symbol, now),
    ).fetchone()
    return json.loads(row["data_json"]) if row else None


def _upsert_cache(conn, source: str, symbol: str, data: dict) -> None:
    """
    Insère ou remplace une entrée de cache pour (source, symbol).
    Utilise des requêtes paramétrées — pas d'injection SQL possible.
    """
    conn.execute(
        "INSERT OR REPLACE INTO market_cache "
        "(source, symbol, data_json, fetched_at, expires_at) VALUES (?,?,?,?,?)",
        (source, symbol, json.dumps(data), _utcnow_iso(), _expires_iso(CACHE_TTL_HOURS)),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Collecte yfinance
# ---------------------------------------------------------------------------

def _fetch_yfinance(symbol: str) -> dict:
    """
    Récupère lastPrice, previousClose, regularMarketVolume pour un ticker.
    Peut lever une exception — à gérer par l'appelant.
    """
    info = yf.Ticker(symbol).fast_info
    price = float(info.lastPrice)
    prev = float(info.previousClose)
    vol = int(info.regularMarketVolume) if info.regularMarketVolume else 0
    pct = (price - prev) / prev * 100 if prev else 0.0
    return {
        "price": price,
        "prev_close": prev,
        "pct_change": round(pct, 4),
        "volume": vol,
    }


# ---------------------------------------------------------------------------
# Collecte 7-day percentage change (via yfinance history)
# ---------------------------------------------------------------------------

def _fetch_1w_pct(symbol: str) -> float | None:
    """
    Calcule la variation pct_change_1w (7 jours) pour symbol via yfinance history.
    Retourne None en cas d'erreur — l'appelant traite None comme donnée manquante.

    Sécurité T-08-01 : hist["Close"] validé numérique via float() ; tout TypeError
    tombe dans le except → None.
    """
    try:
        hist = yf.Ticker(symbol).history(period="7d")
        if hist.empty or len(hist) < 2:
            return None
        first_close = float(hist["Close"].iloc[0])
        last_close = float(hist["Close"].iloc[-1])
        if not first_close:
            return None
        return round((last_close - first_close) / first_close * 100, 4)
    except Exception as e:
        logger.warning("1w history fetch failed for %s: %s", symbol, e)
        return None


# ---------------------------------------------------------------------------
# Collecte Alpha Vantage (supplément)
# ---------------------------------------------------------------------------

def _fetch_alpha_vantage(symbol: str, api_key: str) -> dict | None:
    """
    Appelle Alpha Vantage GLOBAL_QUOTE pour un ticker.

    Retourne un dict avec av_price/av_volume si succès.
    Retourne None si quota épuisé (Note/Information dans la réponse) ou erreur réseau.

    Sécurité T-02-01 : api_key jamais loggée — seuls symbol et message d'erreur.
    """
    try:
        resp = httpx.get(
            AV_BASE_URL,
            params={"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        # Quota épuisé ou limite de fréquence — réponse avec "Note" ou "Information"
        if "Note" in data or "Information" in data:
            return None
        gq = data.get("Global Quote", {})
        return {
            "av_price": gq.get("05. price"),
            "av_volume": gq.get("06. volume"),
        }
    except Exception as e:
        # T-02-01 : on logue symbol et message, PAS api_key
        logger.warning("Alpha Vantage fetch failed for %s: %s", symbol, e)
        return None


# ---------------------------------------------------------------------------
# Fonction principale exportée
# ---------------------------------------------------------------------------

def collect_etf(config: Config) -> dict:
    """
    Collecte les prix ETF pour SPY, QQQ, IWDA.AS, EIMI.AS, CSPX.AS.

    Comportement :
    - Vérifie le cache SQLite (TTL 4h) avant tout appel réseau
    - Source primaire : yfinance (lastPrice, previousClose, volume)
    - Source supplémentaire : Alpha Vantage si config.alpha_vantage_key défini
    - Dégradation gracieuse : retourne toujours un dict, même si tout échoue

    Args:
        config: Config avec db_path et optionnellement alpha_vantage_key

    Returns:
        {
          "tickers": {
            "SPY": {"price": float, "prev_close": float, "pct_change": float, "volume": int},
            ...
          },
          "alpha_vantage_failed": bool,  # True si quota AV épuisé ou clé absente
          "partial": bool,               # True si au moins un ticker a échoué
          "source_used": "yfinance_etf"
        }

    Ne lève jamais d'exception — erreurs encapsulées dans le dict retourné.
    """
    conn = get_connection(config.db_path)
    tickers_data: dict[str, Any] = {}
    partial = False
    # Si pas de clé AV, on considère AV comme indisponible dès le départ
    av_failed = not bool(config.alpha_vantage_key)

    try:
        for symbol in ETF_TICKERS:
            # --- 1. Vérification du cache ---
            cached = _get_cached(conn, CACHE_SOURCE, symbol)
            if cached and "pct_change_1w" in cached:  # WR-02: treat stale entries without key as miss
                logger.debug("Cache hit pour %s", symbol)
                tickers_data[symbol] = cached
                continue

            # --- 2. Collecte yfinance ---
            try:
                data = _fetch_yfinance(symbol)
                data["pct_change_1w"] = _fetch_1w_pct(symbol)
                logger.info("yfinance OK pour %s : price=%.2f", symbol, data["price"])

                # --- 3. Enrichissement Alpha Vantage (si clé présente, ticker OK, pas encore en échec) ---
                if config.alpha_vantage_key and data.get("price") is not None and not av_failed:
                    time.sleep(AV_SLEEP_SECONDS)
                    av_data = _fetch_alpha_vantage(symbol, config.alpha_vantage_key)
                    if av_data is None:
                        av_failed = True
                        logger.warning(
                            "Alpha Vantage quota épuisé — basculement sur yfinance uniquement (T-02-03)"
                        )
                    else:
                        data.update(av_data)

                # --- 4. Mise en cache (succès uniquement) et accumulation ---
                _upsert_cache(conn, CACHE_SOURCE, symbol, data)
                tickers_data[symbol] = data
            except Exception as e:
                logger.error("yfinance échec pour %s : %s", symbol, e)
                tickers_data[symbol] = {
                    "price": None,
                    "prev_close": None,
                    "pct_change": None,
                    "volume": None,
                    "error": str(e),
                }
                partial = True

    except Exception as e:
        # Filet de sécurité : collect_etf ne propage jamais d'exception (Test 5)
        logger.error("Erreur inattendue dans collect_etf : %s", e)
        partial = True
    finally:
        conn.close()

    return {
        "tickers": tickers_data,
        "alpha_vantage_failed": av_failed,
        "partial": partial,
        "source_used": CACHE_SOURCE,
    }
