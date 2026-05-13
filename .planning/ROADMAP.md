# Roadmap: CryptoLascar — Milestone v1.1 Rapports Enrichis

## Overview

Two phases transform the system from plain-text emails into visually rich financial reports. Phase 6 builds the chart generation module (matplotlib PNG charts embedded as base64, with graceful fallback when any chart fails). Phase 7 redesigns the HTML email templates with a dark-mode Bloomberg aesthetic, mobile responsiveness, and wires all three report types to the new visual system.

## Phases

**Phase Numbering:**
- Phases 1–5 completed in Milestone v1.0
- Milestone v1.1 continues from Phase 6

- [ ] **Phase 6: Chart Generation** - Matplotlib chart module producing ETF bar chart, crypto sparklines, Fear & Greed gauge, and PEA colored table — all embedded as PNG base64, with per-chart fallback on failure
- [ ] **Phase 7: Template Redesign & Integration** - Dark mode Bloomberg-style HTML template (responsive, mobile-friendly) applied to all three report types (daily/weekly/monthly) with charts integrated

## Phase Details

### Phase 6: Chart Generation
**Goal**: The daily report can embed four visual elements (ETF bar chart, crypto sparklines, Fear & Greed gauge, PEA colored table) as PNG base64 inline images, and any individual chart failure leaves the run unaffected
**Depends on**: Phase 5 (v1.0 complete)
**Requirements**: CHART-01, CHART-02, CHART-03, CHART-04, CHART-05
**Success Criteria** (what must be TRUE):
  1. Calling the ETF chart function with valid performance data returns a base64 PNG string showing 1-day and 1-week variation bars for each tracked ETF
  2. Calling the crypto sparkline function with 7-day price history for BTC and ETH returns a base64 PNG string with two labeled sparkline curves
  3. Calling the Fear & Greed gauge function with a value (0–100) returns a base64 PNG string showing a color-coded arc gauge
  4. Calling the PEA table function with position data returns an HTML string with rows colored green (positive) or red (negative) based on performance
  5. When any single chart function raises an exception, the caller receives None (or equivalent empty sentinel), logs the error, and the report generation pipeline continues without that chart — the email is still sent
**Plans**: 4 plans in 3 waves
Plans:
**Wave 1**
- [ ] 06-01-PLAN.md — charts/ package bootstrap: Agg backend + requirements.txt

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 06-02-PLAN.md — ETF bar chart (CHART-01) + crypto sparklines (CHART-02)
- [ ] 06-03-PLAN.md — Fear & Greed gauge (CHART-03) + PEA HTML table (CHART-04)

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 06-04-PLAN.md — Unit tests for all 4 generators + CHART-05 fallback verification

**Cross-cutting constraints:**
- Every chart function MUST return `Optional[str]` and catch all exceptions (CHART-05)
- `matplotlib.use("Agg")` called once at package init — never per-function
**UI hint**: yes

### Phase 7: Template Redesign & Integration
**Goal**: All three report types (daily, weekly, monthly) are delivered as visually polished HTML emails using a dark-mode financial template that renders correctly on both mobile and desktop, with charts from Phase 6 embedded where applicable
**Depends on**: Phase 6
**Requirements**: TMPL-01, TMPL-02, TMPL-03
**Success Criteria** (what must be TRUE):
  1. The HTML email template uses a dark background, orange and green accent colors, and a typographic style consistent with professional financial terminals (Bloomberg aesthetic)
  2. Opening the email on a mobile viewport (< 600 px wide) displays a single-column layout with readable font sizes and no horizontal overflow
  3. Opening the email on a desktop viewport displays the intended multi-column or sectioned layout with full chart visibility
  4. A daily report email contains all four chart elements (ETF bars, crypto sparklines, Fear & Greed gauge, PEA colored table) or their text fallbacks, using the new template
  5. Weekly and monthly report emails use the same base template with charts relevant to their scope; the three report types are visually consistent
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 6. Chart Generation | 0/4 | Not started | - |
| 7. Template Redesign & Integration | 0/TBD | Not started | - |
