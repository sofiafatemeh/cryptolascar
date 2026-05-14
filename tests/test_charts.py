"""
tests/test_charts.py — Unit tests for charts/ module (Phase 6).

Coverage:
  CHART-01: generate_etf_chart — happy path (returns base64 PNG), empty/None input
  CHART-02: generate_crypto_sparklines — happy path, empty/None input
  CHART-03: generate_fear_greed_gauge — all 5 zone boundaries, None/out-of-range input
  CHART-04: generate_pea_table — positive/negative/neutral rows, None/empty input
  CHART-05: graceful fallback — all 4 functions return None (not raise) when rendering raises
  Package:  top-level charts import exposes all 4 public functions
"""
from __future__ import annotations

import base64
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Fixtures — reusable test data
# ---------------------------------------------------------------------------

ETF_DATA_VALID = {
    "SPY":     {"1d": 0.52, "1w": 1.30},
    "QQQ":     {"1d": -0.10, "1w": 0.80},
    "IWDA.AS": {"1d": 0.25, "1w": -0.50},
}

BTC_HISTORY_VALID = [40000.0, 41000.0, 42000.0, 41500.0, 43000.0, 44000.0, 45000.0]
ETH_HISTORY_VALID = [2400.0,  2450.0,  2500.0,  2480.0,  2550.0,  2600.0,  2650.0]

PEA_DATA_VALID = [
    {
        "ticker": "MC.PA",
        "name": "LVMH",
        "price": 750.0,
        "change_1d": 1.5,
        "change_1w": 3.2,
        "pea_eligible": True,
    },
    {
        "ticker": "RNO.PA",
        "name": "Renault",
        "price": 42.0,
        "change_1d": -0.8,
        "change_1w": -2.1,
        "pea_eligible": True,
    },
    {
        "ticker": "FP.PA",
        "name": "TotalEnergies",
        "price": 58.5,
        "change_1d": 0.0,
        "change_1w": 1.1,
        "pea_eligible": True,
    },
]


def _is_valid_png(b64_string: str) -> bool:
    """Return True if b64_string decodes to a valid PNG byte sequence."""
    try:
        raw = base64.b64decode(b64_string)
        return raw[:4] == b'\x89PNG'
    except Exception:
        return False


# ---------------------------------------------------------------------------
# CHART-01: ETF bar chart
# ---------------------------------------------------------------------------

def test_etf_chart_returns_base64_png_for_valid_data():
    """CHART-01: Valid ETF data produces a non-None base64 PNG string."""
    from charts.etf import generate_etf_chart
    result = generate_etf_chart(ETF_DATA_VALID, "13 mai 2026")
    assert result is not None, "Expected base64 PNG, got None"
    assert _is_valid_png(result), f"Result is not a valid PNG (first bytes: {base64.b64decode(result)[:8]})"


def test_etf_chart_returns_none_for_none_input():
    """CHART-01 + CHART-05: None input returns None without raising."""
    from charts.etf import generate_etf_chart
    result = generate_etf_chart(None, "13 mai 2026")
    assert result is None, "Expected None for None etf_data"


def test_etf_chart_returns_none_for_empty_dict():
    """CHART-01 + CHART-05: Empty dict returns None without raising."""
    from charts.etf import generate_etf_chart
    result = generate_etf_chart({}, "13 mai 2026")
    assert result is None, "Expected None for empty etf_data"


# ---------------------------------------------------------------------------
# CHART-02: Crypto sparklines
# ---------------------------------------------------------------------------

def test_crypto_sparklines_returns_base64_png_for_valid_data():
    """CHART-02: Valid 7-day BTC/ETH histories produce a non-None base64 PNG."""
    from charts.crypto import generate_crypto_sparklines
    result = generate_crypto_sparklines(BTC_HISTORY_VALID, ETH_HISTORY_VALID)
    assert result is not None, "Expected base64 PNG, got None"
    assert _is_valid_png(result), "Result is not a valid PNG"


