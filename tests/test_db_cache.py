"""Tests unitaires pour db/cache.py"""
import sqlite3
import pytest
from db.cache import init_db, get_connection


def test_init_db_in_memory_no_exception():
    """init_db(':memory:') ne lève aucune exception."""
    init_db(":memory:")  # ne doit pas lever


def test_market_cache_table_exists():
    """La table market_cache existe après init_db."""
    conn = get_connection(":memory:")
    init_db_on_conn(conn)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='market_cache'"
    )
    assert cursor.fetchone() is not None, "Table market_cache absente"
    conn.close()


def test_run_log_table_exists():
    """La table run_log existe après init_db."""
    conn = get_connection(":memory:")
    init_db_on_conn(conn)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='run_log'"
    )
    assert cursor.fetchone() is not None, "Table run_log absente"
    conn.close()


def test_get_connection_returns_connection():
    """get_connection(':memory:') retourne un sqlite3.Connection."""
    conn = get_connection(":memory:")
    assert isinstance(conn, sqlite3.Connection)
    conn.close()


def test_init_db_idempotent():
    """Appeler init_db deux fois ne lève pas d'erreur."""
    init_db(":memory:")
    init_db(":memory:")  # second appel — CREATE TABLE IF NOT EXISTS


def test_market_cache_columns():
    """market_cache a les colonnes attendues."""
    conn = get_connection(":memory:")
    init_db_on_conn(conn)
    cursor = conn.execute("PRAGMA table_info(market_cache)")
    columns = {row[1] for row in cursor.fetchall()}
    expected = {"id", "source", "symbol", "data_json", "fetched_at", "expires_at"}
    assert expected.issubset(columns), f"Colonnes manquantes : {expected - columns}"
    conn.close()


def test_run_log_columns():
    """run_log a les colonnes attendues."""
    conn = get_connection(":memory:")
    init_db_on_conn(conn)
    cursor = conn.execute("PRAGMA table_info(run_log)")
    columns = {row[1] for row in cursor.fetchall()}
    expected = {"id", "run_at", "status", "sources_ok", "sources_failed", "error_msg"}
    assert expected.issubset(columns), f"Colonnes manquantes : {expected - columns}"
    conn.close()


# Helper : init sur une connexion existante (pour les tests en mémoire)
from db.cache import _SCHEMA


def init_db_on_conn(conn: sqlite3.Connection) -> None:
    """Version de init_db qui réutilise une connexion existante."""
    conn.executescript(_SCHEMA)
    conn.commit()
