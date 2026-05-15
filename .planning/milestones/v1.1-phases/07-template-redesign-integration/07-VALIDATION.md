---
phase: 07-template-redesign-integration
slug: 07
status: complete
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-15
audited: 2026-05-15
---

# Phase 7 — Validation Strategy

> Per-phase validation contract. Reconstructed from 4 SUMMARY artifacts (State B).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python 3.11+) |
| **Config file** | none |
| **Quick run command** | `python3 -m pytest tests/test_template_structure.py tests/test_reporters_daily.py tests/test_reporters_base.py tests/test_email.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -x -q` |
| **Estimated runtime** | ~29 seconds |
| **Suite size** | 292 tests (284 pre-Phase-7 + 8 gap fills) |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|------|--------|
| 07-01-T1 | 01 | 1 | TMPL-01 | T-07-02 | `html_section(title)` escapes title via `html.escape()` | unit | `python3 -m pytest tests/test_reporters_base.py -x -q` | tests/test_reporters_base.py | ✅ green |
| 07-01-T1 | 01 | 1 | TMPL-01 | — | `ReportOutput` is NamedTuple with `html_body`/`plain_text` | unit | `python3 -m pytest tests/test_reporters_base.py -x -q` | tests/test_reporters_base.py | ✅ green |
| 07-01-T1 | 01 | 1 | TMPL-01 | CHART-05 | Fallback constants (ETF/CRYPTO/GAUGE/PEA) are exact strings from spec | unit | `python3 -m pytest tests/test_reporters_base.py -x -q` | tests/test_reporters_base.py | ✅ green |
| 07-01-T2 | 01 | 1 | TMPL-01 | T-07-04 | `{{ date }}` NOT marked `\| safe` (XSS prevention) | unit | `python3 -m pytest tests/test_template_structure.py::test_date_variable_not_marked_safe` | tests/test_template_structure.py | ✅ green |
| 07-01-T2 | 01 | 1 | TMPL-01 | — | Template has no light-mode `#ffffff` background | unit | `python3 -m pytest tests/test_template_structure.py::test_template_has_no_light_mode_white_background` | tests/test_template_structure.py | ✅ green |
| 07-01-T2 | 01 | 1 | TMPL-01 | — | Template has no `Georgia` font (old font removed) | unit | `python3 -m pytest tests/test_template_structure.py::test_template_has_no_georgia_font` | tests/test_template_structure.py | ✅ green |
| 07-01-T2 | 01 | 1 | TMPL-01 | — | `MONTHLY CLOSE` badge conditional present | unit | `python3 -m pytest tests/test_template_structure.py::test_template_has_monthly_close_badge` | tests/test_template_structure.py | ✅ green |
| 07-01-T2 | 01 | 1 | TMPL-02 | — | `@media (max-width:600px)` mobile breakpoint present | unit | `python3 -m pytest tests/test_template_structure.py::test_template_has_mobile_breakpoint` | tests/test_template_structure.py | ✅ green |
| 07-02-T1 | 02 | 2 | TMPL-01 | — | `_markdown_to_html()` outputs `#FF6B35` for h1/h2 (dark-mode) | unit | `python3 -m pytest tests/test_email.py -k markdown -x -q` | tests/test_email.py | ✅ green |
| 07-02-T1 | 02 | 2 | TMPL-01 | — | `_markdown_to_html()` uses Courier New font | unit | `python3 -m pytest tests/test_email.py -k markdown -x -q` | tests/test_email.py | ✅ green |
| 07-02-T1 | 02 | 2 | TMPL-01 | T-07-01 | `_markdown_to_html()` XSS-escapes input | unit | `python3 -m pytest tests/test_email.py::test_markdown_xss_escaping` | tests/test_email.py | ✅ green |
| 07-02-T2 | 02 | 2 | TMPL-03 | T-07-01 | `send_email(html_body=...)` bypasses `_markdown_to_html` when truthy | unit | `python3 -m pytest tests/test_email.py -k html_body -x -q` | tests/test_email.py | ✅ green |
| 07-02-T2 | 02 | 2 | TMPL-03 | — | `template.render()` receives `report_type` and `date` | unit | `python3 -m pytest tests/test_email.py::test_send_email_template_render_receives_report_type tests/test_email.py::test_send_email_template_render_receives_date` | tests/test_email.py | ✅ green |
| 07-02-T2 | 02 | 2 | TMPL-01 | — | SMTP password never logged on error | unit | `python3 -m pytest tests/test_email.py::test_send_email_error_never_logs_password_phase7` | tests/test_email.py | ✅ green |
| 07-03-T1 | 03 | 2 | TMPL-03 | — | `build_daily_report()` returns `ReportOutput` | unit | `python3 -m pytest tests/test_reporters_daily.py::test_build_daily_returns_report_output` | tests/test_reporters_daily.py | ✅ green |
| 07-03-T1 | 03 | 2 | TMPL-03 | CHART-05 | `_build_chart_panel()` uses fallback strings when chart returns `None` | unit | `python3 -m pytest tests/test_reporters_daily.py -k fallback -x -q` | tests/test_reporters_daily.py | ✅ green |
| 07-03-T1 | 03 | 2 | TMPL-03 | T-07-10 | Full failure returns degraded `ReportOutput` (never raises) | unit | `python3 -m pytest tests/test_reporters_daily.py::test_total_degradation_returns_report_output` | tests/test_reporters_daily.py | ✅ green |
| 07-03-T1 | 03 | 2 | TMPL-03 | T-07-09 | `_sections_to_html()` escapes `<script>` in body (XSS) | unit | `python3 -m pytest tests/test_reporters_daily.py::test_sections_to_html_escapes_script_tag_in_body` | tests/test_reporters_daily.py | ✅ green |
| 07-03-T1 | 03 | 2 | TMPL-03 | CR-02 | `_sections_to_html()` emits `white-space:pre-wrap` in `<p>` | unit | `python3 -m pytest tests/test_reporters_daily.py::test_sections_to_html_uses_pre_wrap_style` | tests/test_reporters_daily.py | ✅ green |
| 07-03-T1 | 03 | 2 | TMPL-03 | CR-01 | `build_daily_report()` passes YYYY-MM-DD date_str to chart generator | unit | `python3 -m pytest tests/test_reporters_daily.py::test_build_daily_report_passes_today_date_str_to_chart_generator` | tests/test_reporters_daily.py | ✅ green |
| 07-03-T2 | 03 | 2 | TMPL-03 | — | `build_weekly_report()` returns `ReportOutput` with chart panel | unit | `python3 -m pytest tests/test_reporters_weekly.py -x -q` | tests/test_reporters_weekly.py | ✅ green |
| 07-03-T2 | 03 | 2 | TMPL-03 | — | `build_monthly_report()` returns `ReportOutput` with chart panel | unit | `python3 -m pytest tests/test_reporters_monthly.py -x -q` | tests/test_reporters_monthly.py | ✅ green |
| 07-04-T1 | 04 | 3 | TMPL-03 | T-07-15 | `_safe_build()` returns `ReportOutput` (success and fallback paths) | unit | `python3 -m pytest tests/test_dispatch.py -k reportoutput -x -q` | tests/test_dispatch.py | ✅ green |
| 07-04-T2 | 04 | 3 | TMPL-03 | T-07-12 | `main.py` passes `report_text.plain_text` to `archive_report` (not full `ReportOutput`) | unit | `python3 -m pytest tests/test_main_pipeline.py -x -q` | tests/test_main_pipeline.py | ✅ green |
| 07-04-T3 | 04 | 3 | TMPL-01/03 | — | Full pipeline produces dark-mode HTML (`#0d0d0d`, `#FF6B35`, `[DAILY]`) | integration | `python3 -m pytest tests/test_phase7_integration.py -x -q` | tests/test_phase7_integration.py | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covered all phase requirements — no Wave 0 stubs needed.

