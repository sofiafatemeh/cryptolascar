---
phase: 02-data-pipeline
fixed_at: 2026-05-10T07:15:00Z
review_path: .planning/phases/02-data-pipeline/02-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-05-10T07:15:00Z
**Source review:** .planning/phases/02-data-pipeline/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (2 Critical, 7 Warning)
- Fixed: 9
- Skipped: 0

## Fixed Issues

### CR-01: NewsAPI Key Leaked Into Logs

**Files modified:** `collectors/news.py`
**Commit:** 0438266
**Applied fix:** Replaced `resp.raise_for_status()` in `_fetch_newsapi` with a manual status check: `if resp.status_code != 200: raise ValueError(f"NewsAPI returned HTTP {resp.status_code}")`. The URL with `apiKey=` query parameter is never included in any raised exception or log message. Satisfies T-02-17.

---

### CR-02: ETF Collector Caches Fetch Failures

**Files modified:** `collectors/etf.py`
**Commit:** 7cc59f9
**Applied fix:** Moved `_upsert_cache` and `tickers_data[symbol] = data` inside the `try` block for yfinance fetch. Also moved the Alpha Vantage enrichment block inside the same `try` block (it depends on a successful yfinance result anyway). The `except` block now only handles the failure path without writing to cache, matching the pattern in `pea.py` and `macro.py`.

---

### WR-01: Double Sleep in collect_macro

**Files modified:** `collectors/macro.py`, `tests/test_macro.py`
**Commit:** fb1150e
**Applied fix:** Removed the post-fetch `time.sleep(FRED_SLEEP_SECONDS)` call (line 161). Only the pre-fetch sleep (guarded by `if not first_api_call`) remains, reducing total wait from 7s to 3s for 4 cache-miss series. Updated docstring. Added `patch("collectors.macro.time.sleep")` to Test 2 (`test_cache_miss_fetches_fred_and_writes_cache`) and Test 4 (`test_single_series_failure_sets_partial`) so they no longer block during the test run.

---

### WR-02: SQLite Connection Leak in collect_pea

**Files modified:** `collectors/pea.py`
**Commit:** 1bd7d70
**Applied fix:** Wrapped the entire function body after `conn = get_connection(...)` — including the ticker loop and `_check_eligibility` call — in a `try/finally: conn.close()` block. Connection is now guaranteed to close even if `_check_eligibility` raises.

---

### WR-03: SQLite Connection Leak in collect_crypto

**Files modified:** `collectors/crypto.py`
**Commit:** 6204c99
**Applied fix:** Wrapped the entire function body after `conn = get_connection(...)` — including `_all_coins_cached`, the CoinGecko fetch block, and `_fetch_fear_greed` — in a `try/finally: conn.close()` block.

---

### WR-04: SQLite Connection Leak in collect_macro

**Files modified:** `collectors/macro.py`
**Commit:** 29293fd
**Applied fix:** Wrapped the FRED series loop in a `try/finally: conn.close()` block. Connection is guaranteed to close even if an unexpected SQLite error escapes the inner per-series `except` block.

---

### WR-05: Two Connection Leak Paths in collect_news

**Files modified:** `collectors/news.py`
**Commit:** 28da2fe
**Applied fix (path 1):** In the cache-read `except` block, added a `try/except: conn.close()` call before setting `conn = None`. This ensures the connection is closed when `get_connection()` succeeds but `_get_cached()` raises.
**Applied fix (path 2):** In the cache-write block, moved `conn.close()` from inside the `try` (after `_upsert_cache`) into a `finally` block. Connection is now closed even when `_upsert_cache` raises.

---

### WR-06: datetime.utcnow() Deprecated

**Files modified:** `main.py`
**Commit:** 769cb88
**Applied fix:** Replaced both occurrences of `datetime.datetime.utcnow().isoformat() + "Z"` (lines 104 and 152) with `datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`. Uses `replace_all=True` since both occurrences were identical.

---

### WR-07: collect_news Cache-Hit Returns Hardcoded partial: False

**Files modified:** `collectors/news.py`
**Commit:** cccd576
**Applied fix:** Changed `"partial": False` to `"partial": len(cached) == 0` in the cache-hit return path. Added a comment documenting that `newsapi_failed` / `scrape_failed` remain `False` for cache-hit since those flags are not stored in the cache schema.

---

## Test Results

Full test suite run after all fixes: **42 passed, 0 failed** (`python3 -m pytest tests/ -x -q`)

---

_Fixed: 2026-05-10T07:15:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
