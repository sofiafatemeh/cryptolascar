"""tests/test_email.py — TDD RED: tests for delivery/email.py (send_email, archive_report, build_subject)."""
from __future__ import annotations

import smtplib
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

from delivery.email import archive_report, build_subject, send_email
from config import Config


def _make_config(**overrides) -> Config:
    defaults = dict(
        smtp_host="smtp.gmail.com",
        smtp_port=465,
        smtp_user="sender@gmail.com",
        smtp_password="secret",
        recipient_list=["alice@example.com", "bob@example.com"],
        anthropic_api_key="sk-test",
        anthropic_model="claude-sonnet-4-6",
        coingecko_api_key="",
        alpha_vantage_key="",
        fred_api_key="",
        newsapi_key="",
        db_path=Path("test.db"),
        log_level="INFO",
        log_file="",
    )
    defaults.update(overrides)
    return Config(**defaults)


# --- build_subject ---

def test_build_subject_daily():
    assert build_subject("daily", "2026-05-10") == "[DAILY] Analyse du 2026-05-10"


def test_build_subject_weekly():
    assert build_subject("weekly", "2026-05-10") == "[WEEKLY WRAP] Bilan de la semaine 2026-05-10"


def test_build_subject_monthly():
    assert build_subject("monthly", "2026-05-10", month="Mai", year="2026") == "[MONTHLY CLOSE] Bilan du mois Mai 2026"


# --- archive_report ---

def test_archive_report_creates_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reports" / "daily").mkdir(parents=True)
    archive_report("daily", "2026-05-10", "## One Signal\n\nTexte")
    assert (tmp_path / "reports" / "daily" / "2026-05-10.md").exists()


def test_archive_report_content(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reports" / "daily").mkdir(parents=True)
    content = "## Section\n\nCorps du rapport"
    archive_report("daily", "2026-05-10", content)
    assert (tmp_path / "reports" / "daily" / "2026-05-10.md").read_text(encoding="utf-8") == content


def test_archive_report_failure_reraises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reports" / "daily").mkdir(parents=True)
    with patch("delivery.email.Path.write_text", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            archive_report("daily", "2026-05-10", "content")


# --- send_email ---

def test_send_email_calls_smtp_ssl():
    cfg = _make_config()
    mock_smtp = MagicMock()
    with patch("smtplib.SMTP_SSL", return_value=mock_smtp) as mock_cls:
        mock_smtp.__enter__ = lambda s: mock_smtp
        mock_smtp.__exit__ = MagicMock(return_value=False)
        send_email("daily", "2026-05-10", "Texte rapport", cfg)
    mock_cls.assert_called_once_with(cfg.smtp_host, cfg.smtp_port)


def test_send_email_sends_to_recipient_list():
    cfg = _make_config()
    mock_smtp = MagicMock()
    with patch("smtplib.SMTP_SSL", return_value=mock_smtp):
        mock_smtp.__enter__ = lambda s: mock_smtp
        mock_smtp.__exit__ = MagicMock(return_value=False)
        send_email("daily", "2026-05-10", "Texte rapport", cfg)
    sendmail_args = mock_smtp.sendmail.call_args
    assert sendmail_args is not None
    # Second arg is recipient list or individual recipients called multiple times
    called_recipients = sendmail_args[0][1]
    assert set(called_recipients) == set(cfg.recipient_list)


def test_send_email_subject_contains_daily_prefix():
    cfg = _make_config()
    sent_messages = []
    def capture_sendmail(from_addr, to_addrs, msg_str):
        sent_messages.append(msg_str)
    mock_smtp = MagicMock()
    mock_smtp.sendmail.side_effect = capture_sendmail
    with patch("smtplib.SMTP_SSL", return_value=mock_smtp):
        mock_smtp.__enter__ = lambda s: mock_smtp
        mock_smtp.__exit__ = MagicMock(return_value=False)
        send_email("daily", "2026-05-10", "Texte rapport", cfg)
    assert len(sent_messages) == 1
    assert "Subject: [DAILY] Analyse du 2026-05-10" in sent_messages[0]


def test_send_email_html_contains_disclaimer():
    cfg = _make_config()
    sent_messages = []
    def capture_sendmail(from_addr, to_addrs, msg_str):
        sent_messages.append(msg_str)
    mock_smtp = MagicMock()
    mock_smtp.sendmail.side_effect = capture_sendmail
    with patch("smtplib.SMTP_SSL", return_value=mock_smtp):
        mock_smtp.__enter__ = lambda s: mock_smtp
        mock_smtp.__exit__ = MagicMock(return_value=False)
        send_email("daily", "2026-05-10", "Texte rapport", cfg)
    assert "Ceci n'est pas un conseil financier" in sent_messages[0]


def test_send_email_has_plain_text_fallback():
    cfg = _make_config()
    sent_messages = []
    def capture_sendmail(from_addr, to_addrs, msg_str):
        sent_messages.append(msg_str)
    mock_smtp = MagicMock()
    mock_smtp.sendmail.side_effect = capture_sendmail
    with patch("smtplib.SMTP_SSL", return_value=mock_smtp):
        mock_smtp.__enter__ = lambda s: mock_smtp
        mock_smtp.__exit__ = MagicMock(return_value=False)
        send_email("daily", "2026-05-10", "Texte rapport plain", cfg)
    # multipart/alternative message should contain both text/plain and text/html
    assert "Texte rapport plain" in sent_messages[0]
    assert "text/html" in sent_messages[0]


def test_send_email_never_logs_password(caplog):
    import logging
    cfg = _make_config(smtp_password="super_secret_pass")
    with patch("smtplib.SMTP_SSL", side_effect=smtplib.SMTPException("connection refused")):
        with pytest.raises(smtplib.SMTPException):
            with caplog.at_level(logging.ERROR):
                send_email("daily", "2026-05-10", "Texte", cfg)
    assert "super_secret_pass" not in caplog.text


def test_send_email_reraises_on_smtp_error():
    cfg = _make_config()
    with patch("smtplib.SMTP_SSL", side_effect=smtplib.SMTPException("auth failed")):
        with pytest.raises(smtplib.SMTPException):
            send_email("daily", "2026-05-10", "Texte", cfg)
