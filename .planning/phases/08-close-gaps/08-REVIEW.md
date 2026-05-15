---
phase: 08-close-gaps
reviewed: 2026-05-15T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - collectors/etf.py
  - collectors/crypto.py
  - reporters/daily.py
  - reporters/weekly.py
  - reporters/monthly.py
  - tests/test_etf.py
  - tests/test_crypto.py
  - tests/test_reporters_daily.py
  - tests/test_reporters_weekly.py
  - tests/test_reporters_monthly.py
  - tests/test_chart_boundary.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-05-15T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Eleven source files were reviewed covering the two new collectors (ETF `pct_change_1w`, crypto sparklines), three reporter `_build_chart_panel` transform fixes, and the associated test suites. The graceful-degradation contract ("Ne lève jamais") is the dominant concern: `collect_crypto` can propagate unexpected exceptions due to a missing outer `except` clause and an uninitialized `fg_data` variable, directly contradicting its documented guarantee. The `collect_etf` outer guard is correctly written; the problem is isolated to `collect_crypto`. A secondary critical issue is HTTP 4xx/5xx responses being silently treated as success in both collectors. Four warnings cover a falsy-coercion data-silencing edge case, a missing HTTP response validation, and test-description mismatches that will mislead maintainers.

---

## Critical Issues

### CR-01: `collect_crypto` violates its "never raises" contract — `fg_data` may be unbound and exceptions propagate

**File:** `collectors/crypto.py:173-239`

**Issue:** The outer `try` block (line 178) has only a `finally` clause — no `except`. If any unhandled exception escapes the block (e.g., `json.JSONDecodeError` from a corrupt cache row in `_get_cached` called by `_all_coins_cached`, or a database error from `_upsert_cache`), Python runs `finally` (closing the connection) and then re-raises. The `return` statement at line 232 that references `fg_data` is never reached; instead the exception propagates to the caller.

Critically, `fg_data` is only ever assigned on line 227 — inside the `try` block, after all coin-fetching logic. If the `try` block raises before line 227, `fg_data` is never bound. The `return` at line 232 would cause `UnboundLocalError` if Python somehow reached it (it would not, but the invariant is broken). The real effect is that `collect_crypto` raises in the caller, violating the documented "Ne lève jamais d'exception" contract and breaking graceful degradation.

Compare with `collect_etf`, which wraps the entire loop in `try...except Exception` (line 242) and never uses an uninitialized variable in the return dict.

**Fix:**
```python
# Initialize fg_data before the try block so the return is always safe
conn = get_connection(config.db_path)
coins_data: dict[str, Any] = {}
cg_failed = False
fg_failed = False
fg_data = None  # ADD THIS — ensures fg_data is always bound

try:
    ...
    fg_data = _fetch_fear_greed(conn)
    if fg_data is None:
        fg_failed = True
except Exception as e:                         # ADD outer except
    logger.error("Unexpected error in collect_crypto: %s", e)
    cg_failed = True
    fg_failed = True
finally:
    conn.close()
return {
    "coins": coins_data,
    "fear_greed": fg_data,
    ...
}
```

---

### CR-02: No HTTP status validation — non-2xx responses silently parsed as valid data

**File:** `collectors/crypto.py:196-197`, `collectors/etf.py:145-150`

**Issue:** Both collectors call `httpx.get(...)` and immediately call `.json()` on the response without checking `resp.status_code`. A rate-limit response (HTTP 429), a server error (HTTP 500), or an authentication failure (HTTP 401/403) from CoinGecko or Alpha Vantage will return a response body that is not the expected data format. `resp.json()` will succeed (the body is valid JSON), but downstream parsing (`item["current_price"]`, `gq.get("05. price")`) will either produce `None` values silently or raise a `KeyError`/`TypeError` that gets caught by the broad `except Exception` handler — masking the real cause.

Specifically in `crypto.py` line 197: `items = resp.json()` — a 429 response from CoinGecko returns `{"status": {"error_code": 429, "error_message": "..."}}`, not a list, so `for item in items:` will iterate over string keys `"status"`, causing `item["id"]` to raise `KeyError`. This falls into the `except Exception` handler and sets `cg_failed = True` — the degradation does occur, but the root cause is hidden and there is no rate-limit-aware backoff triggered.

In `etf.py` line 150: `data = resp.json()` for Alpha Vantage — the existing check for `"Note"` and `"Information"` keys handles the quota-exceeded case, but HTTP errors (5xx) return different error shapes.

**Fix:**
```python
# In both collectors, add status check before .json():
resp = httpx.get(url, params=params, timeout=15)
resp.raise_for_status()   # raises httpx.HTTPStatusError for 4xx/5xx
data = resp.json()
```
The existing `except Exception` blocks will catch `httpx.HTTPStatusError` and degrade gracefully. This also ensures the error message logged reflects "HTTP 429" rather than a confusing `KeyError`.

---

## Warnings

