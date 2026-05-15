---
phase: 08-close-gaps
status: human_needed
verified: 2026-05-15T00:00:00Z
must_haves_total: 5
must_haves_verified: 4
human_verification:
  - test: "Run a real daily report end-to-end (no mocks, live API keys) and inspect the delivered email"
    expected: "Email contains ETF bar chart (img tag), crypto sparklines for BTC and ETH (img tag), PEA colored table (HTML table with per-position rows)"
    why_human: "SC-1, SC-2, SC-3 require a live API run — yfinance for pct_change_1w and CoinGecko market_chart for sparkline history. The boundary tests prove the transform logic works; only a real API call confirms real data flows to the chart generators in production."
---

# Phase 8 Verification: Close Gaps

**Phase Goal:** All CHART-01/02/04 data-contract mismatches are fixed (real charts render in production), CHART-03 unguarded AttributeError is patched, 7-day sparkline data is collected, and Phase 6 VERIFICATION.md is written
**Verified:** 2026-05-15
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Must-Haves

### SC-1: Running a real daily report shows an ETF bar chart with 1-day and 1-week bars in the email

- **Expected**: `_build_chart_panel` receives `{"TICKER": {"1d": float, "1w": float}}` from the transformed `etf["tickers"]` dict; `generate_etf_chart` returns a base64 PNG; the email HTML contains an `<img>` tag for the ETF chart.
- **Verified**: PARTIALLY — transform logic verified; live API call is human-only
- **Evidence**:
  - `collectors/etf.py` line 213: `data["pct_change_1w"] = _fetch_1w_pct(symbol)` — pct_change_1w added to every ticker dict before cache write.
  - `reporters/daily.py` lines 199–206: `etf_chart_data = {sym: {"1d": t.get("pct_change") or 0.0, "1w": t.get("pct_change_1w") or 0.0} ...}` — correct transform applied.
  - Same transform is identical in `reporters/weekly.py` (lines 183–190) and `reporters/monthly.py` (lines 210–217).
  - `tests/test_chart_boundary.py::TestEtfBoundary::test_etf_boundary_produces_valid_base64` — exercises real `generate_etf_chart` (no mock) with `pct_change=0.5, pct_change_1w=1.2`; asserts `"<img" in result`. PASSES (11/11 boundary tests pass).
  - Full test suite: 321 tests pass.

### SC-2: Running a real daily report shows crypto sparklines for BTC and ETH (7-day history collected via separate CoinGecko endpoint)

- **Expected**: `collect_crypto` enriches `coins["bitcoin"]["history"]` and `coins["ethereum"]["history"]` with lists of >= 7 floats from `CoinGecko /api/v3/coins/{id}/market_chart`; `_build_chart_panel` passes these lists to `generate_crypto_sparklines`; email HTML contains an `<img>` tag for sparklines.
- **Verified**: PARTIALLY — data wiring and transform verified; live CoinGecko call is human-only
- **Evidence**:
  - `collectors/crypto.py` lines 48–50: constants `CG_MARKET_CHART_URL`, `SPARKLINE_SOURCE = "coingecko_sparkline"`, `SPARKLINE_COINS = ["bitcoin", "ethereum"]` defined.
  - `collectors/crypto.py` line 124: `_fetch_sparkline(conn, coin_id, config)` defined; calls `httpx.get` with `days=7`, sleeps `CG_SLEEP_SECONDS=1.5` after each successful call (rate limit compliance), caches under `source="coingecko_sparkline"`.
  - `collectors/crypto.py` lines 221–224: sparkline enrichment block after batch fetch — `coins_data[coin_id]["history"] = _fetch_sparkline(conn, coin_id, config)` for bitcoin and ethereum.
  - `reporters/daily.py` lines 219–221: `btc_hist = (...).get("bitcoin", {}).get("history", [])` / `eth_hist = ...` — correctly reads history from data dict and passes to `generate_crypto_sparklines`.
  - `tests/test_chart_boundary.py::TestCryptoSparklineBoundary::test_sparkline_history_passed_to_generate_crypto_sparklines` — calls real `generate_crypto_sparklines` with 8-element lists; asserts `"<img" in result`. PASSES.

### SC-3: Running a real daily report shows the PEA colored table with per-position rows correctly colored

