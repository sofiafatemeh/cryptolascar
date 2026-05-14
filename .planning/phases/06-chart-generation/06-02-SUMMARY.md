---
phase: 06-chart-generation
plan: 02
subsystem: ui
tags: [matplotlib, charts, base64, etf, crypto, sparklines]

requires:
  - phase: 06-01
    provides: charts/ package with Agg backend and public API surface

provides:
  - generate_etf_chart() — side-by-side 1d/1w ETF bar chart as base64 PNG
  - generate_crypto_sparklines() — BTC/ETH 7-day dual-axis sparklines as base64 PNG

affects: [06-03, 06-04, reporters/daily.py]

tech-stack:
  added: []
  patterns: [base64-PNG encoding pattern, dark-theme color constants, graceful degradation with plt.close("all")]

key-files:
  created:
    - charts/etf.py
    - charts/crypto.py
    - tests/test_charts_etf.py
    - tests/test_charts_crypto.py
  modified:
    - charts/__init__.py

key-decisions:
  - "TDD RED → GREEN: test files committed before implementation for each chart function"
  - "Dual-axis (twinx) for crypto sparklines — BTC and ETH have incompatible price scales"
  - "matplotlib.use('Agg') inherited from charts/__init__.py — no re-import needed"

patterns-established:
  - "Base64 PNG pattern: BytesIO → fig.savefig → b64encode().decode('utf-8') → plt.close(fig)"
  - "Graceful degradation: except Exception → logger.error() → plt.close('all') → return None"
  - "Color constants as module-level ALL_CAPS vars verbatim from UI-SPEC.md"

requirements-completed: [CHART-01, CHART-02]

duration: 8min
completed: 2026-05-13
---

# Plan 06-02: ETF Bar Chart + Crypto Sparklines

**ETF side-by-side performance bar chart and BTC/ETH dual-axis 7-day sparklines as base64 PNG — both with full dark-mode UI-SPEC color contract and None-on-error fallback**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-05-13
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- `generate_etf_chart(etf_data, date_str)` — renders positive/negative 1d and 1w bars in branded colors (#00C851/#FF4444) at alpha 1.0/0.65 with legend "1j"/"1sem"
- `generate_crypto_sparklines(btc_history, eth_history)` — dual-axis area sparklines for BTC (#FF6B35) and ETH (#00C851) with 0.08 fill alpha
- Both functions return None (never raise) on empty, None, or malformed input

## Task Commits

1. **Task 1: RED test for ETF chart** — `0a3f106` (test)
2. **Task 2: RED test for crypto sparklines** — `6ce68c0` (test)
3. **Task 3: Implement both chart generators** — `b4039f4` (feat)

## Files Created/Modified

- `charts/etf.py` — generate_etf_chart(), figsize=(8,4), UI-SPEC color contract
- `charts/crypto.py` — generate_crypto_sparklines(), figsize=(8,3), dual twinx axes
- `charts/__init__.py` — public exports updated
- `tests/test_charts_etf.py` — TDD tests for ETF chart (RED phase)
- `tests/test_charts_crypto.py` — TDD tests for crypto sparklines (RED phase)

## Decisions Made

- Dual-axis (twinx) for crypto sparklines — BTC and ETH have incompatible price scales; a shared y-axis would compress one curve visually
- Explicit `float(v)` cast on all input values before plotting — catches None/str gracefully

## Deviations from Plan

None — plan executed exactly as specified in 06-02-PLAN.md.

## Issues Encountered

None.

## Next Phase Readiness

- ETF and crypto chart functions importable from `charts` package
- Wave 2 parallel plan 06-03 (gauge + PEA table) can proceed independently
- Wave 3 plan 06-04 (tests) unblocked once both Wave 2 plans complete

---
*Phase: 06-chart-generation*
*Completed: 2026-05-13*
