"""
tests/test_main_pipeline.py — Pipeline integration tests for main.py --mode.

Mocks all I/O: collect_all, select_reports, send_email, write_tweet,
archive_report, log_run, init_db, get_config, setup_logging.
Tests all three --mode branches plus outer try/except error paths.

Coverage:
  T1: --mode daily success
  T2: --mode weekly success
  T3: --mode monthly on last day
  T4: --mode monthly on non-last day (early exit, skipped)
  T5: --mode daily when send_email raises SMTPException -> returns 1
  T6: --mode daily when archive_report raises OSError -> returns 1
  T7: REPT-04 dual report (monthly + weekly keys)
  T8: collect_all partial (sources_failed=["news"])
  T9: missing --mode argument -> SystemExit(2)
  T10: invalid --mode value -> SystemExit(2)
"""
from __future__ import annotations

import datetime
import smtplib

import pytest
from unittest.mock import patch, MagicMock, call


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config():
    """Configuration mock avec db_path en mémoire."""
    cfg = MagicMock()
    cfg.db_path = ":memory:"
    cfg.log_level = "INFO"
    cfg.log_file = ""
    cfg.smtp_user = "test@example.com"
    cfg.recipient_list = ["dest@example.com"]
    cfg.anthropic_api_key = "test-key"
    cfg.anthropic_model = "claude-test"
    return cfg


@pytest.fixture
def daily_data():
    """Données collectées sans échec — toutes les sources OK."""
    return {
        "etf": {}, "crypto": {}, "pea": {}, "macro": {}, "news": {},
        "_meta": {
            "sources_ok": ["etf", "crypto", "pea", "macro", "news"],
            "sources_failed": [],
            "collected_at": "2026-05-11T07:00:00Z",
        },
    }


@pytest.fixture
def partial_data():
    """Données collectées avec 'news' en échec."""
    return {
        "etf": {}, "crypto": {}, "pea": {}, "macro": {},
        "news": {"error": "timeout", "source_failed": True},
        "_meta": {
            "sources_ok": ["etf", "crypto", "pea", "macro"],
            "sources_failed": ["news"],
            "collected_at": "2026-05-11T07:00:00Z",
        },
    }


# ---------------------------------------------------------------------------
# Helper : contexte de patch commun pour tous les tests
# ---------------------------------------------------------------------------


def _base_patches(mock_config, data, *, select_return=None, today=None):
    """Retourne un dict de patches à utiliser avec unittest.mock.patch."""
    if select_return is None:
        select_return = {"daily": "Daily report text"}
    if today is None:
        today = datetime.date(2026, 5, 11)  # lundi, pas dernier jour du mois
    return {
        "main.get_config": mock_config,
        "main.setup_logging": MagicMock(),
        "main.init_db": MagicMock(),
        "main.collect_all": MagicMock(return_value=data),
        "main.select_reports": MagicMock(return_value=select_return),
        "main.send_email": MagicMock(),
        "main.write_tweet": MagicMock(),
        "main.archive_report": MagicMock(),
        "main.log_run": MagicMock(),
        "main.is_last_day_of_month": MagicMock(return_value=False),
        "main.datetime": MagicMock(
            date=MagicMock(today=MagicMock(return_value=today)),
            datetime=datetime.datetime,
            timezone=datetime.timezone,
        ),
    }


# ---------------------------------------------------------------------------
# T1 : --mode daily success
# ---------------------------------------------------------------------------


