---
phase: 07-template-redesign-integration
verified: 2026-05-15T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
gaps:
deferred:
human_verification:
  - test: "Open a rendered daily report email on a mobile device (< 600px viewport) and confirm the header stacks vertically, chart cells stack to one column, and no horizontal overflow occurs"
    expected: "Single-column layout with readable font sizes; header brand above badge; chart cells full-width stacked vertically"
    why_human: "CSS @media query behavior cannot be verified programmatically without a browser/email-client rendering engine"
  - test: "Open a rendered daily, weekly, and monthly email in a desktop email client (Gmail, Outlook, or equivalent) and confirm the 2x2 chart grid displays as two rows of two cells, and section cards are legible"
    expected: "Two-row two-column chart panel visible; dark background with orange headings; section body text readable"
    why_human: "Table-based email layout cross-client rendering requires visual inspection"
  - test: "Trigger a daily report run with real ETF data available and open the resulting email — check whether the ETF chart title shows a date (e.g. 'Performance ETFs — 14 mai 2026') or a blank title ('Performance ETFs —')"
    expected: "CR-01 quality gap: the chart title currently shows 'Performance ETFs —' with no date because all three reporters call _build_chart_panel(data, '') with a hardcoded empty string. Verify whether this is visually acceptable or must be fixed before production use."
    why_human: "CR-01 is a known quality gap (07-REVIEW.md). The codebase confirms the empty date_str is hardcoded. A human must decide if this is acceptable for the current milestone or requires a fix."
  - test: "Open a weekly or monthly report email with real data (sections containing Markdown tables and bullet points) and inspect the section body content"
    expected: "CR-02 quality gap: section bodies containing Markdown table rows (| col | col |) and bullet points (- item) are placed in a <p> tag with html.escape() only — no Markdown-to-HTML conversion. Email clients collapse embedded newlines, making tables appear as garbled pipe-separated text on one line. Bullet points show as literal '- **Source** — Title' text. Verify whether this is acceptable or must be fixed before production use."
    why_human: "CR-02 is a known quality gap (07-REVIEW.md). The codebase confirms _sections_to_html() does not convert Markdown to HTML. Automated tests confirmed raw pipe chars and raw **bold** markers appear in html_body. A human must decide acceptability for production."
---

# Phase 7: Template Redesign & Integration Verification Report

**Phase Goal:** All three report types (daily, weekly, monthly) are delivered as visually polished HTML emails using a dark-mode financial template that renders correctly on both mobile and desktop, with charts from Phase 6 embedded where applicable
**Verified:** 2026-05-15T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The HTML email template uses a dark background, orange and green accent colors, Bloomberg aesthetic | VERIFIED | templates/report_email.html: background-color:#0d0d0d, #FF6B35 accents, Courier New font throughout; template renders correctly for all 3 report types |
| 2 | Opening the email on mobile (< 600px) displays single-column layout | VERIFIED (partial — see human) | @media (max-width:600px) block present with chart-cell, header-inner, header-brand, header-right rules; stacking CSS correct; requires human visual confirmation |
| 3 | Opening the email on desktop displays the multi-column sectioned layout | VERIFIED (partial — see human) | 2x2 chart panel table with class="chart-cell" width="50%" confirmed in all reporters; max-width:680px outer container; requires human visual confirmation |
| 4 | Daily report email contains all 4 chart elements or text fallbacks | VERIFIED | build_daily_report() html_body confirmed to contain ETF_FALLBACK, CRYPTO_FALLBACK, GAUGE_FALLBACK, PEA_FALLBACK when generators return None; 4 chart-cell tds present in panel |
| 5 | Weekly and monthly report emails use same base template with charts; all 3 types are visually consistent | VERIFIED | build_weekly_report() and build_monthly_report() return ReportOutput with chart panels; all 3 use delivery/email.py which loads a single template (report_email.html); same html_section() cards used throughout |

**Score:** 5/5 truths verified (core pipeline complete; 4 human items remain for visual and quality confirmation)

