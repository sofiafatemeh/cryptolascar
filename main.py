"""
main.py — Point d'entrée principal de CryptoLascar.

Séquence de démarrage :
1. Charger la configuration depuis .env
2. Configurer le logging
3. Initialiser la base de données SQLite
4. Loguer le démarrage avec timestamp et statut
5. (Phase 2) Déclencher la collecte de données via collect_all()
6. (Phases 3+) Génération de rapport et delivery

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
from collectors.etf import collect_etf
from collectors.crypto import collect_crypto
from collectors.pea import collect_pea
from collectors.macro import collect_macro
from collectors.news import collect_news

logger = get_logger("cryptolascar.main")


def collect_all(config: "Config") -> dict:
    """Orchestre les 5 collecteurs de données. Capture les exceptions par collecteur.

    Retourne un dict combiné avec les données de chaque source et des métadonnées
    d'exécution. Un collecteur en échec n'interrompt pas le run — dégradation gracieuse
    garantie (T-02-23).

    Args:
        config: Configuration complète du système (db_path, clés API, etc.)

    Returns:
        dict avec les clés :
          - "etf"    : résultat de collect_etf (ou {"error": ..., "source_failed": True})
          - "crypto" : résultat de collect_crypto
          - "pea"    : résultat de collect_pea
          - "macro"  : résultat de collect_macro
          - "news"   : résultat de collect_news
          - "_meta"  : {sources_ok, sources_failed, collected_at}

    Ne propage jamais d'exception — les erreurs sont encapsulées dans le dict.
    """
    results: dict = {}
    sources_ok: list[str] = []
    sources_failed: list[str] = []

    collectors_map = {
        "etf": collect_etf,
        "crypto": collect_crypto,
        "pea": collect_pea,
        "macro": collect_macro,
        "news": collect_news,
    }

    for name, collector_fn in collectors_map.items():
        try:
            data = collector_fn(config)
            results[name] = data
            if data.get("partial"):
                sources_ok.append(f"{name}(partial)")
            else:
                sources_ok.append(name)
            logger.info(
                "Collecteur '%s' terminé — partial=%s", name, data.get("partial", False)
            )
        except Exception as e:
            # T-02-23 : exception d'un collecteur ne propage jamais vers l'orchestrateur
            # T-02-22 : on logue uniquement le message d'exception, jamais les API keys
            logger.error(
                "Collecteur '%s' échoué avec une exception non gérée : %s", name, e
            )
            results[name] = {"error": str(e), "source_failed": True}
            sources_failed.append(name)

    results["_meta"] = {
        "sources_ok": sources_ok,
        "sources_failed": sources_failed,
        "collected_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }
    return results


def log_run(
    db_path,
    status: str,
    sources_ok: str = "",
    sources_failed: str = "",
    error_msg: str = "",
) -> None:
    """Enregistre un run dans la table run_log."""
    run_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
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

    logger.info("CryptoLascar démarrage — initialisation en cours")

    # Étape 3 : Initialiser la base de données
    try:
        init_db(config.db_path)
        logger.info("Base de données SQLite initialisée : %s", config.db_path)
    except Exception as exc:
        logger.error("Échec initialisation SQLite : %s", exc, exc_info=True)
        return 1

    # Étape 4 : Loguer le démarrage
    run_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.info("Run démarré à %s", run_at)

    # Étape 5 : Collecte de toutes les données (Phase 2)
    logger.info("Démarrage de la collecte de données...")
    data = collect_all(config)
    meta = data.get("_meta", {})
    sources_ok = meta.get("sources_ok", [])
    sources_failed = meta.get("sources_failed", [])

    if sources_failed:
        status = "partial"
        logger.warning(
            "Run partiel — sources en échec : %s", ", ".join(sources_failed)
        )
    else:
        status = "success"
        logger.info(
            "Collecte complète — sources OK : %s", ", ".join(sources_ok)
        )

    log_run(
        config.db_path,
        status,
        ",".join(sources_ok),
        ",".join(sources_failed),
        "",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