*pytest framework was already installed and all fixture patterns established in prior phases.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Status |
|----------|-------------|------------|-------------------|--------|
| Mobile viewport stacking (< 600px) | TMPL-02 | CSS `@media` rendering requires a browser/email-client engine | Open rendered daily report in mobile browser at < 600px — confirm header stacks, chart cells full-width | ✅ UAT passed (2026-05-15) |
| Desktop email client rendering (Gmail, Outlook) | TMPL-02 | Table-based email HTML rendering varies across clients | Open rendered daily/weekly/monthly in desktop email client — confirm 2x2 chart grid, dark bg, orange headings | ✅ UAT passed (2026-05-15) |

*2 manual items — both confirmed via human UAT (07-HUMAN-UAT.md, 4/4 passed).*

---

## Validation Audit 2026-05-15

| Metric | Count |
|--------|-------|
| Gaps found | 8 |
| Resolved | 8 |
| Escalated to manual-only | 0 |
| Pre-existing test count | 284 |
| Post-audit test count | 292 |
| New test files | 1 (`tests/test_template_structure.py`) |
| Modified test files | 1 (`tests/test_reporters_daily.py`) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or manual-only justification
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0: existing infrastructure — no stubs needed
- [x] No watch-mode flags in any test command
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter
- [x] Manual items confirmed via UAT (07-HUMAN-UAT.md)

**Approval:** approved 2026-05-15
