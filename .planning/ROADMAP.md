# Roadmap: CryptoLascar — Système d'Analyse Financière Automatisé

## Overview

Five phases build the system bottom-up: skeleton first, then data ingestion, then report generation with LLM synthesis, then delivery and side outputs (email + tweet files), and finally the scheduler that wires everything into a continuously running autonomous pipeline. Each phase delivers a fully testable vertical slice.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Project skeleton, .env config, SQLite cache, structured logging, and VPS-ready Python structure
- [ ] **Phase 2: Data Pipeline** - All data collectors (ETFs, crypto, PEA, macro, news/scraping) with rate limiting and PEA eligibility check
- [ ] **Phase 3: Report Generation** - Daily, Weekly, and Monthly report builders with Claude LLM synthesis and HTML/text formatting
- [ ] **Phase 4: Delivery & Side Outputs** - Gmail SMTP email dispatch, tweet file generation, and Markdown archiving
- [ ] **Phase 5: Scheduling & Resilience** - Cron/APScheduler triggers for all 3 report types, graceful degradation end-to-end, and full pipeline smoke test

## Phase Details

### Phase 1: Foundation
**Goal**: A running Python project with all configuration loaded from .env, SQLite initialized, structured logging active, and the directory layout ready for every downstream module
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-03, INFRA-04, STOR-03, STOR-04
**Success Criteria** (what must be TRUE):
  1. `python main.py` (or equivalent entry point) runs without error on a clean VPS with Python 3.11+
  2. All required .env variables are documented in .env.example and loaded at startup; missing variables raise a clear error with the variable name
  3. SQLite database file is created automatically on first run with the correct schema
  4. A log entry with timestamp and run status is written to the log file for every execution attempt
  5. No credentials or secrets appear anywhere in source code — only in .env
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Arborescence du projet, __init__.py des packages, requirements.txt, .gitignore
- [x] 01-02-PLAN.md — .env.example documenté, config.py avec validation des variables obligatoires
- [x] 01-03-PLAN.md — db/cache.py (SQLite init + schema), logging_setup.py, main.py (entry point)

### Phase 2: Data Pipeline
**Goal**: Every data source is collected reliably, rate limits are respected, historical data is cached in SQLite, and PEA eligibility changes trigger an alert flag
**Depends on**: Phase 1
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08
**Success Criteria** (what must be TRUE):
  1. Running the data collection module produces a populated data dict (or equivalent structure) covering ETFs, crypto, macro, and news with no fatal exception
  2. A repeated call within the cache TTL returns data from SQLite without hitting the external API (verified via log or counter)
  3. If an API is unavailable (mocked or real), the collector returns a partial result with the gap noted rather than raising an unhandled exception
  4. The PEA eligibility check runs and logs either "no change" or a detected status change against the AMF/Euronext reference
  5. API call sequences include the required sleep delays; no rate-limit ban is triggered during a full collection run
**Plans**: 6 plans

Plans:
- [x] 02-01-PLAN.md — collectors/etf.py — ETF price collection (SPY, QQQ, IWDA.AS, EIMI.AS, CSPX.AS) via yfinance + Alpha Vantage fallback, 4h cache
- [ ] 02-02-PLAN.md — collectors/crypto.py — Crypto prices (8 coins) via CoinGecko + Fear & Greed via Alternative.me, 1h cache
- [ ] 02-03-PLAN.md — collectors/pea.py — PEA France prices (^FCHI, ^SBF120, CW8.PA, PAEEM.PA, PANX.PA) + static eligibility check + change detection, 4h cache
- [ ] 02-04-PLAN.md — collectors/macro.py — FRED API macro indicators (DGS10, DGS2, CPIAUCSL, M2SL), 24h cache
- [ ] 02-05-PLAN.md — collectors/news.py — NewsAPI + BS4 scraping (CoinDesk, CoinTelegraph, Boursorama, AMF), 2h cache, max 35 headlines
- [ ] 02-06-PLAN.md — Integration: collect_all() in main.py wires all 5 collectors, integration tests, run_log updated

### Phase 3: Report Generation
**Goal**: All three report types (Daily, Weekly, Monthly) are generated as structured documents with Claude-synthesized narrative sections and correct section counts/word targets
**Depends on**: Phase 2
**Requirements**: REPT-01, REPT-02, REPT-03, REPT-04, LLM-01, LLM-02
**Success Criteria** (what must be TRUE):
  1. Running the daily report builder with live or fixture data produces a ~300-word, 6-section document (Macro Snapshot, ETF Radar, Crypto Pulse, PEA Alert, News Feed, One Signal)
  2. Running the weekly report builder produces a ~800-word, 7-section document with data tables populated
  3. Running the monthly report builder produces a ~2000-word, 7-section document with data tables populated
  4. Narrative sections in all reports are generated by the Claude API; the active model is read from ANTHROPIC_MODEL in .env and overridable without code changes
  5. When the last day of the month falls on a Sunday, both the Monthly Close and Weekly Wrap are generated as separate documents in the same run (REPT-04)
**Plans**: TBD

### Phase 4: Delivery & Side Outputs
**Goal**: Reports are sent as formatted HTML emails via Gmail SMTP and tweet files are written to /tweets/; every report is also archived as Markdown
**Depends on**: Phase 3
**Requirements**: REPT-05, MAIL-01, MAIL-02, MAIL-03, MAIL-04, TWEET-01, TWEET-02, TWEET-03, TWEET-04, STOR-01, STOR-02
**Success Criteria** (what must be TRUE):
  1. A daily report email arrives in the recipient inbox rendered as HTML with a plain-text fallback; subject line matches `[DAILY] ...` format
  2. Weekly and Monthly emails arrive with correct `[WEEKLY WRAP]` and `[MONTHLY CLOSE]` subject prefixes and the disclaimer footer
  3. RECIPIENT_LIST in .env controls who receives the emails; changing it requires no code modification
  4. A tweet file `/tweets/YYYY-MM-DD.txt` is written for each daily run (Mon-Sat) and each Sunday Weekly Wrap run; no tweet file is written for Monthly Close
  5. Each tweet file contains 240-270 characters, in French, analyst tone, with 3-4 hashtags from the defined pool
  6. Each report is archived as a Markdown file in the correct subdirectory (`/reports/daily/`, `/reports/weekly/`, `/reports/monthly/`)
**UI hint**: no
**Plans**: TBD

### Phase 5: Scheduling & Resilience
**Goal**: The full pipeline runs autonomously on schedule (3 cron triggers), degrades gracefully when any source fails, and a successful end-to-end smoke test confirms the system is production-ready
**Depends on**: Phase 4
**Requirements**: SCHED-01, SCHED-02, SCHED-03, INFRA-02
**Success Criteria** (what must be TRUE):
  1. Cron entries (or APScheduler config) for daily Mon-Sat 07h00 CET, Sunday 08h00 CET, and end-of-month 08h00 CET are installed and verified with `crontab -l` (or equivalent)
  2. A full end-to-end run (triggered manually or via cron) completes without unhandled exceptions and delivers the email to the recipient inbox
  3. When one data source is deliberately taken offline (e.g., invalid API key), the run completes, a partial report is sent, and the log entry notes the failed source with the gap
  4. The system recovers automatically the next scheduled run without manual intervention after a transient failure
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Complete | 2026-05-09 |
| 2. Data Pipeline | 1/6 | Executing | - |
| 3. Report Generation | 0/TBD | Not started | - |
| 4. Delivery & Side Outputs | 0/TBD | Not started | - |
| 5. Scheduling & Resilience | 0/TBD | Not started | - |
