---
phase: 07-template-redesign-integration
plan: 03
subsystem: reporters
tags: [reporters, daily, weekly, monthly, ReportOutput, chart-panel, tdd, dark-mode]
completed: "2026-05-15"
duration: ~20 min

dependency_graph:
  requires:
    - reporters/base.py::ReportOutput (07-01)
    - reporters/base.py::html_section() (07-01)
    - reporters/base.py::ETF_FALLBACK/CRYPTO_FALLBACK/GAUGE_FALLBACK/PEA_FALLBACK (07-01)
    - charts/__init__.py::generate_etf_chart, generate_crypto_sparklines, generate_fear_greed_gauge, generate_pea_table (Phase 6)
  provides:
    - reporters/daily.py::build_daily_report() -> ReportOutput
    - reporters/weekly.py::build_weekly_report() -> ReportOutput
    - reporters/monthly.py::build_monthly_report() -> ReportOutput
  affects:
    - reporters/dispatch.py (Wave 3 — _safe_build() must handle ReportOutput)
    - main.py (Wave 3 — pipeline loop must unpack ReportOutput fields)

tech_stack:
  added:
    - html (stdlib) imported as _html in weekly.py and monthly.py (section body escaping)
  patterns:
    - TDD RED/GREEN — failing tests committed before implementation (Task 2)
    - ReportOutput dual-output — html_body + plain_text separation (D-02)
    - _build_chart_panel() — 2x2 HTML table with per-cell try/except + fallback strings (CHART-05 / D-15)
    - _sections_to_html() — Markdown section list converted to html_section() dark-mode cards
    - html.escape() — section body_md escaped before insertion into p tag (T-07-09 mitigation)
    - Graceful degradation — outer try/except returns ReportOutput fallback, never raises

key_files:
  created:
    - .planning/phases/07-template-redesign-integration/07-03-SUMMARY.md
    - tests/test_reporters_weekly.py (12 new Phase 7 tests)
    - tests/test_reporters_monthly.py (12 new Phase 7 tests)
  modified:
    - reporters/daily.py (previously updated in 417306c — ReportOutput + _build_chart_panel + _sections_to_html)
    - reporters/weekly.py (build_weekly_report -> ReportOutput, _build_chart_panel, _sections_to_html added)
    - reporters/monthly.py (build_monthly_report -> ReportOutput, _build_chart_panel, _sections_to_html added)
    - tests/test_weekly.py (updated to access result.plain_text instead of raw str)
    - tests/test_monthly.py (updated to access result.plain_text instead of raw str)

decisions:
  - _build_chart_panel() is duplicated across all three reporters (copy verbatim from daily.py) rather than importing from a shared module — avoids introducing a new import chain and keeps each reporter self-contained per plan spec
  - _sections_to_html() also duplicated across reporters for same reason (plan-specified pattern)
  - html.escape() applied to body_md before wrapping in p tag (T-07-09 mitigate: section text is not user-controlled, but escaping prevents accidental Markdown content like <> from breaking the HTML)
  - Old tests (test_weekly.py, test_monthly.py) updated to access .plain_text — Rule 1 (Bug Fix) since they were broken by the return type change

metrics:
  completed: "2026-05-15"
  task_count: 2
  file_count: 7
---

# Phase 7 Plan 03: Reporter ReportOutput Integration Summary

All three reporter build functions updated to return `ReportOutput(html_body, plain_text)` — each assembles a 2×2 chart panel + dark-mode `html_section()` cards into `html_body` while preserving the Markdown `"\n".join(sections)` as `plain_text`. TDD RED/GREEN cycle applied for Task 2 (weekly + monthly).

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| Task 1 (daily.py) | reporters/daily.py — ReportOutput + _build_chart_panel + _sections_to_html | 417306c | PASS |
| Task 2 RED | Failing tests for weekly and monthly ReportOutput (24 new tests) | 5478b22 | PASS |
| Task 2 GREEN | reporters/weekly.py + reporters/monthly.py — ReportOutput pattern applied | 464a455 | PASS |

## What Was Built

### reporters/daily.py (committed in 417306c)

- **`_build_chart_panel(data, date_str) -> str`** — 2×2 HTML table calling all 4 chart generators. Per-cell `try/except` catches exceptions; `None` return substituted with `ETF_FALLBACK` / `CRYPTO_FALLBACK` / `GAUGE_FALLBACK` / `PEA_FALLBACK` exact strings.
- **`_sections_to_html(sections) -> str`** — Converts each Markdown section string (`## Title\n\nbody`) into an `html_section()` dark-mode `<div>` card. Body Markdown text is `html.escape()`-d before being wrapped in a `<p>` tag.
- **`build_daily_report()` return type** — Changed from `-> str` to `-> ReportOutput`. `plain_text = "\n".join(sections)` (unchanged Markdown). `html_body = chart_panel + _sections_to_html(sections)`. Except block returns `ReportOutput(fallback_html, fallback_plain)`.

