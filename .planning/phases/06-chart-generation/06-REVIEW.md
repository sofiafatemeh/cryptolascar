---
phase: 06-chart-generation
reviewed: 2026-05-14T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - charts/__init__.py
  - charts/etf.py
  - charts/crypto.py
  - charts/gauge.py
  - charts/pea.py
  - requirements.txt
  - tests/test_charts.py
  - tests/test_charts_etf.py
  - tests/test_charts_crypto.py
  - tests/test_charts_gauge_pea.py
findings:
  critical: 1
  warning: 3
  info: 4
  total: 8
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-05-14  
**Depth:** standard  
**Files Reviewed:** 10  
**Status:** issues_found

## Summary

Four chart generation modules (`etf.py`, `crypto.py`, `gauge.py`, `pea.py`) were reviewed alongside their test suites. The general architecture is sound: every function wraps all rendering in a top-level `try/except`, closes figures on both success and failure, HTML-escapes user data, and returns `None` on error. One critical correctness bug was found in `gauge.py`'s zone logic. Three warnings cover a broken graceful-degradation contract in `__init__.py`, an inconsistent XSS escaping choice in `pea.py`, and a missing backend guard in `gauge.py`. Four informational items cover code duplication, weak test assertions, and a silent type coercion.

---

## Critical Issues

### CR-01: `gauge.py` — Float scores at zone boundaries fall into unmapped gaps, producing visually incorrect charts

**File:** `charts/gauge.py:41-47` and `charts/gauge.py:64-69`

**Issue:** `ZONES` uses integer range endpoints (`(0, 24, ...)`, `(25, 44, ...)`, etc.). `_zone_for_score` uses `lo <= score <= hi` which evaluates correctly only for integer scores. Float scores such as `24.5`, `44.5`, `55.5`, and `74.5` fall into the gaps between adjacent zones (e.g., the gap between `[0, 24]` and `[25, 44]`), causing `_zone_for_score` to return `(CHART_TEXT, "Unknown")`.

This produces two simultaneous visual errors on a single chart render:
1. The score text and zone label render in `CHART_TEXT` (`#e0e0e0`) instead of the active zone color.
2. Every wedge in the gauge arc renders at `alpha=0.25` (dim) because the `is_active = (lo <= score <= hi)` check in the wedge loop also fails to match any zone. The gauge looks completely inactive for any float input at these boundary values.

The `Fear & Greed Index` API (e.g., from Alternative.me) commonly returns float values. Scores are accepted as `int or float` per the docstring, so this is a contract violation.

**Verification:**
```python
ZONES = [(0,24,...), (25,44,...), (45,55,...), (56,74,...), (75,100,...)]
score = 24.5
# _zone_for_score(24.5) → fallthrough → returns (CHART_TEXT, "Unknown")
# Wedge loop: no zone matches → all alpha=0.25
```

**Fix — change zone boundaries to use floats and close the gaps:**
```python
ZONES = [
    (0.0,  25.0, "#FF4444", "Extreme Fear"),
    (25.0, 45.0, "#FF8C42", "Fear"),
    (45.0, 56.0, "#E0E0E0", "Neutral"),
    (56.0, 75.0, "#00C851", "Greed"),
    (75.0, 100.0, "#00FF7F", "Extreme Greed"),
]
```
Or alternatively, floor/round the score at validation time:
```python
score = float(score)
if not (0.0 <= score <= 100.0):
    ...
# Snap to integer before zone lookup so gaps cannot be reached:
score_int = int(round(score))
active_color, active_label = _zone_for_score(score_int)
```
Either approach closes the gap. No existing test exercises float boundary scores, so this bug is undetected by the current suite.

---

## Warnings

### WR-01: `charts/__init__.py` — `generate_fear_greed_gauge` and `generate_pea_table` silently assigned `None` on `ImportError`, violating CHART-05 graceful degradation for callers

**File:** `charts/__init__.py:29-37`

**Issue:** When `charts/gauge.py` or `charts/pea.py` cannot be imported (e.g., missing dependency), the package silently sets `generate_fear_greed_gauge = None` and `generate_pea_table = None`. Any caller that does `charts.generate_fear_greed_gauge(score)` or `from charts import generate_fear_greed_gauge; generate_fear_greed_gauge(score)` will get `TypeError: 'NoneType' object is not callable` — an unhandled exception that propagates to the pipeline, violating CHART-05's "pipeline never raises from chart generation" contract.

