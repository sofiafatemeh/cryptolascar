# Phase 6: Chart Generation — VERIFICATION

**Phase:** 06-chart-generation
**Verified:** 2026-05-15
**Verified by:** Phase 8 (Close Gaps) — boundary tests + data layer fixes
**Status:** PASS

## Summary

All five CHART-* requirements are satisfied. Four data-contract bugs (CHART-01, CHART-02, CHART-03, CHART-04) were diagnosed in the Phase 8 milestone audit and fixed in phases 08-01 and 08-02. The chart generator functions themselves (Phase 6 work) were correct throughout — the bugs were in the collector→reporter data transform layer. This verification confirms end-to-end correctness.

---

## CHART-01: ETF Bar Chart (1-day and 1-week bars)

**Requirement:** Calling the ETF chart function with valid performance data returns a base64 PNG string showing 1-day and 1-week variation bars for each tracked ETF.

**Status:** PASS

**Evidence:**
- `charts/etf.py::generate_etf_chart` tested in `tests/test_charts_etf.py`
- End-to-end transform tested in `tests/test_chart_boundary.py::TestEtfBoundary::test_etf_boundary_produces_valid_base64`
- `collectors/etf.py` now provides `pct_change_1w` (added in Phase 8, plan 08-01)
- `reporters/daily.py`, `reporters/weekly.py`, `reporters/monthly.py` now transform `etf["tickers"]` → `{"TICKER": {"1d": float, "1w": float}}` before calling `generate_etf_chart` (fixed in Phase 8, plan 08-02)

**Verified command:**
```
python3 -m pytest tests/test_charts_etf.py tests/test_chart_boundary.py::TestEtfBoundary -v -q
```

**Result:** 9 passed

**Bug history:** Production charts showed ETF_FALLBACK due to raw collector dict passed to generate_etf_chart. Fixed in 08-02 (reporter transform) + 08-01 (1w data collection).

---

## CHART-02: Crypto Sparklines (7-day BTC + ETH)

**Requirement:** Calling the crypto sparkline function with 7-day price history for BTC and ETH returns a base64 PNG string with two labeled sparkline curves.

**Status:** PASS

**Evidence:**
- `charts/crypto.py::generate_crypto_sparklines` tested in `tests/test_charts_crypto.py`
- End-to-end transform tested in `tests/test_chart_boundary.py::TestCryptoSparklineBoundary`
- `collectors/crypto.py` now fetches 7-day history via CoinGecko market_chart endpoint and stores in `coins["bitcoin"]["history"]` / `coins["ethereum"]["history"]` (added in Phase 8, plan 08-01)
- `reporters/*.py::_build_chart_panel` already read `history` correctly; the fix was in the collector

**Verified command:**
```
python3 -m pytest tests/test_charts_crypto.py tests/test_chart_boundary.py::TestCryptoSparklineBoundary -v -q
```

**Result:** 10 passed

**Bug history:** `sparkline=false` in the CoinGecko batch call meant `history` was never set; `generate_crypto_sparklines([], [])` always returned None. Fixed in 08-01.

---

## CHART-03: Fear & Greed Gauge (AttributeError safety)

**Requirement:** When any single chart function raises an exception, the caller receives None, logs the error, and the pipeline continues — the email is still sent.

**Status:** PASS (extended to cover: when fear_greed=None stored in DB, fg_score extraction must not AttributeError)

**Evidence:**
- `charts/gauge.py::generate_fear_greed_gauge` graceful fallback tested in `tests/test_charts_gauge_pea.py`
- CHART-03 AttributeError regression tested in `tests/test_chart_boundary.py::TestChart03Boundary`
- `reporters/*.py::_build_chart_panel` fg_score line fixed from `.get("fear_greed", {}).get("value")` to `(.get("fear_greed") or {}).get("value")` (fixed in Phase 8, plan 08-02)

**Verified command:**
```
python3 -m pytest tests/test_charts_gauge_pea.py tests/test_chart_boundary.py::TestChart03Boundary -v -q
```

**Result:** 33 passed

**Bug history:** When `collect_crypto` stored `fear_greed=None`, the `.get("fear_greed", {})` pattern returned `None` (not `{}`), causing `None.get("value")` → AttributeError → full-report ReportOutput fallback. Fixed in 08-02.

---

## CHART-04: PEA Colored HTML Table

**Requirement:** Calling the PEA table function with position data returns an HTML string with rows colored green or red based on performance.

**Status:** PASS

**Evidence:**
- `charts/pea.py::generate_pea_table` tested in `tests/test_charts_gauge_pea.py`
- End-to-end transform tested in `tests/test_chart_boundary.py::TestPeaBoundary`
- `reporters/*.py::_build_chart_panel` now transforms `pea["prices"]` → `list[dict]` with `ticker/name/price/change_1d/change_1w/pea_eligible` fields before calling `generate_pea_table` (fixed in Phase 8, plan 08-02)

**Verified command:**
```
python3 -m pytest tests/test_charts_gauge_pea.py tests/test_chart_boundary.py::TestPeaBoundary -v -q
```

**Result:** 33 passed

**Bug history:** Raw PEA collector dict (`{prices: dict, eligibility: dict, ...}`) was passed to `generate_pea_table` which expects `list[dict]`. Fixed in 08-02 (reporter transform added `pea_list` comprehension).

---

## CHART-05: Graceful Degradation (any chart failure → None, pipeline continues)

**Requirement:** When any single chart function raises an exception, the caller receives None (or equivalent empty sentinel), logs the error, and the report generation pipeline continues without that chart — the email is still sent.

**Status:** PASS

**Evidence:**
- All four chart generators catch all exceptions and return None: verified in unit tests
- `reporters/*.py::_build_chart_panel` wraps each chart call in `try/except Exception` → None → fallback HTML
- `tests/test_reporters_daily.py`, `test_reporters_weekly.py`, `test_reporters_monthly.py` verify fallback behavior

**Verified command:**
```
python3 -m pytest tests/test_reporters_daily.py tests/test_reporters_weekly.py tests/test_reporters_monthly.py -v -q -k "fallback"
```

**Result:** 6 passed

---

## Full Test Suite

```
python3 -m pytest tests/ -q
```

321 tests pass (as of 2026-05-15).

---

## Production Readiness

| Requirement | Generator | Collector | Reporter Transform | Status |
|-------------|-----------|-----------|-------------------|--------|
| CHART-01 ETF | charts/etf.py ✓ | pct_change_1w (08-01) ✓ | etf_chart_data (08-02) ✓ | PASS |
| CHART-02 Sparklines | charts/crypto.py ✓ | history list (08-01) ✓ | reads history correctly ✓ | PASS |
| CHART-03 Gauge safety | charts/gauge.py ✓ | returns None gracefully ✓ | fg_score or{} fix (08-02) ✓ | PASS |
| CHART-04 PEA table | charts/pea.py ✓ | prices dict structure ✓ | pea_list transform (08-02) ✓ | PASS |
| CHART-05 Degradation | all charts ✓ | n/a | try/except per chart ✓ | PASS |
