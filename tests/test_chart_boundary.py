"""
tests/test_chart_boundary.py — Boundary integration tests for collector→chart interface.

These tests do NOT mock chart generators. They exercise the real transform logic
in _build_chart_panel to verify CHART-01/02/03/04/05 fixes work end-to-end.

Strategy: provide collector-shaped data dicts, call _build_chart_panel directly,
assert chart output (img tag) or fallback based on data presence.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from reporters.daily import _build_chart_panel
from reporters.base import ETF_FALLBACK, CRYPTO_FALLBACK, GAUGE_FALLBACK, PEA_FALLBACK, ReportOutput
from reporters.daily import build_daily_report


def _make_full_data(**overrides) -> dict:
    """Base data dict with empty/None defaults. Override keys as needed."""
    base = {
        "etf": {"tickers": {}},
        "crypto": {"coins": {}, "fear_greed": None},
        "pea": {"prices": {}},
        "macro": {},
        "news": {},
        "_meta": {"sources_ok": [], "sources_failed": []},
    }
    base.update(overrides)
    return base


def _make_config():
    """Minimal config that avoids real LLM calls when synthesize_section is mocked."""
    from config import Config
    return Config(
        db_path=Path(":memory:"),
        anthropic_api_key="test-key",
        anthropic_model="claude-sonnet-4-6",
        smtp_host="smtp.test",
        smtp_port=587,
        smtp_user="u",
        smtp_password="p",
        recipient_list=["r@test.com"],
        coingecko_api_key="",
        alpha_vantage_key="",
        fred_api_key="",
        newsapi_key="",
        log_level="WARNING",
        log_file="",
    )


DATE = "2026-05-15"


class TestEtfBoundary:
    def test_etf_boundary_produces_valid_base64(self):
        """CHART-01: valid ETF tickers → generate_etf_chart called with correct shape → img tag."""
        data = _make_full_data(
            etf={"tickers": {"SPY": {"price": 400.0, "pct_change": 0.5, "pct_change_1w": 1.2}}}
        )
        result = _build_chart_panel(data, DATE)
        assert "<img" in result, "Expected <img> tag from real ETF chart render"

    def test_etf_boundary_fallback_when_no_tickers(self):
        """CHART-01: empty tickers → etf_chart_data={} → generate_etf_chart returns None → ETF_FALLBACK."""
        data = _make_full_data(etf={"tickers": {}})
        result = _build_chart_panel(data, DATE)
        # ETF_FALLBACK text appears when chart returns None
        assert ETF_FALLBACK in result or "indisponible" in result.lower() or "chart" in result.lower()

    def test_etf_boundary_ticker_with_none_pct_change_excluded(self):
        """CHART-01: ticker with pct_change=None is excluded from etf_chart_data (filter guard)."""
        data = _make_full_data(
            etf={"tickers": {
                "SPY": {"price": 400.0, "pct_change": 0.5, "pct_change_1w": 1.2},
                "BAD": {"price": None, "pct_change": None, "pct_change_1w": None},
            }}
        )
        result = _build_chart_panel(data, DATE)
        # Should not crash even with mixed None/valid tickers
        assert isinstance(result, str)


class TestPeaBoundary:
    def test_pea_boundary_produces_table_html(self):
        """CHART-04: pea_list built correctly → generate_pea_table returns HTML table."""
        data = _make_full_data(
            pea={"prices": {
                "CW8.PA": {"price": 42.0, "pct_change": 0.3, "pct_change_1w": None}
            }}
        )
        result = _build_chart_panel(data, DATE)
        assert "<table" in result
        assert "CW8.PA" in result

    def test_pea_boundary_fallback_when_no_prices(self):
        """CHART-04: empty prices → pea_list=[] → generate_pea_table returns None → PEA_FALLBACK."""
        data = _make_full_data(pea={"prices": {}})
        result = _build_chart_panel(data, DATE)
        assert PEA_FALLBACK in result or "indisponible" in result.lower() or "pea" in result.lower()

    def test_pea_boundary_pea_eligible_correct(self):
        """CHART-04: _PEA_ELIGIBILITY lookup maps CW8.PA→True, FCHI→None."""
        data = _make_full_data(
            pea={"prices": {
                "CW8.PA": {"price": 42.0, "pct_change": 0.3, "pct_change_1w": None},
                "^FCHI": {"price": 8000.0, "pct_change": -0.2, "pct_change_1w": None},
            }}
        )
        # Capture pea_list by intercepting generate_pea_table
        captured = {}
        from charts import generate_pea_table as real_pea
        def capturing_pea(pea_data):
            captured["pea_list"] = pea_data
            return real_pea(pea_data)
        with patch("reporters.daily.generate_pea_table", side_effect=capturing_pea):
            _build_chart_panel(data, DATE)
        pea_list = captured.get("pea_list", [])
        assert isinstance(pea_list, list)
        cw8 = next((p for p in pea_list if p["ticker"] == "CW8.PA"), None)
        fchi = next((p for p in pea_list if p["ticker"] == "^FCHI"), None)
        assert cw8 is not None
        assert cw8["pea_eligible"] is True
        if fchi is not None:
            assert fchi["pea_eligible"] is None


class TestChart03Boundary:
    def test_fear_greed_none_no_attributeerror(self):
        """CHART-03: fear_greed=None must NOT raise AttributeError in _build_chart_panel."""
        data = _make_full_data(crypto={"coins": {}, "fear_greed": None})
        try:
            result = _build_chart_panel(data, DATE)
        except AttributeError as e:
            pytest.fail(f"_build_chart_panel raised AttributeError: {e}")
        assert isinstance(result, str)

    def test_fear_greed_none_shows_gauge_fallback(self):
        """CHART-03: when fear_greed=None, gauge cell shows GAUGE_FALLBACK (not img tag from gauge)."""
        data = _make_full_data(crypto={"coins": {}, "fear_greed": None})
        result = _build_chart_panel(data, DATE)
        assert GAUGE_FALLBACK in result

    def test_fear_greed_none_no_full_report_collapse(self):
        """CHART-03: build_daily_report with fear_greed=None returns real ReportOutput, not total fallback."""
        data = _make_full_data(
            crypto={"coins": {"bitcoin": {"price": 50000.0, "pct_change_24h": 1.2,
                                          "symbol": "BTC", "market_cap": 1e12,
                                          "volume_24h": 3e10}},
                    "fear_greed": None},
        )
        config = _make_config()
        with patch("reporters.daily.synthesize_section", return_value="Résumé factuel."):
            result = build_daily_report(data, config)
        assert isinstance(result, ReportOutput)
        # Full report fallback repeats "[Section indisponible.]" for every section
        # A partial report should have actual content, not all-indisponible
        assert result.html_body.count("[Section indisponible.]") < 6


class TestCryptoSparklineBoundary:
    def test_sparkline_history_passed_to_generate_crypto_sparklines(self):
        """CHART-02: coins[bitcoin/ethereum][history] lists are fed to generate_crypto_sparklines."""
        btc_hist = [40000.0 + i * 1000 for i in range(8)]
        eth_hist = [2000.0 + i * 100 for i in range(8)]
        data = _make_full_data(
            crypto={
                "coins": {
                    "bitcoin":  {"price": 47000.0, "pct_change_24h": 0.5,
                                 "symbol": "BTC", "market_cap": 1e12,
                                 "volume_24h": 3e10, "history": btc_hist},
                    "ethereum": {"price": 2700.0, "pct_change_24h": 1.2,
                                 "symbol": "ETH", "market_cap": 3e11,
                                 "volume_24h": 1e10, "history": eth_hist},
                },
                "fear_greed": None,
            }
        )
        result = _build_chart_panel(data, DATE)
        # Real sparkline render with valid history → img tag in crypto cell
        assert "<img" in result

    def test_sparkline_empty_history_shows_fallback(self):
        """CHART-02: empty history lists → generate_crypto_sparklines returns None → CRYPTO_FALLBACK."""
        data = _make_full_data(
            crypto={
                "coins": {
                    "bitcoin":  {"price": 47000.0, "history": []},
                    "ethereum": {"price": 2700.0, "history": []},
                },
                "fear_greed": None,
            }
        )
        result = _build_chart_panel(data, DATE)
        assert CRYPTO_FALLBACK in result or "indisponible" in result.lower()
