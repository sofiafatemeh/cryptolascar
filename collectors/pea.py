"""
collectors/pea.py — Collecte des cours PEA France et vérification d'éligibilité.

Fonctionnalités :
- Prix des 5 instruments PEA via yfinance avec cache SQLite 4h
- Vérification d'éligibilité PEA statique (dictionnaire AMF/Euronext hardcodé)
- Détection de changement d'éligibilité avec persistance en base (source="pea_eligibility")
- Dégradation gracieuse : partial=True si un ticker échoue, jamais d'exception propagée

Décisions de conception :
- D-04 : PEA tickers = [^FCHI, ^SBF120, CW8.PA, PAEEM.PA, PANX.PA]
- D-05 : Éligibilité = dictionnaire statique dans pea.py, pas d'appel réseau
- D-06 : eligibility_changed=True dans le résultat si statut changé ; log via get_logger()
- D-07 : Dernier statut connu persisté dans market_cache avec source="pea_eligibility"

Menaces mitigées (threat model 02-03) :
- T-02-09 : Requêtes SQLite paramétrées uniquement — pas d'interpolation de chaînes SQL
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import yfinance as yf

from config import Config
from db.cache import get_connection
from logging_setup import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

PEA_TICKERS = ["^FCHI", "^SBF120", "CW8.PA", "PAEEM.PA", "PANX.PA"]
PRICE_SOURCE = "yfinance_pea"
ELIGIBILITY_SOURCE = "pea_eligibility"
CACHE_TTL_HOURS = 4

# Référence statique AMF/Euronext — mise à jour manuelle lors des changements AMF
# Représente les ISINs connus des instruments éligibles PEA suivis.
PEA_ELIGIBLE_ISINS: dict[str, str | None] = {
    "CW8.PA": "LU1681043599",    # Amundi MSCI World UCITS ETF — éligible PEA
    "PAEEM.PA": "LU1681045537",  # Amundi MSCI EM UCITS ETF — éligible PEA
    "PANX.PA": "LU1681038599",   # Amundi Nasdaq-100 UCITS ETF — éligible PEA
    "^FCHI": None,               # Indice CAC 40 — pas un titre, pas d'ISIN
    "^SBF120": None,             # Indice SBF 120 — pas un titre, pas d'ISIN
}

PEA_ELIGIBILITY_STATUS: dict[str, bool | None] = {
    "CW8.PA": True,
    "PAEEM.PA": True,
    "PANX.PA": True,
    "^FCHI": None,    # Indice — non directement investissable
    "^SBF120": None,
}


# ---------------------------------------------------------------------------
# Utilitaires cache
# ---------------------------------------------------------------------------


def _utcnow_iso() -> str:
    """Retourne la date/heure UTC courante au format ISO 8601."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expires_iso(hours: int) -> str:
    """Retourne la date d'expiration UTC (utcnow + hours) au format ISO 8601."""
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_cached(conn, source: str, symbol: str, check_expiry: bool = True) -> dict | None:
    """
    Retourne les données en cache pour (source, symbol) ou None si absent/expiré.

    Args:
        conn: Connexion SQLite active
        source: Source des données (ex: "yfinance_pea", "pea_eligibility")
        symbol: Symbole du ticker
        check_expiry: Si True, filtre les lignes expirées (expires_at > utcnow)

    Returns:
        dict des données ou None
    """
    if check_expiry:
        now = _utcnow_iso()
        row = conn.execute(
            "SELECT data_json FROM market_cache WHERE source=? AND symbol=? AND expires_at > ?",
            (source, symbol, now),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT data_json FROM market_cache WHERE source=? AND symbol=?",
            (source, symbol),
        ).fetchone()
    return json.loads(row["data_json"]) if row else None


