# Phase 7: Template Redesign & Integration - Pattern Map

**Mapped:** 2026-05-14
**Files analyzed:** 8 (6 modified + 1 reference + 1 replaced)
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `templates/report_email.html` | template | request-response | `templates/report_email.html` (current) | self (replacement) |
| `delivery/email.py` | utility / delivery | request-response | `delivery/email.py` (current) | self (in-place edit) |
| `reporters/daily.py` | reporter | transform | `reporters/weekly.py`, `reporters/monthly.py` | exact (same role + flow) |
| `reporters/weekly.py` | reporter | transform | `reporters/daily.py`, `reporters/monthly.py` | exact |
| `reporters/monthly.py` | reporter | transform | `reporters/daily.py`, `reporters/weekly.py` | exact |
| `reporters/dispatch.py` | router | request-response | `reporters/dispatch.py` (current) | self (in-place edit) |
| `reporters/base.py` | utility | transform | `reporters/base.py` (current) | self (additive) |
| `charts/__init__.py` | module init | — | — | read-only reference |

---

## Pattern Assignments

### `templates/report_email.html` (template, request-response)

**Analog:** `templates/report_email.html` (current — 21-line wrapper being replaced)

**Current template structure** (lines 1–21 — full file):
```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ subject }}</title>
</head>
<body style="margin:0;padding:0;background-color:#ffffff;font-family:Georgia,serif;color:#222222;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:680px;margin:0 auto;">
    <tr>
      <td style="padding:32px 24px;">
        {{ body_html | safe }}
        <hr style="border:none;border-top:1px solid #dddddd;margin:32px 0;">
        <p style="font-size:11px;color:#888888;font-style:italic;">
          Ceci n'est pas un conseil financier. Informations à titre éducatif uniquement.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>
```

**Patterns to preserve in replacement:**
- `{{ subject }}` in `<title>` (auto-escaped by Jinja2 autoescape)
- `{{ body_html | safe }}` — MUST keep `| safe` filter; `body_html` is pre-escaped by reporter layer
- Outer `<table width="100%" ... max-width:680px; margin:0 auto>` centering pattern
- `cellpadding="0" cellspacing="0"` on all tables (email-client reset)
- `padding:32px 24px` on the main content `<td>` (outer wrapper — xl spacing token)
- Footer `<hr>` + disclaimer paragraph at bottom

**New template variables added (from UI-SPEC):**
- `{{ report_type }}` — drives header badge (`daily` / `weekly` / `monthly`); auto-escaped
- `{{ date }}` — ISO date string in header; auto-escaped
- Badge mapping via Jinja2 conditional:
  ```jinja2
  {% if report_type == 'daily' %}[DAILY]
  {% elif report_type == 'weekly' %}[WEEKLY WRAP]
  {% elif report_type == 'monthly' %}[MONTHLY CLOSE]{% endif %}
  ```

**Dark-mode color replacements (from UI-SPEC):**
- `background-color:#ffffff` → `background-color:#0d0d0d` (body + outer)
- `color:#222222` → `color:#e0e0e0` (body text)
- `border-top:1px solid #dddddd` → `border-top:1px solid #2a2a2a` (hr)
- Footer color: `#888888` → `#555555`, font-size `11px` → `12px`
- Remove `font-family:Georgia,serif` → `font-family:'Courier New',monospace` everywhere

**Chart fallback pattern (CHART-05 / D-15):** When chart `Optional[str]` is `None`, reporter passes fallback HTML string. Template receives it already in `body_html` — no `{% if %}` needed for charts in the template itself.

---

### `delivery/email.py` (utility/delivery, request-response)

**Analog:** `delivery/email.py` (current — in-place modifications)

**Imports block** (lines 9–22 — no new imports needed for Phase 7):
```python
from __future__ import annotations

import html as html_stdlib
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import Config
from logging_setup import get_logger
```

**Jinja2 environment — module-level, unchanged** (lines 35–38):
```python
_JINJA_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)
```
This wiring is NOT touched in Phase 7. Template swap is a file replacement; `_JINJA_ENV` stays identical.

