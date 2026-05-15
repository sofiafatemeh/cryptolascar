# Phase 7: Template Redesign & Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 7-template-redesign-integration
**Areas discussed:** Chart injection flow, Template structure, Weekly & monthly chart scope, Body text rendering

---

## Chart injection flow

### Q1 — Who calls chart generators?

| Option | Description | Selected |
|--------|-------------|----------|
| Reporter (daily.py etc.) | build_daily_report() generates charts alongside sections, returns HTML with charts embedded. No signature change to send_email(). | ✓ |
| main.py pipeline | main.py calls chart generators after collect_all(), passes results to send_email(). | |
| email.py (delivery layer) | send_email() receives raw data dict and generates charts itself. | |

**User's choice:** Reporter (daily.py etc.) — Recommended
**Notes:** Charts are part of report content, not the delivery layer.

---

### Q2 — What should build_daily_report() return?

| Option | Description | Selected |
|--------|-------------|----------|
| HTML string with charts embedded inline | Reporter returns a single rich HTML string. send_email() passes it straight to Jinja2 as body_html. No signature changes anywhere. | |
| Tuple (plain_text, charts: dict) | Reporter returns (markdown_text, {'etf': b64, ...}). send_email() assembles final HTML. | |

**Note:** User selected "HTML string with charts embedded inline" but subsequent Q4 clarified that plain_text must also be returned for MIME fallback. Final decision: `(html_body, plain_text)` namedtuple/dataclass.

---

### Q3 — What happens to _markdown_to_html()?

| Option | Description | Selected |
|--------|-------------|----------|
| Bypass it — HTML reporters skip it, pass body_html directly | send_email() detects HTML content. _markdown_to_html() stays for fallback paths. | ✓ |
| Remove it — reporters own all HTML rendering | Phase 7 removes _markdown_to_html() entirely. | |
| Keep as-is — reporters embed chart HTML inside Markdown | Fragile format mixing. | |

**User's choice:** Bypass it
**Notes:** _markdown_to_html() stays but is bypassed when reporters return HTML.

---

### Q4 — What feeds the plain-text MIME fallback?

| Option | Description | Selected |
|--------|-------------|----------|
| Reporters return (html_body, plain_text) | build functions return dual output. send_email() uses HTML for rendering, plain_text for MIME fallback. | ✓ |
| Strip tags from HTML at send time | send_email() strips HTML tags automatically. Quality unpredictable. | |
| Drop the plain-text fallback | Remove text/plain MIME part. Breaks some clients. | |

**User's choice:** Reporters return (html_body, plain_text) — Recommended

---

## Template structure

### Q1 — Universal template vs. separate templates?

| Option | Description | Selected |
|--------|-------------|----------|
| One template with conditionals | Single report_email.html with Jinja2 conditionals. One file to maintain. | ✓ |
| Separate templates (daily/weekly/monthly.html) | Maximum flexibility, 3x CSS to maintain. | |
| Base template + type-specific extends | Jinja2 inheritance. More setup, cleaner if layouts diverge. | |

**User's choice:** One template with conditionals — Recommended

---

### Q2 — Visual complexity level?

| Option | Description | Selected |
|--------|-------------|----------|
| Bloomberg terminal feel — header band + section cards | Branded header, each section in dark card with subtle border. | ✓ |
| Minimal dark — just dark background + typography | Just swap background, update font/color. Faster, less impact. | |
| You decide | Claude picks structure matching 'style Bloomberg'. | |

**User's choice:** Bloomberg terminal feel

---

### Q3 — Template header band content?

| Option | Description | Selected |
|--------|-------------|----------|
| Logo text + date + report type badge | 'CryptoLascar' in orange (#FF6B35) Courier New + date + badge. | ✓ |
| Just the report subject line | Email subject as only header. Simplest. | |
| You decide | Claude designs the header. | |

**User's choice:** Logo text + date + report type badge — Recommended

---

### Q4 — Font stack?

| Option | Description | Selected |
|--------|-------------|----------|
| 'Courier New', monospace for all | Consistent terminal aesthetic throughout. Already used for PEA table in Phase 6. | ✓ |
| Monospace for data, sans-serif for narrative | More readable for long prose, less consistent. | |
| You decide | Claude picks font consistent with Phase 6 UI-SPEC. | |

**User's choice:** 'Courier New', monospace for all

---

## Weekly & monthly chart scope

### Q1 — Charts in Weekly Wrap?

| Option | Description | Selected |
|--------|-------------|----------|
| ETF bar chart (1j/1sem) | Weekly performance — directly relevant. | ✓ |
| Crypto sparklines (7j BTC+ETH) | 7-day history = exactly weekly scope. | ✓ |
| Fear & Greed gauge | Current sentiment — useful weekly context. | ✓ |
| PEA colored table | PEA weekly snapshot. | ✓ |

**User's choice:** All 4 charts

---

### Q2 — Charts in Monthly Close?

| Option | Description | Selected |
|--------|-------------|----------|
| ETF bar chart (1j/1sem) | Current ETF position at month-end. | ✓ |
| Crypto sparklines (7j BTC+ETH) | Only 7 days — less representative for monthly. | ✓ |
| Fear & Greed gauge | Month-end sentiment indicator. | ✓ |
| PEA colored table | Month-end PEA snapshot. | ✓ |

**User's choice:** All 4 charts

---

### Q3 — Where do charts appear in the email?

| Option | Description | Selected |
|--------|-------------|----------|
| Visual panel at the top | Charts grouped after header, before narrative. Bloomberg dashboard style. | ✓ |
| Inline after their section | ETF chart after ETF Radar section, etc. Contextual but long. | |
| You decide | Claude places charts for best visual flow. | |

**User's choice:** Visual panel at the top — Recommended

---

## Body text rendering

### Q1 — Section heading style on dark background?

| Option | Description | Selected |
|--------|-------------|----------|
| Orange accent on dark | ## headings in #FF6B35 Courier New. Matches Bloomberg aesthetic. | ✓ |
| White/light on dark | Headings in #e0e0e0. Subtler. | |
| Green accent on dark | Headings in #00C851. Unconventional for section titles. | |

**User's choice:** Orange accent on dark — Recommended

---

### Q2 — How to update _markdown_to_html() for dark mode?

| Option | Description | Selected |
|--------|-------------|----------|
| Update in-place | Change hardcoded color values. Simple, no new dependencies. | ✓ |
| Migrate to markdown2 library | Better Markdown support but adds dependency. | |
| Move rendering into reporters | Reporters handle all headings. _markdown_to_html() deleted. | |

**User's choice:** Update in-place — Recommended

---

### Q3 — Body prose text color?

| Option | Description | Selected |
|--------|-------------|----------|
| #e0e0e0 (Phase 6 chart_text) | Already established as readable light-on-dark. Consistent across charts and template. | ✓ |
| #ffffff (pure white) | Maximum contrast. Slightly harsh. | |
| You decide | Claude picks prose color consistent with Phase 6. | |

**User's choice:** #e0e0e0 — Recommended

---

## Claude's Discretion

- Section card geometry (border-radius, exact padding, inner spacing) — must use email-safe table-based layout (no CSS grid/flex)
- Mobile breakpoint strategy — media queries in `<style>` block, table-based fluid layout as base
- Chart panel layout arrangement (2×2 grid? stacked? side-by-side pairs?)
- Reporter return type — namedtuple vs dataclass for (html_body, plain_text)

## Deferred Ideas

None — discussion stayed within phase scope.
