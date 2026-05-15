"""tests/test_email.py — TDD RED: tests for delivery/email.py (send_email, archive_report, build_subject)."""
from __future__ import annotations

import email as email_lib
import smtplib
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

from delivery.email import archive_report, build_subject, send_email, _markdown_to_html
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

def test_archive_report_creates_file(tmp_path):
    # Patch _REPORTS_DIR so archive_report writes to tmp_path/reports (WR-03 fix)
    with patch("delivery.email._REPORTS_DIR", tmp_path / "reports"):
        archive_report("daily", "2026-05-10", "## One Signal\n\nTexte")
    assert (tmp_path / "reports" / "daily" / "2026-05-10.md").exists()


def test_archive_report_content(tmp_path):
    # Patch _REPORTS_DIR so archive_report writes to tmp_path/reports (WR-03 fix)
    content = "## Section\n\nCorps du rapport"
    with patch("delivery.email._REPORTS_DIR", tmp_path / "reports"):
        archive_report("daily", "2026-05-10", content)
    assert (tmp_path / "reports" / "daily" / "2026-05-10.md").read_text(encoding="utf-8") == content


def test_archive_report_failure_reraises(tmp_path):
    # Patch _REPORTS_DIR so archive_report writes to tmp_path/reports (WR-03 fix)
    with patch("delivery.email._REPORTS_DIR", tmp_path / "reports"):
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
    assert len(sent_messages) == 1
    # Parse MIME message and decode HTML part to find disclaimer
    # (HTML part may be base64-encoded after CR-03 fix)
    parsed = email_lib.message_from_string(sent_messages[0])
    html_body = ""
    for part in parsed.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            if payload:
                html_body = payload.decode("utf-8", errors="replace")
            break
    assert "Ceci n'est pas un conseil financier" in html_body


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
    assert len(sent_messages) == 1
    # multipart/alternative message should contain both text/plain and text/html
    # Parse and decode MIME parts (may be base64-encoded after CR-03 fix)
    parsed = email_lib.message_from_string(sent_messages[0])
    content_types = set()
    plain_body = ""
    for part in parsed.walk():
        ct = part.get_content_type()
        content_types.add(ct)
        if ct == "text/plain":
            payload = part.get_payload(decode=True)
            if payload:
                plain_body = payload.decode("utf-8", errors="replace")
    assert "Texte rapport plain" in plain_body
    assert "text/html" in content_types


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


# --- _markdown_to_html dark-mode (Phase 7 — 13 behaviors) ---

def test_markdown_h2_color_orange():
    h = _markdown_to_html("## ETF Radar\n\nbody")
    assert "color:#FF6B35" in h

def test_markdown_h2_font_family():
    h = _markdown_to_html("## ETF Radar\n\nbody")
    assert "font-family:'Courier New',monospace" in h

def test_markdown_h2_font_weight():
    h = _markdown_to_html("## ETF Radar\n\nbody")
    assert "font-weight:700" in h

def test_markdown_h2_line_height():
    h = _markdown_to_html("## ETF Radar\n\nbody")
    assert "line-height:1.2" in h

def test_markdown_h2_margin_bottom():
    h = _markdown_to_html("## ETF Radar\n\nbody")
    assert "margin-bottom:12px" in h

def test_markdown_h1_color_orange():
    h = _markdown_to_html("# Title\n\nbody")
    assert "color:#FF6B35" in h

def test_markdown_h1_font_family():
    h = _markdown_to_html("# Title\n\nbody")
    assert "font-family:'Courier New',monospace" in h

def test_markdown_paragraph_color():
    h = _markdown_to_html("prose paragraph")
    assert "color:#e0e0e0" in h

def test_markdown_paragraph_font_family():
    h = _markdown_to_html("prose paragraph")
    assert "font-family:'Courier New',monospace" in h

def test_markdown_paragraph_font_size():
    h = _markdown_to_html("prose paragraph")
    assert "font-size:14px" in h

def test_markdown_paragraph_line_height():
    h = _markdown_to_html("prose paragraph")
    assert "line-height:1.6" in h

def test_markdown_xss_escaping():
    h = _markdown_to_html("<script>alert(1)</script>")
    assert "<script>" not in h

def test_markdown_empty_input_no_crash():
    h = _markdown_to_html("")
    assert isinstance(h, str) and len(h) > 0


# --- send_email html_body parameter (Phase 7 — 8 behaviors) ---

