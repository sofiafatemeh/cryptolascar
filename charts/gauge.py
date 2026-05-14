"""
charts/gauge.py — Fear & Greed gauge chart (CHART-03).

Generates a semicircular arc gauge with 5 color zones, a white needle,
and a large centered score value. Dark-mode matplotlib, base64-encoded PNG.

Public API:
  generate_fear_greed_gauge(score) -> Optional[str]

Input:
  score: int or float — Fear & Greed value from 0 (Extreme Fear) to 100 (Extreme Greed)

Returns: base64 UTF-8 PNG string, or None on any error (invalid score or exception).

CHART-03 / CHART-05.
"""
from __future__ import annotations

import base64
import io
import math
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend, VPS-safe
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from logging_setup import get_logger

logger = get_logger(__name__)

# --- Color constants (verbatim from UI-SPEC.md Color Contract) ---
CHART_BG = "#0d0d0d"
CHART_SPINE = "#2a2a2a"
CHART_TEXT = "#e0e0e0"
NEEDLE_COLOR = "#FFFFFF"

DPI = 150

# Five zones: (min_score_inclusive, max_score_inclusive, hex_color, label)
# Verbatim from UI-SPEC.md §Fear & Greed Gauge Colors
ZONES = [
    (0,  24,  "#FF4444", "Extreme Fear"),
    (25, 44,  "#FF8C42", "Fear"),
    (45, 55,  "#E0E0E0", "Neutral"),
    (56, 74,  "#00C851", "Greed"),
    (75, 100, "#00FF7F", "Extreme Greed"),
]

# Arc geometry constants (UI-SPEC §Fear & Greed Gauge Dimensions)
OUTER_RADIUS = 1.0
INNER_RADIUS = 0.55   # ring width = 0.45 — corresponds to arc_thickness ~0.25 of radius range


def _score_to_angle(score: float) -> float:
    """Convert a 0-100 score to degrees (matplotlib convention: 0°=right, 90°=top, 180°=left).

    Score 0   → angle 180° (left end of arc)
    Score 100 → angle   0° (right end of arc)
    Formula from UI-SPEC: theta = 180 - (score / 100) * 180
    """
    return 180.0 - (score / 100.0) * 180.0


def _zone_for_score(score: float) -> tuple:
    """Return (color, label) of the zone containing score."""
    for lo, hi, color, label in ZONES:
        if lo <= score <= hi:
            return color, label
    return CHART_TEXT, "Unknown"


def generate_fear_greed_gauge(score) -> Optional[str]:
    """Return base64 PNG string of Fear & Greed gauge, or None on any failure.

    score: int or float in range [0, 100]
    Returns None (without raising) for None input, out-of-range scores, or any exception.
    """
    try:
        # Input validation — T-06-09: explicit range check, no silent clamping
        if score is None:
            logger.error("Chart gauge failed: score is None")
            return None
        score = float(score)
        if not (0.0 <= score <= 100.0):
            logger.error(f"Chart gauge failed: score {score} out of range [0, 100]")
            return None

        active_color, active_label = _zone_for_score(score)

        fig, ax = plt.subplots(figsize=(5, 3))   # UI-SPEC: figsize=(5, 3)
        fig.patch.set_facecolor(CHART_BG)
        ax.set_facecolor(CHART_BG)
        ax.set_aspect("equal")
        ax.axis("off")

        # Draw the 5 arc zones as Wedge patches
        # Arc spans 180° (left) to 0° (right) — score 0=left, score 100=right
        for lo, hi, color, label in ZONES:
            zone_start_angle = _score_to_angle(hi)    # higher score → smaller angle
            zone_end_angle   = _score_to_angle(lo)    # lower score  → larger angle
            is_active = (lo <= score <= hi)
            alpha = 1.0 if is_active else 0.25        # UI-SPEC: inactive alpha = 0.25

            wedge = mpatches.Wedge(
                center=(0.0, 0.0),
                r=OUTER_RADIUS,
                theta1=zone_start_angle,
                theta2=zone_end_angle,
                width=OUTER_RADIUS - INNER_RADIUS,    # ring width
                facecolor=color,
                edgecolor=CHART_BG,
                linewidth=1.5,
                alpha=alpha,
            )
            ax.add_patch(wedge)

        # Needle — white line from center to inner arc edge at score's angle
        # UI-SPEC: needle color = #FFFFFF, needle width = 2.5 pt
        needle_angle_rad = math.radians(_score_to_angle(score))
        needle_len = INNER_RADIUS * 0.9   # slightly shorter than inner radius for aesthetics
        nx = needle_len * math.cos(needle_angle_rad)
        ny = needle_len * math.sin(needle_angle_rad)
        ax.plot(
            [0.0, nx], [0.0, ny],
            color=NEEDLE_COLOR,
            linewidth=2.5,            # UI-SPEC: needle width = 2.5 pt
            solid_capstyle="round",
            zorder=10,
        )
        # Needle pivot dot
        ax.plot(0.0, 0.0, "o", color=NEEDLE_COLOR, markersize=5, zorder=11)

        # Score text — 28pt bold, active zone color (UI-SPEC §Typography: gauge center score)
        ax.text(
            0.0, -0.15,
            str(int(round(score))),
            ha="center", va="top",
            fontsize=28,              # UI-SPEC: gauge center score = 28pt bold
            fontweight="bold",
            color=active_color,
        )

        # Zone label — 10pt regular, active zone color (UI-SPEC: axis label + gauge zone label)
        ax.text(
            0.0, -0.45,
            active_label,
            ha="center", va="top",
            fontsize=10,              # UI-SPEC: axis label + gauge zone label = 10pt
            color=active_color,
        )

        # Title — UI-SPEC §Copywriting: "Fear & Greed Index", 13pt bold
        ax.set_title(
            "Fear & Greed Index",
            fontsize=13,
            fontweight="bold",
            color=CHART_TEXT,
            pad=8,
        )

        # Axis limits — show upper semicircle with comfortable margins
        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-0.7, 1.3)

        # Encode to base64 PNG — same pattern as etf.py and crypto.py
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        buf.seek(0)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        plt.close(fig)
        return b64

    except Exception as e:
        logger.error(f"Chart gauge failed: {e}")
        # T-06-10: plt.close("all") in except branch prevents figure leak
        try:
            plt.close("all")
        except Exception:
            pass
        return None