**`_markdown_to_html()` — current pattern to update in-place** (lines 69–97):
```python
def _markdown_to_html(text: str) -> str:
    lines = text.split("\n")
    html_lines = []
    for line in lines:
        if line.startswith("## "):
            safe_content = html_stdlib.escape(line[3:])
            html_lines.append(
                f'<h2 style="color:#1a1a2e;font-size:18px;margin-top:24px;">{safe_content}</h2>'
            )
        elif line.startswith("# "):
            safe_content = html_stdlib.escape(line[2:])
            html_lines.append(
                f'<h1 style="color:#1a1a2e;font-size:22px;">{safe_content}</h1>'
            )
        elif line.strip() == "":
            html_lines.append("")
        else:
            html_lines.append(html_stdlib.escape(line))
    raw = "\n".join(html_lines)
    raw = re.sub(r"\n{2,}", "</p><p>", raw)
    return f"<p>{raw}</p>"
```
**Changes required (D-17 / UI-SPEC `_markdown_to_html()` Update Contract):**
- `h2` style: `color:#1a1a2e` → `color:#FF6B35`, add `font-family:'Courier New',monospace;font-weight:700;line-height:1.2;margin-bottom:12px;`
- `h1` style: same color swap + font additions
- Bare text lines: currently `html_stdlib.escape(line)` with no `<p>` wrapping per line. The `<p>` wrapper uses `re.sub` for double newlines. Update the generated `<p>` to carry `style="color:#e0e0e0;font-family:'Courier New',monospace;font-size:14px;line-height:1.6;"` — the `f"<p>{raw}</p>"` template at line 97 must become the styled version, and the `re.sub` replacement `</p><p>` must also include the style attribute.

**`send_email()` — current signature** (lines 131–138):
```python
def send_email(
    report_type: str,
    date: str,
    plain_text: str,
    config: Config,
    month: str = "",
    year: str = "",
) -> None:
```
**Changes required (D-02, D-03):**
- Accept `html_body: str = ""` as an additional parameter (or accept a `ReportOutput` namedtuple/dataclass)
- When `html_body` is truthy: bypass `_markdown_to_html()`, pass `html_body` directly to `template.render(..., body_html=html_body)`
- When `html_body` is falsy (legacy path): keep `body_html = _markdown_to_html(plain_text)` as-is
- Add `report_type` and `date` to `template.render()` call (new template variables)
- `plain_text` continues to feed `MIMEText(plain_text, "plain", "utf-8")` unchanged (D-05)

**Current template render call** (lines 160–161):
```python
template = _JINJA_ENV.get_template("report_email.html")
html_content = template.render(subject=subject, body_html=body_html)
```
Must become:
```python
html_content = template.render(
    subject=subject,
    body_html=body_html,
    report_type=report_type,
    date=date,
)
```

**Security patterns to preserve — `archive_report()`** (lines 112–114):
```python
if not _SAFE_TYPE_RE.match(report_type):
    raise ValueError(f"Invalid report_type: {report_type!r}")
if not _SAFE_DATE_RE.match(date):
    raise ValueError(f"Invalid date format: {date!r}")
```
These regex guards (`_SAFE_DATE_RE`, `_SAFE_TYPE_RE`) must NOT be removed (T-04-01, CR-02).

**SMTP error handling pattern to preserve** (lines 197–203):
```python
except Exception as e:
    # T-04-01 : smtp_password JAMAIS loggé
    logger.error(
        "Email send failed: report_type=%s recipients=%d error=%s",
        report_type, len(config.recipient_list), str(e),
    )
    raise
```

---

### `reporters/daily.py` (reporter, transform)

**Analog:** `reporters/weekly.py` and `reporters/monthly.py` (same role/flow — will all change identically)

**Current build function signature** (line 163):
```python
def build_daily_report(data: dict, config: Config) -> str:
```
**Change required (D-02):** Return type changes from `str` to a named structure with `html_body: str` and `plain_text: str`.

**Current return pattern** (lines 186–210):
```python
try:
    sections = [
        _macro_section(data, config),
        _etf_section(data, config),
        _crypto_section(data, config),
        _pea_section(data, config),
        _news_section(data, config),
        _one_signal_section(data, config),
    ]
    return "\n".join(sections)
except Exception as e:
    logger.error("build_daily_report failed: %s", e)
    return "\n".join(
        build_section(t, "[Section indisponible.]")
        for t in (
            "Macro Snapshot", "ETF Radar", "Crypto Pulse",
            "PEA Alert", "News Feed", "One Signal",
        )
    )
```
**New pattern:** The `"\n".join(sections)` string becomes `plain_text`. Then call chart generators (from `charts/`) to build `html_body`. Return `ReportOutput(html_body=..., plain_text=plain_text)`.

