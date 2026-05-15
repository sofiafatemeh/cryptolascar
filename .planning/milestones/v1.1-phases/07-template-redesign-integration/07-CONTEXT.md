# Phase 7: Template Redesign & Integration - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform the three report types (daily, weekly, monthly) from minimal plain-HTML emails into dark-mode Bloomberg-style emails with charts embedded — all delivered through the existing Gmail SMTP pipeline.

Specifically:
1. **Template redesign** — Replace the 21-line minimal wrapper (`templates/report_email.html`) with a full dark-mode Bloomberg terminal template: header band + section cards, `#0d0d0d` background, orange/green accents, Courier New monospace throughout
2. **Chart injection** — Wire Phase 6 chart generators into reporters; reporters return `(html_body, plain_text)` with charts embedded inline in `html_body`
3. **Reporter updates** — `daily.py`, `weekly.py`, `monthly.py` each call chart generators and return the new dual-output type
4. **`send_email()` update** — Accept the new reporter output; bypass `_markdown_to_html()` for HTML bodies; keep `plain_text` for the MIME text/plain fallback
5. **`_markdown_to_html()` update** — Update hardcoded light-mode colors to dark-mode palette in-place

**Requirements covered:** TMPL-01, TMPL-02, TMPL-03
**Depends on:** Phase 6 (chart generators in `charts/`)

**NOT in scope:** New report types, new data sources, new chart types, tweet generation changes, APScheduler, monitoring dashboard.

</domain>

<decisions>
## Implementation Decisions

### Chart Injection Flow

- **D-01:** Reporters (`daily.py`, `weekly.py`, `monthly.py`) are responsible for calling chart generators. Charts are part of report content, not the delivery layer.
- **D-02:** Each reporter's build function returns a **named structure (namedtuple or dataclass) with two fields: `html_body` and `plain_text`**. `html_body` is a rich HTML string with `<img>` tags and PEA table already embedded. `plain_text` is the unchanged Markdown narrative for the MIME text/plain fallback.
- **D-03:** `send_email()` is updated to accept the new dual-output structure. When `html_body` is present, it is passed directly to the Jinja2 template as `body_html` — `_markdown_to_html()` is **bypassed** for HTML content.
- **D-04:** `_markdown_to_html()` stays in `email.py` for any legacy plain-text path (no callers initially, but not deleted). It is updated in-place to use dark-mode colors.
- **D-05:** The `plain_text` field from the reporter output feeds the `text/plain` MIME part in `send_email()`, preserving RFC 2822 compliance. The MIME fallback is NOT removed.

### Template Structure

- **D-06:** **One universal template** (`templates/report_email.html`) handles all three report types via Jinja2 conditionals (`{% if etf_chart %}`, `{% if report_type == 'weekly' %}`, etc.). No separate per-type template files.
- **D-07:** Visual complexity target: **Bloomberg terminal feel** — branded header band + section content cards with subtle dark borders. Not just color-swapping — structured layout.
- **D-08:** **Template header band** contains: `CryptoLascar` in orange (`#FF6B35`) Courier New (left), and a report type badge (`[DAILY]`, `[WEEKLY WRAP]`, `[MONTHLY CLOSE]`) + date (right). Passed as template variables `report_type` and `date`.
- **D-09:** **Font stack throughout:** `'Courier New', monospace` for all text — section titles, body prose, data values, footer. Consistent terminal aesthetic matching Phase 6 PEA table typography.
- **D-10:** Section cards: each narrative section wrapped in a `<div>` with dark background (`#111111` or `#0f0f0f`), `1px solid #2a2a2a` border, `16px` padding, `8px` bottom margin. Planner decides exact card geometry.

### Chart Placement

- **D-11:** Charts appear in a **visual panel at the top of the email**, immediately after the header band, before any narrative sections. All available charts for the report type are grouped together as a "dashboard" block.
- **D-12:** **Daily report:** all 4 charts (ETF bar chart, crypto sparklines, Fear & Greed gauge, PEA table).
- **D-13:** **Weekly Wrap:** all 4 charts (ETF bar chart, crypto sparklines, Fear & Greed gauge, PEA table).
- **D-14:** **Monthly Close:** all 4 charts (ETF bar chart, crypto sparklines, Fear & Greed gauge, PEA table).
- **D-15:** Per CHART-05 (Phase 6): if a chart function returns `None`, the template renders the fallback string from Phase 6 UI-SPEC (e.g., `[Graphique ETF indisponible]` in `#888` italic). The email is always sent regardless of chart failures.

### Body Text Rendering

- **D-16:** Section headings (`## ETF Radar`, `## Crypto Pulse`, etc.) styled as **orange (`#FF6B35`) Courier New** in the dark template. Updated in `_markdown_to_html()`.
- **D-17:** `_markdown_to_html()` updated **in-place** (no new library dependency). Color values changed: h1/h2 from `color:#1a1a2e` → `color:#FF6B35`; paragraph text from implied light to `color:#e0e0e0`.
- **D-18:** Body prose text color: **`#e0e0e0`** — the Phase 6 `chart_text` token. Consistent across charts and email template.
- **D-19:** Footer disclaimer text: `color:#555555` (darker grey on dark background, less prominent than on white).

### Claude's Discretion

