# Phase 4: Delivery & Side Outputs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-10
**Phase:** 04-Delivery & Side Outputs
**Areas discussed:** HTML email structure, Tweet generation, Email failure behavior

---

## HTML Email Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Jinja2 template + CSS | Single shared template in templates/ with inline CSS; reporters pass plain text, template wraps it | ✓ |
| Inline string-building in email.py | No Jinja2, f-strings or helpers; simpler, no template files | |
| Reporters output HTML-ready | Phase 3 reporters produce HTML sections directly; requires modifying reporters | |

**Follow-up: Number of templates**

| Option | Description | Selected |
|--------|-------------|----------|
| One shared base template | templates/report_email.html shared by all 3 report types | ✓ |
| One template per report type | templates/daily_email.html etc. — fully independent layouts | |

**Follow-up: Plain-text fallback**

| Option | Description | Selected |
|--------|-------------|----------|
| Use reporters' raw text output directly | Reporters already produce readable plain text → text/plain MIME part | ✓ |
| Strip HTML from rendered template | Render to HTML then strip tags — risk of messy output | |

**Follow-up: Visual richness**

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal: white background, readable typography, section headers | Clean, professional, works in all email clients | ✓ |
| Rich: header banner, colored section cards, table formatting | More polished but heavy CSS and cross-client testing required | |

**Notes:** Clean separation of concerns — reporters own the content, the template owns the presentation.

---

## Tweet Generation

| Option | Description | Selected |
|--------|-------------|----------|
| Claude API call | Extract ONE SIGNAL, send to Claude with strict char/format constraints | Claude's discretion ✓ |
| Template-based | Fixed Python template populated from ONE SIGNAL text | |

**User's choice:** "You decide" — Claude chose Claude API call for consistency with project's LLM synthesis approach.

**Follow-up: Hashtag pool**

| Option | Description | Selected |
|--------|-------------|----------|
| Finance/ETF/Crypto mix | #Bourse #ETF #Crypto #Finance #CAC40 #Bitcoin #Investissement #Marchés | ✓ |
| Define custom list | User-specified hashtags | |

**Follow-up: Tweet source extraction**

| Option | Description | Selected |
|--------|-------------|----------|
| Parse ONE SIGNAL section by header name | Regex/split on section header in report string | ✓ |
| Reporters expose tweet_source field | Phase 3 reporters return a dict with 'tweet_source' key | |

**Notes:** Consistent with how reporters are built — no breaking changes to Phase 3.

---

## Email Failure Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Log error + raise | Re-raise after logging; Phase 5 handles run-level failure | ✓ |
| Log error + return False | Soft failure — may silently swallow issues | |
| Log error + retry once | Retry after 3s delay, then raise | |

**Follow-up: Tweet file write failure**

| Option | Description | Selected |
|--------|-------------|----------|
| Log error + raise (consistent) | Same pattern as email.py | ✓ |
| Log error + continue silently | Tweet is side output, shouldn't block email | |

**Notes:** Consistent exception handling across all delivery modules. Phase 5 decides what to do at run level.

---

## Claude's Discretion

- **Tweet generation method** — User said "you decide". Claude chose Claude API call (LLM synthesis, consistent with project approach, most natural-language output).
- **Archiving implementation** — Placement of archive logic in `delivery/email.py` or thin helper; planner decides.

## Deferred Ideas

- Email retry logic (retry once after 3s) — considered for transient SMTP failures, deferred to Phase 5 graceful degradation.
- Auto-publish to Twitter/X — v2 requirement, explicitly out of scope for v1.
