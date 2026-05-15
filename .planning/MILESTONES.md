# Milestones — CryptoLascar

## v1.0 — Core Pipeline (Completed 2026-05-13)

**Goal:** Système d'analyse financière automatisé fonctionnel en production.

**Delivered:**
- Phase 1: Foundation (config .env, SQLite, logging structuré)
- Phase 2: Data Pipeline (ETFs, crypto, PEA, macro, news — 5 collectors)
- Phase 3: Report Generation (daily/weekly/monthly + Claude synthesis)
- Phase 4: Delivery (Gmail SMTP, tweet files, Markdown archive)
- Phase 5: Scheduling & Resilience (cron installé, smoke test OK)

**Stats:** 5 phases | 17 plans | 121 tests | Email livré en production

---

## v1.1 — Rapports Enrichis (Completed 2026-05-15)

**Goal:** Transformer les emails textuels en rapports visuels avec graphiques PNG inline et template dark mode professionnel.

**Delivered:**
- Phase 6: Chart Generation (`charts/` package — ETF bars, crypto sparklines, Fear & Greed gauge, PEA colored table — CHART-05 graceful fallback)
- Phase 7: Template Redesign & Integration (dark-mode Bloomberg HTML template, responsive/mobile-friendly, all 3 reporters → ReportOutput)
- Phase 8: Close Gaps (production chart data-contract fixes, 7-day sparkline collection, CHART-03 None-guard, boundary tests, Phase 6 VERIFICATION.md)

**Stats:** 3 phases | 11 plans | 292 tests | 70 files changed | +10,789 / -151 LOC | 2 days

**Known tech debt at close:** Markdown table rendering in weekly/monthly HTML (CR-02), `_build_chart_panel` duplicated 3× (IN-01), crontab offset (SCHED-03)

**Archive:** [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md) | [v1.1-REQUIREMENTS.md](milestones/v1.1-REQUIREMENTS.md) | [v1.1-MILESTONE-AUDIT.md](milestones/v1.1-MILESTONE-AUDIT.md)

---

*Updated: 2026-05-15*