def test_crypto_sparklines_returns_none_for_none_input():
    """CHART-02 + CHART-05: None input returns None without raising."""
    from charts.crypto import generate_crypto_sparklines
    result = generate_crypto_sparklines(None, None)
    assert result is None, "Expected None for None inputs"


def test_crypto_sparklines_returns_none_for_empty_lists():
    """CHART-02 + CHART-05: Empty lists return None without raising."""
    from charts.crypto import generate_crypto_sparklines
    result = generate_crypto_sparklines([], [])
    assert result is None, "Expected None for empty price lists"


# ---------------------------------------------------------------------------
# CHART-03: Fear & Greed gauge
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("score,expected_zone", [
    (0,   "Extreme Fear"),
    (10,  "Extreme Fear"),
    (24,  "Extreme Fear"),
    (25,  "Fear"),
    (35,  "Fear"),
    (44,  "Fear"),
    (45,  "Neutral"),
    (50,  "Neutral"),
    (55,  "Neutral"),
    (56,  "Greed"),
    (65,  "Greed"),
    (74,  "Greed"),
    (75,  "Extreme Greed"),
    (90,  "Extreme Greed"),
    (100, "Extreme Greed"),
])
def test_gauge_returns_png_for_all_zone_boundaries(score, expected_zone):
    """CHART-03: All 5 zone boundaries produce valid PNG output."""
    from charts.gauge import generate_fear_greed_gauge
    result = generate_fear_greed_gauge(score)
    assert result is not None, f"Expected base64 PNG for score={score} ({expected_zone}), got None"
    assert _is_valid_png(result), f"Result for score={score} is not valid PNG"


def test_gauge_returns_none_for_none_score():
    """CHART-03 + CHART-05: None score returns None without raising."""
    from charts.gauge import generate_fear_greed_gauge
    result = generate_fear_greed_gauge(None)
    assert result is None, "Expected None for None score"


def test_gauge_returns_none_for_out_of_range_score():
    """CHART-03 + CHART-05: Scores outside [0, 100] return None without raising."""
    from charts.gauge import generate_fear_greed_gauge
    assert generate_fear_greed_gauge(-1) is None, "Expected None for score=-1"
    assert generate_fear_greed_gauge(101) is None, "Expected None for score=101"
    assert generate_fear_greed_gauge(150) is None, "Expected None for score=150"


# ---------------------------------------------------------------------------
# CHART-04: PEA colored HTML table
# ---------------------------------------------------------------------------

def test_pea_table_returns_html_string_for_valid_data():
    """CHART-04: Valid position data returns an HTML string with a <table> element."""
    from charts.pea import generate_pea_table
    result = generate_pea_table(PEA_DATA_VALID)
    assert result is not None, "Expected HTML string, got None"
    assert "<table" in result, "Expected <table element in result"
    assert "</table>" in result, "Expected closing </table> in result"


def test_pea_table_positive_row_color():
    """CHART-04: Positive performance rows use background #0a2e1a."""
    from charts.pea import generate_pea_table, ROW_POSITIVE
    result = generate_pea_table(PEA_DATA_VALID)
    assert result is not None
    assert ROW_POSITIVE in result, f"Expected {ROW_POSITIVE} in positive row background"


def test_pea_table_negative_row_color():
    """CHART-04: Negative performance rows use background #2e0a0a."""
    from charts.pea import generate_pea_table, ROW_NEGATIVE
    result = generate_pea_table(PEA_DATA_VALID)
    assert result is not None
    assert ROW_NEGATIVE in result, f"Expected {ROW_NEGATIVE} in negative row background"


def test_pea_table_neutral_row_color():
    """CHART-04: Zero/missing performance rows use background #111111."""
    from charts.pea import generate_pea_table, ROW_NEUTRAL
    result = generate_pea_table(PEA_DATA_VALID)
    assert result is not None
    assert ROW_NEUTRAL in result, f"Expected {ROW_NEUTRAL} in neutral row background"


