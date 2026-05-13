"""
tests/test_charts_gauge_pea.py — Tests TDD RED/GREEN pour CHART-03 et CHART-04.

CHART-03 : generate_fear_greed_gauge(score) -> Optional[str] (base64 PNG)
CHART-04 : generate_pea_table(pea_data)     -> Optional[str] (HTML string)

Vérifications fonctionnelles (comportement), structurelles (couleurs/typo UI-SPEC)
et de sécurité (XSS via html.escape, T-06-11).
"""
from __future__ import annotations

import base64
import sys
import os

# Ensure project root is in path for both local and worktree executions
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# CHART-03 — Fear & Greed Gauge
# ---------------------------------------------------------------------------

class TestGenerateFearGreedGauge:
    """Tests pour generate_fear_greed_gauge."""

    def _import(self):
        from charts.gauge import generate_fear_greed_gauge
        return generate_fear_greed_gauge

    # --- Valid scores return non-empty base64 PNG ---

    def test_score_50_returns_base64_png(self):
        fn = self._import()
        result = fn(50)
        assert result is not None, "Expected base64 string for score=50, got None"
        assert isinstance(result, str), "Expected str result"
        assert len(result) > 100, "Base64 string seems too short"
        raw = base64.b64decode(result)
        assert raw[:4] == b"\x89PNG", "Expected valid PNG magic bytes"

    def test_score_10_extreme_fear(self):
        fn = self._import()
        result = fn(10)
        assert result is not None
        raw = base64.b64decode(result)
        assert raw[:4] == b"\x89PNG"

    def test_score_35_fear_zone(self):
        fn = self._import()
        result = fn(35)
        assert result is not None
        raw = base64.b64decode(result)
        assert raw[:4] == b"\x89PNG"

    def test_score_65_greed_zone(self):
        fn = self._import()
        result = fn(65)
        assert result is not None
        raw = base64.b64decode(result)
        assert raw[:4] == b"\x89PNG"

    def test_score_90_extreme_greed(self):
        fn = self._import()
        result = fn(90)
        assert result is not None
        raw = base64.b64decode(result)
        assert raw[:4] == b"\x89PNG"

    def test_score_0_boundary(self):
        fn = self._import()
        result = fn(0)
        assert result is not None
        raw = base64.b64decode(result)
        assert raw[:4] == b"\x89PNG"

    def test_score_100_boundary(self):
        fn = self._import()
        result = fn(100)
        assert result is not None
        raw = base64.b64decode(result)
        assert raw[:4] == b"\x89PNG"

    # --- Invalid inputs return None without raising ---

    def test_none_returns_none(self):
        fn = self._import()
        result = fn(None)
        assert result is None, "Expected None for None input"

    def test_out_of_range_high_returns_none(self):
        fn = self._import()
        result = fn(150)
        assert result is None, "Expected None for score=150 (out of range)"

    def test_out_of_range_low_returns_none(self):
        fn = self._import()
        result = fn(-5)
        assert result is None, "Expected None for score=-5 (out of range)"

    def test_invalid_string_returns_none(self):
        fn = self._import()
        result = fn("not-a-number")
        assert result is None, "Expected None for string input"

    # --- Module-level constant verification (UI-SPEC compliance) ---

    def test_gauge_module_constants(self):
        import charts.gauge as mod
        # figsize
        import ast
        import inspect
        source = inspect.getsource(mod)
        assert "figsize=(5, 3)" in source, "figsize=(5, 3) missing (UI-SPEC CHART-03)"
        # Needle
        assert "#FFFFFF" in source, "NEEDLE_COLOR #FFFFFF missing"
        # Five zone colors
        assert "#FF4444" in source, "Extreme Fear color #FF4444 missing"
        assert "#FF8C42" in source, "Fear color #FF8C42 missing"
        assert "#E0E0E0" in source, "Neutral color #E0E0E0 missing"
        assert "#00C851" in source, "Greed color #00C851 missing"
        assert "#00FF7F" in source, "Extreme Greed color #00FF7F missing"
        # Typography sizes
        assert "fontsize=28" in source, "fontsize=28 (gauge center score) missing"
        assert "fontsize=10" in source, "fontsize=10 (zone label) missing"
        # Alpha
        assert "0.25" in source, "Inactive zone alpha 0.25 missing"
        # Needle width
        assert "linewidth=2.5" in source or "linewidth = 2.5" in source, "needle linewidth=2.5 missing"
        # Title
        assert "Fear & Greed Index" in source, "Gauge title missing"


# ---------------------------------------------------------------------------
# CHART-04 — PEA Colored HTML Table
# ---------------------------------------------------------------------------

