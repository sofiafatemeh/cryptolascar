---
phase: 03-report-generation
reviewed: 2026-05-10T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - reporters/base.py
  - reporters/daily.py
  - reporters/dispatch.py
  - reporters/monthly.py
  - reporters/weekly.py
  - tests/test_daily.py
  - tests/test_dispatch.py
  - tests/test_monthly.py
  - tests/test_reporters_base.py
  - tests/test_weekly.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Ten files were reviewed covering the report generation layer (daily/weekly/monthly builders, the dispatch calendar router, the shared Claude synthesis helper, and their test suites). The architecture is sound: graceful degradation is consistently applied across all builders, no credentials are hardcoded, and the calendar routing logic in `dispatch.py` is correct. However, one logic bug in `monthly.py` produces duplicate alert text in the PEA Monthly section, and three warnings address incomplete safety guarantees, a silent failure mode in `base.py`, and a missing PEA eligibility test in the weekly suite.

---

## Warnings

### WR-01: Double PEA eligibility alert in `monthly.py` — duplicate output when `eligibility_changed=True`

**File:** `reporters/monthly.py:134-146`

**Issue:** `_pea_monthly` uses two independent mechanisms to guarantee the eligibility alert appears in the section output: (1) an `alert` variable that is always prepended to the output string, and (2) a secondary guard that also prepends "ALERTE..." directly onto `body` when `body` does not already contain the word. When `synthesize_section` returns text that does not contain "alerte" or "changement" (the common case, and exactly what the mocked tests exercise), **both mechanisms fire**, producing "ALERTE — changement d'éligibilité PEA détecté ce mois." at the top of the section AND "ALERTE — changement d'éligibilité PEA détecté." at the start of the narrative body. The test in `test_monthly.py` only asserts presence of the word "alerte", not uniqueness, so the duplication passes undetected.

Reproduction (no external dependencies):
```python
# Simulate _pea_monthly with eligibility_changed=True and body lacking 'alerte'
alert = "ALERTE — changement d'éligibilité PEA détecté ce mois.\n\n"
body = "NARRATION OK"
table = "| Ticker | Prix | Variation |"

if "alerte" not in body.lower() and "changement" not in body.lower():
    body = "ALERTE — changement d'éligibilité PEA détecté. " + body

out = f"{alert}{table}\n\n{body}"
# out contains "ALERTE" twice
```

**Fix:** Choose one mechanism and remove the other. The `alert` variable approach (prepend to output) is simpler and consistent with `weekly.py`. Remove the secondary body check from `_pea_monthly`:

```python
# reporters/monthly.py _pea_monthly — keep alert variable, remove secondary check
alert = ""
if pea.get("eligibility_changed"):
    alert = "ALERTE — changement d'éligibilité PEA détecté ce mois.\n\n"
prompt = "Commentaire PEA France mensuel ~150 mots. Bilan du mois pour les titres PEA."
body = synthesize_section(prompt, config=config, system=MONTHLY_SYSTEM_PROMPT)
# Remove lines 141-145 (the secondary body prepend)
out = f"{alert}{table}\n\n{body}" if table else f"{alert}{body}"
return build_section("PEA Monthly", out)
```

---

### WR-02: `response.content[0].text` — no guard against empty content list in `base.py`

**File:** `reporters/base.py:52`

**Issue:** The Anthropic SDK can return a `Message` with `content=[]` in edge cases (e.g., when `stop_reason` is unusual or when a streaming error is suppressed). The access `response.content[0].text` would then raise `IndexError`. While this is caught by the broad `except Exception` on line 53 and returns `FALLBACK_TEMPLATE`, the `logger.warning` message only says `"Claude synthesis failed: %s"` — emitting `list index out of range` with no indication that the API call itself succeeded. This obscures the root cause during incident diagnosis.

Additionally, if `content[0]` is not a `TextBlock` (e.g., it is a `ToolUseBlock`), `AttributeError` is raised on `.text`. This is equally silent.

**Fix:** Guard the access explicitly and log a distinct message:

```python
# reporters/base.py
response = client.messages.create(**kwargs)
if not response.content:
    logger.warning("Claude returned empty content list for section (stop_reason=%s)", response.stop_reason)
    return FALLBACK_TEMPLATE
return response.content[0].text
```

---

### WR-03: `weekly.py` PEA eligibility alert lacks the secondary body guarantee that `daily.py` and `monthly.py` both implement

**File:** `reporters/weekly.py:110-115`

**Issue:** `_pea_wrap` in `weekly.py` unconditionally prepends the alert header string to the output when `eligibility_changed=True`, but it does **not** run the secondary check that ensures the word "alerte" or "changement" appears in the synthesized body text. By contrast, `daily.py` (lines 120-125) and `monthly.py` (lines 141-145) both add a secondary guarantee to the body. The inconsistency means a weekly report body could be delivered where the Claude synthesis contradicts or dilutes the alert without any keyword present in the body itself. The existing test suite (`test_weekly.py`) has no test for PEA eligibility alert at all, leaving this gap unverified.

**Fix:** Apply the same secondary guard pattern consistently (or remove it from daily/monthly and rely on the prepended alert variable alone — pick one strategy and apply it uniformly):