def _upsert_cache(
    conn, source: str, symbol: str, data: dict, ttl_hours: int | None = None
) -> None:
    """
    Insère ou remplace une ligne dans market_cache.

    Args:
        conn: Connexion SQLite active
        source: Source des données
        symbol: Symbole du ticker
        data: Données à sérialiser en JSON
        ttl_hours: TTL en heures. Si None, expire en 2099 (stockage permanent).

    Note: Utilise des requêtes paramétrées — T-02-09 mitigé.
    """
    expires = _expires_iso(ttl_hours) if ttl_hours else "2099-12-31T23:59:59Z"
    conn.execute(
        "INSERT OR REPLACE INTO market_cache (source, symbol, data_json, fetched_at, expires_at)"
        " VALUES (?,?,?,?,?)",
        (source, symbol, json.dumps(data), _utcnow_iso(), expires),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Vérification d'éligibilité PEA
# ---------------------------------------------------------------------------


def _check_eligibility(conn) -> tuple[dict[str, Any], bool]:
    """
    Vérifie l'éligibilité PEA de tous les tickers avec un statut défini.

    Logique :
    1. Pour chaque ticker avec un statut booléen (True/False, pas None) :
       a. Récupère le dernier statut connu en cache (source="pea_eligibility")
       b. Si absent : premier run — upsert sans alerte
       c. Si présent et différent : log warning + eligibility_changed=True
       d. Upsert le statut actuel dans tous les cas

    Returns:
        Tuple (eligibility_dict, eligibility_changed)
        - eligibility_dict : {ticker: {"eligible": bool, "isin": str|None}}
        - eligibility_changed : True si au moins un changement détecté
    """
    eligibility: dict[str, Any] = {}
    changed = False

    for ticker, current_eligible in PEA_ELIGIBILITY_STATUS.items():
        if current_eligible is None:
            continue  # Indice — non applicable à l'éligibilité PEA

        cached = _get_cached(conn, ELIGIBILITY_SOURCE, ticker, check_expiry=False)
        if cached is not None:
            last_eligible = cached.get("eligible")
            if last_eligible != current_eligible:
                logger.warning(
                    "PEA eligibility change detected for %s: %s -> %s",
                    ticker,
                    last_eligible,
                    current_eligible,
                )
                changed = True

        data = {"eligible": current_eligible, "isin": PEA_ELIGIBLE_ISINS[ticker]}
        _upsert_cache(conn, ELIGIBILITY_SOURCE, ticker, data)
        eligibility[ticker] = data

    return eligibility, changed


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------


def collect_pea(config: Config) -> dict:
    """
    Collecte les cours PEA France et vérifie l'éligibilité AMF/Euronext.

    Pour chaque ticker PEA :
    - Cherche dans le cache (source="yfinance_pea", TTL 4h)
    - En cas de cache miss : interroge yfinance.Ticker.fast_info
    - En cas d'échec yfinance : enregistre price=None et partial=True

    Vérifie ensuite l'éligibilité de tous les tickers (indépendamment du cache prix).

    Args:
        config: Configuration du système (db_path utilisé)

    Returns:
        dict avec les clés :
          - "prices" : dict {ticker: {"price", "prev_close", "pct_change", "volume"}}
          - "eligibility" : dict {ticker: {"eligible", "isin"}}
          - "eligibility_changed" : bool — True si au moins un changement détecté
          - "partial" : bool — True si au moins un ticker a échoué
          - "source_used" : str — "yfinance_pea"

    Raises:
        Jamais — dégradation gracieuse garantie.
    """
    conn = get_connection(config.db_path)
    prices: dict[str, Any] = {}
    partial = False

    for ticker in PEA_TICKERS:
        cached = _get_cached(conn, PRICE_SOURCE, ticker, check_expiry=True)
        if cached:
            logger.debug("Cache hit pour le ticker PEA %s", ticker)
            prices[ticker] = cached
            continue

        try:
            info = yf.Ticker(ticker).fast_info
            price = float(info.lastPrice)
            prev = float(info.previousClose)
            vol = int(info.regularMarketVolume) if info.regularMarketVolume else 0
            pct = (price - prev) / prev * 100 if prev else 0.0
            data = {
                "price": price,
                "prev_close": prev,
                "pct_change": round(pct, 4),
                "volume": vol,
            }
            _upsert_cache(conn, PRICE_SOURCE, ticker, data, ttl_hours=CACHE_TTL_HOURS)
            logger.info("Cours PEA récupéré %s : price=%.2f (%.2f%%)", ticker, price, pct)
            prices[ticker] = data
        except Exception as exc:
            logger.error(
                "Échec yfinance pour le ticker PEA %s : %s", ticker, exc
            )
            prices[ticker] = {
                "price": None,
                "prev_close": None,
                "pct_change": None,
                "volume": None,
                "error": str(exc),
            }
            partial = True

    eligibility, eligibility_changed = _check_eligibility(conn)
    conn.close()

    return {
        "prices": prices,
        "eligibility": eligibility,
        "eligibility_changed": eligibility_changed,
        "partial": partial,
        "source_used": PRICE_SOURCE,
    }