### Deferred Items

None — Phase 7 is the final milestone phase.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `templates/report_email.html` | Dark-mode Bloomberg terminal email template | VERIFIED | 67 lines; #0d0d0d body bg; #FF6B35 brand+badge; Courier New throughout; @media (max-width:600px) block; {{ body_html | safe }}; {{ date }} without | safe |
| `reporters/base.py` | ReportOutput NamedTuple, html_section(), 4 fallback constants | VERIFIED | ReportOutput(html_body, plain_text) NamedTuple exported; html_section() escapes title via _html_stdlib.escape(); ETF_FALLBACK, CRYPTO_FALLBACK, GAUGE_FALLBACK (with &amp;), PEA_FALLBACK all present |
| `delivery/email.py` | Updated _markdown_to_html() + send_email(html_body=) | VERIFIED | #FF6B35 for h1/h2; #1a1a2e fully removed; html_body: str = "" param; if html_body: bypass; template.render() includes report_type=report_type, date=date |
| `reporters/daily.py` | build_daily_report() -> ReportOutput with chart panel | VERIFIED | Returns ReportOutput; html_body len=3200 with empty data; 4 chart-cell tds; ETF/crypto/gauge/PEA fallbacks used; outer try/except returns degraded ReportOutput |
| `reporters/weekly.py` | build_weekly_report() -> ReportOutput with chart panel | VERIFIED | Returns ReportOutput; html_body len=3626 with empty data; same _build_chart_panel pattern; 7-section degradation fallback |
| `reporters/monthly.py` | build_monthly_report() -> ReportOutput with chart panel | VERIFIED | Returns ReportOutput; html_body len=3651 with empty data; max_tokens=600 preserved in _month_in_review() and _forward_look(); 7-section degradation fallback |
| `reporters/dispatch.py` | _safe_build() and select_reports() returning ReportOutput | VERIFIED | _safe_build() -> ReportOutput; fallback returns ReportOutput(html_body=dark-mode p tag, plain_text=name); select_reports() -> Dict[str, ReportOutput] |
| `main.py` | Pipeline loop consuming ReportOutput.plain_text and ReportOutput.html_body | VERIFIED | report_text.plain_text used 3x (archive_report, send_email plain_text arg, write_tweet); html_body=report_text.html_body in send_email; no bare report_text passed anywhere |
| `tests/test_phase7_integration.py` | 11 integration smoke tests covering full pipeline dark-mode | VERIFIED | 11 tests; all pass; dark-mode markers (#0d0d0d, #FF6B35, CryptoLascar, [DAILY]) verified in SMTP sendmail output via MIME decode |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `delivery/email.py` | `templates/report_email.html` | `_JINJA_ENV.get_template('report_email.html')` | WIRED | Confirmed in delivery/email.py lines 172-178 |
| `reporters/daily.py` | `reporters/base.py` | `from reporters.base import ReportOutput, html_section, ETF_FALLBACK, ...` | WIRED | Import block at lines 23-27 |
| `reporters/weekly.py` | `reporters/base.py` | Same import pattern | WIRED | Import block at lines 22-26 |
| `reporters/monthly.py` | `reporters/base.py` | Same import pattern | WIRED | Import block at lines 23-27 |
| `reporters/daily.py` | `charts/__init__.py` | `from charts import generate_etf_chart, ...` | WIRED | All 4 generators imported and called in _build_chart_panel() |
| `reporters/dispatch.py` | `reporters/base.py` | `from reporters.base import ReportOutput` | WIRED | Line 29 |
| `main.py` | `delivery/email.py send_email()` | `send_email(..., html_body=report_text.html_body)` | WIRED | Lines 228-232; html_body= keyword arg present |
| `main.py` | `delivery/email.py archive_report()` | `archive_report(report_type, date_str, report_text.plain_text)` | WIRED | Line 227 |
| `template.render()` | `templates/report_email.html` | `report_type=report_type, date=date` | WIRED | Lines 173-178 in delivery/email.py; header badge conditional works for daily/weekly/monthly |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `reporters/daily.py html_body` | chart_panel + section cards | _build_chart_panel() + _sections_to_html() | Yes — chart generators called; fallbacks used when None | FLOWING |
| `delivery/email.py html_content` | body_html from reporter | if html_body: body_html = html_body (bypass path) | Yes — html_body flows from reporter through template.render() | FLOWING |
| `reporters/dispatch.py result` | Dict[str, ReportOutput] | _safe_build() calling build_*_report() | Yes — real builder called; fallback ReportOutput returned on failure | FLOWING |
| `main.py SMTP sendmail` | msg.as_string() | report_text.plain_text + report_text.html_body | Yes — verified in integration test: #0d0d0d and #FF6B35 in decoded SMTP output | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 3 reporters return ReportOutput | `build_daily/weekly/monthly_report({}, FakeConfig())` | daily len=3200, weekly len=3626, monthly len=3651 | PASS |
| Template renders for all 3 report_type values | Jinja2 render with report_type=daily/weekly/monthly | [DAILY], [WEEKLY WRAP], [MONTHLY CLOSE] badges confirmed | PASS |
| Full integration smoke test: pipeline produces dark-mode HTML | `pytest tests/test_phase7_integration.py` | 11/11 passed | PASS |
| Full test suite no regressions | `pytest tests/ -q` | 284 passed in 28.91s | PASS |
| ETF chart title receives empty date_str (CR-01) | grep `_build_chart_panel(data, "")` in all 3 reporters | All 3 call with `""` | FAIL (quality gap — see WR-01 below) |
| Section bodies render Markdown tables and bullets as HTML (CR-02) | `_sections_to_html([section_with_table])` | raw `| Ticker |` present; no `<table>` tag; raw `**bold**` present | FAIL (quality gap — see WR-02 below) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TMPL-01 | 07-01, 07-02, 07-03, 07-04 | Dark mode financial template (fond sombre, accents orange/vert, style Bloomberg) | SATISFIED | templates/report_email.html: #0d0d0d body, #FF6B35 accents, Courier New; delivery/email.py _markdown_to_html() outputs #FF6B35 for h1/h2; html_section() uses #111111 cards with #FF6B35 headings |
| TMPL-02 | 07-01 | Template responsive, lisible sur mobile et desktop | SATISFIED (human confirmation needed) | @media (max-width:600px) block with chart-cell stacking; max-width:680px desktop container; table-based layout (no flex/grid); header-brand/header-right mobile classes |
| TMPL-03 | 07-02, 07-03, 07-04 | Les 3 types de rapport utilisent le nouveau template avec graphiques | SATISFIED | All 3 reporters return ReportOutput with 2x2 chart panels; all 3 flow through send_email() -> report_email.html; same template used for daily/weekly/monthly |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| reporters/daily.py | 267 | `_build_chart_panel(data, "")` — hardcoded empty string for date_str | Warning (CR-01) | ETF chart title displays "Performance ETFs —" with no date in production |
| reporters/weekly.py | 256 | `_build_chart_panel(data, "")` — same issue | Warning (CR-01) | Same ETF chart title problem |
| reporters/monthly.py | 296 | `_build_chart_panel(data, "")` — same issue | Warning (CR-01) | Same ETF chart title problem |
| reporters/daily.py | 234-247 | `_sections_to_html()` places raw Markdown in `<p>` via html.escape() only | Warning (CR-02) | Markdown tables (weekly/monthly) and bullets (all reporters) render as garbled text in HTML email; no <table>/<li> structure |
| reporters/weekly.py | 218-231 | Same `_sections_to_html()` issue | Warning (CR-02) | Same |
| reporters/monthly.py | 245-258 | Same `_sections_to_html()` issue | Warning (CR-02) | Same |
| reporters/daily.py, weekly.py, monthly.py | multiple | `_build_chart_panel` and `_sections_to_html` duplicated verbatim 3x | Info (IN-01, IN-02) | Any fix must be applied in 3 places; no functional impact today |
| main.py | 219 | `import locale` inside dispatch loop | Info (IN-05) | Cosmetic; not thread-safe but current run is single-threaded |

### Human Verification Required

#### 1. Mobile Viewport Rendering

**Test:** Render a daily report email and open it in a mobile email client or browser at viewport width 600px or less
**Expected:** Single-column layout — header brand above badge (stacked), chart cells stack to full width vertically, no horizontal scrolling, font sizes readable (18px header, 14px body)
**Why human:** CSS @media query rendering cannot be verified programmatically; requires a browser or email client rendering engine

#### 2. Desktop Viewport Rendering

**Test:** Render a daily, weekly, and monthly report email and open in a desktop email client (Gmail, Outlook, Apple Mail)
**Expected:** Two-row two-column chart panel visible; dark background (#0d0d0d); orange headings in section cards; footer disclaimer visible
**Why human:** Table-based email HTML rendering varies across email clients; requires visual inspection

#### 3. CR-01 — ETF Chart Date Title Acceptability Decision

**Test:** Trigger a run with real ETF data and open the rendered email. Inspect the ETF chart title.
**Expected (current behavior):** Chart title reads "Performance ETFs —" with nothing after the dash, because all three `build_*_report` functions call `_build_chart_panel(data, "")` with a hardcoded empty string.
**Why human:** This is a confirmed quality gap from 07-REVIEW.md (CR-01). The parameter exists and flows to `generate_etf_chart(etf_data, date_str)` which uses it in the chart title (`f"Performance ETFs — {date_str}"`). A developer must decide: (a) acceptable for this milestone, or (b) requires a fix-up commit before the phase is considered complete. The fix is one line per reporter: replace `""` with `datetime.date.today().strftime("%-d %B %Y")`.

#### 4. CR-02 — Markdown Section Body Rendering Acceptability Decision

**Test:** Trigger a weekly or monthly run with real data (sections will contain Markdown tables from `_etf_performance`, `_crypto_recap`, `_pea_wrap`, `_macro_watch` and bullets from `_news_digest`). Open the email HTML body and inspect section card content.
**Expected (current behavior):** Section bodies containing Markdown table rows (`| Ticker | Prix | Variation |`) appear as literal pipe-separated text on a single line. Bullet points (`- **Reuters** — Fed raises rates`) appear as literal text with raw `**bold**` markers. `html.escape()` is applied but no Markdown-to-HTML conversion occurs in `_sections_to_html()`.
**Why human:** This is a confirmed quality gap from 07-REVIEW.md (CR-02). Automated tests confirmed: `| Ticker |` appears raw in html_body; `**Reuters**` appears raw; no `<table>`, `<li>`, or `<strong>` tags generated. A developer must decide: (a) acceptable for this milestone (plain_text is correct; html_body is a known degraded state), or (b) requires implementation of `_md_to_simple_html()` as specified in the review before the phase is complete.

### Gaps Summary

No functional blockers. The core pipeline is complete and all 5 Success Criteria are met at the implementation level: all artifacts exist and are substantively implemented, all key links are wired, and the full test suite passes (284 tests).

Two quality gaps documented in 07-REVIEW.md are confirmed in the codebase:

**CR-01 (quality gap):** All three reporters pass `""` as `date_str` to `_build_chart_panel()`, causing ETF chart titles to display as "Performance ETFs —" with no date. This is a one-line fix per reporter that was not included in Phase 7 plans. Impact: cosmetic in a rendered chart.

**CR-02 (quality gap):** `_sections_to_html()` applies `html.escape()` to Markdown section bodies without converting Markdown syntax to HTML. Weekly and monthly reports with real data will show raw pipe characters from Markdown tables and raw `**bold**` markers in the HTML email body. The plain_text field is unaffected. This is a meaningful visual defect for weekly/monthly reports with tabular data.

Both gaps require a human decision: are they acceptable for the current milestone, or do they require closure commits before Phase 7 can be considered fully complete?

---

_Verified: 2026-05-15T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