def test_pea_table_header_color():
    """CHART-04: Header row uses #1a1a2e background and #FF6B35 text."""
    from charts.pea import generate_pea_table, HEADER_BG, HEADER_TEXT
    result = generate_pea_table(PEA_DATA_VALID)
    assert result is not None
    assert HEADER_BG in result, f"Expected header bg {HEADER_BG}"
    assert HEADER_TEXT in result, f"Expected header text {HEADER_TEXT}"


def test_pea_table_column_headers_present():
    """CHART-04: All 6 column headers are present in the HTML output."""
    from charts.pea import generate_pea_table
    result = generate_pea_table(PEA_DATA_VALID)
    assert result is not None
    for header in ["Ticker", "Nom", "Cours", "1j (%)", "1sem (%)", "Eligible PEA"]:
        assert header in result, f"Missing column header: {header}"


def test_pea_table_returns_none_for_none_input():
    """CHART-04 + CHART-05: None input returns None without raising."""
    from charts.pea import generate_pea_table
    result = generate_pea_table(None)
    assert result is None, "Expected None for None pea_data"


def test_pea_table_returns_none_for_empty_list():
    """CHART-04 + CHART-05: Empty list returns None without raising."""
    from charts.pea import generate_pea_table
    result = generate_pea_table([])
    assert result is None, "Expected None for empty pea_data"


# ---------------------------------------------------------------------------
# CHART-05: Graceful fallback — all functions return None when rendering raises
# ---------------------------------------------------------------------------

def test_etf_chart_fallback_on_rendering_exception():
    """CHART-05: generate_etf_chart returns None (not raises) when plt.subplots raises."""
    from charts import etf as charts_etf
    with patch.object(charts_etf.plt, "subplots", side_effect=RuntimeError("mock render error")):
        result = charts_etf.generate_etf_chart(ETF_DATA_VALID, "13 mai 2026")
    assert result is None, "Expected None when matplotlib raises RuntimeError"


def test_crypto_sparklines_fallback_on_rendering_exception():
    """CHART-05: generate_crypto_sparklines returns None (not raises) when plt.subplots raises."""
    from charts import crypto as charts_crypto
    with patch.object(charts_crypto.plt, "subplots", side_effect=RuntimeError("mock render error")):
        result = charts_crypto.generate_crypto_sparklines(BTC_HISTORY_VALID, ETH_HISTORY_VALID)
    assert result is None, "Expected None when matplotlib raises RuntimeError"


def test_gauge_fallback_on_rendering_exception():
    """CHART-05: generate_fear_greed_gauge returns None (not raises) when plt.subplots raises."""
    from charts import gauge as charts_gauge
    with patch.object(charts_gauge.plt, "subplots", side_effect=RuntimeError("mock render error")):
        result = charts_gauge.generate_fear_greed_gauge(50)
    assert result is None, "Expected None when matplotlib raises RuntimeError"


def test_pea_table_fallback_on_exception():
    """CHART-05: generate_pea_table returns None (not raises) when an exception occurs internally."""
    from charts.pea import generate_pea_table
    # Pass a list containing a non-dict to trigger an internal AttributeError on None.get(...)
    result = generate_pea_table([None])
    assert result is None, "Expected None when internal processing raises"


# ---------------------------------------------------------------------------
# Package-level import: top-level charts module exposes all 4 functions
# ---------------------------------------------------------------------------

def test_charts_package_exports_all_public_functions():
    """Package: all 4 public functions importable from top-level charts package."""
    import charts
    assert hasattr(charts, "generate_etf_chart"), "charts.generate_etf_chart not found"
    assert hasattr(charts, "generate_crypto_sparklines"), "charts.generate_crypto_sparklines not found"
    assert hasattr(charts, "generate_fear_greed_gauge"), "charts.generate_fear_greed_gauge not found"
    assert hasattr(charts, "generate_pea_table"), "charts.generate_pea_table not found"
    assert callable(charts.generate_etf_chart)
    assert callable(charts.generate_crypto_sparklines)
    assert callable(charts.generate_fear_greed_gauge)
    assert callable(charts.generate_pea_table)