The docstring says "Callers must check for None", but a callable that is actually `None` raises on call rather than returning `None`. CHART-05 guarantees callers a callable that returns `None` on failure, not a `None` pseudo-callable.

**Fix — wrap each function in a shim that returns `None` when the module failed to import:**
```python
try:
    from charts.gauge import generate_fear_greed_gauge
except ImportError as e:
    import logging as _logging
    _logging.getLogger(__name__).error(f"charts.gauge unavailable: {e}")
    def generate_fear_greed_gauge(score) -> None:  # type: ignore[misc]
        return None

try:
    from charts.pea import generate_pea_table
except ImportError as e:
    import logging as _logging
    _logging.getLogger(__name__).error(f"charts.pea unavailable: {e}")
    def generate_pea_table(pea_data) -> None:  # type: ignore[misc]
        return None
```

---

### WR-02: `charts/pea.py` — `html.escape(..., quote=False)` leaves double-quote characters unescaped

**File:** `charts/pea.py:161-162`

**Issue:** The code uses `html.escape(value, quote=False)`, which escapes `<`, `>`, and `&` but leaves `"` (double quote) and `'` (single quote) as literal characters. The T-06-11 claim is "ASVS L1 output encoding." ASVS L1 output encoding requires escaping quotes for element content contexts when the string could be re-used in an attribute context by a consuming template engine, mail client, or intermediary.

Currently, `ticker` and `name` content is placed between `<td>...</td>` tags — pure element content — so an unescaped `"` cannot break out of an HTML attribute here. However, the output HTML is destined for Jinja2 templates and email clients. If a consuming Jinja2 template ever wraps this table in `<div title="{{ pea_table }}">`, the unescaped quotes would allow attribute injection. The correct ASVS L1 posture is `quote=True` (the default).

**Fix:**
```python
safe_ticker = html.escape(str(item.get("ticker", "") or ""), quote=True) or "—"
safe_name   = html.escape(str(item.get("name",   "") or ""), quote=True) or "—"
```
The `quote=True` default is safer and has no performance cost.

---

### WR-03: `charts/gauge.py` — No `matplotlib.use("Agg")` call; relies entirely on `charts/__init__.py` import order

**File:** `charts/gauge.py:24-25`

**Issue:** `gauge.py` imports `matplotlib.patches` and `matplotlib.pyplot` at module level without first calling `matplotlib.use("Agg")`. Both `charts/etf.py` and `charts/crypto.py` defensively call `matplotlib.use("Agg")` before importing `pyplot`. `gauge.py` silently depends on `charts/__init__.py` having already set the backend.

This is a hidden ordering dependency. If `charts.gauge` is imported directly in any context where `charts/__init__.py` has not yet run (e.g., a standalone script, a future test fixture, or a REPL session), matplotlib may attempt to initialize a display-dependent backend (TkAgg, Qt5Agg) and raise `cannot connect to X server` on the headless VPS. The current test suite avoids this only because `from charts.gauge import ...` triggers `charts/__init__.py` first, which happens to be the package resolution path — but this is a fragile assumption.

**Fix — add the backend call in `gauge.py` before pyplot import, consistent with `etf.py` and `crypto.py`:**
```python
import matplotlib
matplotlib.use("Agg")  # non-interactive backend, VPS-safe
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
```

---

## Info

### IN-01: `charts/etf.py` and `charts/crypto.py` — Redundant `matplotlib.use("Agg")` calls after `__init__.py` already sets backend

**File:** `charts/etf.py:26`, `charts/crypto.py:25`

**Issue:** Both `etf.py` and `crypto.py` call `matplotlib.use("Agg")` at module level. When imported through the `charts` package (the only supported path), `charts/__init__.py` has already called `matplotlib.use("Agg")` at line 24 before these submodule imports. The repeated calls are harmless when the backend is the same, but they are a maintenance smell — they exist because `gauge.py` omits the call and the pattern is inconsistent. This is IN-01 rather than a warning only because in practice `matplotlib.use()` called again with the same backend emits no warning and has no effect.