**Section builder pattern (unchanged)** — each `_xxx_section()` still returns Markdown string via `build_section()` (line 67 of base.py):
```python
def build_section(title: str, body: str) -> str:
    return f"## {title}\n\n{body}\n"
```
These strings are concatenated into `plain_text`. The `html_body` is built separately by the reporter using chart generators + `_markdown_to_html()` or an `html_section()` helper.

**Graceful degradation pattern to preserve** (lines 35–39 of daily.py — section-level):
```python
if macro.get("source_failed"):
    return build_section(
        "Macro Snapshot",
        "Données macro indisponibles ce matin (source FRED en échec).",
    )
```
Pattern: every `_xxx_section()` checks `source_failed` before accessing data. This applies to both `plain_text` sections and when building the `html_body` section cards.

**Chart generator import pattern to add** (from `charts/__init__.py`):
```python
from charts import (
    generate_etf_chart,
    generate_crypto_sparklines,
    generate_fear_greed_gauge,
    generate_pea_table,
)
```
All four return `Optional[str]`. Callers must check for `None` and substitute fallback HTML.

---

### `reporters/weekly.py` (reporter, transform)

**Analog:** `reporters/daily.py`, `reporters/monthly.py` — identical structural change

**Current build function signature** (line 147):
```python
def build_weekly_report(data: dict, config: Config) -> str:
```
**Change required:** Same as daily — return `ReportOutput(html_body=..., plain_text=...)`.

**Current return pattern** (lines 158–175):
```python
try:
    sections = [
        _executive_summary(data, config),
        _macro_watch(data, config),
        _etf_performance(data, config),
        _crypto_recap(data, config),
        _pea_wrap(data, config),
        _news_digest(data, config),
        _outlook(data, config),
    ]
    return "\n".join(sections)
except Exception as e:
    logger.error("build_weekly_report failed: %s", e)
    return "\n".join(
        build_section(t, "[Section indisponible.]")
        for t in ("Executive Summary", "Macro Watch", "ETF Performance",
                  "Crypto Recap", "PEA Wrap", "News Digest", "Outlook")
    )
```
Identical transform as daily: `"\n".join(sections)` → `plain_text`; chart calls + HTML build → `html_body`.

**Markdown table helper** (lines 31–38) — used for `plain_text` path, no change needed:
```python
def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return ""
    head = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join(["---"] * len(headers)) + "|"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return f"{head}\n{sep}\n{body}"
```

---

### `reporters/monthly.py` (reporter, transform)

**Analog:** `reporters/daily.py`, `reporters/weekly.py` — identical structural change

**Current build function signature** (line 174):
```python
def build_monthly_report(data: dict, config: Config) -> str:
```
**Change required:** Same dual-output return as daily and weekly.

**Current return pattern** (lines 198–224):
```python
try:
    sections = [
        _month_in_review(data, config),
        _macro_backdrop(data, config),
        _etf_monthly(data, config),
        _crypto_monthly(data, config),
        _pea_monthly(data, config),
        _news_themes(data, config),
        _forward_look(data, config),
    ]
    return "\n".join(sections)
except Exception as e:
    logger.error("build_monthly_report failed: %s", e)
    return "\n".join(
        build_section(t, "[Section indisponible.]")
        for t in (
            "Month in Review", "Macro Backdrop", "ETF Monthly Performance",
            "Crypto Monthly", "PEA Monthly", "News & Themes", "Forward Look",
        )
    )
```
Same transform. Monthly uses `max_tokens=600` for `_month_in_review` and `_forward_look` — this is unchanged.

---

### `reporters/dispatch.py` (router, request-response)

**Analog:** `reporters/dispatch.py` (current — minimal in-place edit)

**`_safe_build()` current pattern** (lines 64–82):
```python
def _safe_build(builder, name: str, data: dict, config: Config) -> str:
    try:
        return builder(data, config)
    except Exception as e:
        logger.error("%s build failed: %s", name, e)
        return f"[{name} indisponible — erreur lors de la construction du rapport.]"
```
**Change required:** Return type annotation changes from `str` to the new `ReportOutput` type. The fallback must also return a `ReportOutput` (with fallback `html_body` and `plain_text`).

