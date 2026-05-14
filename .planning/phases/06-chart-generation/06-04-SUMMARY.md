---
phase: 06-chart-generation
plan: 04
subsystem: testing
tags: [pytest, charts, unit-tests, mocking, CHART-05, fallback]

requires:
  - phase: 06-02
    provides: generate_etf_chart, generate_crypto_sparklines
  - phase: 06-03
    provides: generate_fear_greed_gauge, generate_pea_table

provides:
  - tests/test_charts.py — 36-test suite covering all 4 chart generators and CHART-05 fallback

affects: [reporters/daily.py]

tech-stack:
  added: []
  patterns: [patch.object targeting module-level plt import for correct fallback testing, parametrized gauge zone boundary tests]

key-files:
  created:
    - tests/test_charts.py
  modified: []

key-decisions:
  - "patch.object(charts_etf.plt, 'subplots', ...) targets module-level plt — not matplotlib.pyplot directly (per T-06-15)"
  - "Parametrized gauge test covers all 15 boundary values across all 5 zones"
  - "PEA fallback tested with [None] input — triggers AttributeError on None.get() inside loop"

patterns-established:
  - "CHART-05 fallback pattern: patch.object(module.plt, 'subplots', side_effect=RuntimeError) → verify None returned"

requirements-completed: [CHART-01, CHART-02, CHART-03, CHART-04, CHART-05]

duration: 5min
completed: 2026-05-14
---

# Plan 06-04: Comprehensive Chart Test Suite

**36-test pytest suite validating all 4 chart generators (happy path, None-on-error fallback, all 5 gauge zone boundaries) and top-level package imports — automated proof of CHART-05 production safety contract**

## Performance

- **Duration:** ~5 min
- **Completed:** 2026-05-14
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- `tests/test_charts.py` with 36 test functions (22 unique `def test_`) passing in 4.46s
- All 5 Fear & Greed gauge zones verified at boundary scores (0, 24, 25, 44, 45, 55, 56, 74, 75, 100, and intermediates)
- CHART-05 fallback verified for all 3 PNG-producing functions via `patch.object` + `side_effect=RuntimeError`
- PEA table row color assertions import and check module-level constants directly
- Top-level `charts` package export verified

## Task Commits

1. **Task 1: Comprehensive test suite** — `6236b65` (feat)

## Files Created/Modified

- `tests/test_charts.py` — 284 lines, 36 tests, covers CHART-01 through CHART-05

## Decisions Made

- `patch.object(charts_etf.plt, "subplots", ...)` targets the `plt` already bound in the module's namespace, not the global `matplotlib.pyplot` — this is the correct pattern for testing gracefully-degrading chart functions

## Deviations from Plan

None — plan executed exactly as specified in 06-04-PLAN.md.

## Issues Encountered

None. All 36 tests passed on first run.

## Next Phase Readiness

Phase 6 (Chart Generation) is complete. All 4 chart functions are production-ready with:
- Verified visual output (base64 PNG / HTML)
- Automated fallback guarantee (CHART-05)
- 80 total tests across 6 test files

---
*Phase: 06-chart-generation*
*Completed: 2026-05-14*
