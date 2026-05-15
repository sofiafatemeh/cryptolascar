---
phase: 07
slug: template-redesign-integration
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-15
---

# Phase 7 — Security: Template Redesign & Integration

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| reporter `html_body` → `{{ body_html \| safe }}` in template | `html_body` is pre-escaped by reporter layer; template uses `\| safe` only on this variable; all other Jinja2 vars auto-escaped | Pre-sanitized HTML — trusted origin (reporter code, not user input) |
| `html_section(title)` — title parameter → `<h2>` HTML | Title must pass through `html.escape()` inside `html_section()` before insertion | Markdown section heading string — may contain `<>` from API output |
| `{{ subject }}`, `{{ date }}`, `{{ report_type }}` → Jinja2 render | Auto-escaped by `autoescape=select_autoescape(['html'])` — no `\| safe` marker | ISO date string, fixed report type string, subject string |
| `send_email(html_body=)` — reporter-built HTML → SMTP | `html_body` originates from reporter builders only (not user input); passed with `\| safe` in template | Pre-built HTML from trusted pipeline layer |
| SMTP credentials → `logger` | `smtp_password` must never appear in any logger call | Sensitive credential — restricted to SMTP login call only |
| chart generator output → `_build_chart_panel()` → `html_body` | Chart generators return `Optional[str]` (base64 PNG or HTML); embedded directly in chart cells | Base64 strings (alphanumeric-safe) or Phase 6 reporter HTML (trusted) |
| Markdown section text → `_sections_to_html()` → `html_section()` body | `html.escape()` applied to body markdown text before wrapping in `<p>` tag | Build-section output — not user input, but may contain `<>` characters |
| `select_reports()` → `main.py` pipeline loop | `report_text` is now `ReportOutput`; `.plain_text` and `.html_body` accessed explicitly | Typed struct — enforced by NamedTuple contract |
| `report_text.plain_text` → `archive_report()` | `archive_report()` validates `report_type` via `_SAFE_TYPE_RE` and `date` via `_SAFE_DATE_RE` before disk write | Markdown string — validated at boundary |
| `report_text.plain_text` → `write_tweet()` | `write_tweet()` receives Markdown string (not `ReportOutput` object) | Plain Markdown — no HTML escaping concerns |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-07-01 | Injection | `templates/report_email.html — {{ body_html \| safe }}` | mitigate | `html_body` is pre-escaped by reporter layer (`html.escape()` on all user-visible strings via `_markdown_to_html()` and `html_section()`); `\| safe` only on `html_body`; all other template vars auto-escaped | closed |
| T-07-02 | Injection | `reporters/base.py html_section(title)` — XSS via title parameter | mitigate | `html_section()` calls `_html_stdlib.escape(title)` on title before inserting into `<h2>` — raw title never reaches HTML output | closed |
| T-07-03 | Injection | `templates/report_email.html — {{ date }}` and `{{ report_type }}` | accept | Both variables are auto-escaped by Jinja2 `autoescape=True`; production values are ISO date strings and fixed strings (`"daily"`/`"weekly"`/`"monthly"`) — no user input path | closed |
| T-07-04 | Tampering | Jinja2 autoescape bypass — `\| safe` used on wrong variable | mitigate | Template only uses `\| safe` on `body_html`; `subject`, `report_type`, `date` are never marked safe; enforced by acceptance_criteria grep check | closed |
| T-07-05 | Injection | `send_email(html_body=)` — if caller passes unsanitized user input | mitigate | `html_body` originates from reporter builders only (`reporters/daily.py` etc.); those functions call `html_stdlib.escape()` on all user-visible strings; html_body path is reporter-generated, not user-input | closed |
| T-07-06 | Information Disclosure | SMTP error handler — risk of logging `smtp_password` | mitigate | Error handler uses `report_type`, `len(config.recipient_list)`, `str(e)` only; `smtp_password` count in logger calls = 0 (verified by acceptance_criteria grep) | closed |
| T-07-07 | Tampering | `_SAFE_TYPE_RE` / `_SAFE_DATE_RE` removal during email.py refactor | mitigate | Both regexes are in `archive_report()` which was not modified in this phase; acceptance_criteria grep confirms both present with count=2 | closed |
| T-07-08 | Injection | `_build_chart_panel()` — PEA table HTML from `generate_pea_table()` inserted directly | accept | `generate_pea_table` is Phase 6 reporter code (not user input); output is trusted HTML; no user-controlled strings reach this path | closed |
| T-07-09 | Injection | `html_section(title, body_html)` in `build_*_report()` — section `body_html` from Markdown text | mitigate | `html.escape()` applied to `body_md` before wrapping in `<p>` tag inside `_sections_to_html()`; title escaped inside `html_section()` via `_html_stdlib.escape(title)` | closed |
| T-07-10 | Availability | Chart generator raises Exception — could break entire report | mitigate | Each chart call in `_build_chart_panel()` individually wrapped in `try/except`; outer `try/except` in `build_*_report()` catches any remaining exception and returns degraded `ReportOutput`; email is always sent (CHART-05 / D-15) | closed |
| T-07-11 | Information Disclosure | Credential logging in `_build_chart_panel()` / `build_*_report()` except blocks | mitigate | `logger.error` calls use only `str(e)` — never `config`, `api_key`, or `smtp_password` | closed |
| T-07-12 | Injection | `archive_report(report_type, date_str, report_text)` — passing `ReportOutput` object instead of `str` | mitigate | `main.py` Task 2 replaces `report_text` with `report_text.plain_text`; `archive_report()` receives a `str` as expected; `_SAFE_TYPE_RE` and `_SAFE_DATE_RE` guards unchanged | closed |
| T-07-13 | Injection | `write_tweet(report_type, date_str, report_text, config)` — passing `ReportOutput` instead of `str` | mitigate | `main.py` Task 2 replaces `report_text` with `report_text.plain_text`; `write_tweet()` receives plain Markdown string | closed |
| T-07-14 | Tampering | Integration test mocking — incorrect patch targets could silently pass while production code fails | mitigate | Acceptance criteria require `pytest exits 0`; patch targets verified against actual import paths in `reporters/daily.py` (`reporters.daily.generate_*`, `reporters.daily.synthesize_section`); 11 integration tests pass | closed |
| T-07-15 | Information Disclosure | `_safe_build()` fallback log — risk of logging `config` in new fallback `ReportOutput` construction | mitigate | Fallback uses `name` (reporter name string) only — no config fields, no `api_key`, no `smtp_password` in the fallback `html_body` or `plain_text` strings | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-07-01 | T-07-03 | `{{ date }}` and `{{ report_type }}` are auto-escaped by Jinja2 autoescape; production values are ISO date strings and fixed enum strings — no user input path exists for these variables | gsd-secure-phase | 2026-05-15 |
| AR-07-02 | T-07-08 | `generate_pea_table()` returns trusted HTML from Phase 6 reporter code; PEA data originates from market data APIs (Euronext/Yahoo Finance), not user-controlled input; HTML is embedded as-is in chart panel | gsd-secure-phase | 2026-05-15 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-15 | 15 | 15 | 0 | gsd-secure-phase (State B — from PLAN.md + SUMMARY.md artifacts) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-15
