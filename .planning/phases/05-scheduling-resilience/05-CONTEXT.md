# Phase 5: Scheduling & Resilience - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the complete pipeline to run autonomously on schedule and survive source failures:

1. **Cron triggers** — 3 system crontab entries (daily Mon–Sat, Sunday weekly, daily end-of-month check) invoke `python main.py --mode daily|weekly|monthly`
2. **Pipeline wiring** — Extend `main.py` to chain: `collect_all()` → `select_reports()` → `send_email()` + `write_tweet()` — currently `main.py` stops at `collect_all()`
3. **Graceful degradation end-to-end** — Outer try/except in `main.py` catches failures from reporters and delivery (collectors already degrade gracefully); partial run is logged, never aborts silently
4. **Smoke test** — A full end-to-end manual run confirms the system delivers email to the recipient inbox and produces the expected archive + tweet files

**Requirements covered:** SCHED-01, SCHED-02, SCHED-03, INFRA-02

**NOT in scope:** APScheduler daemon, auto-publish to Twitter/X (v2), monitoring dashboard (v2), systemd service files (could be added by user after).

</domain>

<decisions>
## Implementation Decisions

### Scheduler Mechanism

- **D-01:** Use **system cron** (not APScheduler). No long-running daemon — one Python process per run, killed when done. Verifiable with `crontab -l`.
- **D-02:** Install exactly **3 crontab entries**:
  ```
  # CryptoLascar — rapports financiers automatisés
  0 7 * * 1-6   cd /path/to/cryptolascar && python main.py --mode daily    # SCHED-01: lun–sam 07h00
  0 8 * * 0     cd /path/to/cryptolascar && python main.py --mode weekly   # SCHED-02: dimanche 08h00
  0 8 * * *     cd /path/to/cryptolascar && python main.py --mode monthly  # SCHED-03: dernier jour du mois 08h00
  ```
  The monthly entry fires every day at 08h00 — Python checks internally whether today is the last day of the month.
- **D-03:** **End-of-month detection** lives in Python, not in cron: `main.py --mode monthly` checks `datetime.date.today().day == calendar.monthrange(year, month)[1]` and exits 0 early (with a log entry) if not the last day.
- **D-04:** **VPS timezone**: set the system timezone to `Europe/Paris` (`timedatectl set-timezone Europe/Paris`). Cron fires at local time — no DST handling needed in Python, no UTC offset arithmetic.
- **D-05:** **`.env` loading**: cron entries use `cd /path/to/cryptolascar && python main.py --mode ...`. `config.py` calls `load_dotenv()` at startup — python-dotenv finds `.env` in the working directory automatically. No shell `source` or manual export needed.

### Pipeline Entry Point

- **D-06:** `main.py` is the **unified CLI entry point** — it receives `--mode daily|weekly|monthly` and runs the full pipeline: `collect_all()` → `select_reports()` → `send_email()` + `write_tweet()` + `archive_report()`.
- **D-07:** `scheduler/jobs.py` is **not needed** as a pipeline orchestrator. The `scheduler/` package can hold utility helpers only (e.g., an `is_last_day_of_month()` function used by `main.py`). No separate job classes or APScheduler dependency.
- **D-08:** `main.py` `--mode` argument routes to the correct pipeline branch:
  - `--mode daily` → generates daily report, sends email, writes tweet, archives
  - `--mode weekly` → generates weekly report, sends email, writes tweet (TWEET-02), archives
  - `--mode monthly` → checks last-day guard first; if last day: generates monthly report, sends email, no tweet (TWEET-04), archives

### Graceful Degradation (INFRA-02)

- **D-09:** Collectors already return partial dicts on failure — `collect_all()` never raises. This is Phase 2 behavior and carries forward unchanged.
- **D-10:** Report generation and delivery failures (re-raised from Phase 4 modules) are caught by an **outer try/except in main.py**. On exception: log the failure (report type, error message — never API key/SMTP password), write a `run_log` entry with `status="error"`, and exit with code 1. The process does NOT hang or re-raise to the cron daemon.
- **D-11:** Planner decides the exact degradation depth for reporter/LLM and email failures (e.g., whether to still archive even if email fails). The constraint: **a run must always produce a `run_log` entry** — success, partial, or error. No silent failures.

### Claude's Discretion

- **Graceful degradation depth for individual components** (LLM API down → stub report? Email SMTP fails → still write archive?) — deferred to planner. The constraint is INFRA-02: report is sent with gap noted, run never aborts silently.
- **Smoke test implementation** — planner decides whether to add a `--dry-run` flag or rely on a manual trigger with live APIs. The success criterion is: email arrives in inbox, archive written, tweet file written.
- **Crontab installation method** — planner may use `crontab -e` instructions in a setup script (e.g., `scheduler/install_cron.py`) or document it in README. Either is acceptable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Foundation
- `.planning/REQUIREMENTS.md` — SCHED-01, SCHED-02, SCHED-03, INFRA-02 define all scheduling and degradation requirements for this phase
- `.planning/ROADMAP.md §Phase 5` — Goal, success criteria (4 items), dependency on Phase 4
- `.planning/PROJECT.md` — Core constraints: zero hardcoded credentials, graceful degradation principle, APScheduler vs cron decision (now resolved: system cron)

