"""
main.py — Point d'entrée principal de CryptoLascar.

Séquence de démarrage :
1. Charger la configuration depuis .env
2. Configurer le logging
3. Initialiser la base de données SQLite
4. Loguer le démarrage avec timestamp et statut
5. (Phases 2+) Déclencher la collecte et génération de rapport

Utilisation :
    python main.py
"""
from __future__ import annotations

import datetime
import sqlite3
import sys

from config import get_config
from db.cache import init_db, get_connection
from logging_setup import setup_logging, get_logger


def log_run(
    db_path,
    status: str,
    sources_ok: str = "",
    sources_failed: str = "",
    error_msg: str = "",
) -> None:
    """Enregistre un run dans la table run_log."""
    run_at = datetime.datetime.utcnow().isoformat() + "Z"
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO run_log (run_at, status, sources_ok, sources_failed, error_msg)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_at, status, sources_ok, sources_failed, error_msg),
        )
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    """
    Point d'entrée principal.

    Returns:
        int: code de sortie (0 = succès, 1 = erreur de configuration)
    """
    # Étape 1 : Charger la configuration
    try:
        config = get_config()
    except ValueError as exc:
        # Logging pas encore configuré — utiliser print pour ce cas d'erreur critique
        print(f"ERREUR DE CONFIGURATION : {exc}", file=sys.stderr)
        print(
            "Vérifier que .env existe et contient toutes les variables requises.",
            file=sys.stderr,
        )
        return 1

    # Étape 2 : Configurer le logging
    setup_logging(level=config.log_level, log_file=config.log_file or None)
    logger = get_logger("cryptolascar.main")

    logger.info("CryptoLascar démarrage — initialisation en cours")

    # Étape 3 : Initialiser la base de données
    try:
        init_db(config.db_path)
        logger.info("Base de données SQLite initialisée : %s", config.db_path)
    except Exception as exc:
        logger.error("Échec initialisation SQLite : %s", exc, exc_info=True)
        log_run(config.db_path, status="error", error_msg=str(exc))
        return 1

    # Étape 4 : Loguer le démarrage réussi
    run_at = datetime.datetime.utcnow().isoformat() + "Z"
    logger.info("Run démarré à %s", run_at)
    log_run(config.db_path, status="success")

    # Étape 5 : Placeholder pour les phases suivantes
    logger.info(
        "Foundation OK — collecteurs, générateurs et delivery seront câblés en Phase 2+"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
