"""
logging_setup.py — Configuration du logging structuré pour CryptoLascar.

Utilise structlog si disponible, sinon fallback sur le module logging standard.
Chaque entrée de log inclut : timestamp ISO 8601, niveau, logger name, message.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Configure le logging pour l'application.

    Args:
        level: Niveau de log ("DEBUG", "INFO", "WARNING", "ERROR")
        log_file: Chemin vers le fichier de log. Si vide ou None, log uniquement stdout.

    Returns:
        logging.Logger: logger racine configuré
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Format : timestamp ISO + niveau + logger + message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handlers: list[logging.Handler] = []

    # Handler stdout (toujours actif)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    handlers.append(stdout_handler)

    # Handler fichier (optionnel)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configuration du logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Supprimer les handlers existants pour éviter les doublons
    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger nommé (child du logger racine)."""
    return logging.getLogger(name)
