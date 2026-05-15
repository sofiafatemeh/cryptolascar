---
phase: 06-chart-generation
plan: 03
subsystem: ui
tags: [matplotlib, charts, base64, gauge, pea, html-table, fear-greed]

requires:
  - phase: 06-01
    provides: charts/ package with Agg backend and public API surface

provides:
  - generate_fear_greed_gauge() — 5-zone semicircular arc gauge as base64 PNG
  - generate_pea_table() — per-row colored HTML table for PEA positions

affects: [06-04, reporters/daily.py]

tech-stack:
  added: []
  patterns: [matplotlib Wedge patches for arc gauges, HTML string generation with inline styles, html.escape() XSS mitigation]

key-files:
  created:
    - charts/gauge.py
    - charts/pea.py
    - tests/test_charts_gauge_pea.py
  modified: []

key-decisions:
  - "TDD RED → GREEN: test file committed before implementation"
  - "Wedge patches for arc zones (not Arc or pie) — allows per-zone alpha control"
  - "Score-to-angle formula: theta = 180 - (score/100)*180 → score 0=left(180°), 100=right(0°)"
  - "PEA table is HTML string (not PNG) — embeddable directly in Jinja2 email template"
  - "html.escape() on ticker/name fields — XSS mitigation per T-06-11"

patterns-established:
  - "5-zone arc with Wedge patches: inactive alpha=0.25, active alpha=1.0"
  - "HTML table with inline styles — no CSS classes, email-client safe"
  - "Row color derived from change_1d sign: positive=#0a2e1a, negative=#2e0a0a, neutral=#111111"

requirements-completed: [CHART-03, CHART-04]

duration: 8min
completed: 2026-05-13
---

# Plan 06-03: Fear & Greed Gauge + PEA Table

**5-zone semicircular Fear & Greed gauge (white needle, 28pt score) and PEA HTML table with per-row dark background by daily performance — completing the full 4-function chart suite**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-05-13
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `generate_fear_greed_gauge(score)` — renders a semicircular arc of 5 color zones, white needle at the score angle, 28pt bold score text, zone label, and title "Fear & Greed Index"
- `generate_pea_table(pea_data)` — returns an HTML `<table>` with per-row background (#0a2e1a/#2e0a0a/#111111) and colored performance text; all string fields HTML-escaped
- Both functions return None (never raise) on invalid/empty input

## Task Commits

1. **Task 1: RED tests for gauge + PEA table** — `77b7d3f` (test)
2. **Task 2: Implement generate_fear_greed_gauge()** — `4d89243` (feat)
3. **Task 3: Implement generate_pea_table()** — `5ff98fe` (feat)

## Files Created/Modified

- `charts/gauge.py` — generate_fear_greed_gauge(), 5 Wedge zones, white needle
- `charts/pea.py` — generate_pea_table(), inline-styled HTML table with html.escape()
- `tests/test_charts_gauge_pea.py` — 44 TDD tests for gauge + PEA table

## Decisions Made

- Wedge patches chosen over Arc/pie for gauge arc — allows per-zone facecolor and alpha control independently
- Score-to-angle formula anchors 0→180° and 100→0° — natural left-to-right "bad to good" layout
- PEA table outputs HTML (not PNG) — allows responsive layout in email clients that render HTML
- `html.escape()` wraps all external string values (ticker, name) per threat T-06-11

## Deviations from Plan

None — plan executed exactly as specified in 06-03-PLAN.md.

## Issues Encountered

None.

## Next Phase Readiness

- All 4 chart functions complete and importable from `charts` package
- Wave 3 plan 06-04 (comprehensive test suite) is unblocked

---
*Phase: 06-chart-generation*
*Completed: 2026-05-13*
