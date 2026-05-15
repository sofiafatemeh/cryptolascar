"""
tests/test_dispatch.py — Tests TDD pour reporters/dispatch.py (REPT-04).

RED phase : ces tests doivent échouer (ImportError) tant que reporters/dispatch.py
n'est pas implémenté.

Couverture :
  Test 1 — Jour en semaine (pas dernier jour) → uniquement "daily"
  Test 2 — Dimanche mais pas dernier jour → uniquement "weekly"
  Test 3 — Dernier jour du mois (semaine) → uniquement "monthly"
  Test 4 — Dernier jour ET dimanche → DEUX documents "monthly" + "weekly" (REPT-04)
  Test 5 — Le dispatcher ne lève jamais si un builder échoue

  + Tests utilitaires :
  test_is_last_day_of_month_2026_april
  test_is_sunday
"""
from __future__ import annotations

import copy
import os
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from config import Config
from db.cache import init_db

# Import à tester — provoquera ImportError (RED gate) jusqu'à l'implémentation
from reporters.dispatch import select_reports, is_last_day_of_month, is_sunday


# ---------------------------------------------------------------------------
# Fixture : Config avec DB temporaire initialisée
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_config():
    """Crée une Config avec db_path temporaire et tables initialisées."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path)
    cfg = Config(
        smtp_host="localhost",
        smtp_port=587,
        smtp_user="user@example.com",
        smtp_password="password",
        recipient_list=["dest@example.com"],
        anthropic_api_key="test-anthropic-key",
        anthropic_model="claude-sonnet-4-6",
        coingecko_api_key="",
        alpha_vantage_key="",
        fred_api_key="",
        newsapi_key="",
        db_path=Path(db_path),
        log_level="DEBUG",
        log_file="",
    )
    yield cfg
    os.unlink(db_path)


@pytest.fixture
def empty_data():
    """Dict de données vide — suffisant pour tester la logique calendaire."""
    return {}


# ---------------------------------------------------------------------------
# Tests utilitaires — is_last_day_of_month et is_sunday
# ---------------------------------------------------------------------------


def test_is_last_day_of_month_2026_april():
    """
    30 avril 2026 est le dernier jour d'avril.
    29 avril 2026 n'est pas le dernier jour.
    """
    assert is_last_day_of_month(date(2026, 4, 30)) is True, (
        "30 avril 2026 doit être reconnu comme dernier jour du mois"
    )
    assert is_last_day_of_month(date(2026, 4, 29)) is False, (
        "29 avril 2026 ne doit pas être reconnu comme dernier jour du mois"
    )


def test_is_sunday():
    """
    10 mai 2026 est un dimanche (weekday() == 6).
    11 mai 2026 est un lundi (weekday() == 0).
    """
    assert is_sunday(date(2026, 5, 10)) is True, (
        "10 mai 2026 doit être reconnu comme dimanche"
    )
    assert is_sunday(date(2026, 5, 11)) is False, (
        "11 mai 2026 ne doit pas être reconnu comme dimanche"
    )


# ---------------------------------------------------------------------------
# Test 1 — Jour en semaine (pas dernier jour) → uniquement "daily"
# ---------------------------------------------------------------------------


def test_select_reports_weekday_returns_only_daily(tmp_config, empty_data):
    """
    12 mai 2026 est un mardi et n'est pas le dernier jour de mai.
    select_reports doit retourner uniquement {"daily": "DAILY_OUTPUT"}.
    Clés "weekly" et "monthly" absentes.
    """
    today = date(2026, 5, 12)  # Mardi, pas dernier jour de mai

    with (
        patch("reporters.dispatch.build_daily_report", return_value="DAILY_OUTPUT"),
        patch("reporters.dispatch.build_weekly_report", return_value="WEEKLY_OUTPUT"),
        patch("reporters.dispatch.build_monthly_report", return_value="MONTHLY_OUTPUT"),
    ):
        result = select_reports(today, empty_data, tmp_config)

    assert result == {"daily": "DAILY_OUTPUT"}, (
        f"Un mardi (pas dernier jour) doit retourner uniquement 'daily'. "
        f"Résultat: {result}"
    )
    assert "weekly" not in result, "Clé 'weekly' ne doit pas être présente un mardi"
    assert "monthly" not in result, "Clé 'monthly' ne doit pas être présente un mardi"


# ---------------------------------------------------------------------------
# Test 2 — Dimanche mais pas dernier jour → uniquement "weekly"
# ---------------------------------------------------------------------------


def test_select_reports_sunday_not_last_day_returns_only_weekly(tmp_config, empty_data):
    """
    10 mai 2026 est un dimanche mais n'est pas le dernier jour de mai.
    select_reports doit retourner uniquement {"weekly": "WEEKLY_OUTPUT"}.
    Clés "daily" et "monthly" absentes.
    """
    today = date(2026, 5, 10)  # Dimanche, mais pas dernier jour de mai (31 mai)

    with (
        patch("reporters.dispatch.build_daily_report", return_value="DAILY_OUTPUT"),
        patch("reporters.dispatch.build_weekly_report", return_value="WEEKLY_OUTPUT"),
        patch("reporters.dispatch.build_monthly_report", return_value="MONTHLY_OUTPUT"),
    ):
        result = select_reports(today, empty_data, tmp_config)

    assert result == {"weekly": "WEEKLY_OUTPUT"}, (
        f"Un dimanche (pas dernier jour) doit retourner uniquement 'weekly'. "
        f"Résultat: {result}"
    )
    assert "daily" not in result, "Clé 'daily' ne doit pas être présente un dimanche"
    assert "monthly" not in result, (
        "Clé 'monthly' ne doit pas être présente un dimanche qui n'est pas dernier jour"
    )


# ---------------------------------------------------------------------------
# Test 3 — Dernier jour du mois (semaine) → uniquement "monthly"
# ---------------------------------------------------------------------------


def test_select_reports_last_day_weekday_returns_only_monthly(tmp_config, empty_data):
    """
    30 avril 2026 est un jeudi et est le dernier jour d'avril.
    select_reports doit retourner uniquement {"monthly": "MONTHLY_OUTPUT"}.
    """
    today = date(2026, 4, 30)  # Jeudi, dernier jour d'avril

    with (
        patch("reporters.dispatch.build_daily_report", return_value="DAILY_OUTPUT"),
        patch("reporters.dispatch.build_weekly_report", return_value="WEEKLY_OUTPUT"),
        patch("reporters.dispatch.build_monthly_report", return_value="MONTHLY_OUTPUT"),
    ):
        result = select_reports(today, empty_data, tmp_config)

    assert result == {"monthly": "MONTHLY_OUTPUT"}, (
        f"Le dernier jour d'un mois (jeudi) doit retourner uniquement 'monthly'. "
        f"Résultat: {result}"
    )
    assert "daily" not in result, "Clé 'daily' absente attendue"
    assert "weekly" not in result, "Clé 'weekly' absente attendue"


# ---------------------------------------------------------------------------
# Test 4 — Dernier jour ET dimanche → "monthly" + "weekly" (REPT-04)
# ---------------------------------------------------------------------------


def test_select_reports_last_sunday_returns_both_monthly_and_weekly(
    tmp_config, empty_data
):
    """
    31 mai 2026 est un dimanche ET le dernier jour de mai.
    REPT-04 : select_reports doit retourner les DEUX clés "monthly" ET "weekly"
    dans le même dict (deux documents, deux emails à émettre).
    """
    today = date(2026, 5, 31)  # Dimanche ET dernier jour de mai 2026

    with (
        patch("reporters.dispatch.build_daily_report", return_value="DAILY_OUTPUT"),
        patch("reporters.dispatch.build_weekly_report", return_value="WEEKLY_OUTPUT"),
        patch("reporters.dispatch.build_monthly_report", return_value="MONTHLY_OUTPUT"),
    ):
        result = select_reports(today, empty_data, tmp_config)

    assert "monthly" in result, (
        f"REPT-04 : 'monthly' doit être dans le résultat quand dernier jour + dimanche. "
        f"Résultat: {result}"
    )
    assert "weekly" in result, (
        f"REPT-04 : 'weekly' doit être dans le résultat quand dernier jour + dimanche. "
        f"Résultat: {result}"
    )
    assert result["monthly"] == "MONTHLY_OUTPUT", "Valeur monthly incorrecte"
    assert result["weekly"] == "WEEKLY_OUTPUT", "Valeur weekly incorrecte"
    assert "daily" not in result, (
        "Clé 'daily' ne doit pas apparaître quand c'est le dernier jour du mois"
    )


# ---------------------------------------------------------------------------
# Test 5 — Le dispatcher ne lève jamais si un builder échoue
# ---------------------------------------------------------------------------


def test_select_reports_never_raises_when_builder_fails(tmp_config, empty_data):
    """
    Si build_daily_report lève une exception interne, select_reports ne doit
    pas propager l'exception — le run continue (dégradation gracieuse, T-03-12).
    Le résultat doit être un dict (potentiellement avec une clé "daily" contenant
    un message d'erreur, ou sans cette clé si l'erreur est absorbée).
    """
    today = date(2026, 5, 12)  # Mardi normal

    def failing_builder(data, config):
        raise RuntimeError("Simulated builder crash")

    with patch("reporters.dispatch.build_daily_report", side_effect=failing_builder):
        # Ne doit pas lever — dégradation gracieuse
        try:
            result = select_reports(today, empty_data, tmp_config)
        except Exception as exc:
            pytest.fail(
                f"select_reports ne doit jamais lever une exception, "
                f"got: {type(exc).__name__}: {exc}"
            )

    # Le résultat doit être un dict (même partiel)
    assert isinstance(result, dict), "select_reports doit toujours retourner un dict"
    # Si "daily" est présent, sa valeur doit être un ReportOutput non vide
    from reporters.base import ReportOutput
    if "daily" in result:
        assert isinstance(result["daily"], ReportOutput), (
            "La valeur de 'daily' doit être un ReportOutput (pas une str brute)"
        )
        assert len(result["daily"].plain_text) > 0, "Le fallback plain_text ne doit pas être vide"


# ---------------------------------------------------------------------------
# Nouveaux tests — _safe_build et select_reports retournent ReportOutput
# ---------------------------------------------------------------------------


def test_safe_build_success_returns_reportoutput(tmp_config):
    """
    _safe_build() doit retourner le résultat du builder tel quel lorsqu'il réussit.
    Lorsque le builder retourne un ReportOutput, _safe_build doit retourner ce ReportOutput.
    """
    from reporters.base import ReportOutput
    from reporters.dispatch import _safe_build

    expected = ReportOutput(html_body="<p>html</p>", plain_text="plain text")

    def ok_builder(data, config):
        return expected

    result = _safe_build(ok_builder, "Test", {}, tmp_config)
    assert isinstance(result, ReportOutput), (
        f"_safe_build doit retourner un ReportOutput, got {type(result)}"
    )
    assert result.html_body == "<p>html</p>", "html_body doit être préservé"
    assert result.plain_text == "plain text", "plain_text doit être préservé"


def test_safe_build_exception_returns_reportoutput_fallback(tmp_config):
    """
    _safe_build() doit retourner un ReportOutput dégradé (pas lever) quand le builder échoue.
    """
    from reporters.base import ReportOutput
    from reporters.dispatch import _safe_build

    def failing_builder(data, config):
        raise RuntimeError("Crash simulé")

    result = _safe_build(failing_builder, "Daily Report", {}, tmp_config)
    assert isinstance(result, ReportOutput), (
        f"Fallback de _safe_build doit être un ReportOutput, got {type(result)}"
    )
    assert len(result.plain_text) > 0, "plain_text du fallback ne doit pas être vide"
    assert len(result.html_body) > 0, "html_body du fallback ne doit pas être vide"


def test_safe_build_fallback_contains_reporter_name(tmp_config):
    """
    Le ReportOutput de fallback doit contenir le nom du reporter dans html_body et plain_text.
    """
    from reporters.base import ReportOutput
    from reporters.dispatch import _safe_build

    def failing_builder(data, config):
        raise ValueError("Erreur de test")

    result = _safe_build(failing_builder, "Monthly Close", {}, tmp_config)
    assert "Monthly Close" in result.plain_text, (
        "Le nom du reporter doit apparaître dans plain_text"
    )
    assert "Monthly Close" in result.html_body, (
        "Le nom du reporter doit apparaître dans html_body"
    )


def test_select_reports_returns_reportoutput_values(tmp_config, empty_data):
    """
    select_reports() doit retourner un dict dont toutes les valeurs sont des ReportOutput.
    """
    from reporters.base import ReportOutput
    from reporters.dispatch import select_reports

    wednesday = date(2026, 5, 13)
    mock_output = ReportOutput(html_body="<p>html</p>", plain_text="texte plain")

    with patch("reporters.dispatch.build_daily_report", return_value=mock_output):
        result = select_reports(wednesday, empty_data, tmp_config)

    assert "daily" in result
    assert isinstance(result["daily"], ReportOutput), (
        f"select_reports doit retourner des ReportOutput, got {type(result['daily'])}"
    )
    assert result["daily"].html_body == "<p>html</p>"
    assert result["daily"].plain_text == "texte plain"


def test_select_reports_dict_annotation_is_reportoutput(tmp_config, empty_data):
    """
    Le type de retour de select_reports doit être Dict[str, ReportOutput].
    Vérifié via isinstance sur chaque valeur.
    """
    from reporters.base import ReportOutput
    from reporters.dispatch import select_reports

    wednesday = date(2026, 5, 13)
    mock_output = ReportOutput(html_body="<div>x</div>", plain_text="x")

    with patch("reporters.dispatch.build_daily_report", return_value=mock_output):
        result = select_reports(wednesday, empty_data, tmp_config)

    for key, value in result.items():
        assert isinstance(value, ReportOutput), (
            f"Clé '{key}' doit être un ReportOutput, got {type(value)}"
        )