- **Expected**: `_build_chart_panel` transforms `pea["prices"]` dict into `list[dict]` with keys `ticker/name/price/change_1d/change_1w/pea_eligible`; `generate_pea_table` returns HTML `<table>` with color-coded rows.
- **Verified**: PARTIALLY — transform logic and PEA table rendering verified by boundary test; live PEA data collection is human-only
- **Evidence**:
  - `reporters/daily.py` lines 39–52: module-level `_PEA_NAMES` and `_PEA_ELIGIBILITY` dicts defined for all 5 PEA tickers.
  - `reporters/daily.py` lines 241–253: `pea_list` comprehension transforms `pea["prices"]` to `list[dict]` with all required keys; filters on `price is not None`.
  - Same transform is identical in `reporters/weekly.py` (lines 225–237) and `reporters/monthly.py` (lines 252–264).
  - `tests/test_chart_boundary.py::TestPeaBoundary::test_pea_boundary_produces_table_html` — calls real `generate_pea_table` with `CW8.PA` position; asserts `"<table" in result` and `"CW8.PA" in result`. PASSES.
  - `tests/test_chart_boundary.py::TestPeaBoundary::test_pea_boundary_pea_eligible_correct` — captures pea_list argument; asserts `cw8["pea_eligible"] is True` and `fchi["pea_eligible"] is None`. PASSES.

### SC-4: When collect_crypto stores fear_greed=None, the Fear & Greed gauge is silently skipped (None returned) and the rest of the report is unaffected

- **Expected**: `fg_score = ((data.get("crypto") or {}).get("fear_greed") or {}).get("value")` returns `None`; `generate_fear_greed_gauge` is not called; gauge cell shows `GAUGE_FALLBACK`; no `AttributeError` propagates; report is not fully degraded.
- **Verified**: VERIFIED
- **Evidence**:
  - `reporters/daily.py` line 195: `fg_score = ((data.get("crypto") or {}).get("fear_greed") or {}).get("value")` — None-safe pattern present.
  - Same pattern at `reporters/weekly.py` line 179 and `reporters/monthly.py` line 206.
  - `reporters/daily.py` line 231: `gauge_b64 = generate_fear_greed_gauge(fg_score) if fg_score is not None else None` — gauge call guarded by `if fg_score is not None`.
  - `reporters/daily.py` line 108: `fg = crypto.get("fear_greed") or {}` — None-safe pattern also in `_crypto_section` (catches the Rule 1 deviation fixed in 08-02).
  - `tests/test_chart_boundary.py::TestChart03Boundary::test_fear_greed_none_no_attributeerror` — directly calls `_build_chart_panel` with `fear_greed=None`; asserts no `AttributeError`. PASSES.
  - `tests/test_chart_boundary.py::TestChart03Boundary::test_fear_greed_none_shows_gauge_fallback` — asserts `GAUGE_FALLBACK in result`. PASSES.
  - `tests/test_chart_boundary.py::TestChart03Boundary::test_fear_greed_none_no_full_report_collapse` — calls `build_daily_report` with `fear_greed=None`; asserts `result.html_body.count("[Section indisponible.]") < 6`. PASSES.
  - All 3 Chart03 boundary tests pass programmatically without requiring a live run. SC-4 is fully verifiable from code.

### SC-5: Phase 6 VERIFICATION.md exists and confirms all five CHART-* requirements satisfied

- **Expected**: File `.planning/phases/06-chart-generation/06-VERIFICATION.md` exists, contains CHART-01 through CHART-05 each marked PASS, with bug history notes.
- **Verified**: VERIFIED
- **Evidence**:
  - File exists at `.planning/phases/06-chart-generation/06-VERIFICATION.md` (142 lines).
  - `grep -c "CHART-0[12345]" 06-VERIFICATION.md` = 12 (>= 5).
  - `grep -c "PASS" 06-VERIFICATION.md` = 11 (>= 5).
  - `grep -c "Bug history" 06-VERIFICATION.md` = 4 (>= 3).
  - Document-level `**Status:** PASS` present.
  - All five CHART-* requirements listed with individual `**Status:** PASS` entries.

---

## Requirement Traceability