**`select_reports()` current signature and return** (lines 85–123):
```python
def select_reports(today: _dt.date, data: dict, config: Config) -> Dict[str, str]:
    ...
    result["daily"] = _safe_build(build_daily_report, "Daily Report", data, config)
    return result
```
**Change required:** Return type becomes `Dict[str, ReportOutput]` (or equivalent). All three builder calls through `_safe_build()` return the new type.

**`main.py` pipeline consumption** (lines 213–229 of main.py):
```python
reports = select_reports(today, data, config)
for report_type, report_text in reports.items():
    ...
    archive_report(report_type, date_str, report_text)
    send_email(report_type, date_str, report_text, config,
               month=month_fr, year=year_str)
```
After Phase 7, `report_text` becomes a `ReportOutput`. `archive_report()` receives `report_text.plain_text` (unchanged Markdown). `send_email()` receives the full `ReportOutput` or its fields unpacked. The planner must audit `main.py` lines 214–229 to update this loop.

---

### `reporters/base.py` (utility, transform)

**Analog:** `reporters/base.py` (current — additive change only)

**Current `build_section()` pattern** (lines 65–67):
```python
def build_section(title: str, body: str) -> str:
    """Assemble une section au format Markdown : '## {title}\\n\\n{body}\\n'."""
    return f"## {title}\n\n{body}\n"
```
This function is NOT changed — it continues to serve the `plain_text` path.

**Potential new `html_section()` helper** (D-10 / CONTEXT.md §Integration Points):
If added, it mirrors `build_section()` but returns a dark-mode `<div>` card per UI-SPEC:
```python
def html_section(title: str, body_html: str) -> str:
    """Assemble une section HTML dark-mode card."""
    # title is already HTML-escaped by caller (via html.escape())
    return (
        '<div style="background:#111111;border:1px solid #2a2a2a;'
        'padding:16px;margin-bottom:8px;">'
        f'<h2 style="color:#FF6B35;font-family:\'Courier New\',monospace;'
        f'font-size:18px;font-weight:700;margin-top:0;margin-bottom:12px;'
        f'line-height:1.2;">{title}</h2>'
        f'{body_html}'
        '</div>'
    )
```
Planner decides whether to place this in `base.py` or inline in each reporter. The pattern above is directly from UI-SPEC Layout Structure §Narrative Sections.

**`FALLBACK_TEMPLATE` constant** (line 19):
```python
FALLBACK_TEMPLATE = "[Section indisponible — synthèse Claude temporairement indisponible.]"
```
Unchanged — used in `synthesize_section()` graceful degradation and referenced in UI-SPEC Copywriting Contract.

---

### `charts/__init__.py` (module init — read-only reference)

**Public API** (lines 45–50):
```python
__all__ = [
    "generate_etf_chart",
    "generate_crypto_sparklines",
    "generate_fear_greed_gauge",
    "generate_pea_table",
]
```

**Return types:**
- `generate_etf_chart(etf_data, date_str)` → `Optional[str]` (base64 PNG string)
- `generate_crypto_sparklines(btc_history, eth_history)` → `Optional[str]` (base64 PNG string)
- `generate_fear_greed_gauge(score)` → `Optional[str]` (base64 PNG string)
- `generate_pea_table(pea_data)` → `Optional[str]` (HTML string — NOT a PNG)

**CHART-05 graceful degradation — import guard pattern** (lines 29–43):
```python
try:
    from charts.gauge import generate_fear_greed_gauge
except ImportError as e:
    import logging as _logging
    _logging.getLogger(__name__).error(f"charts.gauge unavailable: {e}")
    def generate_fear_greed_gauge(score) -> None:
        return None
```
Reporters must treat `None` return as "chart unavailable" and substitute the exact fallback HTML from UI-SPEC.

**IMG tag template for base64 PNG (from Phase 6 UI-SPEC):**
```html
<img src="data:image/png;base64,{b64_string}"
     alt="{alt_text}"
     style="display:block;max-width:100%;height:auto;margin:16px 0;" />
```

---

## Shared Patterns