def test_send_email_accepts_html_body_param():
    import inspect
    sig = inspect.signature(send_email)
    assert "html_body" in sig.parameters
    assert sig.parameters["html_body"].default == ""

def test_send_email_html_body_bypasses_markdown():
    cfg = _make_config()
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: mock_smtp
    mock_smtp.__exit__ = MagicMock(return_value=False)
    with patch("smtplib.SMTP_SSL", return_value=mock_smtp):
        with patch("delivery.email._markdown_to_html") as mock_md:
            send_email("daily", "2026-05-10", "plain text", cfg, html_body="<p>rich html</p>")
            mock_md.assert_not_called()

def test_send_email_no_html_body_calls_markdown():
    cfg = _make_config()
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: mock_smtp
    mock_smtp.__exit__ = MagicMock(return_value=False)
    with patch("smtplib.SMTP_SSL", return_value=mock_smtp):
        with patch("delivery.email._markdown_to_html", return_value="<p>converted</p>") as mock_md:
            send_email("daily", "2026-05-10", "plain text", cfg, html_body="")
            mock_md.assert_called_once_with("plain text")

def test_send_email_template_render_receives_report_type():
    cfg = _make_config()
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: mock_smtp
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_template = MagicMock()
    mock_template.render.return_value = "<html>ok</html>"
    with patch("smtplib.SMTP_SSL", return_value=mock_smtp):
        with patch("delivery.email._JINJA_ENV") as mock_env:
            mock_env.get_template.return_value = mock_template
            send_email("daily", "2026-05-10", "plain", cfg)
    _, kwargs = mock_template.render.call_args
    assert kwargs.get("report_type") == "daily"

def test_send_email_template_render_receives_date():
    cfg = _make_config()
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: mock_smtp
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_template = MagicMock()
    mock_template.render.return_value = "<html>ok</html>"
    with patch("smtplib.SMTP_SSL", return_value=mock_smtp):
        with patch("delivery.email._JINJA_ENV") as mock_env:
            mock_env.get_template.return_value = mock_template
            send_email("daily", "2026-05-10", "plain", cfg)
    _, kwargs = mock_template.render.call_args
    assert kwargs.get("date") == "2026-05-10"

def test_send_email_mime_plain_uses_plain_text():
    cfg = _make_config()
    sent_messages = []
    def capture_sendmail(from_addr, to_addrs, msg_str):
        sent_messages.append(msg_str)
    mock_smtp = MagicMock()
    mock_smtp.sendmail.side_effect = capture_sendmail
    mock_smtp.__enter__ = lambda s: mock_smtp
    mock_smtp.__exit__ = MagicMock(return_value=False)
    with patch("smtplib.SMTP_SSL", return_value=mock_smtp):
        send_email("daily", "2026-05-10", "unique_plain_text_789", cfg, html_body="<p>rich</p>")
    parsed = __import__("email").message_from_string(sent_messages[0])
    plain_body = ""
    for part in parsed.walk():
        if part.get_content_type() == "text/plain":
            payload = part.get_payload(decode=True)
            if payload:
                plain_body = payload.decode("utf-8", errors="replace")
            break
    assert "unique_plain_text_789" in plain_body

def test_send_email_html_body_truthy_used_in_html_part():
    cfg = _make_config()
    sent_messages = []
    def capture_sendmail(from_addr, to_addrs, msg_str):
        sent_messages.append(msg_str)
    mock_smtp = MagicMock()
    mock_smtp.sendmail.side_effect = capture_sendmail
    mock_smtp.__enter__ = lambda s: mock_smtp
    mock_smtp.__exit__ = MagicMock(return_value=False)
    with patch("smtplib.SMTP_SSL", return_value=mock_smtp):
        send_email("daily", "2026-05-10", "plain", cfg, html_body="<p>unique_rich_html_456</p>")
    parsed = __import__("email").message_from_string(sent_messages[0])
    html_body = ""
    for part in parsed.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            if payload:
                html_body = payload.decode("utf-8", errors="replace")
            break
    assert "unique_rich_html_456" in html_body

def test_send_email_error_never_logs_password_phase7(caplog):
    import logging
    cfg = _make_config(smtp_password="phase7_secret_pass")
    with patch("smtplib.SMTP_SSL", side_effect=smtplib.SMTPException("refused")):
        with pytest.raises(smtplib.SMTPException):
            with caplog.at_level(logging.ERROR):
                send_email("daily", "2026-05-10", "Texte", cfg)
    assert "phase7_secret_pass" not in caplog.text
