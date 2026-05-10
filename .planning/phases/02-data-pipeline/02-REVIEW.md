---
phase: 02-data-pipeline
reviewed: 2026-05-10T06:20:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - collectors/etf.py
  - tests/test_etf.py
  - collectors/crypto.py
  - tests/test_crypto.py
  - collectors/pea.py
  - tests/test_pea.py
  - collectors/macro.py
  - tests/test_macro.py
  - collectors/news.py
  - tests/test_news.py
  - tests/test_integration.py
  - main.py
findings:
  critical: 2
  warning: 7
  info: 0
  total: 9
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-10T06:20:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

The data pipeline implements five collectors (ETF, crypto, PEA, macro, news) with SQLite caching and graceful degradation. The overall architecture is sound, parameterized SQL is used throughout, and the orchestration layer correctly isolates collector failures. However, two blockers were found: a security vulnerability that logs the NewsAPI key on HTTP error responses, and a correctness bug in `etf.py` that caches failure states and silently masks subsequent failures. Seven additional warnings cover connection leaks (no `finally` blocks on three collectors), a double-sleep bug in `macro.py` that inflates both production wait time and test duration by 2x, deprecated `datetime.utcnow()` calls, and a news connection leak path.

---

## Critical Issues

### CR-01: NewsAPI Key Leaked Into Logs via `raise_for_status()`

**File:** `collectors/news.py:106`
**Issue:** `_fetch_newsapi` calls `resp.raise_for_status()`. When the NewsAPI server returns a 4xx/5xx status, `httpx` raises `HTTPStatusError` whose `str()` representation includes the full request URL — which contains `apiKey=<secret>` as a query parameter. The caller at line 335 logs `str(exc)` directly:

```python
logger.error("NewsAPI fetch failed: %s", exc)
```

This directly contradicts the stated security requirement T-02-17 ("la clé API NewsAPI n'est jamais loguée"). This can be reproduced:

```python
r = httpx.Response(status_code=401,
    request=httpx.Request('GET', 'https://newsapi.org/v2/everything?apiKey=SECRET'))
r.raise_for_status()
# raises: "Client error '401 Unauthorized' for url '...?apiKey=SECRET'"
```

**Fix:** Check status manually and log only the status code, never call `raise_for_status()` when secrets are in URL parameters:

```python
def _fetch_newsapi(api_key: str) -> list[dict]:
    params = {
        "q": "ETF OR crypto OR bourse OR CAC",
        "language": "fr",
        "sortBy": "publishedAt",
        "pageSize": NEWSAPI_PAGE_SIZE,
        "apiKey": api_key,
    }
    resp = httpx.get(NEWSAPI_URL, params=params, timeout=10)
    if resp.status_code != 200:
        # Log status code only — never the URL which contains apiKey
        raise ValueError(f"NewsAPI returned HTTP {resp.status_code}")
    articles = resp.json().get("articles", [])
    ...
```

---

### CR-02: ETF Collector Caches Fetch Failures with 4-Hour TTL

**File:** `collectors/etf.py:188-212`
**Issue:** When `_fetch_yfinance` raises an exception for a ticker, the error dict `{"price": None, "error": "..."}` is assigned to `data` (lines 190-196) and then unconditionally written to the cache at line 212:

```python
_upsert_cache(conn, CACHE_SOURCE, symbol, data)   # line 212 — always executed
```

This means a transient network error or a market-closed yfinance timeout permanently poisons the cache for that ticker for 4 hours. Any subsequent call within the TTL window returns the cached `price=None` entry via the cache-hit path (lines 179-182), which does **not** set `partial=True`. The downstream report silently receives `None` prices without any failure flag for the duration of the TTL.

For comparison, `collectors/pea.py` and `collectors/macro.py` correctly skip caching when a fetch fails — the `_upsert_cache` call is inside the `try` block only.

**Fix:** Move the cache write inside the `try` block, before the `except`:

```python
try:
    data = _fetch_yfinance(symbol)
    logger.info("yfinance OK pour %s : price=%.2f", symbol, data["price"])
    # Only cache on success
    _upsert_cache(conn, CACHE_SOURCE, symbol, data)
    tickers_data[symbol] = data
except Exception as e:
    logger.error("yfinance échec pour %s : %s", symbol, e)
    tickers_data[symbol] = {
        "price": None,
        "prev_close": None,
        "pct_change": None,
        "volume": None,
        "error": str(e),
    }
    partial = True
```

---

## Warnings

### WR-01: Double Sleep in `collect_macro` Doubles Rate-Limit Delay

**File:** `collectors/macro.py:154-161`
**Issue:** The rate-limiting logic applies two `time.sleep(1.0)` calls for every cache-miss fetch starting from the second series: a pre-fetch sleep (line 155) and a post-fetch sleep (line 161). For 4 series all missing cache, the actual wait is 7 seconds instead of the intended ~3 seconds:

```
Series 1: [no pre-sleep] → fetch → sleep(1.0) post
Series 2: sleep(1.0) pre → fetch → sleep(1.0) post   ← 2 sleeps between calls 1 and 2
Series 3: sleep(1.0) pre → fetch → sleep(1.0) post
Series 4: sleep(1.0) pre → fetch → sleep(1.0) post
Total: 7 × 1.0s = 7 seconds
```

Additionally, `test_macro.py` Test 2 and Test 4 (`test_cache_miss_fetches_fred_and_writes_cache`, `test_single_series_failure_sets_partial`) do not patch `time.sleep`, so they actually block for 7 seconds and ~5 seconds respectively during the test run.