### Phase 4 Output (what Phase 5 wires together)
- `delivery/email.py` — `send_email(config, subject, body_html, plain_text)` and `archive_report(report_type, date, content)` — Phase 5 calls these; failures re-raise
- `delivery/tweet.py` — `write_tweet(config, report_type, date, report_text)` — Phase 5 calls this; failures re-raise
- `.planning/phases/04-delivery-side-outputs/04-CONTEXT.md` — D-07 (email failure re-raises), D-12 (tweet failure re-raises) — Phase 5 is the outer catcher

### Phase 3 Output (report dispatch)
- `reporters/dispatch.py` — `select_reports(today, data, config) -> Dict[str, str]` — returns dict with keys `"daily"`, `"weekly"`, `"monthly"` based on current date; handles REPT-04 dual-emission (Monthly + Weekly on last Sunday of month)
- `reporters/base.py` — shows `synthesize_section()` pattern for LLM calls with graceful degradation — reference for how reporter failures should be handled

### Phase 1 Infrastructure (reuse)
- `config.py` — `get_config()` and `Config` dataclass — already has all SMTP, Anthropic, and path fields; `load_dotenv()` called here
- `logging_setup.py` — `setup_logging()` + `get_logger(name)` — established logging pattern
- `db/cache.py` — `init_db()`, `get_connection()` — SQLite init already called by main.py
- `main.py` — Current entry point (collect_all only); Phase 5 extends it with --mode argument and full pipeline

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main.py:collect_all()` — Already wired, already handles partial failures; Phase 5 adds the downstream chain after it
- `main.py:log_run()` — Writes to `run_log` SQLite table; Phase 5 uses this for all run outcomes (success, partial, error)
- `reporters/dispatch.py:select_reports()` — Already handles the REPT-04 dual-emission edge case (last Sunday of month); Phase 5 calls it directly
- `scheduler/is_last_day_of_month()` — Will be a small utility function Phase 5 creates for the monthly cron guard

### Established Patterns
- **Config dependency injection** — `get_config()` called once in `main.py`, passed as parameter to all functions — Phase 5 must follow this pattern
- **Never log credentials** — All error logs use report type / source name / error message only (T-02-22 / T-03-01 patterns)
- **Re-raise after logging** — Phase 4 delivery modules log then re-raise; `main.py` outer try/except is the terminal catch
- **TDD RED/GREEN** — All prior phases used it; Phase 5 should mock `subprocess`/`crontab` for installation tests, mock all delivery/reporter functions for pipeline integration tests

### Integration Points
- `main.py` — The critical integration point: needs `--mode` argument parsing (argparse), branches to correct pipeline per mode, wraps everything in outer try/except that writes to run_log
- `scheduler/__init__.py` — Empty stub; `scheduler/jobs.py` will NOT be created; a `scheduler/utils.py` with `is_last_day_of_month()` is the only addition needed

</code_context>

<specifics>
## Specific Ideas

- The 3 crontab entries should be documented in the project (README or a `scheduler/install_cron.sh` helper) with the exact lines to copy-paste, including the `cd /path/to/cryptolascar &&` prefix so python-dotenv finds `.env`.
- `crontab -l` must show the 3 entries as proof — this is explicit in SCHED-01's success criterion: "verified with `crontab -l` (or equivalent)".
- The monthly cron guard: `if not is_last_day_of_month(): logger.info("Not last day of month — skipping monthly report"); sys.exit(0)` — clean, testable, no shell logic.
- The Sunday `--mode weekly` at 08h00 (not 07h00) — important: `0 8 * * 0` not `0 7 * * 0`.

</specifics>

<deferred>
## Deferred Ideas

- **APScheduler daemon + systemd service** — APScheduler was considered but rejected in favor of system cron for simplicity. Could be revisited in v2 if the VPS needs managed restarts.
- **`--dry-run` flag** — Planner may or may not add this for smoke testing. Not a locked decision.
- **Email retry on transient SMTP failure** — Was deferred from Phase 4 (04-CONTEXT.md). Still deferred to a future resilience phase or v2.
- **Monitoring / alerting on run failures** — v2 requirement (MONIT-01, MONIT-02). Not in Phase 5 scope.

</deferred>

---

*Phase: 5-Scheduling & Resilience*
*Context gathered: 2026-05-10*
