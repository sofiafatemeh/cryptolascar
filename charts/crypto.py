"""
charts/crypto.py — Crypto price sparklines (CHART-02).

Generates overlapping BTC and ETH 7-day price sparklines,
rendered as a dark-mode matplotlib figure, base64-encoded PNG.

Public API:
  generate_crypto_sparklines(btc_history, eth_history) -> Optional[str]

Input:
  btc_history: list[float] — BTC closing prices over 7 days (oldest → newest)
  eth_history: list[float] — ETH closing prices over 7 days (oldest → newest)

Returns: base64 UTF-8 PNG string, or None on any error.

CHART-02 / CHART-05.
"""
from __future__ import annotations

import base64
import io
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend, VPS-safe
import matplotlib.pyplot as plt
import numpy as np

from logging_setup import get_logger

logger = get_logger(__name__)

# --- Color constants (verbatim from UI-SPEC.md Color Contract) ---
CHART_BG = "#0d0d0d"
CHART_GRID = "#1f1f1f"
CHART_SPINE = "#2a2a2a"
CHART_TEXT = "#e0e0e0"
SPARK_BTC = "#FF6B35"   # BTC 7-day line — orange accent
SPARK_ETH = "#00C851"   # ETH 7-day line — green
SPARK_FILL_ALPHA = 0.08  # area fill under each curve

DPI = 150


def generate_crypto_sparklines(
    btc_history: Optional[list],
    eth_history: Optional[list],
) -> Optional[str]:
    """Return base64 PNG string of BTC/ETH sparklines, or None on any failure.

    btc_history: list[float] — 7 daily closing prices for BTC (oldest first)
    eth_history: list[float] — 7 daily closing prices for ETH (oldest first)
    """
    try:
        if not btc_history or not eth_history:
            logger.error("Chart crypto failed: btc_history or eth_history is empty or None")
            return None
        if len(btc_history) < 2 or len(eth_history) < 2:
            logger.error("Chart crypto failed: need at least 2 data points for sparklines")
            return None

        btc = [float(v) for v in btc_history]
        eth = [float(v) for v in eth_history]
        x = np.arange(len(btc))   # day indices 0..N-1 (BTC)
        x_eth = np.arange(len(eth))  # day indices for ETH

        fig, ax = plt.subplots(figsize=(8, 3))  # UI-SPEC: figsize=(8,3)
        fig.patch.set_facecolor(CHART_BG)
        ax.set_facecolor(CHART_BG)

        # BTC line (UI-SPEC: SPARK_BTC, linewidth=2.0, no markers)
        ax.plot(x, btc, color=SPARK_BTC, linewidth=2.0, marker="", label="BTC")
        ax.fill_between(x, btc, alpha=SPARK_FILL_ALPHA, color=SPARK_BTC)

        # ETH on twin axis (different price scale)
        ax2 = ax.twinx()
        ax2.set_facecolor(CHART_BG)
        ax2.plot(x_eth, eth, color=SPARK_ETH, linewidth=2.0, marker="", label="ETH")
        ax2.fill_between(x_eth, eth, alpha=SPARK_FILL_ALPHA, color=SPARK_ETH)
        ax2.tick_params(colors=CHART_TEXT, labelsize=9)
        for spine in ax2.spines.values():
            spine.set_edgecolor(CHART_SPINE)

        # Primary axis styling
        ax.set_ylabel("Prix (USD)", fontsize=10, color=CHART_TEXT)  # UI-SPEC: y-axis label
        ax.tick_params(colors=CHART_TEXT, labelsize=9)
        ax.yaxis.grid(True, color=CHART_GRID, alpha=0.5, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.xaxis.grid(False)
        for spine in ax.spines.values():
            spine.set_edgecolor(CHART_SPINE)

        # Title (UI-SPEC Copywriting: "BTC / ETH — 7 derniers jours", 13pt bold)
        ax.set_title(
            "BTC / ETH — 7 derniers jours",
            fontsize=13,
            fontweight="bold",
            color=CHART_TEXT,
            pad=10,
        )

        # Combined legend from both axes
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(
            lines1 + lines2,
            labels1 + labels2,
            fontsize=9,
            facecolor=CHART_BG,
            edgecolor=CHART_SPINE,
            labelcolor=CHART_TEXT,
        )

        # Encode to base64 PNG
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        buf.seek(0)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        plt.close(fig)
        return b64

    except Exception as e:
        logger.error(f"Chart crypto failed: {e}")
        try:
            plt.close("all")
        except Exception:
            pass
        return None
