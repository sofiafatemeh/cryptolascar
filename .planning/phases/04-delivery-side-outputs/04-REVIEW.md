---
phase: 04-delivery-side-outputs
reviewed: 2026-05-10T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - delivery/email.py
  - delivery/tweet.py
  - templates/report_email.html
  - tests/test_email.py
  - tests/test_tweet.py
findings:
  critical: 3
  warning: 4
  info: 2
  total: 9
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-05-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Five files covering the email delivery, tweet generation, the Jinja2 HTML template, and their test suites were reviewed at standard depth. The implementation broadly follows the project constraints (no hardcoded credentials, graceful degradation, re-raise on failure). However three blockers require immediate attention: an XSS/HTML-injection path from LLM output through the email template, a path traversal via unvalidated `date` and `report_type` parameters, and a duplicate `Content-Transfer-Encoding` header that violates RFC 2045 and can cause email delivery failures. Four warnings cover the `autoescape=False` root cause of the XSS, an unguarded index access on the Claude API response, and two test-quality issues.

## Critical Issues

### CR-01: HTML Injection from LLM Output via Jinja2 autoescape=False

**File:** `delivery/email.py:137`, `templates/report_email.html:12`

**Issue:** The Jinja2 environment is created with `autoescape=False`, which disables HTML escaping for every variable in the template — including `{{ subject }}` (rendered in `<title>`) and `{{ body_html | safe }}`. `body_html` is produced by `_markdown_to_html(plain_text)`, which itself does no HTML escaping of the input text before inserting it into `<h1>`/`<h2>` tags or paragraph blocks. Because `plain_text` ultimately originates from Claude API responses (LLM-generated), a prompt-injection attack or an unexpected API response containing HTML/JavaScript is inserted verbatim into the outbound email HTML. Example: a report containing `## <img src=x onerror=alert(1)> Section` results in `<h2 style="..."><img src=x onerror=alert(1)> Section</h2>` in the email body. While major email clients strip `<script>`, event handlers in `<img>`, `<a>`, or `<svg>` tags are less consistently filtered and may execute in some clients.

**Fix:**
```python
# delivery/email.py — enable autoescape for HTML templates
env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=True,   # enables escaping for .html templates by default
)
```

Then in `_markdown_to_html`, the heading content must be HTML-escaped before embedding:
```python
import html as html_stdlib

# Inside _markdown_to_html, for each heading line:
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
else:
    html_lines.append(html_stdlib.escape(line))
```

The `{{ body_html | safe }}` in the template remains correct — the HTML is pre-built and trusted once the escaping is done in Python. With `autoescape=True`, `{{ subject }}` is escaped automatically without needing `| safe`.

---

### CR-02: Path Traversal via Unvalidated `date` and `report_type` Parameters

**File:** `delivery/email.py:97-100`, `delivery/tweet.py:147-148`

**Issue:** Both `archive_report` and `write_tweet` construct filesystem paths by interpolating caller-supplied `date` and `report_type` strings directly:

```python
# email.py:97
dest = Path("reports") / report_type / f"{date}.md"

# tweet.py:147
dest = Path("tweets") / f"{date}.txt"
```

Neither parameter is validated. A `date` value of `"../../../etc/cron.d/evil"` produces the path `reports/daily/../../../etc/cron.d/evil.md`. Combined with `dest.parent.mkdir(parents=True, exist_ok=True)`, this can create arbitrary directories. If the process has sufficient permissions it can also overwrite arbitrary files (e.g., crontab entries, `.env`, system configs). A malformed `report_type` of `"../secret"` produces `reports/../secret/2026-05-10.md`.

In the current codebase these values come from trusted callers, but the functions are public APIs with no documented constraints, making this a latent security defect.

**Fix:**
```python
import re

_SAFE_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SAFE_TYPE_RE = re.compile(r"^(daily|weekly|monthly)$")

def archive_report(report_type: str, date: str, content: str) -> None:
    if not _SAFE_TYPE_RE.match(report_type):
        raise ValueError(f"Invalid report_type: {report_type!r}")
    if not _SAFE_DATE_RE.match(date):
        raise ValueError(f"Invalid date format: {date!r}")
    dest = Path("reports") / report_type / f"{date}.md"
    ...
```

Apply the same validation at the top of `write_tweet` before path construction.

---

### CR-03: Duplicate Content-Transfer-Encoding Header Violates RFC 2045

**File:** `delivery/email.py:151-161`

**Issue:** The MIME construction for the HTML part emits **two** `Content-Transfer-Encoding` headers: `7bit` (set internally by `MIMEText('', 'html')`) and `quoted-printable` (added manually on line 155, then again implicitly by `set_charset('utf-8')` on line 156). RFC 2045 §6.4 forbids more than one `Content-Transfer-Encoding` field per body part. The resulting headers look like:

```
Content-Transfer-Encoding: 7bit
Content-Transfer-Encoding: quoted-printable
```

Strict SMTP servers and spam filters may reject messages with duplicate `Content-Transfer-Encoding` headers. Some MUAs parse only the first header (`7bit`), which would cause the QP-encoded payload to be decoded incorrectly, producing garbled accented characters (`=C3=A9` displayed literally instead of `é`). This is a silent delivery failure mode — the email either bounces or displays corrupted.

**Fix:** Avoid `set_charset()` after manually setting headers. Instead, build the HTML part cleanly without the conflicting call:

```python
# delivery/email.py — replace lines 151-161 with:
html_encoded = quopri.encodestring(html_content.encode("utf-8")).decode("ascii")
html_part = MIMEText("", "html", "utf-8")
# MIMEText("", "html", "utf-8") sets charset but defaults to base64;
# Override the transfer encoding before setting payload:
del html_part["Content-Transfer-Encoding"]
html_part["Content-Transfer-Encoding"] = "quoted-printable"
html_part.set_payload(html_encoded)
```

