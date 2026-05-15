# Roadmap: CryptoLascar

## Milestones

- ✅ **v1.0 Core Pipeline** — Phases 1–5 (shipped 2026-05-13)
- ✅ **v1.1 Rapports Enrichis** — Phases 6–8 (shipped 2026-05-15)
- 📋 **v1.2** — Phases 9+ (planning next)

## Phases

<details>
<summary>✅ v1.0 Core Pipeline (Phases 1–5) — SHIPPED 2026-05-13</summary>

- [x] **Phase 1: Foundation** (3/3 plans) — SQLite cache, .env config, logging structuré — completed 2026-05-09
- [x] **Phase 2: Data Pipeline** (6/6 plans) — ETF, crypto, PEA, macro, news collectors — completed 2026-05-11
- [x] **Phase 3: Report Generation** (4/4 plans) — daily/weekly/monthly + Claude synthesis — completed 2026-05-12
- [x] **Phase 4: Delivery & Side Outputs** (2/2 plans) — Gmail SMTP, tweet files, Markdown archive — completed 2026-05-12
- [x] **Phase 5: Scheduling & Resilience** (2/2 plans) — cron installé, smoke test, graceful degradation — completed 2026-05-13

*17 plans total | 121 tests | Archive: [milestones/v1.0-ROADMAP.md](milestones/)*

</details>

<details>
<summary>✅ v1.1 Rapports Enrichis (Phases 6–8) — SHIPPED 2026-05-15</summary>

- [x] **Phase 6: Chart Generation** (4/4 plans) — matplotlib charts/ package: ETF bars, crypto sparklines, F&G gauge, PEA table — completed 2026-05-15
- [x] **Phase 7: Template Redesign & Integration** (4/4 plans) — dark-mode Bloomberg HTML template, ReportOutput, all 3 reporters wired — completed 2026-05-15
- [x] **Phase 8: Close Gaps** (3/3 plans) — data-contract fixes CHART-01/02/04, CHART-03 guard, sparkline endpoint, boundary tests, Phase 6 VERIFICATION.md — completed 2026-05-15

*11 plans total | 292 tests | 70 files, +10,789 LOC | Archive: [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)*

</details>

### 📋 v1.2 (Planning Next)

Run `/gsd-new-milestone` to define scope, requirements, and roadmap for the next milestone.

Candidates from tech debt / deferred backlog:
- CR-02: Markdown table rendering in weekly/monthly HTML (pipe text → real HTML tables)
- IN-01: Consolidate `_build_chart_panel` / `_sections_to_html` duplication across 3 reporters
- SCHED-03: Resolve crontab offset divergence
- DIST-01: Auto-publish tweets via Tweepy (deferred from v1.0)
- MONIT-01: Minimal web dashboard for run status
- DATA-ADV-01/02/03: Reddit/Twitter sentiment, Google Trends

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 3/3 | Complete | 2026-05-09 |
| 2. Data Pipeline | v1.0 | 6/6 | Complete | 2026-05-11 |
| 3. Report Generation | v1.0 | 4/4 | Complete | 2026-05-12 |
| 4. Delivery & Side Outputs | v1.0 | 2/2 | Complete | 2026-05-12 |
| 5. Scheduling & Resilience | v1.0 | 2/2 | Complete | 2026-05-13 |
| 6. Chart Generation | v1.1 | 4/4 | Complete | 2026-05-15 |
| 7. Template Redesign & Integration | v1.1 | 4/4 | Complete | 2026-05-15 |
| 8. Close Gaps | v1.1 | 3/3 | Complete | 2026-05-15 |
| 9. TBD | v1.2 | 0/? | Not started | - |
