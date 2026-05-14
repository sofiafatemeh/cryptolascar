"""
charts/pea.py — PEA colored HTML table (CHART-04).

Generates a styled HTML table of PEA position data with per-row coloring
based on daily performance. Output is an HTML string (not PNG).

Public API:
  generate_pea_table(pea_data) -> Optional[str]

Input:
  pea_data: list[dict] — each dict may contain:
    "ticker":      str   — e.g. "MC.PA"
    "name":        str   — e.g. "LVMH Moët Hennessy"
    "price":       float — last closing price
    "change_1d":   float — 1-day % variation (positive = green row)
    "change_1w":   float — 1-week % variation
    "pea_eligible": bool or None — PEA eligibility status

Returns: HTML string containing a <table>, or None on any error.

CHART-04 / CHART-05.

Security: T-06-11 — all string values from external data are HTML-escaped
via html.escape() before embedding in output (ASVS L1 output encoding).
"""
from __future__ import annotations

import html
from typing import Optional

from logging_setup import get_logger

logger = get_logger(__name__)

# --- Color tokens (verbatim from UI-SPEC.md §PEA Colored Table) ---
ROW_POSITIVE = "#0a2e1a"   # row bg when daily performance > 0
ROW_NEGATIVE = "#2e0a0a"   # row bg when daily performance < 0
ROW_NEUTRAL  = "#111111"   # row bg when performance == 0 or missing
TEXT_POSITIVE = "#00C851"  # performance % text when positive
TEXT_NEGATIVE = "#FF4444"  # performance % text when negative
TEXT_NEUTRAL  = "#888888"  # performance % text when neutral/missing
HEADER_BG    = "#1a1a2e"   # header row background
HEADER_TEXT  = "#FF6B35"   # header text — orange accent
CELL_TEXT    = "#e0e0e0"   # ticker and name text in data rows
BORDER       = "#2a2a2a"   # table and cell border

# --- Typography (UI-SPEC.md §PEA Table Typography) ---
FONT_FAMILY = '"Courier New", monospace'
FONT_SIZE   = "12px"

# Cell padding: 8px vertical, 12px horizontal (UI-SPEC §Chart Dimensions PEA)
CELL_PADDING = "8px 12px"

# Column headers (UI-SPEC §Copywriting Contract §PEA Table Column Headers)
HEADERS = ["Ticker", "Nom", "Cours", "1j (%)", "1sem (%)", "Eligible PEA"]


def _fmt_pct(value) -> str:
    """Format a float as +1.23% or -1.23%, or — if None."""
    if value is None:
        return "—"
    try:
        v = float(value)
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:.2f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_price(value) -> str:
    """Format a price float as '750.00', or — if None."""
    if value is None:
        return "—"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "—"


def _pea_badge(eligible) -> str:
    """Return 'Oui', 'Non', or — for PEA eligibility."""
    if eligible is True:
        return "Oui"
    if eligible is False:
        return "Non"
    return "—"


def _row_style(change_1d) -> tuple:
    """Return (row_bg, perf_color) based on daily performance value."""
    if change_1d is None:
        return ROW_NEUTRAL, TEXT_NEUTRAL
    try:
        v = float(change_1d)
    except (TypeError, ValueError):
        return ROW_NEUTRAL, TEXT_NEUTRAL
    if v > 0:
        return ROW_POSITIVE, TEXT_POSITIVE
    if v < 0:
        return ROW_NEGATIVE, TEXT_NEGATIVE
    return ROW_NEUTRAL, TEXT_NEUTRAL


def generate_pea_table(pea_data: Optional[list]) -> Optional[str]:
    """Return HTML table string for PEA positions, or None on any failure.

    pea_data: list[dict] — see module docstring for field names.
    Returns None for empty or None input without raising.

    Security: T-06-11 — ticker and name are HTML-escaped before output.
    """
    try:
        if not pea_data:
            logger.error("Chart pea failed: pea_data is empty or None")
            return None

        base_cell_style = (
            f"font-family:{FONT_FAMILY};"
            f"font-size:{FONT_SIZE};"
            f"padding:{CELL_PADDING};"
            f"border:1px solid {BORDER};"
            f"color:{CELL_TEXT};"
        )
        header_cell_style = (
            f"font-family:{FONT_FAMILY};"
            f"font-size:{FONT_SIZE};"
            f"font-weight:700;"
            f"padding:{CELL_PADDING};"
            f"border:1px solid {BORDER};"
            f"color:{HEADER_TEXT};"
            f"background-color:{HEADER_BG};"
        )

        # Table wrapper style
        table_style = (
            f"border-collapse:collapse;"
            f"width:100%;"
            f"background-color:{ROW_NEUTRAL};"
            f"font-family:{FONT_FAMILY};"
        )

        # Header row — left-aligned for first 2 cols, right-aligned for numeric cols
        header_cells = "".join(
            f'<th style="{header_cell_style}text-align:{"left" if i < 2 else "right"};">'
            f"{h}</th>"
            for i, h in enumerate(HEADERS)
        )
        header_row = f'<tr style="background-color:{HEADER_BG};">{header_cells}</tr>'

        # Data rows
        data_rows = []
        for item in pea_data:
            change_1d = item.get("change_1d")
            change_1w = item.get("change_1w")
            row_bg, perf_color_1d = _row_style(change_1d)
            _, perf_color_1w = _row_style(change_1w)

            row_style = f"background-color:{row_bg};"

            # T-06-11: HTML-escape all string fields from external data (ASVS L1)
            safe_ticker = html.escape(str(item.get("ticker", "") or ""), quote=False) or "—"
            safe_name = html.escape(str(item.get("name", "") or ""), quote=False) or "—"

            # Ticker — left-aligned
            ticker_td = (
                f'<td style="{base_cell_style}text-align:left;">'
                f"{safe_ticker}</td>"
            )
            # Name — left-aligned
            name_td = (
                f'<td style="{base_cell_style}text-align:left;">'
                f"{safe_name}</td>"
            )
            # Price — right-aligned
            price_td = (
                f'<td style="{base_cell_style}text-align:right;">'
                f"{_fmt_price(item.get('price'))}</td>"
            )
            # 1j (%) — right-aligned, colored
            pct_1d_td = (
                f'<td style="{base_cell_style}text-align:right;color:{perf_color_1d};font-weight:700;">'
                f"{_fmt_pct(change_1d)}</td>"
            )
            # 1sem (%) — right-aligned, colored
            pct_1w_td = (
                f'<td style="{base_cell_style}text-align:right;color:{perf_color_1w};font-weight:700;">'
                f"{_fmt_pct(change_1w)}</td>"
            )
            # Eligible PEA — right-aligned
            eligible_td = (
                f'<td style="{base_cell_style}text-align:right;">'
                f"{_pea_badge(item.get('pea_eligible'))}</td>"
            )

            row = (
                f'<tr style="{row_style}">'
                f"{ticker_td}{name_td}{price_td}{pct_1d_td}{pct_1w_td}{eligible_td}"
                f"</tr>"
            )
            data_rows.append(row)

        rows_html = "\n".join(data_rows)
        table_html = (
            f'<table style="{table_style}">'
            f"<thead>{header_row}</thead>"
            f"<tbody>{rows_html}</tbody>"
            f"</table>"
        )
        return table_html

    except Exception as e:
        logger.error(f"Chart pea failed: {e}")
        return None
