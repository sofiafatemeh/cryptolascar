---
phase: 6
slug: 06-chart-generation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-14
audited: 2026-05-14
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for the charts/ package (matplotlib chart generators).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | none (rootdir auto-detected) |
| **Quick run command** | `python3 -m pytest tests/test_charts.py -q` |
| **Full suite command** | `python3 -m pytest tests/test_charts.py tests/test_charts_etf.py tests/test_charts_crypto.py tests/test_charts_gauge_pea.py -v` |
| **Estimated runtime** | ~7 seconds |
| **Last run result** | 80 passed, 0 failed |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_charts.py -q`
- **After every plan wave:** Run full suite command above
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~7 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-T1 | 01 | 1 | CHART-01..05 | T-06-01 | `matplotlib.use("Agg")` called at import — no DISPLAY crash on VPS | grep + unit | `grep 'matplotlib\.use.*Agg' charts/__init__.py` | ✅ | ✅ green |
| 06-01-T2 | 01 | 1 | CHART-01..05 | T-06-02 | PyPI-only deps declared with minimum versions | grep | `grep 'matplotlib>=3.8.0' requirements.txt` | ✅ | ✅ green |
| 06-02-T1 | 02 | 2 | CHART-01 | T-06-04 | generate_etf_chart returns valid base64 PNG or None — never raises | unit | `python3 -m pytest tests/test_charts.py tests/test_charts_etf.py -k etf -q` | ✅ | ✅ green |
| 06-02-T2 | 02 | 2 | CHART-02 | T-06-05 T-06-06 | generate_crypto_sparklines returns valid base64 PNG or None — float cast catches invalid values | unit | `python3 -m pytest tests/test_charts.py tests/test_charts_crypto.py -k crypto -q` | ✅ | ✅ green |
| 06-03-T1 | 03 | 2 | CHART-03 | T-06-09 T-06-10 | Score validated in [0,100]; out-of-range/None → None; Wedge rendering error caught by except | unit | `python3 -m pytest tests/test_charts.py tests/test_charts_gauge_pea.py -k gauge -q` | ✅ | ✅ green |
| 06-03-T2 | 03 | 2 | CHART-04 | T-06-11 | Ticker/name values HTML-escaped (XSS mitigated); empty/None → None | unit | `python3 -m pytest tests/test_charts.py tests/test_charts_gauge_pea.py -k pea -q` | ✅ | ✅ green |
| 06-04-T1 | 04 | 3 | CHART-01..05 | T-06-14 T-06-15 | All 4 functions return None when plt.subplots raises RuntimeError; package exports all 4 names | unit | `python3 -m pytest tests/test_charts.py -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Test Files

| File | Tests | Requirements |
|------|-------|--------------|
| `tests/test_charts.py` | 36 (22 unique def test_ + 14 parametrized) | CHART-01..05 — full integration + fallback |
| `tests/test_charts_etf.py` | 6 | CHART-01 — ETF chart edge cases |
| `tests/test_charts_crypto.py` | 8 | CHART-02 — sparkline edge cases |
| `tests/test_charts_gauge_pea.py` | 30 | CHART-03 gauge zone boundaries, CHART-04 PEA table + XSS (T-06-11) |
| **Total** | **80** | **All phase requirements** |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.
- pytest already installed (pytest 9.0.3)
- test files created as part of Plan 04 (Wave 3) execution
- No stub stubs needed — all chart functions fully implemented before tests were written

---

## Manual-Only Verifications

All phase behaviors have automated verification.

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual color accuracy of chart output | CHART-01..03 | Pixel-level rendering cannot be fully asserted in pytest — color tokens verified by constant grep, not visual inspection | Open daily email report in browser, visually confirm dark theme, correct colors, gauge needle position |
| Email embedding of base64 PNG | CHART-01..03 | End-to-end email delivery not in unit scope | Trigger `main.py` and inspect received email in client |

---

## Validation Audit 2026-05-14

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated to manual-only | 2 (visual color accuracy, email embedding) |
| Total tests verified | 80 |
| Test files | 4 |
| Requirements covered | 5/5 (CHART-01 through CHART-05) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none — all covered)
- [x] No watch-mode flags
- [x] Feedback latency < 10s (actual: ~7s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-14