**Fix:** Resolve WR-03 by adding `matplotlib.use("Agg")` to `gauge.py`, which makes the three PNG-generating submodules consistent and self-contained. The existing calls in `etf.py` and `crypto.py` are then intentional defensive redundancy, which is acceptable.

---

### IN-02: `charts/etf.py:62-63` — Falsy coercion via `... or 0.0` silently converts `False` to `0.0`

**File:** `charts/etf.py:62-63`

**Issue:**
```python
values_1d = [etf_data[t].get("1d", 0.0) or 0.0 for t in tickers]
values_1w = [etf_data[t].get("1w", 0.0) or 0.0 for t in tickers]
```
The `or 0.0` idiom is intended to replace `None` with `0.0`, but it also replaces `False`, `0`, and `""` with `0.0`. A legitimate `0.0` value is fine (it evaluates as falsy and maps back to `0.0`), but `False` passed as a performance value would be silently treated as `0.0` with no log. The idiomatic fix is an explicit `None` check.

**Fix:**
```python
values_1d = [0.0 if etf_data[t].get("1d") is None else float(etf_data[t].get("1d", 0.0)) for t in tickers]
```
Or more readably:
```python
def _safe_float(v, default=0.0):
    return default if v is None else float(v)
values_1d = [_safe_float(etf_data[t].get("1d")) for t in tickers]
values_1w = [_safe_float(etf_data[t].get("1w")) for t in tickers]
```

---

### IN-03: Test coverage gap — no test exercises float scores at zone boundary gaps in `gauge.py`

**File:** `tests/test_charts.py:125-147`, `tests/test_charts_gauge_pea.py:42-82`

**Issue:** Every parametrized gauge test uses integer scores. The zone gap bug identified in CR-01 (scores such as `24.5`, `44.5`, `55.5`, `74.5`) is entirely absent from the test suite. Because the Fear & Greed API commonly returns floats, this gap means the bug ships undetected.

**Fix — add parametrized float boundary tests:**
```python
@pytest.mark.parametrize("score", [24.5, 44.5, 55.5, 74.5])
def test_gauge_float_boundary_scores_return_png(score):
    from charts.gauge import generate_fear_greed_gauge
    result = generate_fear_greed_gauge(score)
    assert result is not None, f"Expected PNG for float score {score}, got None"
    assert _is_valid_png(result)
```
After fixing CR-01, this test should pass. Before the fix, it would reveal the "Unknown" zone rendering defect.

---

### IN-04: `tests/test_charts_crypto.py:55-64` — Mismatched-length BTC/ETH test has no assertion on correctness

**File:** `tests/test_charts_crypto.py:55-64`

**Issue:** The `test_mixed_btc_eth_lengths` test passes if the function either returns a valid PNG or returns `None` — any outcome is accepted. This provides no regression protection. The purpose of the test appears to verify that the function does not crash on mismatched input, which is worthwhile, but the comment "both are acceptable" means a silent failure (returning `None` when a chart was expected) would pass the test.

**Fix — assert at minimum that the function does not raise (which the current structure already ensures) and add a separate test documenting the expected behavior (chart or degraded-none):**
```python
def test_mixed_btc_eth_lengths_does_not_raise():
    """Mismatched lengths must not raise — returning either a PNG or None is acceptable."""
    from charts.crypto import generate_crypto_sparklines
    btc = [40000.0, 41000.0, 42000.0, 43000.0, 44000.0]
    eth = [2400.0, 2450.0, 2500.0, 2480.0, 2550.0, 2600.0, 2650.0]
    try:
        result = generate_crypto_sparklines(btc, eth)
        if result is not None:
            raw = base64.b64decode(result)
            assert raw[:4] == b"\x89PNG", "Non-None result must be a valid PNG"
    except Exception as e:
        pytest.fail(f"generate_crypto_sparklines raised unexpectedly: {e}")
```
This is semantically identical to the current test but makes the intent explicit.

---

_Reviewed: 2026-05-14_  
_Reviewer: Claude (gsd-code-reviewer)_  
_Depth: standard_
