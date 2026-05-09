"""
config.py — Chargement et validation centralisée de la configuration.
Toutes les variables proviennent de .env via python-dotenv.
Aucun secret hardcodé dans ce fichier.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv


def _require(name: str) -> str:
    """Retourne la valeur de la variable d'environnement ou lève ValueError."""
    value = os.getenv(name)
    if not value:
        raise ValueError(
            f"Variable d'environnement manquante ou vide : {name}. "
            f"Vérifier .env (voir .env.example pour la liste complète)."
        )
    return value


def _optional(name: str, default: str = "") -> str:
    """Retourne la valeur de la variable ou la valeur par défaut."""
    return os.getenv(name, default)


@dataclass
class Config:
    """Configuration complète du système CryptoLascar."""

    # SMTP
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    recipient_list: List[str]

    # LLM
    anthropic_api_key: str
    anthropic_model: str

    # APIs de données
    coingecko_api_key: str
    alpha_vantage_key: str
    fred_api_key: str
    newsapi_key: str

    # Storage
    db_path: Path

    # Logging
    log_level: str
    log_file: str


def get_config(env_file: str = ".env") -> Config:
    """
    Charge le fichier .env et retourne un objet Config validé.
    Lève ValueError si une variable obligatoire est absente.

    Args:
        env_file: Chemin vers le fichier .env (défaut : ".env" à la racine)

    Returns:
        Config: objet de configuration complet et validé

    Raises:
        ValueError: si une variable obligatoire est manquante ou vide
    """
    load_dotenv(env_file, override=False)

    # Variables SMTP obligatoires
    smtp_host = _require("SMTP_HOST")
    smtp_port_str = _require("SMTP_PORT")
    smtp_user = _require("SMTP_USER")
    smtp_password = _require("SMTP_PASSWORD")
    recipient_raw = _require("RECIPIENT_LIST")

    # Variables LLM obligatoires
    anthropic_api_key = _require("ANTHROPIC_API_KEY")
    anthropic_model = _optional("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # APIs de données optionnelles — absentes = collector désactivé (dégradation gracieuse)
    coingecko_api_key = _optional("COINGECKO_API_KEY")
    alpha_vantage_key = _optional("ALPHA_VANTAGE_KEY")
    fred_api_key = _optional("FRED_API_KEY")
    newsapi_key = _optional("NEWSAPI_KEY")

    # Storage
    db_path_str = _optional("DB_PATH", "cryptolascar.db")

    # Logging
    log_level = _optional("LOG_LEVEL", "INFO")
    log_file = _optional("LOG_FILE", "")

    # Conversions de types
    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        raise ValueError(f"SMTP_PORT doit être un entier, reçu : {smtp_port_str!r}")

    recipient_list = [r.strip() for r in recipient_raw.split(",") if r.strip()]
    if not recipient_list:
        raise ValueError("RECIPIENT_LIST ne peut pas être vide.")

    return Config(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        recipient_list=recipient_list,
        anthropic_api_key=anthropic_api_key,
        anthropic_model=anthropic_model,
        coingecko_api_key=coingecko_api_key,
        alpha_vantage_key=alpha_vantage_key,
        fred_api_key=fred_api_key,
        newsapi_key=newsapi_key,
        db_path=Path(db_path_str),
        log_level=log_level.upper(),
        log_file=log_file,
    )
