"""tests/test_reporters_daily.py — Phase 7 TDD tests for reporters/daily.py ReportOutput."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from config import Config
from reporters.base import ReportOutput
from reporters.daily import build_daily_report


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
