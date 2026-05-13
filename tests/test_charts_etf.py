"""
tests/test_charts_etf.py — Tests pour charts/etf.py (CHART-01).

Phase TDD RED: ces tests échouent avant implémentation de charts/etf.py.
"""
import base64
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestGenerateEtfChart:
    """Tests for generate_etf_chart()"""

    def test_valid_data_returns_non_empty_string(self):
        """generate_etf_chart() with valid data returns a non-empty base64 string."""
        from charts.etf import generate_etf_chart
        data = {
            "SPY": {"1d": 0.52, "1w": 1.3},
            "QQQ": {"1d": -0.1, "1w": 0.8},
        }
        result = generate_etf_chart(data, "13 mai 2026")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_valid_data_returns_valid_png(self):
        """Returned string decodes as valid PNG (starts with \\x89PNG)."""
        from charts.etf import generate_etf_chart
        data = {
            "SPY": {"1d": 0.52, "1w": 1.3},
            "QQQ": {"1d": -0.1, "1w": 0.8},
        }
        result = generate_etf_chart(data, "13 mai 2026")
        assert result is not None
        raw = base64.b64decode(result)
        assert raw[:4] == b"\x89PNG", f"Not a PNG: {raw[:4]!r}"

    def test_none_input_returns_none(self):
        """generate_etf_chart(None, ...) returns None without raising."""
        from charts.etf import generate_etf_chart
        result = generate_etf_chart(None, "13 mai 2026")
        assert result is None

    def test_empty_dict_returns_none(self):
        """generate_etf_chart({}, ...) returns None (nothing to plot)."""
        from charts.etf import generate_etf_chart
        result = generate_etf_chart({}, "13 mai 2026")
        assert result is None

    def test_negative_values_return_valid_png(self):
        """generate_etf_chart() with all negative values still returns a valid PNG."""
        from charts.etf import generate_etf_chart
        data = {
            "EEM": {"1d": -1.5, "1w": -3.2},
            "GLD": {"1d": -0.3, "1w": -0.8},
        }
        result = generate_etf_chart(data, "13 mai 2026")
        assert result is not None
        raw = base64.b64decode(result)
        assert raw[:4] == b"\x89PNG"

    def test_mixed_positive_negative_values(self):
        """generate_etf_chart() with mixed values returns a valid PNG."""
        from charts.etf import generate_etf_chart
        data = {
            "SPY": {"1d": 0.52, "1w": -0.3},
            "QQQ": {"1d": -0.1, "1w": 1.2},
            "EWQ": {"1d": 0.0, "1w": 0.0},
        }
        result = generate_etf_chart(data, "13 mai 2026")
        assert result is not None
        raw = base64.b64decode(result)
        assert raw[:4] == b"\x89PNG"