### WR-01: `or 0.0` pattern silences exact-zero percentage change with a valid alternative meaning

**File:** `reporters/daily.py:201-202`, `reporters/weekly.py:185-186`, `reporters/monthly.py:212-213`

**Issue:** The ETF chart transform uses `t.get("pct_change") or 0.0` and `t.get("pct_change_1w") or 0.0`. In Python, `0.0 or 0.0` evaluates to `0.0` (the second operand), so the end result is numerically identical. However, the intent of `or 0.0` is to replace `None` with `0.0`. Using this pattern also means that if `pct_change` were `0.0` (a legitimate "flat market" value), Python evaluates `0.0` as falsy and the expression short-circuits to `0.0` — coincidentally correct here, but only because both sides are `0.0`.

The issue is code clarity and hidden coupling: the filter one line above (`if t.get("pct_change") is not None`) correctly uses `is not None`, meaning `pct_change = 0.0` will pass the filter. Then `0.0 or 0.0` produces `0.0` — correct by coincidence, not by logic. Any future reader who changes the default from `0.0` to another sentinel value (e.g., `float("nan")`) will silently corrupt data for flat-market days.

The same pattern appears identically in all three reporter modules (daily line 201-202, weekly lines 185-186, monthly lines 212-213).

**Fix:**
```python
# Replace:
"1d": t.get("pct_change") or 0.0,
"1w": t.get("pct_change_1w") or 0.0,

# With explicit None-check:
"1d": t.get("pct_change") if t.get("pct_change") is not None else 0.0,
"1w": t.get("pct_change_1w") if t.get("pct_change_1w") is not None else 0.0,
# Or more concisely using the walrus operator or a helper:
"1d": (v := t.get("pct_change")) if v is not None else 0.0,
```

---

### WR-02: `_fetch_1w_pct` not called on cache-hit path — stale cache silently drops `pct_change_1w`

**File:** `collectors/etf.py:203-208`

**Issue:** When a cache hit is found for a ticker (lines 204-208), `tickers_data[symbol] = cached` is returned directly and `continue` skips the entire live-fetch path. `pct_change_1w` is only appended to `data` on line 213 — in the cache-miss path. This means:

1. On the first successful fetch, `pct_change_1w` is stored in the cache (verified by Test 8).
2. On the second call within the 4-hour TTL, the cached `data` is returned — which includes `pct_change_1w` from the first fetch, so it appears to work.
3. If a cache entry was written by older code (before this phase), or if the initial fetch's `_fetch_1w_pct` returned `None` and was cached as `None`, the cache will serve `pct_change_1w: None` for up to 4 hours with no recalculation attempt.

This is a latent correctness issue: old cache entries (e.g., from Phase 2 before `pct_change_1w` was added) do not contain this key at all. The cache hit returns data without `pct_change_1w`, and the reporter's `t.get("pct_change_1w")` returns `None` — silently producing a flat-line chart entry rather than real data.

**Fix:** Cache migration or a version/schema key is the correct long-term fix. As an immediate workaround, add a key-presence check in the cache hit path:
```python
cached = _get_cached(conn, CACHE_SOURCE, symbol)
if cached and "pct_change_1w" in cached:
    logger.debug("Cache hit pour %s", symbol)
    tickers_data[symbol] = cached
    continue
# else: fall through to live fetch (treats missing key as a stale cache miss)
```

---

### WR-03: `_fetch_sparkline` sleeps after writing cache — sleep fires even on cache-hit warmup

**File:** `collectors/crypto.py:147`

**Issue:** In `_fetch_sparkline`, `time.sleep(CG_SLEEP_SECONDS)` is called on line 147, after a successful API response and before writing cache. The sleep is intended to respect CoinGecko's rate limit between calls. However, the sleep only triggers on cache miss (the cache-hit path returns early on line 137). This is correct behavior.

The issue is ordering: the sleep fires *before* `_upsert_cache` writes to the database (line 148). If `_upsert_cache` raises (disk full, DB locked), the sleep has already occurred, the data is lost, and the next call will refetch. More critically, if an exception is raised during the sleep itself (e.g., `KeyboardInterrupt`, `SystemExit`), `_upsert_cache` never runs — the rate limit was consumed but nothing was cached. The correct order is: fetch → validate → cache → sleep.

**Fix:**
```python
resp = httpx.get(url, params=params, timeout=15)
data = resp.json()
prices = [float(price) for _, price in data.get("prices", [])]
_upsert_cache(conn, SPARKLINE_SOURCE, coin_id, {"prices": prices})  # cache first
logger.info("Sparkline %s: %d points", coin_id, len(prices))
time.sleep(CG_SLEEP_SECONDS)  # sleep last, as rate-limit courtesy
return prices
```

---

### WR-04: Test module docstring/comment describes opposite behavior to the test function for Test 9

**File:** `tests/test_crypto.py:16`, `tests/test_crypto.py:391-395`

**Issue:** The module-level docstring at line 16 states:
```
Test 9 — sparkline skip when coins came from cache (no extra call for cached data)
```

