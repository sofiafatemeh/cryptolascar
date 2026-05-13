"""
charts/ — Chart generation module for CryptoLascar email reports.

All chart functions render matplotlib figures to PNG, base64-encode the result,
and return the string for inline embedding in HTML emails.

Backend: matplotlib.use("Agg") — non-interactive, VPS-safe (no display required).
DPI: 150 (all charts).

Public API:
  generate_etf_chart(etf_data, date_str)         -> Optional[str]  # base64 PNG
  generate_crypto_sparklines(btc_history, eth_history) -> Optional[str]  # base64 PNG
  generate_fear_greed_gauge(score)               -> Optional[str]  # base64 PNG
  generate_pea_table(pea_data)                   -> Optional[str]  # HTML string

Every function catches ALL exceptions, logs the error, and returns None on failure.
Callers must check for None and substitute the fallback HTML string from UI-SPEC.md.

CHART-05 graceful degradation: pipeline never raises from chart generation.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")  # MUST be called before any other matplotlib import

from charts.etf import generate_etf_chart
from charts.crypto import generate_crypto_sparklines

try:
    from charts.gauge import generate_fear_greed_gauge
except ImportError:
    generate_fear_greed_gauge = None  # type: ignore[assignment]  # not yet implemented

try:
    from charts.pea import generate_pea_table
except ImportError:
    generate_pea_table = None  # type: ignore[assignment]  # not yet implemented

__all__ = [
    "generate_etf_chart",
    "generate_crypto_sparklines",
    "generate_fear_greed_gauge",
    "generate_pea_table",
]
