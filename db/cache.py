"""
db/cache.py — Initialisation SQLite et fonctions de cache des données de marché.

Deux tables :
- market_cache : cache des données collectées (TTL-based)
- run_log      : historique des exécutions du pipeline
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union


# Schema SQL — CREATE TABLE IF NOT EXISTS pour idempotence
_SCHEMA = """
CREATE TABLE IF NOT EXISTS market_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT    NOT NULL,          -- ex: "coingecko", "yfinance", "fred"
    symbol      TEXT    NOT NULL,          -- ex: "BTC", "SPY", "DGS10"
    data_json   TEXT    NOT NULL,          -- données sérialisées en JSON
    fetched_at  TEXT    NOT NULL,          -- ISO 8601 UTC
    expires_at  TEXT    NOT NULL           -- ISO 8601 UTC (fetched_at + TTL)
);

CREATE INDEX IF NOT EXISTS idx_market_cache_source_symbol
    ON market_cache (source, symbol);

CREATE TABLE IF NOT EXISTS run_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at          TEXT    NOT NULL,      -- ISO 8601 UTC
    status          TEXT    NOT NULL,      -- "success" | "partial" | "error"
    sources_ok      TEXT    DEFAULT '',   -- sources ayant répondu (CSV)
    sources_failed  TEXT    DEFAULT '',   -- sources en échec (CSV)
    error_msg       TEXT    DEFAULT ''    -- message d'erreur si status=error
);
"""


def get_connection(db_path: Union[str, Path] = "cryptolascar.db") -> sqlite3.Connection:
    """
    Retourne une connexion SQLite vers db_path.
    Crée le fichier DB si absent. Active WAL pour de meilleures performances.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Union[str, Path] = "cryptolascar.db") -> None:
    """
    Initialise la base de données SQLite : crée les tables si elles n'existent pas.
    Idempotent — peut être appelé plusieurs fois sans erreur.

    Args:
        db_path: Chemin vers le fichier SQLite. Passer ":memory:" pour les tests.
    """
    conn = get_connection(db_path)
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()
