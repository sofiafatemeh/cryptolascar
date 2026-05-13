---
phase: 05-scheduling-resilience
reviewed: 2026-05-13T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - scheduler/utils.py
  - scheduler/install_cron.sh
  - tests/test_main_pipeline.py
  - main.py
  - delivery/email.py
  - delivery/tweet.py
findings:
  critical: 2
  warning: 4
  info: 2
  total: 8
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-05-13T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

The phase 5 implementation wires the full pipeline correctly and the scheduler guard logic
(is_last_day_of_month) is sound. The test suite covers all ten documented scenarios.
However, two blockers were found: a resource leak in the SMTP_SSL path (connection not closed
on exception), and a scheduling collision where `--mode weekly` and `--mode monthly` both fire
at the exact same minute on the last Sunday of the month, causing duplicate weekly report
delivery. Four warnings cover silent locale fallback, wasteful daily data collection for the
monthly mode, an unused dead-code variable in the tests, and an idempotency flaw in the cron
installer that can falsely declare "already installed".

---

## Critical Issues

### CR-01: SMTP_SSL connection leaked on exception

**File:** `delivery/email.py:179-204`

**Issue:** The `SMTP_SSL` branch constructs the connection with `ctx = smtplib.SMTP_SSL(...)` outside
a context manager. If `ctx.login()` or `ctx.sendmail()` raises, the `except Exception` block
at line 198 catches and re-raises the error, but `ctx.quit()` (line 184) is never reached.
The underlying TCP socket is not closed until the object is garbage-collected. In contrast,
the STARTTLS branch (port != 465) correctly uses `with smtplib.SMTP(...) as smtp:`, which
calls `smtp.__exit__` on any exit path.

`smtplib.SMTP_SSL` inherits `__enter__`/`__exit__` from `smtplib.SMTP` so the fix is
trivial — use the same context-manager pattern already used for the STARTTLS branch.

**Fix:**
```python
# Replace lines 180-184:
if config.smtp_port == 465:
    with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) as ctx:
        ctx.login(config.smtp_user, config.smtp_password)
        ctx.sendmail(config.smtp_user, config.recipient_list, msg.as_string())
```

---

### CR-02: Duplicate weekly report delivery on last Sunday of month (cron race)

**File:** `scheduler/install_cron.sh:12-14`

**Issue:** Two independent cron entries fire at the exact same wall-clock minute on the last
Sunday of any month:

```
0 8 * * 0     ...  --mode weekly    # every Sunday at 08:00
0 8 * * *     ...  --mode monthly   # every day at 08:00
```

On the last Sunday of a month, `--mode monthly` runs and `select_reports()` (via REPT-04)
returns **both** `"monthly"` and `"weekly"` keys — so it sends both emails and tweets.
Simultaneously, `--mode weekly` fires and independently runs the same full weekly pipeline.
The result is that on the last Sunday of the month recipients receive two weekly-wrap
emails for the same date.

The fix is to offset the monthly cron by one minute so it cannot coincide with the weekly:

**Fix:**
```bash
CRON_MONTHLY="1 8 * * *     cd $PROJECT_DIR && $PYTHON main.py --mode monthly"
```

A single-minute offset is sufficient: when `--mode monthly` runs at 08:01 and it is the
last Sunday of the month, REPT-04 will emit the weekly report. The `--mode weekly` at 08:00
should then be suppressed. The cleaner architectural fix is to make `select_reports` aware
of whether REPT-04 already ran, or to exclude the last-Sunday-of-month from `--mode weekly`
in cron. The one-minute offset is a minimal safe fix that avoids duplicate delivery without
changing the pipeline logic.

---

## Warnings

### WR-01: Silent locale fallback produces wrong-language email subject for monthly reports

**File:** `main.py:219-224`

**Issue:** When the system does not have `fr_FR.UTF-8` installed, `locale.setlocale()` raises
`locale.Error`, which is silently swallowed by `except locale.Error: pass`. The code then
calls `today.strftime("%B")` in whatever locale is active (typically `C` / `en_US`). The
resulting monthly email subject reads "[MONTHLY CLOSE] Bilan du mois **May** 2026" instead
of "mai 2026". There is no log warning, so this failure is invisible in production.

**Fix:**
```python
try:
    locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
except locale.Error:
    logger.warning(
        "fr_FR.UTF-8 locale not available — monthly email subject will use English month name. "
        "Install it with: sudo locale-gen fr_FR.UTF-8"
    )
```

