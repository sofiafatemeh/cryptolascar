"""
main.py — Point d'entrée principal de CryptoLascar.

Séquence de démarrage :
1. Parser le mode CLI (--mode daily|weekly|monthly)
2. Charger la configuration depuis .env
3. Configurer le logging
4. Initialiser la base de données SQLite
5. Loguer le démarrage avec timestamp et statut
6. Déclencher la collecte de données via collect_all()
7. Guard mensuel : sortie anticipée si --mode monthly et pas dernier jour du mois
8. Génération et livraison des rapports (select_reports → send_email + write_tweet + archive_report)

Utilisation :
    python main.py --mode daily
    python main.py --mode weekly
    python main.py --mode monthly
"""
from __future__ import annotations

import argparse
import calendar
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
from reporters.dispatch import select_reports
from delivery.email import send_email, archive_report
from delivery.tweet import write_tweet
from delivery.vercel import push_report
from scheduler.utils import is_last_day_of_month

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


def main(argv: list[str] | None = None) -> int:
    """
    Point d'entrée principal.

    Args:
        argv: arguments CLI (None = sys.argv[1:], pour la testabilité)

    Returns:
        int: code de sortie (0 = succès, 1 = erreur de configuration ou de pipeline)
    """
    # Étape 1 : Parser le mode CLI
    parser = argparse.ArgumentParser(
        description="CryptoLascar — pipeline de rapports financiers automatisés"
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["daily", "weekly", "monthly"],
        metavar="MODE",
        help="Type de rapport à générer : daily | weekly | monthly",
    )
    args = parser.parse_args(argv)
    mode = args.mode

    # Étape 2 : Charger la configuration
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

    # Étape 3 : Configurer le logging
    setup_logging(level=config.log_level, log_file=config.log_file or None)

    logger.info("CryptoLascar démarrage — mode=%s", mode)

    # Étape 4 : Initialiser la base de données
    try:
        init_db(config.db_path)
        logger.info("Base de données SQLite initialisée : %s", config.db_path)
    except Exception as exc:
        logger.error("Échec initialisation SQLite : %s", exc, exc_info=True)
        return 1

    # Étape 5 : Loguer le démarrage
    run_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.info("Run démarré à %s", run_at)

    # Étape 6 : Collecte de toutes les données
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

    # Étape 7 : Guard mensuel (D-03) — sortie anticipée si pas le dernier jour du mois
    today = datetime.date.today()
    if mode == "monthly" and not is_last_day_of_month(today):
        logger.info(
            "Mode monthly — aujourd'hui (%s) n'est pas le dernier jour du mois — run ignoré",
            today.isoformat(),
        )
        log_run(config.db_path, "skipped", ",".join(sources_ok), ",".join(sources_failed), "")
        return 0

    # Étape 8 : Génération et livraison des rapports (D-06, D-08)
    date_str = today.isoformat()
    try:
        reports = select_reports(today, data, config)
        for report_type, report_text in reports.items():
            # Paramètres spéciaux pour le rapport mensuel (sujet email)
            month_fr = ""
            year_str = ""
            if report_type == "monthly":
                import locale
                try:
                    locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
                except locale.Error:
                    pass
                month_fr = today.strftime("%B")
                year_str = str(today.year)

            archive_report(report_type, date_str, report_text.plain_text)
            push_report(report_type, today, content_md=report_text.plain_text)
            send_email(
                report_type, date_str, report_text.plain_text, config,
                month=month_fr, year=year_str,
                html_body=report_text.html_body,
            )
            write_tweet(report_type, date_str, report_text.plain_text, config)
            logger.info("Pipeline complété pour report_type=%s date=%s", report_type, date_str)

        # Mise à jour du run_log avec le statut final (D-11)
        log_run(config.db_path, status, ",".join(sources_ok), ",".join(sources_failed), "")
        return 0

    except Exception as exc:
        # D-10 : capture les erreurs reporters/delivery — JAMAIS les credentials
        # T-05-01 : log uniquement report_type + str(exc), jamais smtp_password ou api_key
        err_msg = f"Pipeline error mode={mode}: {exc}"
        logger.error(err_msg, exc_info=True)
        log_run(
            config.db_path,
            "error",
            ",".join(sources_ok),
            ",".join(sources_failed),
            err_msg,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
