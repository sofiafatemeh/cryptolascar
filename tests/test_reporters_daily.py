"""tests/test_reporters_daily.py — Phase 7 TDD tests for reporters/daily.py ReportOutput."""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from config import Config
from reporters.base import ReportOutput
from reporters.daily import build_daily_report, _sections_to_html


def _make_config():
    return Config(
        smtp_host="smtp.gmail.com",
        smtp_port=465,
        smtp_user="sender@gmail.com",
        smtp_password="secret",
        recipient_list=["alice@example.com"],
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


@pytest.fixture(autouse=True)
def mock_synthesize():
    with patch("reporters.daily.synthesize_section", return_value="Narration de test.") as m:
        yield m


@pytest.fixture(autouse=True)
def mock_charts_none():
    """Default: all chart generators return None (unavailable)."""
    with patch("reporters.daily.generate_etf_chart", return_value=None), \
         patch("reporters.daily.generate_crypto_sparklines", return_value=None), \
         patch("reporters.daily.generate_fear_greed_gauge", return_value=None), \
         patch("reporters.daily.generate_pea_table", return_value=None):
        yield


def test_build_daily_returns_report_output():
    r = build_daily_report({}, _make_config())
    assert isinstance(r, ReportOutput)


def test_plain_text_contains_macro_heading():
    r = build_daily_report({}, _make_config())
    assert "## Macro Snapshot" in r.plain_text


def test_html_body_contains_chart_table():
    r = build_daily_report({}, _make_config())
    assert '<table width="100%"' in r.html_body


def test_html_body_contains_chart_cells():
    r = build_daily_report({}, _make_config())
    assert 'class="chart-cell"' in r.html_body


def test_html_body_etf_fallback_when_chart_none():
    r = build_daily_report({}, _make_config())
    assert "[Graphique ETF indisponible]" in r.html_body


def test_html_body_crypto_fallback_when_chart_none():
    r = build_daily_report({}, _make_config())
    assert "[Graphique crypto indisponible]" in r.html_body


def test_html_body_etf_chart_embedded_when_returned():
    with patch("reporters.daily.generate_etf_chart", return_value="abc123"):
        r = build_daily_report({}, _make_config())
    assert "data:image/png;base64,abc123" in r.html_body


def test_html_body_pea_html_embedded_when_returned():
    with patch("reporters.daily.generate_pea_table", return_value="<table>pea</table>"):
        r = build_daily_report({}, _make_config())
    assert "<table>pea</table>" in r.html_body


def test_html_body_contains_section_card_background():
    r = build_daily_report({}, _make_config())
    assert "background:#111111" in r.html_body


def test_total_degradation_returns_report_output():
    r = build_daily_report({}, _make_config())
    assert isinstance(r, ReportOutput)


def test_plain_text_has_section_indisponible_on_full_failure():
    with patch("reporters.daily._macro_section", side_effect=RuntimeError("boom")), \
         patch("reporters.daily._etf_section", side_effect=RuntimeError("boom")), \
         patch("reporters.daily._crypto_section", side_effect=RuntimeError("boom")), \
         patch("reporters.daily._pea_section", side_effect=RuntimeError("boom")), \
         patch("reporters.daily._news_section", side_effect=RuntimeError("boom")), \
         patch("reporters.daily._one_signal_section", side_effect=RuntimeError("boom")):
        r = build_daily_report({}, _make_config())
    assert "[Section indisponible.]" in r.plain_text


def test_html_body_nonempty_on_full_failure():
    with patch("reporters.daily._macro_section", side_effect=RuntimeError("boom")), \
         patch("reporters.daily._etf_section", side_effect=RuntimeError("boom")), \
         patch("reporters.daily._crypto_section", side_effect=RuntimeError("boom")), \
         patch("reporters.daily._pea_section", side_effect=RuntimeError("boom")), \
         patch("reporters.daily._news_section", side_effect=RuntimeError("boom")), \
         patch("reporters.daily._one_signal_section", side_effect=RuntimeError("boom")):
        r = build_daily_report({}, _make_config())
    assert isinstance(r.html_body, str) and len(r.html_body) > 0


# ---------------------------------------------------------------------------
# Gap 6 — _sections_to_html() applies html.escape() to body (T-07-09 XSS)
# ---------------------------------------------------------------------------

def test_sections_to_html_escapes_script_tag_in_body():
    """Gap 6: _sections_to_html must escape HTML special chars in section body.

    An attacker-controlled body containing '<script>alert(1)</script>' must be
    escaped to '&lt;script&gt;alert(1)&lt;/script&gt;' — raw '<script>' must
    never appear in the rendered HTML output.
    """
    xss_payload = "<script>alert(1)</script>"
    # Build a valid Markdown-style section: title line, blank line, body
    malicious_section = f"## Injected Section\n\n{xss_payload}"
    result = _sections_to_html([malicious_section])

    assert "<script>" not in result, (
        "_sections_to_html rendered '<script>' unescaped — XSS vulnerability (T-07-09); "
        "html.escape() must be applied to the section body."
    )
    assert "&lt;script&gt;" in result, (
        "_sections_to_html did not produce '&lt;script&gt;' in output — "
        "html.escape() is not being applied to the section body."
    )


# ---------------------------------------------------------------------------
# Gap 7 — _sections_to_html() uses white-space:pre-wrap in <p> tag (CR-02)
# ---------------------------------------------------------------------------

def test_sections_to_html_uses_pre_wrap_style():
    """Gap 7: _sections_to_html must emit white-space:pre-wrap on the body <p>.

    CR-02 fix requires that newlines within section bodies are visually preserved
    in email clients. Without white-space:pre-wrap, multi-line content collapses.
    """
    section = "## ETF Radar\n\nLe marché est stable.\nHausses notables."
    result = _sections_to_html([section])

    assert "white-space:pre-wrap" in result, (
        "_sections_to_html does not include 'white-space:pre-wrap' in the <p> style — "
        "CR-02 fix is missing; newlines in section bodies will not render correctly."
    )


# ---------------------------------------------------------------------------
# Gap 8 — build_daily_report passes non-empty date_str to _build_chart_panel
# ---------------------------------------------------------------------------

def test_build_daily_report_passes_today_date_str_to_chart_generator():
    """Gap 8: build_daily_report must pass today's date (YYYY-MM-DD) to generate_etf_chart.

    CR-01 fix: date_str must be a non-empty, well-formed YYYY-MM-DD string.
    An empty or None date_str would cause chart titles to be blank.

    Strategy: patch generate_etf_chart to capture its date_str argument, then
    assert it matches YYYY-MM-DD format and is truthy.
    """
    captured = {}

    def capturing_etf_chart(etf_data, date_str):
        captured["date_str"] = date_str
        return None  # return None so fallback HTML is used — doesn't matter for this test

    with patch("reporters.daily.generate_etf_chart", side_effect=capturing_etf_chart):
        build_daily_report({}, _make_config())

    assert "date_str" in captured, (
        "generate_etf_chart was never called — cannot verify date_str argument."
    )
    date_str = captured["date_str"]
    assert date_str, (
        f"date_str passed to generate_etf_chart is empty or falsy: {date_str!r} — "
        "CR-01 fix requires a non-empty date string."
    )
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str), (
        f"date_str '{date_str}' does not match YYYY-MM-DD format — "
        "CR-01 fix requires today's date in ISO format."
    )