| Req ID | Plan(s) | Description | Status | Evidence |
|--------|---------|-------------|--------|----------|
| CHART-01 | 08-01, 08-02 | ETF bar chart 1d/1w in email | VERIFIED (programmatic) + human needed for live run | `_fetch_1w_pct` in etf.py; `etf_chart_data` transform in all 3 reporters; boundary test `test_etf_boundary_produces_valid_base64` passes |
| CHART-02 | 08-01 | Crypto sparklines 7-day BTC+ETH in email | VERIFIED (programmatic) + human needed for live run | `_fetch_sparkline` with market_chart endpoint in crypto.py; history enrichment; boundary test `test_sparkline_history_passed_to_generate_crypto_sparklines` passes |
| CHART-03 | 08-02 | Fear & Greed gauge silently skipped when None | VERIFIED (fully automated) | `or {}` pattern in all 3 reporters; 3 boundary tests pass covering no-AttributeError, GAUGE_FALLBACK, no report collapse |
| CHART-04 | 08-02 | PEA colored table with per-position rows | VERIFIED (programmatic) + human needed for live run | `pea_list` comprehension in all 3 reporters; `_PEA_NAMES`/`_PEA_ELIGIBILITY` dicts; boundary tests `test_pea_boundary_produces_table_html` and `test_pea_boundary_pea_eligible_correct` pass |
| CHART-05 | 08-02 | Chart failure → None → pipeline continues | VERIFIED | Each chart call wrapped in `try/except Exception → None`; 06-VERIFICATION.md documents with test evidence; 321 tests pass including fallback tests |

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `collectors/etf.py` | `pct_change_1w` field + `_fetch_1w_pct` helper | VERIFIED | Lines 109–128 define `_fetch_1w_pct`; line 213 assigns result to `data["pct_change_1w"]`; grep counts: 2 occurrences each |
| `collectors/crypto.py` | `_fetch_sparkline`, `SPARKLINE_SOURCE`, `CG_MARKET_CHART_URL`, history enrichment | VERIFIED | Lines 48–50 constants; lines 124–153 `_fetch_sparkline`; lines 221–224 enrichment block; sleep at line 147 |
| `reporters/daily.py` | `etf_chart_data` transform, `pea_list` transform, None-safe `fg_score` | VERIFIED | All three fixes present at correct locations; `_PEA_NAMES` + `_PEA_ELIGIBILITY` at module level (lines 39–52) |
| `reporters/weekly.py` | Same three fixes as daily.py | VERIFIED | Identical patterns confirmed at lines 38–51, 183–190, 225–237; `_crypto_recap` uses `or {}` at line 114 |
| `reporters/monthly.py` | Same three fixes as daily.py | VERIFIED | Identical patterns confirmed at lines 39–52, 210–217, 252–264; `_crypto_monthly` uses `or {}` at line 137 |
| `tests/test_chart_boundary.py` | 11 boundary integration tests, no chart generator mocking in assertion-path tests | VERIFIED | 11 `def test_` functions; 11/11 pass; `test_etf_boundary_produces_valid_base64` and `test_sparkline_history_passed_to_generate_crypto_sparklines` do not mock chart generators |
| `.planning/phases/06-chart-generation/06-VERIFICATION.md` | CHART-01..05 all PASS, bug histories documented | VERIFIED | File exists; 12 CHART-0x references; 11 PASS occurrences; 4 Bug history notes; document-level PASS |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `collectors/etf.py::collect_etf` | `etf["tickers"][sym]["pct_change_1w"]` | `_fetch_1w_pct(symbol)` called at line 213 | WIRED | Value added before `_upsert_cache`; flows through cache to reporter |
| `collectors/crypto.py::collect_crypto` | `coins["bitcoin"]["history"]` and `coins["ethereum"]["history"]` | `_fetch_sparkline` enrichment block lines 221–224 | WIRED | Returns `list[float]` or `[]` on failure; both CG sleep and cache wired |
| `reporters/daily.py::_build_chart_panel` | `charts.generate_etf_chart` | `etf_chart_data = {sym: {"1d": ..., "1w": ...} ...}` lines 199–209 | WIRED | Transform applied before chart call; filter removes None pct_change entries |
| `reporters/daily.py::_build_chart_panel` | `charts.generate_pea_table` | `pea_list = [{ticker, name, price, ...} ...]` lines 241–253, 255–258 | WIRED | list[dict] passed to generator; empty list → None → PEA_FALLBACK |
| `reporters/daily.py::_build_chart_panel` | `fear_greed value` | `((data.get("crypto") or {}).get("fear_greed") or {}).get("value")` line 195 | WIRED | None-safe; when None → `fg_score=None` → gauge call skipped → GAUGE_FALLBACK |
| `reporters/daily.py::_build_chart_panel` | `charts.generate_crypto_sparklines` | `btc_hist = (...).get("bitcoin", {}).get("history", [])` lines 219–221 | WIRED | History list read from coins data; passed directly to sparklines generator |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `reporters/daily.py::_build_chart_panel` | `etf_chart_data` | `collectors/etf.py::_fetch_1w_pct` (yfinance) | Yes — real yfinance `history(period="7d")` call | FLOWING (live API; boundary test confirms transform) |
| `reporters/daily.py::_build_chart_panel` | `btc_hist`, `eth_hist` | `collectors/crypto.py::_fetch_sparkline` (CoinGecko market_chart) | Yes — real CoinGecko endpoint with `days=7` | FLOWING (live API; boundary test confirms transform) |
| `reporters/daily.py::_build_chart_panel` | `pea_list` | `collectors/pea.py::collect_pea` (yfinance PEA tickers) | Yes — collector provides prices dict | FLOWING |
| `reporters/daily.py::_build_chart_panel` | `fg_score` | `collectors/crypto.py::_fetch_fear_greed` (Alternative.me) | Yes — returns `None` gracefully when unavailable | FLOWING (None-safe) |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 11 boundary tests pass | `python3 -m pytest tests/test_chart_boundary.py -q` | 11 passed in 2.92s | PASS |
| Full 321-test suite passes | `python3 -m pytest tests/ -q` | 321 passed in 34.42s | PASS |
| `pct_change_1w` in etf.py (>= 2) | `grep -c "pct_change_1w" collectors/etf.py` | 2 | PASS |
| `_fetch_1w_pct` in etf.py (>= 2) | `grep -c "_fetch_1w_pct" collectors/etf.py` | 2 | PASS |
| `etf_chart_data` in all 3 reporters | grep counts | 2, 2, 2 | PASS |
| `pea_list` in all 3 reporters | grep counts | 2, 2, 2 | PASS |
| `_PEA_NAMES` in all 3 reporters | grep counts | 2, 2, 2 | PASS |
| CHART-03 None-safe pattern in all 3 reporters | grep match | Present in daily/weekly/monthly | PASS |
| `_fetch_sparkline` in crypto.py (>= 2) | `grep -c "_fetch_sparkline" collectors/crypto.py` | 2 | PASS |
| `market_chart` in crypto.py | `grep -c "market_chart" collectors/crypto.py` | 2 | PASS |
| Sleep after sparkline API call | line 147 in crypto.py | `time.sleep(CG_SLEEP_SECONDS)` inside `_fetch_sparkline` | PASS |
| No hardcoded credentials | grep for raw key strings | No matches | PASS |
| 06-VERIFICATION.md CHART references | `grep -c "CHART-0[12345]"` | 12 | PASS |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No stubs, hardcoded data, or TODO/FIXME found in modified files |

