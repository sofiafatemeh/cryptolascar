---
phase: 08-close-gaps
fixed_at: 2026-05-15T00:00:00Z
review_path: .planning/phases/08-close-gaps/08-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 08: Code Review Fix Report

**Fixed at:** 2026-05-15T00:00:00Z
**Source review:** .planning/phases/08-close-gaps/08-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (2 Critical, 4 Warning)
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: `collect_crypto` violates its "never raises" contract — `fg_data` may be unbound and exceptions propagate

**Files modified:** `collectors/crypto.py`
**Commit:** 10010d9
**Applied fix:** Added `fg_data = None` initialization before the outer `try` block so the return statement is always safe. Added `except Exception as e` clause before the existing `finally` to catch any unexpected error, log it, set `cg_failed = True` and `fg_failed = True`, and allow `finally: conn.close()` to run cleanly. This enforces the documented "Ne lève jamais d'exception" contract.

---

### CR-02: No HTTP status validation — non-2xx responses silently parsed as valid data

**Files modified:** `collectors/crypto.py`, `collectors/etf.py`
**Commit:** e9e6b91
**Applied fix:** Added `resp.raise_for_status()` before every `resp.json()` call for all `httpx.get(...)` calls in both files: `_fetch_fear_greed`, `_fetch_sparkline`, the batch fetch inside `collect_crypto`, and `_fetch_alpha_vantage` in `etf.py`. Existing `except Exception` blocks catch the `httpx.HTTPStatusError` and degrade gracefully with a properly labelled error message.

---

### WR-01: `or 0.0` pattern silences exact-zero percentage change

**Files modified:** `reporters/daily.py`, `reporters/weekly.py`, `reporters/monthly.py`
**Commit:** b40ffff
**Applied fix:** Replaced `t.get("pct_change") or 0.0` and `t.get("pct_change_1w") or 0.0` with explicit `is not None` ternary expressions in all three `_build_chart_panel` functions. The new form correctly handles `0.0` as a valid flat-market value rather than treating it as falsy.

---

### WR-02: `_fetch_1w_pct` not called on cache-hit path — stale cache silently drops `pct_change_1w`

**Files modified:** `collectors/etf.py`, `tests/test_etf.py`
**Commits:** 0796cb2, 2117e18
**Applied fix:** Changed the cache-hit guard from `if cached:` to `if cached and "pct_change_1w" in cached:` so old cache entries written before `pct_change_1w` was introduced are treated as cache misses and re-fetched with the complete schema. Also updated `test_cache_hit_skips_yfinance` to include `pct_change_1w` in its fixture data so it correctly represents a valid current-schema cache entry.

---

### WR-03: `_fetch_sparkline` sleeps before caching — incorrect order

**Files modified:** `collectors/crypto.py`
**Commit:** eef4ee6
**Applied fix:** Swapped the order of `_upsert_cache(...)` and `time.sleep(CG_SLEEP_SECONDS)` in `_fetch_sparkline` so caching always happens before the rate-limit sleep. Order is now: fetch → raise_for_status → parse → cache → log → sleep → return.

---

### WR-04: Test module docstring/comment describes opposite behavior for Test 9

**Files modified:** `tests/test_crypto.py`
**Commit:** fba257c
**Applied fix:** Updated module-level docstring line 16 from "sparkline skip when coins came from cache (no extra call for cached data)" to "sparkline fetched even when coins come from cache (sparkline has its own cache)". Updated section comment line 391 from "sparkline skipped when coins come from cache" to "sparkline fetched when coins from cache but sparkline cache is empty". Test function name and assertions were already correct; only the descriptions were wrong.

---

## Test Results

All 321 tests pass after fixes.

```
321 passed in 33.08s
```

---

_Fixed: 2026-05-15T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
