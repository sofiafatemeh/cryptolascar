---
phase: 04-delivery-side-outputs
fixed_at: 2026-05-10T00:00:00Z
review_path: .planning/phases/04-delivery-side-outputs/04-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 04: Code Review Fix Report

**Fixed at:** 2026-05-10T00:00:00Z
**Source review:** `.planning/phases/04-delivery-side-outputs/04-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (3 Critical + 4 Warning)
- Fixed: 7
- Skipped: 0

## Fixed Issues

### CR-01: HTML Injection from LLM Output via Jinja2 autoescape=False

**Files modified:** `delivery/email.py`
**Commit:** 3dc1504
**Applied fix:**
- Added `import html as html_stdlib` to use stdlib HTML escaping
- In `_markdown_to_html`: applied `html_stdlib.escape()` to heading content (`line[3:]` for `##`, `line[2:]` for `#`) and to all plain text lines before appending them
- Combined with WR-01 fix (autoescape=True) — `{{ subject }}` is now auto-escaped by Jinja2, `{{ body_html | safe }}` continues to work because the HTML is pre-built and escaped in Python

---

### CR-02: Path Traversal via Unvalidated `date` and `report_type` Parameters

**Files modified:** `delivery/email.py`, `delivery/tweet.py`
**Commit:** 3dc1504 (email.py), 50c9da8 (tweet.py)
**Applied fix:**
- Added module-level regex constants in both files:
  - `_SAFE_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")`
  - `_SAFE_TYPE_RE = re.compile(r"^(daily|weekly|monthly)$")`
- In `archive_report` (email.py): validate both params before any path construction, raise `ValueError` on mismatch
- In `write_tweet` (tweet.py): validate both params after the monthly early-return (so "monthly" still skips cleanly), raise `ValueError` on mismatch
- Docstrings updated to document the `ValueError` raise

---

### CR-03: Duplicate Content-Transfer-Encoding Header Violates RFC 2045

**Files modified:** `delivery/email.py`
**Commit:** 3dc1504
**Applied fix:**
- Replaced the manual `quopri.encodestring` + `MIMEText("", "html")` + `set_payload` + `set_charset` chain (which produced two `Content-Transfer-Encoding` headers) with a single clean call: `MIMEText(html_content, "html", "utf-8")`
- Python's email library handles encoding automatically (base64) — no duplicate headers
- Also removed the now-unused `import quopri` and `import email.charset` imports
- Tests updated to parse MIME parts via `email.message_from_string` and decode payloads rather than searching raw message string

---

### WR-01: autoescape=False is Broader Than Needed (Root Cause of CR-01)

**Files modified:** `delivery/email.py`
**Commit:** 3dc1504
**Applied fix:**
- Replaced `from jinja2 import Environment, FileSystemLoader` with `from jinja2 import Environment, FileSystemLoader, select_autoescape`
- Changed `autoescape=False` to `autoescape=select_autoescape(["html"])` — escaping is now on for `.html` templates, off for other types
- Moved `_JINJA_ENV` to module level (combining with IN-02 improvement, consistent with module-level pattern)

---

### WR-02: Unchecked Index Access on Claude API Response

**Files modified:** `delivery/tweet.py`
**Commit:** 50c9da8
**Applied fix:**
- Added defensive guard before `response.content[0]`:
  ```python
  if not response.content:
      raise ValueError(f"Claude returned empty content list (stop_reason={response.stop_reason!r})")
  content_block = response.content[0]
  if content_block.type != "text":
      raise ValueError(f"Unexpected content block type: {content_block.type!r}")
  tweet_text = content_block.text.strip()
  ```
- Both `ValueError` cases are caught by the existing `except Exception` block and logged without leaking the API key (T-04-05 preserved)
- Tests updated: all `MagicMock(text=...)` calls became `MagicMock(type="text", text=...)` so the type check passes

---

### WR-03: Relative Paths Are cwd-Dependent

**Files modified:** `delivery/email.py`, `delivery/tweet.py`
**Commit:** 3dc1504 (email.py), 50c9da8 (tweet.py)
**Applied fix:**
- `delivery/email.py`: added `_PROJECT_ROOT = Path(__file__).parent.parent` and `_REPORTS_DIR = _PROJECT_ROOT / "reports"` at module level; `archive_report` now uses `_REPORTS_DIR / report_type / f"{date}.md"`
- `delivery/tweet.py`: added `_PROJECT_ROOT = Path(__file__).parent.parent` and `_TWEETS_DIR = _PROJECT_ROOT / "tweets"` at module level; `write_tweet` now uses `_TWEETS_DIR / f"{date}.txt"`
- Tests updated: replaced `monkeypatch.chdir(tmp_path)` with `patch("delivery.email._REPORTS_DIR", tmp_path / "reports")` and `patch("delivery.tweet._TWEETS_DIR", tmp_path / "tweets")` so tests remain isolated without cwd dependency

---

### WR-04: TWEET_OK Fixture Below Minimum Tweet Length

**Files modified:** `tests/test_tweet.py`
**Commit:** f3aa199
**Applied fix:**
- Replaced the 159-char `TWEET_OK` string with a 247-char string that falls within [240, 270]:
  ```python
  TWEET_OK = (
      "Momentum haussier sur les marchés européens cette semaine. "
      "Les ETFs PEA affichent +1.2% de progression notable, portés par la tech et l'immobilier. "
      "Surveillance renforcée sur la crypto en cette période volatile. "
      "#Bourse #ETF #CAC40 #Investissement"
  )
  assert 240 <= len(TWEET_OK) <= 270, f"TWEET_OK length {len(TWEET_OK)} is outside [240, 270]"
  ```
- The assert at module level acts as a compile-time guard — if TWEET_OK drifts out of range, every test import will fail immediately with a clear message

---

## Skipped Issues

None — all 7 in-scope findings were fixed.

---

## Test Suite Result

All 103 tests pass after fixes: `python3 -m pytest tests/ -x -q` → `103 passed`

---

_Fixed: 2026-05-10T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
