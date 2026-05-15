"""
tests/test_phase7_integration.py — Phase 7 integration smoke tests.

Verifies the full pipeline from reporter output through Jinja2 rendering:
- ReportOutput dual-output type
- Dark-mode _markdown_to_html() colors
- send_email() renders dark-mode template with html_body
- Full pipeline smoke: select_reports -> send_email -> rendered HTML contains dark-mode markers
"""
from __future__ import annotations

import base64
import datetime
import email as stdlib_email
import types
import unittest
from unittest.mock import MagicMock, patch


def _decode_email_string(email_string: str) -> str:
    """Decode a MIME multipart email string, returning all decoded parts concatenated."""
    msg = stdlib_email.message_from_string(email_string)
    parts = []
    if msg.is_multipart():
        for part in msg.walk():
            payload = part.get_payload(decode=True)
            if payload is not None:
                charset = part.get_content_charset() or "utf-8"
                parts.append(payload.decode(charset, errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            parts.append(payload.decode(charset, errors="replace"))
    return "\n".join(parts)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**kwargs):
    """Create a minimal Config-like object for testing."""
    defaults = {
        "anthropic_api_key": "test-key",
        "anthropic_model": "claude-sonnet-4-6",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "test@example.com",
        "smtp_password": "test-password",
        "recipient_list": ["recipient@example.com"],
        "db_path": ":memory:",
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Test: ReportOutput type contract
# ---------------------------------------------------------------------------

class TestReportOutput(unittest.TestCase):

    def test_reportoutput_importable(self):
        from reporters.base import ReportOutput
        r = ReportOutput(html_body="<p>html</p>", plain_text="plain")
        self.assertEqual(r.html_body, "<p>html</p>")
        self.assertEqual(r.plain_text, "plain")

    def test_reportoutput_fields(self):
        from reporters.base import ReportOutput
        r = ReportOutput(html_body="<p>x</p>", plain_text="x")
        self.assertIsInstance(r.html_body, str)
        self.assertIsInstance(r.plain_text, str)


# ---------------------------------------------------------------------------
# Test: _markdown_to_html dark-mode output
# ---------------------------------------------------------------------------

class TestMarkdownToHtmlDarkMode(unittest.TestCase):

    def setUp(self):
        from delivery.email import _markdown_to_html
        self._fn = _markdown_to_html

    def test_h2_uses_orange_accent(self):
        out = self._fn("## ETF Radar\n\nbody text")
        self.assertIn("#FF6B35", out)
        self.assertNotIn("#1a1a2e", out)

    def test_h2_has_courier_new(self):
        out = self._fn("## ETF Radar\n\nbody text")
        self.assertIn("Courier New", out)

    def test_paragraph_has_dark_text_color(self):
        out = self._fn("This is a paragraph")
        self.assertIn("color:#e0e0e0", out)

    def test_h1_uses_orange_accent(self):
        out = self._fn("# Title\n\nbody")
        self.assertIn("#FF6B35", out)


# ---------------------------------------------------------------------------
# Test: dispatch returns ReportOutput
# ---------------------------------------------------------------------------

class TestDispatchReturnsReportOutput(unittest.TestCase):

    def test_safe_build_success_returns_reportoutput(self):
        from reporters.base import ReportOutput
        from reporters.dispatch import _safe_build

        def mock_builder(data, config):
            return ReportOutput(html_body="<p>html</p>", plain_text="plain")

        result = _safe_build(mock_builder, "Test", {}, _make_config())
        self.assertIsInstance(result, ReportOutput)
        self.assertEqual(result.html_body, "<p>html</p>")

    def test_safe_build_exception_returns_reportoutput(self):
        from reporters.base import ReportOutput
        from reporters.dispatch import _safe_build

        def failing_builder(data, config):
            raise RuntimeError("Simulated failure")

        result = _safe_build(failing_builder, "Test Report", {}, _make_config())
        self.assertIsInstance(result, ReportOutput)
        self.assertIn("Test Report", result.plain_text)
        self.assertIn("Test Report", result.html_body)

    @patch("reporters.dispatch.build_daily_report")
    def test_select_reports_weekday_returns_reportoutput_dict(self, mock_daily):
        from reporters.base import ReportOutput
        from reporters.dispatch import select_reports

        mock_output = ReportOutput(html_body="<p>daily</p>", plain_text="daily plain")
        mock_daily.return_value = mock_output

        # Use a Wednesday (not last day, not Sunday)
        wednesday = datetime.date(2026, 5, 13)
        result = select_reports(wednesday, {}, _make_config())

        self.assertIn("daily", result)
        self.assertIsInstance(result["daily"], ReportOutput)


# ---------------------------------------------------------------------------
# Test: send_email renders dark-mode template with html_body
# ---------------------------------------------------------------------------

class TestSendEmailDarkModeRendering(unittest.TestCase):

    @patch("delivery.email.smtplib.SMTP")
    def test_send_email_passes_html_body_to_template(self, mock_smtp):
        """Verify html_body bypasses _markdown_to_html and reaches SMTP sendmail."""
        from delivery.email import send_email

        config = _make_config()
        smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = smtp_instance

        html_body = (
            '<div style="background:#0d0d0d;">'
            '<h2 style="color:#FF6B35;">ETF Radar</h2>'
            '<p style="color:#e0e0e0;">Le marche est stable.</p>'
            '</div>'
        )
        send_email(
            report_type="daily",
            date="2026-05-13",
            plain_text="## ETF Radar\n\nLe marche est stable.",
            config=config,
            html_body=html_body,
        )

        # Verify sendmail was called
        self.assertTrue(smtp_instance.sendmail.called)
        # Get rendered email string from sendmail call
        call_args = smtp_instance.sendmail.call_args
        raw_email = call_args[0][2]  # third positional arg is the message string
        email_string = _decode_email_string(raw_email)

        # Dark-mode markers must be present in rendered HTML
        self.assertIn("#0d0d0d", email_string)
        self.assertIn("#FF6B35", email_string)
        self.assertIn("CryptoLascar", email_string)
        self.assertIn("[DAILY]", email_string)


# ---------------------------------------------------------------------------
# Test: Full pipeline smoke test
# ---------------------------------------------------------------------------

class TestPipelineFullSmoke(unittest.TestCase):

    @patch("delivery.email.smtplib.SMTP")
    @patch("reporters.daily.generate_etf_chart", return_value=None)
    @patch("reporters.daily.generate_crypto_sparklines", return_value=None)
    @patch("reporters.daily.generate_fear_greed_gauge", return_value=None)
    @patch("reporters.daily.generate_pea_table", return_value=None)
    @patch("reporters.daily.synthesize_section", return_value="Narration test.")
    def test_full_pipeline_produces_dark_mode_html(
        self,
        mock_synth,
        mock_pea,
        mock_gauge,
        mock_crypto,
        mock_etf,
        mock_smtp,
    ):
        """End-to-end: daily report built, dispatched, rendered via Jinja2, sent via SMTP.

        Mocks: Claude API (synthesize_section), all 4 chart generators, SMTP.
        Verifies: final HTML in SMTP sendmail contains dark-mode color tokens.
        """
        import datetime
        from reporters.dispatch import select_reports
        from delivery.email import send_email

        config = _make_config()
        smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = smtp_instance

        data = {
            "etf": {"tickers": {}, "source_failed": False},
            "crypto": {"coins": {}, "fear_greed": {"label": "Neutral", "value": 50}, "source_failed": False},
            "pea": {"prices": {}, "source_failed": False},
            "macro": {"series": {}, "source_failed": False},
            "news": {"headlines": [], "source_failed": False},
            "_meta": {"sources_ok": ["etf", "crypto"], "sources_failed": []},
        }

        wednesday = datetime.date(2026, 5, 13)
        reports = select_reports(wednesday, data, config)

        self.assertIn("daily", reports)
        report_output = reports["daily"]

        # html_body must be present
        self.assertTrue(report_output.html_body, "html_body is empty")
        # plain_text must be present
        self.assertTrue(report_output.plain_text, "plain_text is empty")

        # Send email with ReportOutput unpacked (as main.py does)
        send_email(
            "daily",
            "2026-05-13",
            report_output.plain_text,
            config,
            html_body=report_output.html_body,
        )

        # Verify SMTP was invoked
        self.assertTrue(smtp_instance.sendmail.called, "sendmail not called")
        raw_email = smtp_instance.sendmail.call_args[0][2]
        email_string = _decode_email_string(raw_email)

        # Dark-mode invariants
        self.assertIn("#0d0d0d", email_string, "dark background missing from email")
        self.assertIn("#FF6B35", email_string, "orange accent missing from email")
        self.assertIn("CryptoLascar", email_string, "brand name missing from email")
        self.assertIn("[DAILY]", email_string, "daily badge missing from email")


if __name__ == "__main__":
    unittest.main()
