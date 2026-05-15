---
phase: 07-template-redesign-integration
reviewed: 2026-05-15T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - main.py
  - reporters/base.py
  - reporters/daily.py
  - reporters/dispatch.py
  - reporters/monthly.py
  - reporters/weekly.py
  - templates/report_email.html
  - tests/test_dispatch.py
  - tests/test_main_pipeline.py
  - tests/test_monthly.py
  - tests/test_phase7_integration.py
  - tests/test_reporters_base.py
  - tests/test_reporters_monthly.py
  - tests/test_reporters_weekly.py
  - tests/test_weekly.py
findings:
  critical: 2
  warning: 2
  info: 6
  total: 10
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-05-15T00:00:00Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Phase 7 delivered the ReportOutput dual-output type, dark-mode HTML email template, 2x2 chart panels, and full pipeline wiring (reporters → dispatch → main.py → delivery). The core contract — `ReportOutput(html_body, plain_text)` as a NamedTuple, graceful degradation at every level, no credentials in logs — is correctly implemented throughout.

Two blocking defects were found. First, all three reporters pass an empty string for `date_str` to `generate_etf_chart`, producing charts with a blank title (`"Performance ETFs —"`). Second, `_sections_to_html` places raw Markdown (including table rows, bullet points, and `**bold**` markers) into a single `<p>` tag with no HTML conversion; email clients collapse the embedded newlines to spaces, rendering monthly and weekly section bodies as unformatted walls of text and pipe characters.

Two warnings cover a double-ALERTE condition in `reporters/weekly.py` when `eligibility_changed=True`, and credential exposure risk from `exc_info=True` in the main pipeline error handler. Six info-level items cover code duplication across the three reporter modules and minor test quality issues.

---

## Critical Issues

### CR-01: Empty `date_str` passed to `generate_etf_chart` in all three reporters

**File:** `reporters/daily.py:267`, `reporters/weekly.py:256`, `reporters/monthly.py:296`

**Issue:** All three `build_*_report` functions call `_build_chart_panel(data, "")` — hardcoding an empty string for `date_str`. `_build_chart_panel` forwards this to `generate_etf_chart(etf_data, date_str)`, and `charts/etf.py` uses `date_str` as the chart title suffix (confirmed: `f"Performance ETFs — {date_str}"` at line 113 of `charts/etf.py`). Every ETF chart rendered in production shows `"Performance ETFs —"` with no date, defeating the purpose of the parameter.

The `_build_chart_panel` function signature is `def _build_chart_panel(data: dict, date_str: str) -> str:` — the parameter exists, callers simply never populate it.

**Fix:** Compute `date_str` from `datetime.date.today()` inside `_build_chart_panel` (simplest fix), or thread the date down from `main.py` into the reporter `build_*_report` functions:

```python
# Option A: Compute inside _build_chart_panel (no signature change)
def _build_chart_panel(data: dict) -> str:
    import datetime
    date_str = datetime.date.today().strftime("%-d %B %Y")  # e.g. "13 mai 2026"
    ...

# Option B: Thread from callers (three call sites to update)
chart_panel = _build_chart_panel(data, datetime.date.today().isoformat())
```

---

### CR-02: `_sections_to_html` places raw Markdown into a `<p>` tag without HTML conversion

**File:** `reporters/daily.py:234-247`, `reporters/weekly.py:218-231`, `reporters/monthly.py:245-258`

**Issue:** The shared `_sections_to_html` implementation splits each Markdown section on the first two newlines, takes everything after them as `body_md`, applies `html.escape()`, and wraps it in a `<p>` tag:

```python
body_escaped = _html.escape(body_md)
p_body = (
    f'<p style="color:#e0e0e0;...font-size:14px;line-height:1.6;">{body_escaped}</p>'
)
```

`html.escape()` does not convert Markdown to HTML. The result:

- **Monthly and weekly reports:** Markdown table rows (`| Ticker | Prix | Variation |`) appear as literal pipe-separated text. Email clients treat raw newlines inside `<p>` as whitespace, collapsing `|---|---|---|` rows onto the same line as the header, producing garbled output. The section bodies of `_etf_monthly`, `_crypto_monthly`, `_pea_monthly`, `_macro_backdrop`, `_macro_watch`, `_etf_performance`, `_crypto_recap`, and `_pea_wrap` are all affected.
- **All reporters:** Bullet points from `_news_section` / `_news_digest` / `_news_themes` appear as `- Title (Source)` literal text with no `<ul><li>` structure, collapsed to a single line.
- **All reporters:** `**bold**` markers from news bullets appear literally.

The `plain_text` field is unaffected and correct. Only `html_body` is broken.

