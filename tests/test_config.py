"""Tests unitaires pour config.py"""
import os
import pytest
from unittest.mock import patch


FULL_ENV = {
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": "587",
    "SMTP_USER": "test@gmail.com",
    "SMTP_PASSWORD": "secret",
    "RECIPIENT_LIST": "a@example.com,b@example.com",
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "ANTHROPIC_MODEL": "claude-sonnet-4-6",
    "COINGECKO_API_KEY": "cg-test",
    "ALPHA_VANTAGE_KEY": "av-test",
    "FRED_API_KEY": "fred-test",
    "NEWSAPI_KEY": "news-test",
}


def _get_config_with_env(extra_env: dict = None, remove_keys: list = None):
    """Helper : charge get_config() avec un environnement contrôlé."""
    from config import get_config
    env = dict(FULL_ENV)
    if extra_env:
        env.update(extra_env)
    if remove_keys:
        for k in remove_keys:
            env.pop(k, None)
    # On passe un fichier .env inexistant pour forcer l'usage des vars d'env mockées
    with patch.dict(os.environ, env, clear=True):
        return get_config(env_file=".env.nonexistent")


def test_get_config_full_env_no_exception():
    """Un .env complet ne lève aucune exception."""
    config = _get_config_with_env()
    assert config is not None


def test_missing_smtp_host_raises_valueerror():
    """SMTP_HOST manquant lève ValueError mentionnant SMTP_HOST."""
    with pytest.raises(ValueError, match="SMTP_HOST"):
        _get_config_with_env(remove_keys=["SMTP_HOST"])


def test_missing_anthropic_api_key_raises_valueerror():
    """ANTHROPIC_API_KEY manquant lève ValueError mentionnant ANTHROPIC_API_KEY."""
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        _get_config_with_env(remove_keys=["ANTHROPIC_API_KEY"])


def test_smtp_host_value():
    """config.smtp_host retourne la valeur du .env."""
    config = _get_config_with_env()
    assert config.smtp_host == "smtp.gmail.com"


def test_recipient_list_is_list():
    """recipient_list est une liste Python, pas une string."""
    config = _get_config_with_env()
    assert isinstance(config.recipient_list, list)
    assert len(config.recipient_list) == 2
    assert "a@example.com" in config.recipient_list


def test_anthropic_model_default():
    """ANTHROPIC_MODEL absent => valeur par défaut claude-sonnet-4-6."""
    config = _get_config_with_env(remove_keys=["ANTHROPIC_MODEL"])
    assert config.anthropic_model == "claude-sonnet-4-6"
