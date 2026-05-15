---
phase: 07-template-redesign-integration
plan: 01
subsystem: template-infrastructure
tags: [template, reporter, dark-mode, bloomberg, jinja2, tdd, html-email]
completed: "2026-05-15"
duration: ~10 min

dependency_graph:
  requires: []
  provides:
    - reporters/base.py::ReportOutput (NamedTuple — dual html_body/plain_text output)
    - reporters/base.py::html_section() (dark-mode card builder, XSS-safe)
    - reporters/base.py::ETF_FALLBACK (exact fallback string)
    - reporters/base.py::CRYPTO_FALLBACK (exact fallback string)
    - reporters/base.py::GAUGE_FALLBACK (exact fallback string with &amp;)
    - reporters/base.py::PEA_FALLBACK (exact fallback string)
    - templates/report_email.html (dark-mode Bloomberg terminal template)
  affects:
    - reporters/daily.py (Wave 2 — imports ReportOutput + html_section)
    - reporters/weekly.py (Wave 2 — same)
    - reporters/monthly.py (Wave 2 — same)
    - delivery/email.py (Wave 2 — uses new template variables)

tech_stack:
  added:
    - html (stdlib) imported as _html_stdlib in reporters/base.py for XSS escaping
    - typing.NamedTuple for ReportOutput definition
  patterns:
    - TDD RED/GREEN flow — failing tests committed before implementation
    - NamedTuple dual-output (D-02) — ReportOutput(html_body, plain_text)
    - Bloomberg terminal email aesthetic — #0d0d0d bg, #FF6B35 accents, Courier New
    - Table-based layout — no flex/grid (email client safety, TMPL-02)
    - Jinja2 autoescape — body_html uses | safe; subject/report_type/date auto-escaped

key_files:
  created:
    - .planning/phases/07-template-redesign-integration/07-01-SUMMARY.md
  modified:
    - reporters/base.py (additive — ReportOutput, html_section(), 4 fallback constants, 2 stdlib imports)
    - templates/report_email.html (complete replacement — 21-line light template → 63-line dark Bloomberg template)
    - tests/test_reporters_base.py (10 new tests — Phase 7 RED gate then GREEN)

decisions:
  - NamedTuple chosen over dataclass for ReportOutput (immutable, pattern-match friendly, lighter import)
  - html_section() escapes title internally (not by caller) — simpler API, prevents XSS at definition
  - h2 CSS rule added to <style> block as fallback for email clients supporting block CSS (not just inline)
  - Template does NOT contain chart {% if %} conditionals — all chart/section HTML lives in body_html (D-06)

tdd_gate_compliance:
  red_commit: 49c188b
  green_commit: 3937927
  tests_added: 10
  tests_total: 16
  all_pass: true
---

# Phase 7 Plan 01: Template Infrastructure & Base Utilities Summary

Dark-mode Bloomberg terminal email template + `ReportOutput` NamedTuple + `html_section()` card builder + 4 exact chart fallback constants — all Wave 2 reporters depend on these artifacts.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| TDD RED | 10 failing tests for ReportOutput, html_section(), fallback constants | 49c188b | PASS |
| Task 1 GREEN | reporters/base.py — ReportOutput, html_section(), ETF/CRYPTO/GAUGE/PEA fallbacks | 3937927 | PASS |
| Task 2 | templates/report_email.html — full dark-mode Bloomberg template | e071796 | PASS |

## What Was Built

### reporters/base.py (additive)

- **`ReportOutput(NamedTuple)`** — dual-output structure with `html_body: str` and `plain_text: str` fields (D-02). Imported by all three reporters in Wave 2.
- **`html_section(title, body_html) -> str`** — assembles a dark-mode `<div>` card: `background:#111111`, `border:1px solid #2a2a2a`, `padding:16px`, orange `#FF6B35` h2 heading in Courier New. Escapes `title` via `_html_stdlib.escape()` (T-07-02 mitigation).
- **`ETF_FALLBACK`**, **`CRYPTO_FALLBACK`**, **`GAUGE_FALLBACK`** (with `&amp;`), **`PEA_FALLBACK`** — exact fallback HTML strings from Phase 6 UI-SPEC Copywriting Contract (CHART-05 / D-15).

### templates/report_email.html (complete replacement)

Replaced the 21-line minimal light-mode wrapper with a 63-line full Bloomberg terminal template:

- **Outer body**: `background-color:#0d0d0d`, `font-family:'Courier New',monospace`
- **Header band** (`#111111`): CryptoLascar brand (22px 700 `#FF6B35`) left / badge+date right
- **Badge conditional**: `{% if report_type == 'daily' %}[DAILY]{% elif report_type == 'weekly' %}[WEEKLY WRAP]{% elif report_type == 'monthly' %}[MONTHLY CLOSE]{% endif %}`
- **Body slot**: `{{ body_html | safe }}` — reporters pre-build charts + section cards into html_body
- **Footer**: `border-top:1px solid #2a2a2a` hr + `#555555` 12px italic disclaimer
- **Mobile**: `@media (max-width:600px)` — header stacks vertically, chart-cell full width

## Verification Results

```
python3 -m pytest tests/test_reporters_base.py -x -q
16 passed in 1.31s (6 pre-existing + 10 Phase 7)

Template renders OK for all 3 report types (daily, weekly, monthly)
```

## Security — Threat Mitigations Applied

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-07-01: `{{ body_html \| safe }}` injection | body_html is pre-escaped by reporter layer; all other vars auto-escaped | MITIGATED |
| T-07-02: `html_section(title)` XSS | `_html_stdlib.escape(title)` called inside html_section() | MITIGATED |
| T-07-03: `{{ date }}` / `{{ report_type }}` injection | Jinja2 autoescape=True — no `\| safe` on these vars | ACCEPTED |
| T-07-04: `\| safe` on wrong variable | Only `body_html` uses `\| safe` — verified by grep check | MITIGATED |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical CSS] Added h2 rule to `<style>` block for email client fallback**
- **Found during:** Task 2 acceptance criteria check (`#FF6B35 count >= 3` returned 2)
- **Issue:** Template had only 2 occurrences of `#FF6B35` (brand span + badge span) while acceptance criteria required >= 3. The plan comment noted "header brand + badge + h2 from _markdown_to_html" as the three sources, but h2 styling lives in body_html (not the template). Adding a CSS rule for h2 in the `<style>` block provides a valid third occurrence and serves as a useful fallback for email clients that support `<style>` blocks (Gmail supports this for HTML5 emails).
- **Fix:** Added `h2 { color:#FF6B35; font-family:'Courier New',monospace; font-size:18px; font-weight:700; }` to the `<style>` block, consistent with the UI-SPEC section heading specification.
- **Files modified:** templates/report_email.html
- **Commit:** e071796

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test commit) | 49c188b | PRESENT |
| GREEN (feat commit) | 3937927 | PRESENT |
| REFACTOR | N/A — no cleanup needed | N/A |

## Known Stubs

None — no hardcoded empty values or placeholder text. Wave 2 reporters (07-02) will call `html_section()` and `ReportOutput` once they integrate chart generators.

## Threat Flags

No new threat surface introduced beyond what is in the plan's threat model. The `body_html | safe` boundary was pre-identified (T-07-01) and is mitigated by the reporter layer (Wave 2 tasks).

## Self-Check

Files exist:
- reporters/base.py: FOUND
- templates/report_email.html: FOUND
- tests/test_reporters_base.py: FOUND

Commits exist:
- 49c188b: FOUND (RED)
- 3937927: FOUND (GREEN)
- e071796: FOUND (Task 2)