Or the simplest correct approach — let Python's email library handle encoding automatically:
```python
html_part = MIMEText(html_content, "html", "utf-8")
# Python will base64-encode automatically; QP is a style preference, not a requirement.
```

## Warnings

### WR-01: Jinja2 autoescape=False is Broader Than Needed (Root Cause of CR-01)

**File:** `delivery/email.py:137`

**Issue:** `autoescape=False` was set explicitly. The `| safe` filter on `body_html` in the template is present to mark that variable as pre-rendered HTML, but disabling autoescape globally removes protection for all other template variables (currently `{{ subject }}`). Even if `body_html` legitimately needs `| safe`, the correct pattern is `autoescape=True` (the default for `.html` templates when using `select_autoescape`) so that other variables remain protected.

**Fix:**
```python
from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)
```

This enables escaping for `.html` files while allowing `| safe` for the pre-built `body_html` variable.

---

### WR-02: Unchecked Index Access on Claude API Response

**File:** `delivery/tweet.py:129`

**Issue:** `response.content[0].text.strip()` is called without guarding against an empty `content` list. The Anthropic API may return `stop_reason="max_tokens"` with an empty content list, or a response with `type="tool_use"` blocks instead of text blocks. In either case `content[0]` raises `IndexError`. While `IndexError` is a subclass of `Exception` and is caught by the `except Exception` block at line 130, the logged error message `"Tweet generation failed: ... error=list index out of range"` is opaque — there is no indication that the API returned an unexpected response structure. Additionally, if the `content[0]` block exists but its `type` is not `"text"`, accessing `.text` raises `AttributeError` which is also caught silently.

**Fix:**
```python
if not response.content:
    raise ValueError(
        f"Claude returned empty content list (stop_reason={response.stop_reason!r})"
    )
content_block = response.content[0]
if content_block.type != "text":
    raise ValueError(
        f"Unexpected content block type: {content_block.type!r}"
    )
tweet_text = content_block.text.strip()
```

---

### WR-03: Relative Paths in archive_report and write_tweet Are cwd-Dependent

**File:** `delivery/email.py:97`, `delivery/tweet.py:147`

**Issue:** Both functions construct storage paths relative to the current working directory (`Path("reports")`, `Path("tweets")`). If the process cwd differs from the project root (e.g., when invoked from a cron job with a different working directory, or from a unit test without `monkeypatch.chdir`), reports and tweets are silently written to the wrong location. The tests correctly use `monkeypatch.chdir(tmp_path)` to control this, but production callers (scheduler, main.py) must ensure cwd is always the project root — an implicit constraint with no enforcement.

**Fix:** Anchor paths to the project root at module load time (the same pattern already used for `_TEMPLATES_DIR`):

```python
# At the top of email.py
_PROJECT_ROOT = Path(__file__).parent.parent
_REPORTS_DIR = _PROJECT_ROOT / "reports"

# In archive_report:
dest = _REPORTS_DIR / report_type / f"{date}.md"
```

Apply the same pattern in `tweet.py` for `_TWEETS_DIR`.

---

### WR-04: TWEET_OK Test Fixture is Below the Minimum Tweet Length

**File:** `tests/test_tweet.py:47`

**Issue:** `TWEET_OK` is defined as a 159-character string but the system constraint is `[240, 270]` characters. Every test that uses `TWEET_OK` as the mocked Claude response will trigger a `WARNING` log (the "length outside [240, 270]" warning in `write_tweet`) during the test run. While the tests still pass (the file is written anyway), the spurious warnings in test output obscure genuine warnings and make CI log review harder. The variable name `TWEET_OK` implies it represents a valid tweet, but it does not satisfy the defined constraint.

**Fix:**
```python
# tests/test_tweet.py — replace TWEET_OK with a 240-270 char string
TWEET_OK = (
    "Momentum haussier sur les marchés européens cette semaine. "
    "Les ETFs PEA affichent +1.2% de progression notable. "
    "Surveillance renforcée sur la crypto en cette période volatile. "
    "#Bourse #ETF #CAC40 #Investissement"
)
# Verify: len(TWEET_OK) should be in [240, 270]
```

## Info

### IN-01: Unused Test Fixture TWEET_240

**File:** `tests/test_tweet.py:46`

**Issue:** `TWEET_240 = "A" * 200 + " #Bourse #ETF #Crypto #Finance"` is defined at module level (line 46) but is never referenced in any test. The comment suggests it was intended for a "test 9" that was either renamed or removed. Its actual length is 230 characters, inconsistent with the name `TWEET_240`.

**Fix:** Remove the unused constant, or if a short-tweet warning test was intended, rename it to `TWEET_SHORT` and use it in `test_write_tweet_logs_warning_for_short_tweet_but_writes_anyway` instead of the inline `short_tweet = "Court"`.

---

### IN-02: Jinja2 Environment Recreated on Every send_email Call

**File:** `delivery/email.py:137-139`

**Issue:** A new `jinja2.Environment` and `FileSystemLoader` are instantiated inside `send_email` on every invocation. Jinja2 environments are meant to be created once and reused — they cache parsed templates and the filesystem scanner. In production the email is sent at most once per day, so this has no observable impact, but it is inconsistent with Jinja2 best-practice patterns and could become an issue if `send_email` is ever called in a loop or from tests with high frequency.

**Fix:** Move the environment to module level:
```python
# delivery/email.py — at module level, after _TEMPLATES_DIR is defined
_JINJA_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

# In send_email, replace the env/template lines with:
template = _JINJA_ENV.get_template("report_email.html")
html_content = template.render(subject=subject, body_html=body_html)
```

---

_Reviewed: 2026-05-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
