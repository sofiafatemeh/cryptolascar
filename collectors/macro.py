"""
collectors/macro.py — Collecte des indicateurs macroéconomiques via FRED API.

Séries collectées :
  - DGS10    : Taux 10-year Treasury (rendement obligataire long)
  - DGS2     : Taux 2-year Treasury (rendement obligataire court)
  - CPIAUCSL : Consumer Price Index (inflation US)
  - M2SL     : M2 Money Stock (masse monétaire)

Cache SQLite 24h — une série en cache ne déclenche pas d'appel FRED.
Sleep 1.0s entre chaque appel FRED pour respecter le rate limit.
Dégradation gracieuse — jamais d'exception propagée.

Sécurité (T-02-13) : la clé API n'est jamais loguée — seul le series_id et le
message d'erreur sont inclus dans les logs.
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

FRED_SERIES = ["DGS10", "DGS2", "CPIAUCSL", "M2SL"]
CACHE_SOURCE = "fred"
CACHE_TTL_HOURS = 24
FRED_SLEEP_SECONDS = 1.0
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def _utcnow_iso() -> str:
    """Retourne l'heure UTC courante en format ISO 8601."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expires_iso(hours: int) -> str:
    """Retourne l'heure d'expiration UTC en format ISO 8601."""
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _get_cached(conn, source: str, symbol: str) -> dict | None:
    """
    Recherche une entrée valide dans market_cache (expires_at > maintenant).
    Retourne le dict désérialisé ou None si absent / expiré.
    """
    now = _utcnow_iso()
    row = conn.execute(
        "SELECT data_json FROM market_cache WHERE source=? AND symbol=? AND expires_at > ?",
        (source, symbol, now),
    ).fetchone()
    return json.loads(row["data_json"]) if row else None


def _upsert_cache(conn, source: str, symbol: str, data: dict) -> None:
    """
    Insère ou remplace une entrée dans market_cache.
    Requête paramétrée pour éviter les injections SQL (T-02-14).
    """
    conn.execute(
        "INSERT OR REPLACE INTO market_cache "
        "(source, symbol, data_json, fetched_at, expires_at) "
        "VALUES (?,?,?,?,?)",
        (
            source,
            symbol,
            json.dumps(data),
            _utcnow_iso(),
            _expires_iso(CACHE_TTL_HOURS),
        ),
    )
    conn.commit()


def _fetch_fred_series(series_id: str, api_key: str) -> dict:
    """
    Appelle l'API FRED pour récupérer l'observation la plus récente d'une série.

    Lève une exception si la requête échoue ou si aucune valeur valide n'est trouvée.
    Note : api_key est passé comme paramètre httpx — jamais inclus dans les logs (T-02-13).
    """
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 2,
    }
    resp = httpx.get(FRED_BASE_URL, params=params, timeout=15)
    observations = resp.json().get("observations", [])
    # Cherche la première observation non-manquante ("." = donnée non disponible)
    for obs in observations:
        if obs["value"] != ".":
            return {
                "value": float(obs["value"]),
                "date": obs["date"],
                "series_id": series_id,
            }
    raise ValueError(f"No valid observation found for {series_id}")


def collect_macro(config: Config) -> dict:
    """
    Collecte les indicateurs macro via FRED API : DGS10, DGS2, CPIAUCSL, M2SL.

    Comportement :
    - Si fred_api_key vide : fred_failed=True, series={}, pas d'appel HTTP
    - Cache SQLite 24h par série (source="fred")
    - Sleep 1.0s après chaque appel FRED réussi (rate limit T-02-15)
    - Échec d'une série : partial=True, value=None pour cette série
    - Jamais d'exception propagée — toujours retourne un dict

    Returns:
        dict avec les clés :
          "series"      : dict[series_id -> {"value", "date", "series_id"}]
          "fred_failed" : bool (True si clé manquante)
          "partial"     : bool (True si au moins une série en échec)
          "source_used" : "fred"
    """
    if not config.fred_api_key:
        logger.warning("FRED_API_KEY non configurée — collecte macro ignorée")
        return {
            "series": {},
            "fred_failed": True,
            "partial": True,
            "source_used": CACHE_SOURCE,
        }

    conn = get_connection(config.db_path)
    series_data: dict[str, Any] = {}
    fred_failed = False
    partial = False
    first_api_call = True  # Contrôle du sleep avant le premier appel

    for series_id in FRED_SERIES:
        # Vérification du cache avant tout appel FRED
        cached = _get_cached(conn, CACHE_SOURCE, series_id)
        if cached:
            logger.debug("Cache hit FRED série %s", series_id)
            series_data[series_id] = cached
            continue

        # Cache miss — appel FRED avec sleep de rate-limiting (T-02-15)
        try:
            if not first_api_call:
                time.sleep(FRED_SLEEP_SECONDS)
            first_api_call = False

            data = _fetch_fred_series(series_id, config.fred_api_key)

            # Sleep après chaque appel réussi (1s entre les appels)
            time.sleep(FRED_SLEEP_SECONDS)

            _upsert_cache(conn, CACHE_SOURCE, series_id, data)
            logger.info(
                "FRED %s récupéré : value=%.4f (date=%s)",
                series_id,
                data["value"],
                data["date"],
            )
            series_data[series_id] = data

        except Exception as e:
            # Log uniquement le series_id et le message d'erreur — jamais l'api_key (T-02-13)
            logger.error("Échec FRED pour %s : %s", series_id, e)
            series_data[series_id] = {
                "value": None,
                "date": None,
                "series_id": series_id,
                "error": str(e),
            }
            partial = True

    conn.close()
    return {
        "series": series_data,
        "fred_failed": fred_failed,
        "partial": partial,
        "source_used": CACHE_SOURCE,
    }