The section comment at line 391 says:
```
# Test 9 — sparkline skipped when coins come from cache
```

But the actual test function is named `test_sparkline_fetch_called_even_with_cached_coins` (line 395), and its docstring and assertion at line 443 (`assert len(market_chart_calls) == 2`) assert the *opposite* — that sparkline calls ARE made even when coins are cached.

This contradiction between the comment/docstring and the actual test assertion means a reviewer reading the module-level summary will have an inverted understanding of the production behavior. The implementation behavior is: when coin batch data comes from cache but sparkline cache is empty, `_fetch_sparkline` IS called (correct per `collect_crypto` logic). The test name and body are correct; the module summary and section comment are wrong.

**Fix:** Update the module docstring line 16 and section comment line 391 to:
```python
# Module docstring:
# Test 9 — sparkline fetched even when coins come from cache (sparkline has its own cache)

# Section comment:
# Test 9 — sparkline fetched when coins from cache but sparkline cache is empty
```

---

## Info

### IN-01: `format_pct` and `format_currency` in `reporters/base.py` are not None-safe — callers rely on default values

**File:** `reporters/base.py:112-120`

**Issue:** Both `format_pct(value: float)` and `format_currency(value: float, ...)` perform arithmetic or string formatting directly on `value` without guarding against `None`. The callers in all three reporters use `t.get("pct_change", 0.0)` and `c.get("pct_change_24h", 0.0)` as default, which is safe when the key is absent. However, if the key is present with value `None` explicitly (as happens in the error-path dict returned by `collect_etf` for a failed ticker), the `get(..., 0.0)` call returns `None` — because `None` is a present value, not a missing key. This would produce `TypeError: '>=' not supported between instances of 'NoneType' and 'int'` inside `format_pct`.

The caller guard `if t.get("price") is not None` protects most paths, but in `_etf_section` (daily.py line 90), the condition is `if t.get("price") is not None and t.get("pct_change") is not None` — this is correct. The weekly/monthly table builders also guard on `price is not None` before calling `format_pct(t.get("pct_change", 0.0))`, but do not re-check whether `pct_change` itself is None.

No crash occurs today because the price-None guard on the row-building path catches the failure ticker early. However this relies on the failure-path dict always having `price=None` when `pct_change=None`. If this coupling ever breaks, `format_pct` will crash.

**Fix:** Add a None guard inside `format_pct`:
```python
def format_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"
```

---

### IN-02: `MOCK_CG_RESPONSE` in test_crypto.py covers only 2 of 8 `CRYPTO_IDS`

**File:** `tests/test_crypto.py:41-58`

**Issue:** `MOCK_CG_RESPONSE` contains entries for only `bitcoin` and `ethereum`, but `CRYPTO_IDS` has 8 coins (`binancecoin`, `solana`, `ripple`, `cardano`, `avalanche-2`, `dogecoin` are absent). Tests 2, 3, 4, 6, 7, 10 that return `MOCK_CG_RESPONSE` as the CoinGecko batch response will produce `coins_data` with only 2 entries rather than the expected 8. This means the production invariant "8 coins collected" is never tested. If the production API response is later filtered/transformed differently, the tests would still pass with 2 coins.

This does not cause the tests to fail incorrectly — they pass with 2 coins because the assertions only check `bitcoin` — but it reduces coverage fidelity. Not a crash bug, but a meaningful gap.

**Fix:** Extend `MOCK_CG_RESPONSE` to include all 8 `CRYPTO_IDS`:
```python
MOCK_CG_RESPONSE = [
    {"id": "bitcoin", "symbol": "btc", "current_price": 60000.0, ...},
    {"id": "ethereum", "symbol": "eth", "current_price": 3500.0, ...},
    {"id": "binancecoin", "symbol": "bnb", "current_price": 300.0, ...},
    # ... all 8 entries
]
```

---

### IN-03: `_build_chart_panel` is duplicated verbatim across three reporter modules

**File:** `reporters/daily.py:191-272`, `reporters/weekly.py:175-256`, `reporters/monthly.py:202-283`

**Issue:** The `_build_chart_panel` function is 81 lines of identical code copied into `daily.py`, `weekly.py`, and `monthly.py`. The `_PEA_NAMES` and `_PEA_ELIGIBILITY` dicts are also duplicated in all three modules. Any future fix or enhancement (e.g., adding a new chart cell, changing fallback HTML) must be applied in three places simultaneously. The Phase 8 CHART-03/01/04 fixes themselves were applied correctly in all three copies, but this was only verified because tests exist — a future fix that misses one copy would be hard to detect.

**Fix:** Extract `_build_chart_panel`, `_PEA_NAMES`, and `_PEA_ELIGIBILITY` to `reporters/base.py` or a new `reporters/charts_panel.py` module and import it in all three reporters. This is a refactoring task and does not require changing test coverage.

---

_Reviewed: 2026-05-15T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