No tests cover this condition — existing tests check that `"background:#111111"` and chart `<table>` tags are present, but none verify that section body text is legible or correctly structured in the HTML output.

**Fix:** Convert Markdown to HTML before wrapping. Minimal approach using the standard library:

```python
def _sections_to_html(sections: list[str]) -> str:
    """Convert Markdown sections list to html_section() card HTML."""
    import re
    parts = []
    for md_section in sections:
        lines_s = md_section.strip().split("\n", 2)
        title_s = lines_s[0].lstrip("# ").strip() if lines_s else "Section"
        body_md = lines_s[2].strip() if len(lines_s) > 2 else ""

        # Convert Markdown table rows to <table> HTML
        body_html = _md_to_simple_html(body_md)
        p_body = (
            f'<div style="color:#e0e0e0;font-family:\'Courier New\',monospace;'
            f'font-size:14px;line-height:1.6;">{body_html}</div>'
        )
        parts.append(html_section(title_s, p_body))
    return "".join(parts)


def _md_to_simple_html(md: str) -> str:
    """Minimal Markdown-to-HTML for section bodies (tables, bullets, paragraphs)."""
    import re, html as _html

    lines = md.split("\n")
    out = []
    in_table = False
    in_ul = False

    for line in lines:
        if re.match(r"\|.*\|", line):
            if re.match(r"\|[-| :]+\|", line):
                continue  # separator row
            if not in_table:
                out.append('<table style="border-collapse:collapse;width:100%;color:#e0e0e0;">')
                in_table = True
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            cells_html = "".join(f'<td style="padding:4px 8px;border-bottom:1px solid #2a2a2a;">{_html.escape(c)}</td>' for c in cells)
            out.append(f"<tr>{cells_html}</tr>")
        else:
            if in_table:
                out.append("</table>")
                in_table = False
            if line.startswith("- "):
                if not in_ul:
                    out.append('<ul style="margin:4px 0;padding-left:16px;">')
                    in_ul = True
                content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", _html.escape(line[2:]))
                out.append(f"<li>{content}</li>")
            else:
                if in_ul:
                    out.append("</ul>")
                    in_ul = False
                if line.strip():
                    out.append(f'<p style="margin:4px 0;">{_html.escape(line)}</p>')

    if in_table:
        out.append("</table>")
    if in_ul:
        out.append("</ul>")

    return "".join(out)
```

Move this to `reporters/base.py` (see IN-01/IN-02) so it is not duplicated.

---

## Warnings

### WR-01: Double ALERTE in weekly PEA section when Claude omits the keyword

**File:** `reporters/weekly.py:122-134`

**Issue:** When `eligibility_changed=True`, `_pea_wrap` always prepends the `alert` string to the section output (`alert = "ALERTE — changement d'éligibilité PEA détecté.\n\n"`). It then applies a secondary guard: if Claude's body does not contain `"alerte"` or `"changement"`, it prepends `"ALERTE — changement d'éligibilité PEA détecté. "` to `body` as well. When the secondary guard fires, the final section body is:

```
ALERTE — changement d'éligibilité PEA détecté.
[table]

ALERTE — changement d'éligibilité PEA détecté. [Claude narrative]
```

This produces the `ALERTE` banner twice, making the report look like a formatting error.

Note: `reporters/daily.py` avoids this because the `alert` string is injected only into the Claude prompt (not the output), so only the secondary guard writes to the rendered section body. `reporters/monthly.py` also avoids it because `_pea_monthly` prepends `alert` to the section output but has no secondary guard that modifies `body`.

**Fix:** In `_pea_wrap`, drop the secondary guard that prepends to `body` since `alert` is already prepended to the section output. If Claude must always include the keyword, enforce it via the prompt:

```python
# reporters/weekly.py _pea_wrap — remove the secondary guard entirely:
# The alert variable is already prepended before the table, so ALERTE always appears.

# REMOVE these lines (127-133):
# if (
#     pea.get("eligibility_changed")
#     and "alerte" not in body.lower()
#     and "changement" not in body.lower()
# ):
#     body = "ALERTE — changement d'éligibilité PEA détecté. " + body
```

Alternatively, keep the secondary guard but remove the `alert` prefix variable so only one path fires.

---

### WR-02: `logger.error(err_msg, exc_info=True)` in main pipeline error handler

**File:** `main.py:244`

**Issue:** The outer error handler in `main()` logs the full traceback via `exc_info=True`:

```python
err_msg = f"Pipeline error mode={mode}: {exc}"
logger.error(err_msg, exc_info=True)
```

`err_msg` itself uses `str(exc)`, which is generally safe for `smtplib` exceptions (they include server response codes, not the password). However, `exc_info=True` appends the full Python traceback to the log record. Some third-party libraries embed connection parameters or credential-related data in their exception chains or `__context__`. If this ever fires for an SMTP authentication failure from a library that embeds auth headers in its exception, the traceback could expose credentials in the log file.

