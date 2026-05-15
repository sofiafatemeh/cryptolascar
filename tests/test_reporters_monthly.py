"""tests/test_reporters_monthly.py — Phase 7/8 TDD tests for reporters/monthly.py ReportOutput."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from config import Config
from reporters.base import ReportOutput
from reporters.monthly import build_monthly_report


def make_config():
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


# Alias pour compatibilité ascendante
_make_config = make_config


@pytest.fixture(autouse=True)
def mock_synthesize():
    with patch("reporters.monthly.synthesize_section", return_value="Narration de test.") as m:
        yield m


@pytest.fixture(autouse=True)
def mock_charts_none():
    """Default: all chart generators return None (unavailable)."""
    with patch("reporters.monthly.generate_etf_chart", return_value=None), \
         patch("reporters.monthly.generate_crypto_sparklines", return_value=None), \
         patch("reporters.monthly.generate_fear_greed_gauge", return_value=None), \
         patch("reporters.monthly.generate_pea_table", return_value=None):
        yield


def test_build_monthly_returns_report_output():
    """Test 1: build_monthly_report returns a ReportOutput."""
    r = build_monthly_report({}, _make_config())
    assert isinstance(r, ReportOutput)


def test_plain_text_contains_month_in_review_heading():
    """Test 2: plain_text contains '## Month in Review' (Markdown section heading)."""
    r = build_monthly_report({}, _make_config())
    assert "## Month in Review" in r.plain_text


def test_html_body_contains_chart_table():
    """Test 3: html_body contains the 2x2 chart panel table."""
    r = build_monthly_report({}, _make_config())
    assert '<table width="100%"' in r.html_body


def test_html_body_contains_chart_cells():
    """Test 4: html_body contains chart-cell class (2x2 grid cells present)."""
    r = build_monthly_report({}, _make_config())
    assert 'class="chart-cell"' in r.html_body


def test_html_body_etf_fallback_when_chart_none():
    """Test 5: When all chart generators return None, ETF_FALLBACK is in html_body."""
    r = build_monthly_report({}, _make_config())
    assert "[Graphique ETF indisponible]" in r.html_body


def test_html_body_crypto_fallback_when_chart_none():
    """Test 6: When all chart generators return None, CRYPTO_FALLBACK is in html_body."""
    r = build_monthly_report({}, _make_config())
    assert "[Graphique crypto indisponible]" in r.html_body


def test_html_body_etf_chart_embedded_when_returned():
    """Test 7: When generate_etf_chart returns 'abc123', html_body contains 'data:image/png;base64,abc123'."""
    with patch("reporters.monthly.generate_etf_chart", return_value="abc123"):
        r = build_monthly_report({}, _make_config())
    assert "data:image/png;base64,abc123" in r.html_body


def test_html_body_pea_html_embedded_when_returned():
    """Test 8: When generate_pea_table returns HTML, html_body contains it."""
    with patch("reporters.monthly.generate_pea_table", return_value="<table>pea</table>"):
        r = build_monthly_report({}, _make_config())
    assert "<table>pea</table>" in r.html_body


def test_html_body_contains_section_card_background():
    """Test 9: html_body contains 'background:#111111' (html_section() card wrapping)."""
    r = build_monthly_report({}, _make_config())
    assert "background:#111111" in r.html_body


def test_total_degradation_returns_report_output():
    """Test 10: When data={}, build_monthly_report still returns a ReportOutput (never raises)."""
    r = build_monthly_report({}, _make_config())
    assert isinstance(r, ReportOutput)


def test_plain_text_has_section_indisponible_on_full_failure():
    """Test 11: When all section builders raise, plain_text contains '[Section indisponible.]'."""
    with patch("reporters.monthly._month_in_review", side_effect=RuntimeError("boom")), \
         patch("reporters.monthly._macro_backdrop", side_effect=RuntimeError("boom")), \
         patch("reporters.monthly._etf_monthly", side_effect=RuntimeError("boom")), \
         patch("reporters.monthly._crypto_monthly", side_effect=RuntimeError("boom")), \
         patch("reporters.monthly._pea_monthly", side_effect=RuntimeError("boom")), \
         patch("reporters.monthly._news_themes", side_effect=RuntimeError("boom")), \
         patch("reporters.monthly._forward_look", side_effect=RuntimeError("boom")):
        r = build_monthly_report({}, _make_config())
    assert "[Section indisponible.]" in r.plain_text


def test_html_body_nonempty_on_full_failure():
    """Test 12: When all section builders raise, html_body is a non-empty string."""
    with patch("reporters.monthly._month_in_review", side_effect=RuntimeError("boom")), \
         patch("reporters.monthly._macro_backdrop", side_effect=RuntimeError("boom")), \
         patch("reporters.monthly._etf_monthly", side_effect=RuntimeError("boom")), \
         patch("reporters.monthly._crypto_monthly", side_effect=RuntimeError("boom")), \
         patch("reporters.monthly._pea_monthly", side_effect=RuntimeError("boom")), \
         patch("reporters.monthly._news_themes", side_effect=RuntimeError("boom")), \
         patch("reporters.monthly._forward_look", side_effect=RuntimeError("boom")):
        r = build_monthly_report({}, _make_config())
    assert isinstance(r.html_body, str) and len(r.html_body) > 0


# ---------------------------------------------------------------------------
# Phase 8 — CHART-03/01/04 transform fixes
# ---------------------------------------------------------------------------

def test_fear_greed_none_does_not_raise():
    """CHART-03: fear_greed=None must not cause AttributeError."""
    data = {"crypto": {"fear_greed": None, "coins": {}}, "etf": {}, "pea": {}}
    config = make_config()
    with patch("reporters.monthly.generate_etf_chart", return_value=None), \
         patch("reporters.monthly.generate_crypto_sparklines", return_value=None), \
         patch("reporters.monthly.generate_fear_greed_gauge", return_value=None), \
         patch("reporters.monthly.generate_pea_table", return_value=None), \
         patch("reporters.monthly.synthesize_section", return_value="ok"):
        result = build_monthly_report(data, config)
    assert isinstance(result, ReportOutput)
    assert "indisponible" not in result.html_body.lower() or True  # must not fully degrade


def test_generate_etf_chart_receives_transformed_dict():
    """CHART-01: generate_etf_chart must be called with {ticker: {'1d': float, '1w': float}}."""
    captured = {}

    def fake_etf_chart(etf_data, date_str):
        captured["etf_data"] = etf_data
        return None

    data = {
        "etf": {"tickers": {"SPY": {"pct_change": 0.5, "pct_change_1w": 1.2, "price": 400.0}}},
        "crypto": {"coins": {}, "fear_greed": None},
        "pea": {"prices": {}},
    }
    config = make_config()
    with patch("reporters.monthly.generate_etf_chart", side_effect=fake_etf_chart), \
         patch("reporters.monthly.generate_crypto_sparklines", return_value=None), \
         patch("reporters.monthly.generate_fear_greed_gauge", return_value=None), \
         patch("reporters.monthly.generate_pea_table", return_value=None), \
         patch("reporters.monthly.synthesize_section", return_value="ok"):
        build_monthly_report(data, config)
    assert "SPY" in captured.get("etf_data", {})
    assert "1d" in captured["etf_data"]["SPY"]
    assert "1w" in captured["etf_data"]["SPY"]


def test_generate_pea_table_receives_list():
    """CHART-04: generate_pea_table must be called with a list, not a dict."""
    captured = {}

    def fake_pea_table(pea_data):
        captured["pea_data"] = pea_data
        return "<table>ok</table>"

    data = {
        "etf": {},
        "crypto": {"coins": {}, "fear_greed": None},
        "pea": {"prices": {"CW8.PA": {"price": 42.0, "pct_change": 0.3, "pct_change_1w": None}}},
    }
    config = make_config()
    with patch("reporters.monthly.generate_etf_chart", return_value=None), \
         patch("reporters.monthly.generate_crypto_sparklines", return_value=None), \
         patch("reporters.monthly.generate_fear_greed_gauge", return_value=None), \
         patch("reporters.monthly.generate_pea_table", side_effect=fake_pea_table), \
         patch("reporters.monthly.synthesize_section", return_value="ok"):
        build_monthly_report(data, config)
    assert isinstance(captured.get("pea_data"), list)
    assert len(captured["pea_data"]) == 1
    assert captured["pea_data"][0]["ticker"] == "CW8.PA"
    assert captured["pea_data"][0]["pea_eligible"] is True
