---
phase: 6
slug: chart-generation
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-14
---

# Phase 6 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| VPS environment → matplotlib | Agg backend must be forced before any pyplot import | No display env var on headless server |
| PyPI packages → application | Dependencies (matplotlib, numpy, Pillow) from official PyPI only | Package integrity / supply chain |
| collector data → chart functions | etf_data and crypto history values are floats from external APIs | External API float values |
| chart functions → email HTML | Base64 PNG output embedded in email body | Binary image data |
| collector data → gauge | Score value from Fear & Greed API; must be validated 0–100 before use | External API integer value |
| collector data → PEA table | pea_data dict content must not allow XSS injection into HTML output | External-origin string fields (ticker, name) |
| chart HTML output → email body | PEA table HTML string embedded directly in email body | HTML markup |
| test process → chart module | Tests import and invoke real chart functions; Agg backend must be active | Test isolation |
| mock patches → chart internals | patch.object must target correct module attribute | Test correctness |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-06-01 | Denial of Service | matplotlib Agg backend | mitigate | `matplotlib.use("Agg")` called at `charts/__init__.py` line 24 before any pyplot import — verified present | closed |
| T-06-02 | Tampering | requirements.txt supply chain | mitigate | matplotlib>=3.8.0, numpy>=1.26.0, Pillow>=10.0.0 listed in requirements.txt with no --extra-index-url or private registry — verified | closed |
| T-06-03 | Denial of Service | missing chart submodule import | accept | Expected transient state until Plans 02–03 execute; documented in PLAN.md and SUMMARY-01 — see accepted risks | closed |
| T-06-04 | Denial of Service | generate_etf_chart with malformed input | mitigate | Outer `except Exception` catches all failures; returns None; pipeline continues — verified in charts/etf.py:137 | closed |
| T-06-05 | Denial of Service | generate_crypto_sparklines with malformed input | mitigate | Same outer `except Exception` pattern; returns None — verified in charts/crypto.py:123 | closed |
| T-06-06 | Tampering | Float conversion from API data | mitigate | Explicit `float(v)` cast in charts/crypto.py:62–63; ValueError caught by outer try/except — verified | closed |
| T-06-07 | Information Disclosure | Exception messages in etf/crypto logs | accept | Logs only `str(e)`, never raw API responses or credentials — consistent with v1.0 pattern — see accepted risks | closed |
| T-06-08 | Denial of Service | matplotlib figure leak on exception | mitigate | `plt.close("all")` in except branch of etf.py:140 and crypto.py:126 — verified | closed |
| T-06-09 | Tampering | generate_fear_greed_gauge score validation | mitigate | Explicit `0.0 <= score <= 100.0` check at gauge.py:86; out-of-range logs error and returns None — verified | closed |
| T-06-10 | Denial of Service | matplotlib Wedge rendering with invalid geometry | mitigate | Outer `except Exception` at gauge.py:177; `plt.close("all")` at gauge.py:181 — verified | closed |
| T-06-11 | Injection (XSS) | generate_pea_table ticker/name in HTML | mitigate | `html.escape(..., quote=True)` on ticker and name fields at pea.py:161–162; ASVS L1 output encoding — verified | closed |
| T-06-12 | Information Disclosure | Exception messages in gauge/pea logs | accept | Logs only `str(e)` — no API keys or credentials in chart module scope — see accepted risks | closed |
| T-06-13 | Denial of Service | generate_pea_table with large dataset | accept | Table size bounded by PEA holdings (5–30 rows typical); no pagination needed at this scale — see accepted risks | closed |
| T-06-14 | Denial of Service | test_charts.py — matplotlib Agg not set before test runner | mitigate | charts/__init__.py calls `matplotlib.use("Agg")` at import time; any `charts.*` import in tests triggers this — verified | closed |
| T-06-15 | Tampering | Incorrect mock target invalidates CHART-05 test | mitigate | `patch.object(charts_etf.plt, "subplots", ...)` pattern used at test_charts.py:241 — targets module-level import correctly — verified | closed |
| T-06-16 | Denial of Service | pip install failure during test setup | accept | CI environment responsibility; test file itself does not install dependencies — see accepted risks | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-03 | ImportError for chart submodules expected until Plans 02–03 execute; transient state documented in PLAN.md threat register and SUMMARY-01 | gsd-security-auditor | 2026-05-14 |
| AR-06-02 | T-06-07 | etf/crypto exception logs emit `str(e)` only; no credentials, API keys, or raw API responses exist in chart module scope — consistent with v1.0 logging pattern established in phases 02-01 through 02-04 | gsd-security-auditor | 2026-05-14 |
| AR-06-03 | T-06-12 | gauge/pea exception logs emit `str(e)` only; same justification as AR-06-02 | gsd-security-auditor | 2026-05-14 |
| AR-06-04 | T-06-13 | PEA table size bounded by real-world holdings (5–30 rows); no adversarial input path to this function — data originates from pea.py collector under user control | gsd-security-auditor | 2026-05-14 |
| AR-06-05 | T-06-16 | pip install failures are CI environment responsibility; chart test file does not manage dependency installation and this is by design | gsd-security-auditor | 2026-05-14 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-14 | 16 | 16 | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-14
