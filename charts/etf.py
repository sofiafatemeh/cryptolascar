"""
charts/etf.py — ETF performance bar chart (CHART-01).

Generates a side-by-side bar chart of 1-day and 1-week ETF performance,
rendered as a dark-mode matplotlib figure, base64-encoded PNG.

Public API:
  generate_etf_chart(etf_data, date_str) -> Optional[str]

Input:
  etf_data: dict mapping ticker (str) to {"1d": float, "1w": float}
            Values are percentage variations (e.g. 1.5 means +1.5%).
  date_str: str — formatted date for chart title (e.g. "13 mai 2026")

Returns: base64 UTF-8 PNG string, or None on any error.

CHART-01 / CHART-05.
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
BAR_POSITIVE = "#00C851"
BAR_NEGATIVE = "#FF4444"
BAR_1DAY_ALPHA = 1.0
BAR_1WEEK_ALPHA = 0.65

DPI = 150


def generate_etf_chart(
    etf_data: Optional[dict],
    date_str: str,
) -> Optional[str]:
    """Return base64 PNG string of ETF bar chart, or None on any failure.

    etf_data: dict[str, dict] — {"TICKER": {"1d": float, "1w": float}, ...}
    date_str: str — e.g. "13 mai 2026"
    """
    try:
        if not etf_data:
            logger.error("Chart etf failed: etf_data is empty or None")
            return None

        tickers = list(etf_data.keys())
        values_1d = [etf_data[t].get("1d", 0.0) or 0.0 for t in tickers]
        values_1w = [etf_data[t].get("1w", 0.0) or 0.0 for t in tickers]

        n = len(tickers)
        x = np.arange(n)  # group centers
        bar_w = 0.35       # width per bar (UI-SPEC: bar width = 0.35)
        gap = 0.05         # gap between pairs (UI-SPEC: 0.05 between pairs)

        fig, ax = plt.subplots(figsize=(8, 4))  # UI-SPEC: figsize=(8,4)
        fig.patch.set_facecolor(CHART_BG)
        ax.set_facecolor(CHART_BG)

        # 1-day bars (left of each group) — full opacity
        bars_1d = ax.bar(  # noqa: F841
            x - (bar_w / 2 + gap / 2),
            values_1d,
            width=bar_w,
            linewidth=0,  # UI-SPEC: bar edge width=0
            alpha=BAR_1DAY_ALPHA,
            color=[BAR_POSITIVE if v >= 0 else BAR_NEGATIVE for v in values_1d],
            label="1j",
        )

        # 1-week bars (right of each group) — dimmed
        bars_1w = ax.bar(  # noqa: F841
            x + (bar_w / 2 + gap / 2),
            values_1w,
            width=bar_w,
            linewidth=0,
            alpha=BAR_1WEEK_ALPHA,
            color=[BAR_POSITIVE if v >= 0 else BAR_NEGATIVE for v in values_1w],
            label="1sem",
        )

        # Axes labels and ticks (UI-SPEC Typography)
        ax.set_xticks(x)
        ax.set_xticklabels(tickers, fontsize=9, color=CHART_TEXT)  # tick label: 9pt
        ax.set_ylabel("Variation (%)", fontsize=10, color=CHART_TEXT)  # axis label: 10pt
        ax.tick_params(colors=CHART_TEXT, labelsize=9)

        # Grid (UI-SPEC: horizontal only, chart_grid, alpha 0.5)
        ax.yaxis.grid(True, color=CHART_GRID, alpha=0.5, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.xaxis.grid(False)

        # Spines (UI-SPEC: chart_spine)
        for spine in ax.spines.values():
            spine.set_edgecolor(CHART_SPINE)

        # Title (UI-SPEC Typography: 13pt bold; Copywriting: "Performance ETFs — {date}")
        ax.set_title(
            f"Performance ETFs — {date_str}",
            fontsize=13,
            fontweight="bold",
            color=CHART_TEXT,
            pad=10,
        )

        # Legend (UI-SPEC Typography: 9pt)
        ax.legend(
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
        logger.error(f"Chart etf failed: {e}")
        try:
            plt.close("all")
        except Exception:
            pass
        return None
