"""tests/test_template_structure.py — Phase 7 structural tests for report_email.html template.

Gaps covered:
  Gap 1: Template has no light-mode background (#ffffff absent)
  Gap 2: Template has no Georgia font (old font fully removed)
  Gap 3: {{ date }} NOT marked | safe (XSS prevention, T-07-04)
  Gap 4: @media (max-width:600px) breakpoint present (TMPL-02)
  Gap 5: MONTHLY CLOSE badge conditional present (TMPL-01)
"""
from __future__ import annotations

from pathlib import Path

import pytest

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "report_email.html"


@pytest.fixture(scope="module")
def template_content() -> str:
    assert TEMPLATE_PATH.exists(), f"Template file not found: {TEMPLATE_PATH}"
    return TEMPLATE_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Gap 1 — No light-mode white background
# ---------------------------------------------------------------------------

def test_template_has_no_light_mode_white_background(template_content: str):
    """Gap 1: Template must be dark-mode only — #ffffff must not appear anywhere.

    If the template contains #ffffff (case-insensitive), a light-mode background
    was left in, violating the dark-mode design requirement.
    """
    assert "#ffffff" not in template_content.lower(), (
        "Template contains '#ffffff' — light-mode background found; "
        "expected pure dark-mode palette (no #ffffff)."
    )


# ---------------------------------------------------------------------------
# Gap 2 — No Georgia font (old font fully removed)
# ---------------------------------------------------------------------------

def test_template_has_no_georgia_font(template_content: str):
    """Gap 2: Template must not reference the Georgia serif font.

    The design switch to 'Courier New' monospace replaced Georgia.
    Any remaining Georgia reference indicates an incomplete font migration.
    """
    assert "georgia" not in template_content.lower(), (
        "Template contains 'Georgia' font reference — old serif font was not fully removed; "
        "expected only 'Courier New' monospace."
    )


# ---------------------------------------------------------------------------
# Gap 3 — {{ date }} NOT marked | safe (XSS prevention, T-07-04)
# ---------------------------------------------------------------------------

def test_date_variable_not_marked_safe(template_content: str):
    """Gap 3: The {{ date }} variable must NOT use the | safe filter.

    Marking {{ date }} as safe would allow XSS if the date string contains HTML.
    The date must be auto-escaped by Jinja2's default escaping mechanism.

    Requirement: {{ date }} appears at least once AND {{ date | safe }} appears 0 times.
    """
    # The variable must actually be used in the template (not deleted)
    assert "{{ date }}" in template_content, (
        "Template does not contain '{{ date }}' at all — "
        "the date variable is missing from the template."
    )
    # The variable must NOT be marked safe (XSS vector)
    assert "{{ date | safe }}" not in template_content, (
        "Template contains '{{ date | safe }}' — this is an XSS vulnerability (T-07-04); "
        "the date field must NOT be marked safe."
    )


# ---------------------------------------------------------------------------
# Gap 4 — @media (max-width:600px) breakpoint present (TMPL-02)
# ---------------------------------------------------------------------------

def test_template_has_mobile_breakpoint(template_content: str):
    """Gap 4: Template must include a responsive @media (max-width:600px) breakpoint.

    TMPL-02 requires mobile-first responsive design. Without this breakpoint,
    the email layout breaks on screens narrower than 600px.
    """
    assert "max-width:600px" in template_content, (
        "Template does not contain '@media (max-width:600px)' breakpoint — "
        "TMPL-02 responsive design requirement is unmet."
    )


# ---------------------------------------------------------------------------
# Gap 5 — MONTHLY CLOSE badge conditional present (TMPL-01)
# ---------------------------------------------------------------------------

def test_template_has_monthly_close_badge(template_content: str):
    """Gap 5: Template must conditionally render a [MONTHLY CLOSE] badge.

    TMPL-01 requires that monthly reports display a special badge label.
    The conditional block must be present in the template source.
    """
    assert "MONTHLY CLOSE" in template_content, (
        "Template does not contain 'MONTHLY CLOSE' badge text — "
        "TMPL-01 report-type badge requirement is unmet."
    )