This is a defense-in-depth concern. CLAUDE.md constraint: "Zéro credential hardcodé — tout via .env" and the threat model T-05-01 states "log uniquement report_type + str(exc), jamais smtp_password ou api_key". The `exc_info=True` is inconsistent with T-05-01.

**Fix:** Remove `exc_info=True` from the outer pipeline error handler. Retain it for the SQLite init failure (line 175) where no credentials are in scope:

```python
# main.py line 244 — remove exc_info=True:
logger.error(err_msg)  # T-05-01: no traceback — could expose credentials via exc chain
```

---

## Info

### IN-01: `_build_chart_panel` defined identically in all three reporters

**File:** `reporters/daily.py:175`, `reporters/weekly.py:159`, `reporters/monthly.py:186`

**Issue:** The 57-line `_build_chart_panel` function is copy-pasted verbatim across all three reporter modules. Any fix to chart rendering (e.g., CR-01 above) must be applied in three places.

**Fix:** Move to `reporters/base.py` and import from there:
```python
# reporters/base.py — add:
def build_chart_panel(data: dict, date_str: str) -> str: ...

# reporters/daily.py, weekly.py, monthly.py — replace local def with:
from reporters.base import build_chart_panel
```

---

### IN-02: `_sections_to_html` defined identically in all three reporters

**File:** `reporters/daily.py:234`, `reporters/weekly.py:218`, `reporters/monthly.py:245`

**Issue:** Same copy-paste duplication as IN-01. Any change to section card rendering must be applied in three places.

**Fix:** Move to `reporters/base.py` alongside `html_section()` and import from there.

---

### IN-03: `_table()` defined identically in both monthly and weekly reporters

**File:** `reporters/monthly.py:45-52`, `reporters/weekly.py:43-50`

**Issue:** The 8-line Markdown table builder function is duplicated between the two reporters that use it.

**Fix:** Move to `reporters/base.py` and export it.

---

### IN-04: `is_last_day_of_month` defined in both `reporters/dispatch.py` and `scheduler/utils.py`

**File:** `reporters/dispatch.py:38-49`, `scheduler/utils.py:11-22`

**Issue:** Identical function defined in two modules. `main.py` imports from `scheduler.utils`; `reporters/dispatch.py` defines its own copy. If the calendar logic ever needs a fix (e.g., timezone awareness), one copy could be updated while the other is missed.

**Fix:** Remove the duplicate from `reporters/dispatch.py` and import from `scheduler.utils`:
```python
# reporters/dispatch.py — replace local definition with:
from scheduler.utils import is_last_day_of_month
```

---

### IN-05: `import locale` inside the report-dispatch loop

**File:** `main.py:219`

**Issue:** `import locale` is placed inside the `for report_type, report_text in reports.items():` loop. Python caches module imports so this is not a repeated load, but it is idiomatic to place imports at the top of the module. Additionally, `locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")` modifies a global C-library setting; if a future refactor introduces threading (e.g., via APScheduler thread pools), concurrent reports could corrupt each other's locale state.

**Fix:**
```python
# main.py — move to top-level imports:
import locale

# In the loop, document the global-state risk:
if report_type == "monthly":
    try:
        locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")  # global — not thread-safe
    except locale.Error:
        pass
    month_fr = today.strftime("%B")
    year_str = str(today.year)
```

---

### IN-06: Tests 1-4 in `test_dispatch.py` mock report builders to return plain strings

**File:** `tests/test_dispatch.py:119-121`, `144-150`, `175-183`, `205-222`

**Issue:** Tests 1-4 patch `build_daily_report`, `build_weekly_report`, and `build_monthly_report` to return plain strings (`"DAILY_OUTPUT"`, etc.) and assert `result == {"daily": "DAILY_OUTPUT"}`. Because `_safe_build` returns whatever the builder returns without type-forcing, these tests pass — but they do not verify the actual type contract. If a builder were accidentally changed to return a plain string, these tests would still pass while the production `main.py` loop (`report_text.plain_text`, `report_text.html_body`) would raise `AttributeError`.

**Fix:** Use `ReportOutput` objects in the mock returns, consistent with the newer tests (Tests 6-9 in the same file):
```python
from reporters.base import ReportOutput
_ro = ReportOutput(html_body="<p>html</p>", plain_text="text")
with patch("reporters.dispatch.build_daily_report", return_value=_ro):
    result = select_reports(today, empty_data, tmp_config)
assert result["daily"] is _ro
```

---

_Reviewed: 2026-05-15T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