def test_mode_daily_success(mock_config, daily_data):
    """--mode daily complet retourne 0 et log_run status='success'."""
    from main import main

    today = datetime.date(2026, 5, 11)
    patches = _base_patches(
        mock_config,
        daily_data,
        select_return={"daily": "Daily report text"},
        today=today,
    )

    with patch("main.get_config", return_value=mock_config), \
         patch("main.setup_logging"), \
         patch("main.init_db"), \
         patch("main.collect_all", return_value=daily_data) as mock_collect, \
         patch("main.select_reports", return_value={"daily": "Daily report text"}), \
         patch("main.send_email") as mock_send, \
         patch("main.write_tweet") as mock_tweet, \
         patch("main.archive_report") as mock_archive, \
         patch("main.log_run") as mock_log_run, \
         patch("main.is_last_day_of_month", return_value=False), \
         patch("main.datetime") as mock_dt:
        mock_dt.date.today.return_value = today
        mock_dt.datetime = datetime.datetime
        mock_dt.timezone = datetime.timezone

        result = main(["--mode", "daily"])

    assert result == 0
    mock_send.assert_called_once_with("daily", today.isoformat(), "Daily report text", mock_config, month="", year="")
    mock_tweet.assert_called_once_with("daily", today.isoformat(), "Daily report text", mock_config)
    mock_archive.assert_called_once_with("daily", today.isoformat(), "Daily report text")
    # D-11 : exactement un log_run avec status success ou partial
    mock_log_run.assert_called_once()
    log_args = mock_log_run.call_args[0]
    assert log_args[1] == "success", f"Expected status='success', got '{log_args[1]}'"


# ---------------------------------------------------------------------------
# T2 : --mode weekly success
# ---------------------------------------------------------------------------


def test_mode_weekly_success(mock_config, daily_data):
    """--mode weekly retourne 0 et appelle send_email/write_tweet avec report_type='weekly'."""
    from main import main

    today = datetime.date(2026, 5, 11)
    with patch("main.get_config", return_value=mock_config), \
         patch("main.setup_logging"), \
         patch("main.init_db"), \
         patch("main.collect_all", return_value=daily_data), \
         patch("main.select_reports", return_value={"weekly": "Weekly report text"}), \
         patch("main.send_email") as mock_send, \
         patch("main.write_tweet") as mock_tweet, \
         patch("main.archive_report") as mock_archive, \
         patch("main.log_run") as mock_log_run, \
         patch("main.is_last_day_of_month", return_value=False), \
         patch("main.datetime") as mock_dt:
        mock_dt.date.today.return_value = today
        mock_dt.datetime = datetime.datetime
        mock_dt.timezone = datetime.timezone

        result = main(["--mode", "weekly"])

    assert result == 0
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args
    assert call_kwargs[0][0] == "weekly", f"Expected report_type='weekly', got '{call_kwargs[0][0]}'"
    mock_tweet.assert_called_once()
    assert mock_tweet.call_args[0][0] == "weekly"


# ---------------------------------------------------------------------------
# T3 : --mode monthly sur le dernier jour du mois
# ---------------------------------------------------------------------------


def test_mode_monthly_last_day(mock_config, daily_data):
    """--mode monthly le dernier jour du mois retourne 0 et appelle send_email avec report_type='monthly'."""
    from main import main

    today = datetime.date(2026, 5, 31)  # dernier jour de mai
    with patch("main.get_config", return_value=mock_config), \
         patch("main.setup_logging"), \
         patch("main.init_db"), \
         patch("main.collect_all", return_value=daily_data), \
         patch("main.select_reports", return_value={"monthly": "Monthly report text"}), \
         patch("main.send_email") as mock_send, \
         patch("main.write_tweet") as mock_tweet, \
         patch("main.archive_report") as mock_archive, \
         patch("main.log_run") as mock_log_run, \
         patch("main.is_last_day_of_month", return_value=True), \
         patch("main.datetime") as mock_dt:
        mock_dt.date.today.return_value = today
        mock_dt.datetime = datetime.datetime
        mock_dt.timezone = datetime.timezone

        result = main(["--mode", "monthly"])

    assert result == 0
    mock_send.assert_called_once()
    assert mock_send.call_args[0][0] == "monthly"
    # tweet.py gère TWEET-04 en interne, mais write_tweet est bien appelé
    mock_tweet.assert_called_once()
    assert mock_tweet.call_args[0][0] == "monthly"


# ---------------------------------------------------------------------------
# T4 : --mode monthly hors dernier jour (skip)
# ---------------------------------------------------------------------------