- **Section card geometry** — exact border-radius, padding values, inner spacing of section cards. Must be consistent, readable, and email-client safe (no CSS grid/flex — table-based layout).
- **Mobile breakpoint strategy** — since inline CSS is required for email clients, responsive design uses `max-width:600px` media queries within a `<style>` block in `<head>`, with a table-based fluid layout as the base. Planner decides exact breakpoint rules.
- **Chart panel layout** — exact arrangement of 4 charts in the top panel (2×2 grid? stacked? side-by-side ETF+sparklines then gauge+PEA?). Must render correctly at `max-width:680px` for desktop.
- **Reporter return type** — namedtuple vs dataclass for the `(html_body, plain_text)` dual output. Planner picks whichever is cleaner.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — TMPL-01, TMPL-02, TMPL-03 define all template requirements for this phase
- `.planning/ROADMAP.md §Phase 7` — Goal, success criteria (5 items), dependency on Phase 6
- `.planning/PROJECT.md` — Core constraints: zero hardcoded credentials, graceful degradation, dark mode financial aesthetic

### Phase 6 Visual Contract (MANDATORY — colors, fallbacks, IMG tags)
- `.planning/phases/06-chart-generation/06-UI-SPEC.md` — **Color contract** (`#0d0d0d` bg, `#FF6B35` orange, `#00C851` green, `#e0e0e0` text, `#2a2a2a` borders), IMG tag template for base64 PNG embedding, fallback HTML strings per chart, chart dimensions/DPI. Phase 7 template MUST honor all Phase 6 color tokens.

### Existing Implementation (read before touching these files)
- `templates/report_email.html` — Current 21-line minimal template to be replaced
- `delivery/email.py` — `send_email()`, `archive_report()`, `_markdown_to_html()`, Jinja2 setup. Phase 7 modifies this file.
- `reporters/daily.py` — `build_daily_report(data, config) -> str` — signature changes to return dual output
- `reporters/weekly.py` — `build_weekly_report()` — same signature change
- `reporters/monthly.py` — `build_monthly_report()` — same signature change
- `reporters/dispatch.py` — `select_reports()` — may need update to handle new reporter return type
- `charts/__init__.py` — Public chart API: `generate_etf_chart`, `generate_crypto_sparklines`, `generate_fear_greed_gauge`, `generate_pea_table` — all return `Optional[str]`

### Phase 5 Integration (main.py pipeline)
- `.planning/phases/05-scheduling-resilience/05-CONTEXT.md §D-06` — `main.py` calls `select_reports()` → `send_email()`. Phase 7 must not break the pipeline wiring.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `delivery/email.py:_JINJA_ENV` — Module-level Jinja2 environment with `FileSystemLoader("templates/")` and `autoescape`. Template swap is a file replacement; Jinja2 wiring is unchanged.
- `delivery/email.py:build_subject()` — Already formats `[DAILY]`, `[WEEKLY WRAP]`, `[MONTHLY CLOSE]` subjects. Phase 7 template header badge uses the same strings.
- `charts/__init__.py` — All 4 chart generators already exported with `Optional[str]` return type and CHART-05 graceful degradation. No chart code changes needed in Phase 7.

### Established Patterns
- **CHART-05 graceful degradation** — Chart `None` → fallback HTML string. Phase 7 template must implement this pattern consistently for all 4 chart positions.
- **Jinja2 `| safe` filter** — `body_html` is passed with `| safe` in the current template. Phase 7 must maintain this for pre-escaped HTML from reporters. New template variables passed by value (subject, report_type, date) remain auto-escaped.
- **`_SAFE_TYPE_RE` + `_SAFE_DATE_RE`** validation in `archive_report()` — security pattern to carry forward; path traversal prevention already in place.

### Integration Points
- `delivery/email.py:send_email()` — Primary integration point. Signature changes from `(report_type, date, plain_text, config, month, year)` to accept dual reporter output. Backward compatibility with `plain_text`-only callers should be considered.
- `reporters/base.py:build_section()` — Currently returns Markdown `## Heading\n\nbody`. Phase 7 reporters may want an `html_section()` equivalent that returns a dark-mode styled `<div>` card. Planner decides whether to add this helper to `base.py`.
- `main.py` pipeline — `select_reports()` returns a dict of report strings; `send_email()` is called with them. Planner must audit `main.py` to ensure the dual-output reporter change doesn't break the dispatch flow.

</code_context>

<specifics>
## Specific Ideas

- **Bloomberg terminal header:** "CryptoLascar" branding in `#FF6B35` Courier New (left), report type badge + ISO date (right). Dark band (`#111111` or `#0d0d0d`) spanning full width.
- **Chart dashboard at top:** 4 charts grouped into a visual block immediately after the header. PNG charts as `<img>` with `data:image/png;base64,...` src (per Phase 6 IMG tag template). PEA table as inline HTML block.
- **Section cards:** each of the 6 daily sections (Macro Snapshot, ETF Radar, Crypto Pulse, PEA Alert, News Feed, One Signal) wrapped in a distinct dark card. Heading in orange `#FF6B35`, body in `#e0e0e0`.
- **Email width:** `max-width:680px` (unchanged from current template). Mobile layout: single-column, font sizes ≥ 14px, no horizontal overflow.
- **Font:** `'Courier New', monospace` everywhere — headings, body, data values, footer. No web font loading (email client safety).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 7-Template Redesign & Integration*
*Context gathered: 2026-05-14*