_SAMPLE_PEA_DATA = [
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


class TestGeneratePeaTable:
    """Tests pour generate_pea_table."""

    def _import(self):
        from charts.pea import generate_pea_table
        return generate_pea_table

    # --- Basic return type ---

    def test_valid_data_returns_html_string(self):
        fn = self._import()
        result = fn(_SAMPLE_PEA_DATA)
        assert result is not None, "Expected HTML string, got None"
        assert isinstance(result, str), "Expected str type"
        assert "<table" in result, "Expected <table element in output"

    # --- Row coloring per performance ---

    def test_positive_row_has_positive_bg(self):
        fn = self._import()
        result = fn(_SAMPLE_PEA_DATA)
        assert "#0a2e1a" in result, "Positive row bg #0a2e1a missing"

    def test_negative_row_has_negative_bg(self):
        fn = self._import()
        result = fn(_SAMPLE_PEA_DATA)
        assert "#2e0a0a" in result, "Negative row bg #2e0a0a missing"

    def test_neutral_row_has_neutral_bg(self):
        fn = self._import()
        result = fn(_SAMPLE_PEA_DATA)
        assert "#111111" in result, "Neutral row bg #111111 missing"

    # --- Performance text colors ---

    def test_positive_pct_color(self):
        fn = self._import()
        result = fn(_SAMPLE_PEA_DATA)
        assert "#00C851" in result, "Positive pct color #00C851 missing"

    def test_negative_pct_color(self):
        fn = self._import()
        result = fn(_SAMPLE_PEA_DATA)
        assert "#FF4444" in result, "Negative pct color #FF4444 missing"

    def test_neutral_pct_color(self):
        fn = self._import()
        result = fn(_SAMPLE_PEA_DATA)
        assert "#888888" in result, "Neutral pct color #888888 missing"

    # --- Header styling ---

    def test_header_bg_color(self):
        fn = self._import()
        result = fn(_SAMPLE_PEA_DATA)
        assert "#1a1a2e" in result, "Header bg #1a1a2e missing"

    def test_header_text_color(self):
        fn = self._import()
        result = fn(_SAMPLE_PEA_DATA)
        assert "#FF6B35" in result, "Header text #FF6B35 missing"

    # --- Column headers present ---

    def test_column_headers_present(self):
        fn = self._import()
        result = fn(_SAMPLE_PEA_DATA)
        for header in ["Ticker", "Nom", "Cours", "1j (%)", "1sem (%)", "Eligible PEA"]:
            assert header in result, f"Column header '{header}' missing from table"

    # --- Data values rendered ---

    def test_ticker_in_output(self):
        fn = self._import()
        result = fn(_SAMPLE_PEA_DATA)
        assert "MC.PA" in result, "Ticker MC.PA not found in output"

    def test_price_formatted(self):
        fn = self._import()
        result = fn(_SAMPLE_PEA_DATA)
        assert "750.00" in result, "Price 750.00 not formatted correctly"

    def test_pea_eligible_oui(self):
        fn = self._import()
        result = fn(_SAMPLE_PEA_DATA)
        assert "Oui" in result, "PEA eligible 'Oui' not found"

    # --- Invalid inputs ---

    def test_none_returns_none(self):
        fn = self._import()
        result = fn(None)
        assert result is None, "Expected None for None input"

    def test_empty_list_returns_none(self):
        fn = self._import()
        result = fn([])
        assert result is None, "Expected None for empty list"

    # --- XSS mitigation (T-06-11) ---

    def test_xss_ticker_escaped(self):
        """Ticker with HTML special chars must be escaped (T-06-11)."""
        fn = self._import()
        malicious_data = [
            {
                "ticker": "<script>alert('xss')</script>",
                "name": "Evil Corp",
                "price": 1.0,
                "change_1d": 0.5,
                "change_1w": 1.0,
                "pea_eligible": None,
            }
        ]
        result = fn(malicious_data)
        assert result is not None
        # Raw <script> tag must NOT appear verbatim in output
        assert "<script>" not in result, "XSS: unescaped <script> tag in HTML output"
        # Escaped form should be present
        assert "&lt;script&gt;" in result, "XSS: <script> not properly HTML-escaped"

    def test_xss_name_escaped(self):
        """Name with HTML special chars must be escaped (T-06-11)."""
        fn = self._import()
        malicious_data = [
            {
                "ticker": "TEST",
                "name": '<img src="x" onerror="alert(1)">',
                "price": 10.0,
                "change_1d": -1.0,
                "change_1w": 0.0,
                "pea_eligible": False,
            }
        ]
        result = fn(malicious_data)
        assert result is not None
        assert '<img src="x"' not in result, "XSS: unescaped <img> in HTML output"

    # --- Module-level constant verification (UI-SPEC compliance) ---

    def test_pea_module_constants(self):
        import charts.pea as mod
        import inspect
        source = inspect.getsource(mod)
        assert "#0a2e1a" in source, "ROW_POSITIVE #0a2e1a missing"
        assert "#2e0a0a" in source, "ROW_NEGATIVE #2e0a0a missing"
        assert "#111111" in source, "ROW_NEUTRAL #111111 missing"
        assert "#00C851" in source, "TEXT_POSITIVE #00C851 missing"
        assert "#FF4444" in source, "TEXT_NEGATIVE #FF4444 missing"
        assert "#888888" in source, "TEXT_NEUTRAL #888888 missing"
        assert "#1a1a2e" in source, "HEADER_BG #1a1a2e missing"
        assert "#FF6B35" in source, "HEADER_TEXT #FF6B35 missing"
        assert "#2a2a2a" in source, "BORDER #2a2a2a missing"
        assert "8px 12px" in source, "CELL_PADDING 8px 12px missing"
        assert "12px" in source, "FONT_SIZE 12px missing"
