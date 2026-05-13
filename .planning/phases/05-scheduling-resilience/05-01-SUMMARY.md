---
phase: 05-scheduling-resilience
plan: "01"
subsystem: pipeline-wiring
tags: [argparse, scheduler, pipeline, tdd, monthly-guard, graceful-degradation]
dependency_graph:
  requires: [04-01, 04-02, 03-01]
  provides: [scheduler/utils.py, main.py --mode pipeline]
  affects: [main.py, scheduler/utils.py, tests/test_main_pipeline.py]
tech_stack:
  added: [argparse, calendar, locale]
  patterns: [tdd-red-green, argv-injection-testability, outer-try-except, monthly-guard]
key_files:
  created:
    - scheduler/utils.py
    - tests/test_main_pipeline.py
    - tests/test_scheduler_utils.py
  modified:
    - main.py
decisions:
  - "argv=None parameter in main() allows tests to inject args without subprocess"
  - "Monthly guard (D-03) placed after collect_all() so data is still available but select_reports is skipped"
  - "Outer try/except wraps only reporter/delivery block, not collect_all() (D-09)"
  - "locale fallback: fr_FR.UTF-8 attempted, English fallback if unavailable"
  - "D-11 enforced: every code path (success/partial/skipped/error) writes exactly one run_log entry"
metrics:
  duration: "~7 minutes"
  completed: "2026-05-13"
  tasks_completed: 3
  files_changed: 4
---

# Phase 5 Plan 01: --mode Pipeline Wiring + scheduler/utils.py Summary

**One-liner:** Argparse --mode CLI wiring main.py to full collect→report→email+tweet+archive pipeline with monthly end-of-month guard and outer try/except guaranteeing a run_log entry on every execution path.

## What Was Implemented

### scheduler/utils.py (Task 1)
Single exported function `is_last_day_of_month(today: datetime.date) -> bool` using `calendar.monthrange()` for correct handling of all month lengths including leap years. Located in `scheduler/` per D-07 (no `scheduler/jobs.py` needed).

### main.py Extension (Task 2)
Extended `main()` with:
- **`argv: list[str] | None = None` parameter** for test injection (argparse testability pattern)
- **`--mode daily|weekly|monthly` argparse** (required, exit 2 if missing/invalid)
- **Full pipeline chain**: `collect_all()` → `is_last_day_of_month()` guard → `select_reports()` → loop: `archive_report()` + `send_email()` + `write_tweet()`
- **Monthly guard (D-03)**: exits 0 with `status="skipped"` on non-last-day of month (before select_reports call)
- **REPT-04 support**: iterates all keys from `select_reports()` — supports dual monthly+weekly emission
- **Outer try/except (D-10)**: catches any reporter/delivery exception, writes `status="error"`, exits 1
- **T-05-01 compliance**: `err_msg` contains only `mode` and `str(exc)`, never smtp_password or api_key
- **D-11 compliance**: every code path writes exactly one `run_log` entry
- **Locale handling**: attempts `fr_FR.UTF-8` for French month name in monthly email subject, falls back gracefully to English

### tests/test_main_pipeline.py (Task 3)
10 integration tests with full mock isolation (all I/O mocked via `unittest.mock.patch`):

| Test | Description |
|------|-------------|
| T1 `test_mode_daily_success` | Full daily pipeline, log_run status="success" |
| T2 `test_mode_weekly_success` | Weekly pipeline, send_email called with report_type="weekly" |
| T3 `test_mode_monthly_last_day` | Monthly pipeline on last day, send_email report_type="monthly" |
| T4 `test_mode_monthly_skip_non_last_day` | Early exit, select_reports NOT called, status="skipped" |
| T5 `test_mode_daily_send_email_failure` | SMTPException → returns 1, status="error" |
| T6 `test_mode_daily_archive_failure` | OSError → returns 1, status="error" |
| T7 `test_rept04_dual_report` | REPT-04: 2 send_email calls, 1 log_run |
| T8 `test_partial_collect` | Partial sources, send_email still called, sources_failed="news" in log_run |
| T9 `test_missing_mode_exits_2` | Missing --mode → SystemExit(2) |
| T10 `test_invalid_mode_exits_2` | Invalid --mode value → SystemExit(2) |

## Key Patterns

1. **argv injection for testability**: `main(argv=["--mode", "daily"])` avoids subprocess overhead
2. **Monthly guard position**: after `collect_all()` (data collected) but before `select_reports()` (no expensive LLM calls on skip)
3. **Outer try/except scope**: wraps only `select_reports` + delivery loop, not `collect_all()` (which never raises per D-09)
4. **Single log_run per run (D-11)**: enforced by structure — success path has one call, early-exit guard has one call, except block has one call

## Test Count

- **Before plan**: 103 tests (103 passed)
- **Task 1 adds**: 8 tests (scheduler/utils.py)
- **Task 3 adds**: 10 tests (pipeline integration)
- **After plan**: 121 tests (121 passed, 0 failures, 0 regressions)

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 8e3ba34 | test | RED phase — failing tests for scheduler/utils.py |
| 591640d | feat | GREEN phase — implement scheduler/utils.py |
| c5612f4 | feat | Extend main.py with --mode argparse and full pipeline |
| 74dc043 | test | 10 pipeline integration tests for main.py --mode branches |

## Deviations from Plan

None — plan executed exactly as written.

The verification assertion in the plan used `"'error'"` (single quotes) to match the source, but main.py uses `"error"` (double quotes). This is a cosmetic discrepancy in the plan's inline verification snippet only — the actual implementation and tests correctly use `"error"` as the status string in `log_run()`. All 10 must-have truths and all 5 artifacts are delivered as specified.

## Threat Surface Scan

No new security-relevant surface introduced beyond what the plan's threat model covers:
- T-05-01: verified — `err_msg` only contains `mode` and `str(exc)`, never credentials
- T-05-04: verified — every code path writes exactly one `run_log` entry

## Self-Check: PASSED

- [x] `scheduler/utils.py` exists and importable
- [x] `main.py` has argparse, all 4 pipeline functions wired
- [x] `tests/test_main_pipeline.py` exists with 10 test functions
- [x] All commits exist: 8e3ba34, 591640d, c5612f4, 74dc043
- [x] Full suite: 121 passed, 0 failed