---

## Human Verification Required

### 1. Live Production Run Verification

**Test:** Configure `.env` with real API keys (COINGECKO_API_KEY for market_chart, valid yfinance access). Run `python3 main.py` or trigger a daily report run. Inspect the delivered email (salsaloca.strasbourg@gmail.com).

**Expected:**
- ETF section contains an `<img>` tag (not `ETF_FALLBACK` text) showing grouped bars for each ticker with both 1-day and 1-week variation.
- Crypto section contains an `<img>` tag (not `CRYPTO_FALLBACK` text) showing sparkline curves for BTC and ETH.
- PEA section contains an HTML `<table>` (not `PEA_FALLBACK` text) with rows colored green/red per performance.
- Fear & Greed gauge is either present (if Alternative.me is reachable) or silently absent with `GAUGE_FALLBACK` — no exception, no full-report collapse.

**Why human:** SC-1, SC-2, SC-3 require real network calls. Boundary tests prove the transform logic is correct and the chart generators produce `<img>`-triggering output with synthetic data. Only a live run confirms:
1. yfinance `history(period="7d")` returns >= 2 data points for all 5 ETF tickers.
2. CoinGecko market_chart endpoint is reachable and returns >= 7 price points for bitcoin and ethereum.
3. PEA collector (`collectors/pea.py`) populates `pea["prices"]` with real prices so the transform produces a non-empty `pea_list`.

---

## Gaps Summary

No code gaps. All five phase goal elements are present and wired in the codebase:

1. **CHART-01/02/04 data-contract mismatches** — fixed. ETF transform (`etf_chart_data`), crypto sparkline collection (`_fetch_sparkline`), and PEA transform (`pea_list`) are implemented and confirmed by 11 passing boundary tests.
2. **CHART-03 AttributeError** — patched. The `(... .get("fear_greed") or {}).get("value")` pattern is in all three reporters plus `_crypto_section` in daily.py (Rule 1 fix). Three dedicated tests confirm the fix.
3. **7-day sparkline data** — collected. `_fetch_sparkline` uses CoinGecko `/api/v3/coins/{id}/market_chart` with `days=7`, sleeps 1.5s after each call (rate limit compliance), caches under `source="coingecko_sparkline"`.
4. **Phase 6 VERIFICATION.md** — written. Confirms CHART-01..05 all PASS with evidence and bug histories.

The only gap is operational: SC-1, SC-2, and SC-3 ("shows in the email") require a live production run that no automated test can substitute for.

---

_Verified: 2026-05-15_
_Verifier: Claude (gsd-verifier)_
