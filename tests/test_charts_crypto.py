"""
tests/test_charts_crypto.py — Tests pour charts/crypto.py (CHART-02).

Phase TDD RED: ces tests échouent avant implémentation de charts/crypto.py.
"""
import base64
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BTC_7D = [40000.0, 41000.0, 42000.0, 41500.0, 43000.0, 44000.0, 45000.0]
ETH_7D = [2400.0, 2450.0, 2500.0, 2480.0, 2550.0, 2600.0, 2650.0]


class TestGenerateCryptoSparklines:
    """Tests for generate_crypto_sparklines()"""

    def test_valid_data_returns_non_empty_string(self):
        """generate_crypto_sparklines() with valid 7-day data returns a non-empty base64 string."""
        from charts.crypto import generate_crypto_sparklines
        result = generate_crypto_sparklines(BTC_7D, ETH_7D)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_valid_data_returns_valid_png(self):
        """Returned string decodes as valid PNG (starts with \\x89PNG)."""
        from charts.crypto import generate_crypto_sparklines
        result = generate_crypto_sparklines(BTC_7D, ETH_7D)
        assert result is not None
        raw = base64.b64decode(result)
        assert raw[:4] == b"\x89PNG", f"Not a PNG: {raw[:4]!r}"

    def test_none_input_returns_none(self):
        """generate_crypto_sparklines(None, None) returns None without raising."""
        from charts.crypto import generate_crypto_sparklines
        result = generate_crypto_sparklines(None, None)
        assert result is None

    def test_empty_lists_return_none(self):
        """generate_crypto_sparklines([], []) returns None (nothing to plot)."""
        from charts.crypto import generate_crypto_sparklines
        result = generate_crypto_sparklines([], [])
        assert result is None

    def test_single_element_returns_none(self):
        """generate_crypto_sparklines with single-element lists returns None (cannot draw line)."""
        from charts.crypto import generate_crypto_sparklines
        result = generate_crypto_sparklines([42000.0], [2500.0])
        assert result is None

    def test_mixed_btc_eth_lengths(self):
        """generate_crypto_sparklines works when BTC and ETH have different lengths."""
        from charts.crypto import generate_crypto_sparklines
        btc = [40000.0, 41000.0, 42000.0, 43000.0, 44000.0]
        eth = [2400.0, 2450.0, 2500.0, 2480.0, 2550.0, 2600.0, 2650.0]
        result = generate_crypto_sparklines(btc, eth)
        # Should return valid PNG or None — both are acceptable (not raise)
        if result is not None:
            raw = base64.b64decode(result)
            assert raw[:4] == b"\x89PNG"

    def test_btc_none_eth_valid_returns_none(self):
        """generate_crypto_sparklines(None, valid) returns None."""
        from charts.crypto import generate_crypto_sparklines
        result = generate_crypto_sparklines(None, ETH_7D)
        assert result is None

    def test_btc_valid_eth_none_returns_none(self):
        """generate_crypto_sparklines(valid, None) returns None."""
        from charts.crypto import generate_crypto_sparklines
        result = generate_crypto_sparklines(BTC_7D, None)
        assert result is None