### reporters/weekly.py (committed in 464a455)

Identical structural pattern applied:
- `_build_chart_panel()` — exact copy from daily.py
- `_sections_to_html()` — exact copy from daily.py
- `build_weekly_report()` → `ReportOutput` with 7 section degradation fallback titles
- `import html as _html` added, existing `ReportOutput` / `html_section` / chart imports already in place (from 417306c partial update)
- Duplicate `logger = get_logger(__name__)` line cleaned up

### reporters/monthly.py (committed in 464a455)

Identical structural pattern applied:
- Full import block added: `import html as _html`, `ReportOutput`, `html_section`, 4 fallback constants, all 4 chart generators
- `_build_chart_panel()` and `_sections_to_html()` added
- `build_monthly_report()` → `ReportOutput` with 7 monthly section degradation fallback titles
- `max_tokens=600` preserved in `_month_in_review()` (line 52) and `_forward_look()` (line 170)

### Test updates (committed in 464a455)

- `tests/test_weekly.py` and `tests/test_monthly.py` updated to access `result.plain_text` instead of treating the return value as a bare string. This is required since `build_weekly_report` and `build_monthly_report` now return `ReportOutput` — the string-method calls (`splitlines()`, `split()`, `find()`, `lower()`, `in`) apply to `.plain_text`.

## Verification Results

```
python3 -m pytest tests/test_reporters_daily.py tests/test_reporters_weekly.py tests/test_reporters_monthly.py tests/test_daily.py tests/test_weekly.py tests/test_monthly.py -q
59 passed in 4.58s

All three reporters return ReportOutput with non-empty html_body and plain_text:
  daily:   OK — html_body len=3200, plain_text len=479
  weekly:  OK — html_body len=3626, plain_text len=573
  monthly: OK — html_body len=3651, plain_text len=594

max_tokens=600 preserved in reporters/monthly.py: 2 occurrences (PASS)
```

## Security — Threat Mitigations Applied

| Threat | Mitigation | Status |
|--------|------------|--------|
| T-07-09: Injection via section body_html | `html.escape()` applied to body_md before wrapping in `<p>` in `_sections_to_html()` | MITIGATED |
| T-07-10: Chart generator raises Exception | Each chart call in `_build_chart_panel()` individually wrapped in `try/except`; outer `try/except` in `build_*_report()` returns degraded ReportOutput | MITIGATED |
| T-07-11: Credential logging | `logger.error("build_*_report failed: %s", e)` logs only `str(e)` — never config, api_key | MITIGATED |
| T-07-08: PEA table HTML inserted directly | `generate_pea_table()` is Phase 6 reporter code (not user input); accepted per plan threat model | ACCEPTED |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_weekly.py and test_monthly.py to access .plain_text**
- **Found during:** Task 2 verification
- **Issue:** Pre-existing tests in `test_weekly.py` and `test_monthly.py` called `report.splitlines()`, `report.split()`, `report.find()` directly on the return value. After changing `build_weekly_report` and `build_monthly_report` to return `ReportOutput`, these calls raised `AttributeError: 'ReportOutput' object has no attribute 'splitlines'`.
- **Fix:** Updated all test functions to assign `report = result.plain_text` after calling the builder, preserving all existing assertion logic.
- **Files modified:** tests/test_weekly.py, tests/test_monthly.py
- **Commit:** 464a455

**2. [Rule 1 - Bug] Removed duplicate `logger = get_logger(__name__)` in weekly.py**
- **Found during:** Task 2 implementation (reading the file)
- **Issue:** The 417306c commit had introduced a duplicate `logger = get_logger(__name__)` line (lines 35 and 37) when adding the chart imports.
- **Fix:** Removed the duplicate line.
- **Files modified:** reporters/weekly.py
- **Commit:** 464a455

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test commit — weekly + monthly) | 5478b22 | PRESENT |
| GREEN (feat commit — weekly + monthly) | 464a455 | PRESENT |
| REFACTOR | N/A — no cleanup needed | N/A |

Note: Task 1 (daily.py) was pre-committed (417306c) without a separate RED gate commit — the `test_reporters_daily.py` was included in the same feat commit. This is a TDD gate compliance gap for Task 1, documented here for tracking.

## Known Stubs

None — all three reporters wire actual chart generators. Chart `None` returns are handled by exact fallback strings from the Phase 6 UI-SPEC Copywriting Contract (not placeholder text).

## Threat Flags

No new threat surface introduced beyond the plan's threat model. All identified T-07-xx threats from the plan's `<threat_model>` are addressed above.

## Self-Check

Files exist:
- reporters/daily.py: FOUND
- reporters/weekly.py: FOUND
- reporters/monthly.py: FOUND
- tests/test_reporters_weekly.py: FOUND
- tests/test_reporters_monthly.py: FOUND

Commits exist:
- 417306c: FOUND (daily.py feat)
- 5478b22: FOUND (RED gate)
- 464a455: FOUND (GREEN gate)