### Reporter Dual-Output Return Type
**Applies to:** `reporters/daily.py`, `reporters/weekly.py`, `reporters/monthly.py`, `reporters/dispatch.py`

All three reporters change from `-> str` to a named structure. Pattern choice (namedtuple vs dataclass — planner decides):

**namedtuple option:**
```python
from typing import NamedTuple

class ReportOutput(NamedTuple):
    html_body: str
    plain_text: str
```

**dataclass option:**
```python
from dataclasses import dataclass

@dataclass
class ReportOutput:
    html_body: str
    plain_text: str
```

Place definition in `reporters/base.py` (shared module) so all three reporters import from one location.

### Chart Fallback HTML Strings
**Source:** Phase 6 UI-SPEC Copywriting Contract + UI-SPEC §Chart Panel
**Applies to:** All three reporters when calling chart generators

```python
# Use exactly these strings when chart function returns None:
ETF_FALLBACK    = '<p style="color:#888;font-style:italic;">[Graphique ETF indisponible]</p>'
CRYPTO_FALLBACK = '<p style="color:#888;font-style:italic;">[Graphique crypto indisponible]</p>'
GAUGE_FALLBACK  = '<p style="color:#888;font-style:italic;">[Gauge Fear &amp; Greed indisponible]</p>'
PEA_FALLBACK    = '<p style="color:#888;font-style:italic;">[Tableau PEA indisponible]</p>'
```
Define these constants in `reporters/base.py` alongside `FALLBACK_TEMPLATE`, or inline in each reporter. The exact strings are from the UI-SPEC — do not paraphrase.

### Graceful Degradation — Never Raise
**Source:** `reporters/daily.py` (lines 186–210), `reporters/weekly.py` (lines 158–175), `reporters/monthly.py` (lines 198–224)
**Applies to:** All reporter build functions, `dispatch._safe_build()`

The outer `try/except Exception` in every `build_*_report()` function must be preserved. When Phase 7 adds chart generation calls inside the `try` block, any chart exception is absorbed by this filet, which returns the dual-output fallback (both `html_body` and `plain_text` as degraded strings).

### Security — Credential Logging Prohibition
**Source:** `delivery/email.py` (lines 197–203), `reporters/base.py` (lines 59–62), `reporters/daily.py` (lines 197–198)
**Applies to:** All modified files

```python
# NEVER log config, smtp_password, or api_key — log only: report_type, len(recipients), str(e)
logger.error("Email send failed: report_type=%s recipients=%d error=%s",
             report_type, len(config.recipient_list), str(e))
```
Pattern: `str(e)` or `type(e).__name__` only in error logs — never `str(config)` or any credential field.

### HTML Escaping Contract
**Source:** `delivery/email.py` (lines 80–81, 84–85, 92), `templates/report_email.html` (line 12)
**Applies to:** `templates/report_email.html`, `delivery/email.py`, all reporters building `html_body`

- `body_html` in template: always `{{ body_html | safe }}` — reporter output is trusted pre-escaped HTML
- Template variables `subject`, `report_type`, `date`: never use `| safe` — Jinja2 autoescape handles them
- In `_markdown_to_html()`: `html_stdlib.escape()` is called on every user-visible string before wrapping in HTML tags (lines 80, 84, 92)
- In `html_section()` (if added to base.py): title parameter must be `html.escape()`-d by caller

### `_SAFE_TYPE_RE` + `_SAFE_DATE_RE` Path Traversal Guards
**Source:** `delivery/email.py` (lines 31–32, 112–116)
**Applies to:** `delivery/email.py` (unchanged — preserve as-is)

```python
_SAFE_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SAFE_TYPE_RE = re.compile(r"^(daily|weekly|monthly)$")
```
These guards in `archive_report()` are NOT touched by Phase 7 changes.

---

## No Analog Found

No files in Phase 7 lack a codebase analog. All modifications are in-place edits to existing files with strong self-analogy or cross-reporter analogy.

---

## Metadata

**Analog search scope:** `templates/`, `delivery/`, `reporters/`, `charts/`, `main.py`
**Files read:** 10 (report_email.html, email.py, daily.py, weekly.py, monthly.py, base.py, dispatch.py, charts/__init__.py, main.py, 06-UI-SPEC.md)
**Pattern extraction date:** 2026-05-14