def test_mode_monthly_skip_non_last_day(mock_config, daily_data):
    """--mode monthly sur un jour non-dernier retourne 0 sans appeler select_reports."""
    from main import main

    today = datetime.date(2026, 5, 10)  # 10 mai, pas dernier jour
    with patch("main.get_config", return_value=mock_config), \
         patch("main.setup_logging"), \
         patch("main.init_db"), \
         patch("main.collect_all", return_value=daily_data), \
         patch("main.select_reports") as mock_select, \
         patch("main.send_email") as mock_send, \
         patch("main.write_tweet") as mock_tweet, \
         patch("main.archive_report") as mock_archive, \
         patch("main.log_run") as mock_log_run, \
         patch("main.is_last_day_of_month", return_value=False), \
         patch("main.datetime") as mock_dt:
        mock_dt.date.today.return_value = today
        mock_dt.datetime = datetime.datetime
        mock_dt.timezone = datetime.timezone

        result = main(["--mode", "monthly"])

    assert result == 0
    # select_reports NE doit PAS être appelé (sortie anticipée)
    mock_select.assert_not_called()
    mock_send.assert_not_called()
    # D-11 : log_run appelé avec status='skipped'
    mock_log_run.assert_called_once()
    log_args = mock_log_run.call_args[0]
    assert log_args[1] == "skipped", f"Expected status='skipped', got '{log_args[1]}'"


# ---------------------------------------------------------------------------
# T5 : --mode daily — send_email lève SMTPException
# ---------------------------------------------------------------------------


def test_mode_daily_send_email_failure(mock_config, daily_data):
    """Quand send_email lève SMTPException, main retourne 1 et log_run status='error'."""
    from main import main

    today = datetime.date(2026, 5, 11)
    with patch("main.get_config", return_value=mock_config), \
         patch("main.setup_logging"), \
         patch("main.init_db"), \
         patch("main.collect_all", return_value=daily_data), \
         patch("main.select_reports", return_value={"daily": "Daily report text"}), \
         patch("main.send_email", side_effect=smtplib.SMTPException("Connection refused")), \
         patch("main.write_tweet"), \
         patch("main.archive_report"), \
         patch("main.log_run") as mock_log_run, \
         patch("main.is_last_day_of_month", return_value=False), \
         patch("main.datetime") as mock_dt:
        mock_dt.date.today.return_value = today
        mock_dt.datetime = datetime.datetime
        mock_dt.timezone = datetime.timezone

        result = main(["--mode", "daily"])

    assert result == 1
    mock_log_run.assert_called_once()
    log_args = mock_log_run.call_args[0]
    assert log_args[1] == "error", f"Expected status='error', got '{log_args[1]}'"
    # T-05-01 : l'error_msg contient "Pipeline error" mais pas de credential
    error_msg = log_args[4]
    assert "Pipeline error" in error_msg
    assert "smtp_password" not in error_msg
    assert "api_key" not in error_msg


# ---------------------------------------------------------------------------
# T6 : --mode daily — archive_report lève OSError
# ---------------------------------------------------------------------------


def test_mode_daily_archive_failure(mock_config, daily_data):
    """Quand archive_report lève OSError, main retourne 1 et log_run status='error'."""
    from main import main

    today = datetime.date(2026, 5, 11)
    with patch("main.get_config", return_value=mock_config), \
         patch("main.setup_logging"), \
         patch("main.init_db"), \
         patch("main.collect_all", return_value=daily_data), \
         patch("main.select_reports", return_value={"daily": "Daily report text"}), \
         patch("main.send_email"), \
         patch("main.write_tweet"), \
         patch("main.archive_report", side_effect=OSError("Disk full")), \
         patch("main.log_run") as mock_log_run, \
         patch("main.is_last_day_of_month", return_value=False), \
         patch("main.datetime") as mock_dt:
        mock_dt.date.today.return_value = today
        mock_dt.datetime = datetime.datetime
        mock_dt.timezone = datetime.timezone

        result = main(["--mode", "daily"])

    assert result == 1
    mock_log_run.assert_called_once()
    log_args = mock_log_run.call_args[0]
    assert log_args[1] == "error", f"Expected status='error', got '{log_args[1]}'"


# ---------------------------------------------------------------------------
# T7 : REPT-04 — select_reports retourne {"monthly": ..., "weekly": ...}
# ---------------------------------------------------------------------------