Additionally, `locale.setlocale` is a process-global side effect. In the current single-process
cron context this is harmless, but it is worth noting.

---

### WR-02: `collect_all()` runs wastefully for every daily `--mode monthly` invocation

**File:** `main.py:182-207`

**Issue:** Step 6 (collect_all — all five collectors) executes unconditionally before Step 7
(the monthly guard at line 202). On the 30 or so non-last days of each month, the process
contacts all five external APIs (yfinance, CoinGecko, macro, news, PEA) for no purpose —
every collected result is discarded at the guard check. Given rate-limit constraints
documented in CLAUDE.md and the free-tier APIs in use, this is an unnecessary daily drain
on API quotas.

**Fix:** Move the monthly guard check to immediately after argparse (before `collect_all`):

```python
# After Step 3 (setup_logging), add:
today = datetime.date.today()
if mode == "monthly" and not is_last_day_of_month(today):
    logger.info("Mode monthly — %s is not the last day — skipping.", today.isoformat())
    # init_db still needed to write the skipped log entry
    init_db(config.db_path)
    log_run(config.db_path, "skipped", "", "", "")
    return 0
```

---

### WR-03: Idempotency check in `install_cron.sh` is too broad — may falsely skip installation

**File:** `scheduler/install_cron.sh:17`

**Issue:** The already-installed check greps the entire crontab for the project directory path:

```bash
if crontab -l 2>/dev/null | grep -q "$PROJECT_DIR"; then
```

This will match any crontab entry that contains the project path as a substring — including
unrelated entries the user may have added manually (e.g., a custom backup script under the
same parent directory). If any such entry exists, the three CryptoLascar crontab entries are
never installed and the script silently exits 0, giving a false "already installed" message.

**Fix:** Grep for a CryptoLascar-specific string that can only appear in the installed entries:

```bash
if crontab -l 2>/dev/null | grep -q "main.py --mode daily"; then
```

This is specific to the CryptoLascar cron entries without over-constraining the path.

---

### WR-04: `_base_patches()` return value is built and immediately discarded in T1

**File:** `tests/test_main_pipeline.py:115-120`

**Issue:** `test_mode_daily_success` calls `_base_patches()` and stores the result in `patches`
(lines 115-120), then never uses `patches`. The test immediately opens its own `with patch(...)`
block that manually re-patches every symbol. The `_base_patches` call is dead code — it wastes
computation and creates a maintenance trap (if someone updates `_base_patches` expecting T1 to
use it, T1 will still use its own hard-coded patches).

No other test uses `_base_patches` either: `grep` confirms `_base_patches` is defined at
line 80 and called only at line 115. The function itself is never actually applied.

**Fix:** Either delete the `patches = _base_patches(...)` call on lines 115-120 and the
`_base_patches` function entirely (since no test applies it), or refactor all tests to actually
use it via `unittest.mock.patch.multiple(**patches)`:

```python
# Option A: delete dead code
# Remove lines 115-120 entirely; the subsequent `with patch(...)` block is the real setup.

# Option B: use _base_patches as intended
with patch.multiple("main", **_base_patches(mock_config, daily_data, ...)):
    result = main(["--mode", "daily"])
```

---

## Info

### IN-01: `import locale` placed inside a hot loop

**File:** `main.py:219`

**Issue:** `import locale` appears inside the `for report_type, report_text in reports.items()`
loop, inside an `if report_type == "monthly":` guard. Python caches imports after the first
execution, so this is not a correctness bug, but it is an unconventional pattern that
contradicts PEP 8 (all imports at the top of the file). It also makes the locale dependency
non-obvious when reading the module's imports.

**Fix:** Move `import locale` to the top-level import section of `main.py` alongside the
other standard library imports.

---

### IN-02: `scheduler/utils.py` docstring references a non-existent deliverable

**File:** `scheduler/utils.py:4`

**Issue:** Line 4 reads `"D-07: scheduler/jobs.py n'est pas créé"`. This is a planning
annotation from D-07 of the context document, not user-facing documentation. It is noise
in the module docstring and will confuse anyone reading the source without access to the
planning artifacts.

**Fix:** Replace with a simple module docstring:

```python
"""scheduler/utils.py — Calendar utilities for the CryptoLascar scheduler."""
```

---

_Reviewed: 2026-05-13T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