**Fix:** Use only the pre-fetch sleep pattern (remove the post-fetch sleep):

```python
for series_id in FRED_SERIES:
    cached = _get_cached(conn, CACHE_SOURCE, series_id)
    if cached:
        series_data[series_id] = cached
        continue

    try:
        if not first_api_call:
            time.sleep(FRED_SLEEP_SECONDS)   # only one sleep, before the call
        first_api_call = False

        data = _fetch_fred_series(series_id, config.fred_api_key)
        # Remove the second time.sleep() here
        _upsert_cache(conn, CACHE_SOURCE, series_id, data)
        ...
```

Also add `patch("collectors.macro.time.sleep")` to tests 2 and 4 to prevent slow test runs.

---

### WR-02: SQLite Connection Not Closed on Exception in `collect_pea`

**File:** `collectors/pea.py:204-244`
**Issue:** `conn = get_connection(...)` is called at line 204, and `conn.close()` is at line 244 — but there is no `try/finally` wrapping the function body. If `_check_eligibility(conn)` at line 243 raises an unexpected exception (e.g., a SQLite error mid-upsert), the connection is never closed. SQLite WAL connections held open can block checkpointing and lock the database file for other processes.

**Fix:** Wrap with `try/finally`:

```python
conn = get_connection(config.db_path)
try:
    for ticker in PEA_TICKERS:
        ...
    eligibility, eligibility_changed = _check_eligibility(conn)
finally:
    conn.close()
```

---

### WR-03: SQLite Connection Not Closed on Exception in `collect_crypto`

**File:** `collectors/crypto.py:138-189`
**Issue:** Same pattern as WR-02. `conn` is opened at line 138 and closed at line 189 without a `finally` guard. If `_fetch_fear_greed(conn)` raises an unhandled exception, the connection leaks.

**Fix:** Same `try/finally` pattern around the function body after `conn = get_connection(...)`.

---

### WR-04: SQLite Connection Not Closed on Exception in `collect_macro`

**File:** `collectors/macro.py:138-183`
**Issue:** Same pattern as WR-02 and WR-03. `conn` is opened at line 138 and closed at line 183 without a `finally` guard. An unexpected exception in the loop (e.g., a SQLite error during `_upsert_cache`) would leak the connection.

**Fix:** Same `try/finally` pattern.

---

### WR-05: Two Connection Leak Paths in `collect_news`

**File:** `collectors/news.py:318-321` and `collectors/news.py:362-366`

**Issue (path 1 — line 318-321):** Inside the initial cache-read `try` block, if `get_connection()` succeeds but `_get_cached()` then raises, execution enters the `except` block which sets `conn = None` — but never calls `conn.close()` first. The valid SQLite connection is silently abandoned:

```python
try:
    conn = get_connection(config.db_path)   # succeeds
    cached = _get_cached(conn)              # throws
    ...
except Exception as exc:
    logger.error("Cache read error: %s", exc)
    conn = None   # ← connection leaked, never closed
```

**Issue (path 2 — line 362-366):** When the cache write succeeds in reaching `_upsert_cache` but that call raises, `conn.close()` on line 364 is unreachable because it sits after the throwing call inside the same `try` block:

```python
try:
    _upsert_cache(conn, final)   # throws
    conn.close()                 # ← never reached
except Exception as exc:
    logger.error("Cache write error: %s", exc)   # conn leaked
```

**Fix for both paths:** Use `try/finally` or close before reassigning:

```python
# Path 1 fix:
except Exception as exc:
    logger.error("Cache read error: %s", exc)
    try:
        conn.close()
    except Exception:
        pass
    conn = None

# Path 2 fix:
try:
    _upsert_cache(conn, final)
finally:
    conn.close()
```

---

### WR-06: `datetime.utcnow()` Deprecated in Python 3.12+

**File:** `main.py:104` and `main.py:152`
**Issue:** `datetime.datetime.utcnow()` is deprecated as of Python 3.12 (confirmed active `DeprecationWarning` on the runtime environment which is Python 3.12.3). It is scheduled for removal in a future Python release. The project targets Python 3.11+, so this warning fires on the declared minimum-compatible version plus the actual deployment version.

```python
run_at = datetime.datetime.utcnow().isoformat() + "Z"   # lines 104 and 152
```

**Fix:** Use the timezone-aware equivalent already used throughout all collector modules:

```python
run_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

---

### WR-07: `collect_news` Returns `partial: False` for Cache-Hit Path Even When Cache Was Populated from Partial Data

**File:** `collectors/news.py:310-317`
**Issue:** When the cache is hit, the function returns a hardcoded `"partial": False` regardless of whether the cached data was originally gathered with partial failures (e.g., NewsAPI was down when the cache was written). The `newsapi_failed` and `scrape_failed` flags are also hardcoded to `False`. This means a cache entry that was written during a degraded run masks the degradation for up to 2 hours.

```python
return {
    "headlines": cached,
    "count": len(cached),
    "newsapi_failed": False,   # ← hardcoded, ignores original collection state
    "scrape_failed": False,    # ← same
    "partial": False,          # ← same
    "source_used": CACHE_SOURCE,
}
```

**Fix:** Store the failure flags alongside the headlines in the cache JSON, or accept that cached-hit returns do not accurately reflect the degradation state and document this explicitly. The minimal fix is to not claim `partial: False` — use `"partial": len(cached) == 0` or store the flags in the cache.

---

_Reviewed: 2026-05-10T06:20:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
