# Phase 5: Scheduling & Resilience - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-10
**Phase:** 5-Scheduling & Resilience
**Areas discussed:** Scheduler mechanism

---

## Scheduler mechanism

### Q1: Scheduler implementation

| Option | Description | Selected |
|--------|-------------|----------|
| System cron | 3 crontab entries; one process per run; verifiable with `crontab -l`; end-of-month detection via Python wrapper | ✓ |
| APScheduler | Long-running Python daemon; manages complex schedules in pure Python; requires systemd/nohup | |
| Hybrid: cron launches Python, Python decides | Single daily cron; Python decides which reports to run based on date/weekday | |

**User's choice:** System cron
**Notes:** Simpler, standard VPS approach, no daemon to manage.

---

### Q2: End-of-month trigger mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Cron fires daily, Python checks internally | `0 8 * * *`; Python checks `calendar.monthrange()` and exits early if not last day | ✓ |
| Shell wrapper script | Cron calls a shell script that evaluates date before calling Python | |
| Pre-computed cron per month | 12 specific cron entries; overly complex | |

**User's choice:** Cron fires daily, Python checks internally
**Notes:** Keeps date logic in Python, no shell complexity.

---

### Q3: Number of crontab entries

| Option | Description | Selected |
|--------|-------------|----------|
| 3 entries: daily Mon–Sat, Sunday, daily end-of-month check | Clean separation matching REQUIREMENTS.md exactly | ✓ |
| 2 entries: Mon–Sat daily + Sunday (monthly piggybacks) | Fewer lines but blurs report type separation | |
| 1 entry: single daily cron, Python does everything | Simplest crontab but Sunday/monthly would fire at 07h00 instead of 08h00 | |

**User's choice:** 3 entries
**Notes:** Matches SCHED-01, SCHED-02, SCHED-03 exactly.

---

### Q4: Cron invocation command

| Option | Description | Selected |
|--------|-------------|----------|
| `python main.py --mode daily\|weekly\|monthly` | main.py is unified entry point; clean, testable | ✓ |
| Dedicated runner scripts (run_daily.py, etc.) | More files but maximum isolation | |
| `scheduler/jobs.py` as CLI | jobs.py is both library and CLI; keeps main.py data-only | |

**User's choice:** `python main.py --mode daily|weekly|monthly`
**Notes:** main.py becomes the unified entry point for all report modes.

---

### Q5: Timezone handling

| Option | Description | Selected |
|--------|-------------|----------|
| Set VPS timezone to Europe/Paris | `timedatectl set-timezone Europe/Paris`; cron fires at local time; no DST gymnastics | ✓ |
| Add TZ=Europe/Paris to crontab | Works on most Linux without touching system clock | |
| Keep UTC cron, convert in Python | Fragile; requires manual crontab edit twice a year for DST | |

**User's choice:** Set VPS timezone to Europe/Paris
**Notes:** Right long-term setup for a French-market system.

---

### Q6: .env loading in cron

| Option | Description | Selected |
|--------|-------------|----------|
| python-dotenv loads automatically via `cd /path && python main.py` | `load_dotenv()` in config.py finds .env in working directory | ✓ |
| Cron sources .env explicitly | `source .env &&` — fragile with quoted values and multiline vars | |
| Shell wrapper that exports vars | More control but adds a shell layer to maintain | |

**User's choice:** python-dotenv loads automatically
**Notes:** Already the established pattern; no changes needed.

---

### Q7: Role of scheduler/jobs.py

| Option | Description | Selected |
|--------|-------------|----------|
| main.py is only entry point — scheduler/jobs.py not needed | scheduler/ can hold utility helpers only (e.g., is_last_day_of_month()) | ✓ |
| scheduler/jobs.py contains pipeline logic, main.py calls it | Clean separation: main.py is CLI adapter, jobs.py is orchestrator | |
| You decide | Leave split to planner | |

**User's choice:** main.py is only entry point
**Notes:** scheduler/jobs.py not created; a scheduler/utils.py with is_last_day_of_month() is sufficient.

---

## Areas not discussed (user-deferred to planner)

- **Pipeline entry point wiring** — How main.py is extended with the full chain (collect → dispatch → email + tweet + archive)
- **Graceful degradation depth** — What happens when LLM/Claude is down during report generation; whether archive is still written if email fails
- **Smoke test strategy** — Whether to add --dry-run flag or rely on a live manual trigger

## Claude's Discretion

- Exact degradation behavior for individual components (LLM down, SMTP failure) — planner decides
- Smoke test implementation (--dry-run vs manual trigger) — planner decides
- Crontab installation method (install script vs README documentation) — planner decides

## Deferred Ideas

- APScheduler daemon + systemd service — rejected for v1, could be revisited in v2
- Email retry on transient SMTP failure — previously deferred from Phase 4, still deferred
- Monitoring/alerting on run failures — v2 requirement (MONIT-01, MONIT-02)
