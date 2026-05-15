# Project Retrospective — CryptoLascar

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v1.0 — Core Pipeline

**Shipped:** 2026-05-13
**Phases:** 5 | **Plans:** 17

### What Was Built

- Complete autonomous financial pipeline: 5 data collectors (ETF, crypto, PEA, macro, news)
- Daily/weekly/monthly report generation with Claude narrative synthesis
- Gmail SMTP email delivery + tweet file generation + Markdown archiving
- Cron scheduling with graceful degradation guarantees
- SQLite cache with TTL, structured logging, .env configuration

### What Worked

- Wave-based plan execution prevented dependency issues — never ran a plan on a broken dependency
- Graceful degradation as a first-class constraint (not afterthought) eliminated a whole class of production bugs
- SQLite standard library instead of SQLAlchemy — right call, zero overhead for this scale

### What Was Inefficient

- No boundary/integration tests between collectors and reporters — led directly to the v1.1 gap audit finding

### Patterns Established

- `load_dotenv(override=False)` — system env vars take priority over .env (VPS security)
- `_require()` exposes only the variable name in ValueError, never its value
- `time.sleep()` after successful API call (not before) to avoid unnecessary delays on first call

### Key Lessons

1. Test the full data flow, not just unit behavior — mocking at the boundary doesn't verify integration
2. Graceful degradation must be tested with real failure injection, not just "design intent"

---

## Milestone: v1.1 — Rapports Enrichis

**Shipped:** 2026-05-15
**Phases:** 3 (6, 7, 8) | **Plans:** 11 | **2 days**

### What Was Built

- `charts/` package with 4 generators (ETF bar chart, crypto sparklines, Fear & Greed gauge, PEA colored table) — all `Optional[str]` with CHART-05 fallback
- Dark-mode Bloomberg-style HTML email template — responsive, mobile-friendly, orange/green accents
- All 3 reporters refactored to `ReportOutput(html_body, plain_text)`, wired via `reporters/dispatch.py`
- Phase 8 (inserted after audit): data-contract transform layer, 7-day sparkline endpoint, CHART-03 None-guard, 11 boundary integration tests, Phase 6 VERIFICATION.md

### What Worked

- Milestone audit (`/gsd-audit-milestone`) caught 3 broken chart paths before shipping — prevented production regression
- Inserting Phase 8 inline (via `/gsd-phase --insert`) was clean: no disruption to existing phase numbering, clear dependency chain
- Data transforms in `_build_chart_panel` (reporters layer), not in collectors — kept collectors agnostic, made testing much simpler
- 11 boundary tests in `test_chart_boundary.py` crossing real collector→chart interface without mocks — high signal, found nothing new (confirming Phase 8 fixes were correct)

### What Was Inefficient

- The test suite for reporters mocked all chart generators with `return_value=None` — this validated only the CHART-05 fallback path and masked all 3 integration blockers for the entire Phase 6+7 execution window
- `_build_chart_panel()` and `_sections_to_html()` duplicated verbatim across daily/weekly/monthly reporters — any future change requires triple application; should have gone into `reporters/base.py` from Phase 7
- Phase 6 VERIFICATION.md was missing at Phase 7 handoff — the audit protocol caught it but it caused an extra inserted phase

### Patterns Established

- **Boundary tests are mandatory** when a new module (charts/) receives data from an existing module (collectors/). The boundary test must use real output shapes, not mocks.
- **VERIFICATION.md must be written at phase completion** — not deferred to the next phase. Missing verification enabled the data-contract bugs to go undetected across Phase 6 and 7.
- **`or {}` after `.get()` when the stored value may be `None`**: `data.get('key', {})` returns `None` if the stored value is `None` (not the `{}` default). Use `(data.get('key') or {})` to guard against this.
- **Separate cache entry for sparkline data** (TTL 1h) from main crypto cache (TTL 15min) — different freshness requirements deserve different cache keys

### Key Lessons

1. **Mocking a module's return value at the call site validates the fallback path only** — it never verifies that real data flows correctly through the module. For boundary testing, inject real-shaped data and let the function execute.
2. **Audit before closing a milestone** — `/gsd-audit-milestone` found 3 production-broken chart paths that 292 passing tests missed entirely. The audit is not bureaucracy; it's the last integration check.
3. **Collector output shapes and chart generator input shapes are separate contracts** — establish both explicitly in the phase plan and write a boundary test before marking the integration complete.
4. **Phase 8 pattern**: when an audit finds integration gaps, inserting a dedicated closure phase is cleaner than patching mid-existing-phase. The insert is one command; the work stays atomic.

### Cost Observations

- Model: claude-sonnet-4-6 exclusively
- Sessions: 2–3 sessions (Phase 6–7 in one session, Phase 8 in another)
- Notable: Wave-based execution with parallel plan dispatch (Phases 6+7 each had wave-2 plans run in parallel) reduced wall time significantly

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 5 | 17 | Established baseline — collectors, reporters, delivery, scheduling |
| v1.1 | 3 | 11 | Added visual layer; audit step revealed integration gap class; Phase 8 pattern established |

### Cumulative Quality

| Milestone | Tests | LOC (approx) | Key Addition |
|-----------|-------|--------------|--------------|
| v1.0 | 121 | ~2,400 | Full pipeline + graceful degradation |
| v1.1 | 292 | ~12,000+ | Charts + template + boundary tests |

### Top Lessons (Verified Across Milestones)

1. **Boundary testing across module interfaces is mandatory** — pure unit tests with mocks never catch data-contract bugs
2. **Graceful degradation must be a constraint from day one** — retrofitting it costs more than building it in
3. **VERIFICATION.md at phase completion, not deferred** — verification gaps compound across phases