def test_rept04_dual_report(mock_config, daily_data):
    """REPT-04 : send_email appelé deux fois (once per report type)."""
    from main import main

    today = datetime.date(2026, 5, 31)  # dernier dimanche du mois (par hypothèse)
    dual_reports = {
        "monthly": "Monthly report text",
        "weekly": "Weekly report text",
    }
    with patch("main.get_config", return_value=mock_config), \
         patch("main.setup_logging"), \
         patch("main.init_db"), \
         patch("main.collect_all", return_value=daily_data), \
         patch("main.select_reports", return_value=dual_reports), \
         patch("main.send_email") as mock_send, \
         patch("main.write_tweet") as mock_tweet, \
         patch("main.archive_report") as mock_archive, \
         patch("main.log_run") as mock_log_run, \
         patch("main.is_last_day_of_month", return_value=True), \
         patch("main.datetime") as mock_dt:
        mock_dt.date.today.return_value = today
        mock_dt.datetime = datetime.datetime
        mock_dt.timezone = datetime.timezone

        result = main(["--mode", "monthly"])

    assert result == 0
    # send_email appelé deux fois (monthly + weekly)
    assert mock_send.call_count == 2, f"Expected 2 send_email calls, got {mock_send.call_count}"
    # archive_report appelé deux fois
    assert mock_archive.call_count == 2, f"Expected 2 archive_report calls, got {mock_archive.call_count}"
    # write_tweet appelé deux fois (tweet.py gère TWEET-04 en interne pour monthly)
    assert mock_tweet.call_count == 2, f"Expected 2 write_tweet calls, got {mock_tweet.call_count}"
    # Exactement un log_run (D-11)
    mock_log_run.assert_called_once()


# ---------------------------------------------------------------------------
# T8 : collect_all partiel (sources_failed=["news"])
# ---------------------------------------------------------------------------


def test_partial_collect(mock_config, partial_data):
    """Collecte partielle : send_email toujours appelé, log_run.sources_failed contient 'news'."""
    from main import main

    today = datetime.date(2026, 5, 11)
    with patch("main.get_config", return_value=mock_config), \
         patch("main.setup_logging"), \
         patch("main.init_db"), \
         patch("main.collect_all", return_value=partial_data), \
         patch("main.select_reports", return_value={"daily": "Daily report text"}), \
         patch("main.send_email") as mock_send, \
         patch("main.write_tweet"), \
         patch("main.archive_report"), \
         patch("main.log_run") as mock_log_run, \
         patch("main.is_last_day_of_month", return_value=False), \
         patch("main.datetime") as mock_dt:
        mock_dt.date.today.return_value = today
        mock_dt.datetime = datetime.datetime
        mock_dt.timezone = datetime.timezone

        result = main(["--mode", "daily"])

    assert result == 0
    # La livraison se fait malgré les données partielles
    mock_send.assert_called_once()
    # log_run appelé avec sources_failed contenant "news"
    mock_log_run.assert_called_once()
    log_args = mock_log_run.call_args[0]
    assert "news" in log_args[3], f"Expected 'news' in sources_failed, got '{log_args[3]}'"
    # status devrait être "partial" (collect partiel)
    assert log_args[1] == "partial", f"Expected status='partial', got '{log_args[1]}'"


# ---------------------------------------------------------------------------
# T9 : --mode manquant -> SystemExit(2)
# ---------------------------------------------------------------------------


def test_missing_mode_exits_2():
    """Argparse retourne code 2 si --mode est absent."""
    from main import main

    with pytest.raises(SystemExit) as exc_info:
        main([])

    assert exc_info.value.code == 2, f"Expected exit code 2, got {exc_info.value.code}"


# ---------------------------------------------------------------------------
# T10 : --mode invalide -> SystemExit(2)
# ---------------------------------------------------------------------------


def test_invalid_mode_exits_2():
    """Argparse retourne code 2 si --mode reçoit une valeur invalide."""
    from main import main

    with pytest.raises(SystemExit) as exc_info:
        main(["--mode", "invalid"])

    assert exc_info.value.code == 2, f"Expected exit code 2, got {exc_info.value.code}"