```python
# reporters/weekly.py _pea_wrap — after body = synthesize_section(...)
if (
    pea.get("eligibility_changed")
    and "alerte" not in body.lower()
    and "changement" not in body.lower()
):
    body = "ALERTE — changement d'éligibilité PEA détecté. " + body
return build_section("PEA Wrap", f"{alert}{table}\n\n{body}" if table else f"{alert}{body}")
```

Also add a test case to `test_weekly.py` covering `eligibility_changed=True`, analogous to `test_daily.py` Test 7 and `test_monthly.py` Test 7.

---

### WR-04: T-03-01 log-safety guarantee is not adversarially verified in `test_reporters_base.py`

**File:** `tests/test_reporters_base.py:126-138`

**Issue:** Test 4 is intended to prove that the Anthropic API key never appears in logs (threat model T-03-01). The mock raises `Exception("network error")` — a message that trivially does not contain "test-anthropic-key". The test would still pass if `logger.warning` were changed to `logger.warning("key=%s err=%s", config.anthropic_api_key, e)`, because `"network error"` still does not contain `"test-anthropic-key"`. The test does not prove the property it claims; it only proves the current exception message doesn't leak the key.

**Fix:** Use a mock that raises an exception whose `str()` representation includes the API key value, then assert it still does not appear in logs:

```python
# tests/test_reporters_base.py — Test 4 hardened version
def test_synthesize_section_never_logs_api_key(tmp_config, caplog):
    mock_client = MagicMock()
    # Adversarial: exception message itself contains the key
    mock_client.messages.create.side_effect = Exception(
        f"AuthenticationError: key={tmp_config.anthropic_api_key}"
    )
    with patch("reporters.base.Anthropic", return_value=mock_client):
        with caplog.at_level(logging.DEBUG, logger="reporters.base"):
            synthesize_section("test prompt", config=tmp_config)
    assert tmp_config.anthropic_api_key not in caplog.text
```

This test will **fail** with the current implementation (the exception message is logged verbatim via `%s`), exposing a real T-03-01 violation when the SDK surfaces the key in its error string. The fix in `base.py` is to log only `type(e).__name__` rather than `str(e)`:

```python
# reporters/base.py line 55 — log only the exception type, never its message
logger.warning("Claude synthesis failed: %s", type(e).__name__)
```

---

## Info

### IN-01: `_table` function duplicated identically in `weekly.py` and `monthly.py`

**File:** `reporters/weekly.py:31-38`, `reporters/monthly.py:33-40`

**Issue:** Both modules define an identical private `_table` function. If the Markdown table format ever needs to change (e.g., adding spaces around `---` separators for broader renderer compatibility), the change must be made in two places. The function belongs in `reporters/base.py` where shared formatting helpers already live (`format_pct`, `format_currency`, `build_section`).

**Fix:** Move `_table` to `reporters/base.py` and import it in both `weekly.py` and `monthly.py`.

---

### IN-02: Misleading threat-model comment in `base.py` references non-existent `section_name` variable

**File:** `reporters/base.py:5-7`

**Issue:** The module-level docstring states: *"seuls section_name et str(e) apparaissent dans les logs en cas d'échec."* The function `synthesize_section` has no `section_name` parameter and does not log any section name — it logs only `str(e)`. The comment documents a property that does not exist in the implementation, which could mislead future maintainers about what is and is not logged.

**Fix:** Correct the comment to reflect reality:

```python
# T-03-01 : la clé Anthropic n'est jamais loggée — seul str(e) apparaît dans les logs.
```

---

### IN-03: `from typing import Dict` is legacy in Python 3.11+

**File:** `reporters/dispatch.py:26`

**Issue:** Python 3.11 (the declared minimum version) supports `dict[str, str]` as a built-in generic directly in type annotations. `from typing import Dict` is deprecated since Python 3.9 and will eventually be removed.

**Fix:**

```python
# reporters/dispatch.py — remove the typing import and update annotation
def select_reports(today: _dt.date, data: dict, config: Config) -> dict[str, str]:
```

---

### IN-04: `test_weekly.py` `MOCK_DATA_FULL` omits `_meta` key — `_executive_summary` silently uses empty sources list

**File:** `tests/test_weekly.py:128-134`

**Issue:** `MOCK_DATA_FULL` does not include a `"_meta"` key. `_executive_summary` calls `data.get("_meta", {}) or {}` which returns `{}`, so the prompt sent to Claude lists `sources_ok=[]` and `sources_failed=[]`. This means word-count tests and section tests pass, but the executive summary prompt is materially less informative than what production generates. If `_executive_summary` behavior is ever made conditional on `_meta` contents, existing tests would not detect regressions.

**Fix:** Add `_meta` to `MOCK_DATA_FULL` in `test_weekly.py`, consistent with the fixtures in `test_daily.py` and `test_monthly.py`:

```python
MOCK_DATA_FULL = {
    "etf": MOCK_ETF_OK,
    "crypto": MOCK_CRYPTO_OK,
    "pea": MOCK_PEA_OK,
    "macro": MOCK_MACRO_OK,
    "news": MOCK_NEWS_OK,
    "_meta": {
        "sources_ok": ["etf", "crypto", "pea", "macro", "news"],
        "sources_failed": [],
        "collected_at": "2026-05-09T06:00:00Z",
    },
}
```

---

_Reviewed: 2026-05-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
