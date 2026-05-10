# Phase 4: Delivery & Side Outputs - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the Phase 3 reporters' output to the outside world:
1. **Email delivery** — send HTML emails via Gmail SMTP with a plain-text fallback (`delivery/email.py`)
2. **Tweet file generation** — produce `/tweets/YYYY-MM-DD.txt` from the ONE SIGNAL section via Claude API (`delivery/tweet.py`)
3. **Markdown archiving** — persist each report as a Markdown file in `/reports/{type}/` (`delivery/email.py` or a dedicated archiver)

**Modules to produce:**
- `delivery/email.py` — HTML email sender via Gmail SMTP (MAIL-01 through MAIL-04, REPT-05)
- `delivery/tweet.py` — tweet file generator (TWEET-01 through TWEET-04)
- `templates/report_email.html` — Jinja2 email template (shared by all 3 report types)

**Input:** `dispatch.py`'s `select_reports()` returns `Dict[str, str]` with keys `"daily"`, `"weekly"`, and/or `"monthly"` — each value is a plain-text report string from the reporters.

**NOT in scope for Phase 4:** Scheduler triggers (Phase 5), end-to-end graceful degradation logic (Phase 5), auto-posting to Twitter/X (v2), SendGrid/Mailgun (v2).

</domain>

<decisions>
## Implementation Decisions

### HTML Email Structure (REPT-05)

- **D-01:** Use a single Jinja2 template `templates/report_email.html` shared by all three report types (daily, weekly, monthly). The template receives the report body as a variable; only the content changes, not the template.
- **D-02:** HTML visual style: minimal — white background, readable typography, `<h2>` section headers for each report section. No complex CSS, no tables, no header banners. Must render cleanly in Gmail without extensive CSS.
- **D-03:** Plain-text fallback: pass the reporters' raw text output directly as the `text/plain` MIME part of the multipart email. No HTML stripping or conversion step.

### Email Sending (MAIL-01 through MAIL-04)

- **D-04:** `delivery/email.py` uses `smtplib.SMTP_SSL` (or `SMTP` + `starttls`) with credentials from `Config` (`smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`).
- **D-05:** Subject line format per MAIL-03:
  - Daily: `[DAILY] Analyse du {date}`
  - Weekly: `[WEEKLY WRAP] Bilan de la semaine {date}`
  - Monthly: `[MONTHLY CLOSE] Bilan du mois {month} {year}`
- **D-06:** Footer disclaimer per MAIL-04 hardcoded in the Jinja2 template: `"Ceci n'est pas un conseil financier. Informations à titre éducatif uniquement."`
- **D-07:** Failure behavior: log the error (include report type, recipient count, error message — NEVER credentials or SMTP password) then re-raise the exception. Phase 5 caller handles run-level failure recording.

### Tweet Generation (TWEET-01 through TWEET-04)

- **D-08:** Tweet source extraction: `delivery/tweet.py` parses the report string for the ONE SIGNAL section using a regex/split on the section header (e.g., `## One Signal` or `# One Signal`). Extracts the text beneath the header.
- **D-09:** Tweet content generation: Claude API call (consistent with the project's LLM synthesis approach). Prompt instructs Claude to produce exactly 240–270 characters, French language, analyst tone, ending with 3–4 hashtags chosen from the defined pool.
- **D-10:** Hashtag pool (embedded constant in `delivery/tweet.py`): `#Bourse #ETF #Crypto #Finance #CAC40 #Bitcoin #Investissement #Marchés`. Claude selects 3–4 from this list based on the report content.
- **D-11:** Tweet routing per TWEET-01 through TWEET-04:
  - Daily run (Mon–Sat): tweet based on Daily Report ONE SIGNAL → `/tweets/YYYY-MM-DD.txt`
  - Sunday Weekly run: tweet based on Weekly Wrap summary section → `/tweets/YYYY-MM-DD.txt`
  - Monthly Close run: no tweet file generated (TWEET-04)
- **D-12:** Tweet failure behavior: log the error (report type, date, error message — NEVER the API key) then re-raise. Consistent with email failure handling (D-07).

### Markdown Archiving (STOR-01, STOR-02)

- **D-13 (Claude's discretion):** Archive the reporters' raw text output as-is (already plain text / markdown-structured). Filename pattern: `/reports/{type}/{YYYY-MM-DD}.md`. Archiving happens immediately after successful report generation, before email send. Archiving failure logs and re-raises (same pattern as D-07/D-12).

### Claude's Discretion

- **Tweet generation method** — User deferred to Claude. Decision: Claude API call (same tool as report synthesis, consistent with project approach, best natural-language output).
- **Archiving implementation** — Archiving logic placed in `delivery/email.py` (or a thin `archive()` helper called alongside `send_email()`). The planner can split it out if warranted.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Foundation
- `.planning/REQUIREMENTS.md` — REPT-05, MAIL-01 through MAIL-04, TWEET-01 through TWEET-04, STOR-01, STOR-02 define all delivery requirements for this phase
- `.planning/ROADMAP.md §Phase 4` — Goal, success criteria, plan count
- `.planning/PROJECT.md` — Core constraints: zero hardcoded credentials, graceful degradation principle, Gmail SMTP only in v1

### Phase 3 Output (what Phase 4 consumes)
- `reporters/dispatch.py` — `select_reports(today, data, config) -> Dict[str, str]` — the direct input to Phase 4; keys are `"daily"`, `"weekly"`, `"monthly"`
- `reporters/base.py` — `build_section()` helper; shows the plain-text output format reporters produce
- `reporters/daily.py` — Reference for ONE SIGNAL section header naming convention (section 6)

### Phase 1 Infrastructure (reuse)
- `config.py` — `Config` dataclass with SMTP fields (`smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `recipient_list`) and `anthropic_api_key` / `anthropic_model` for tweet generation
- `logging_setup.py` — `get_logger(name)` for structured logging in delivery modules

### Prior Phase Context
- `.planning/phases/02-data-pipeline/02-CONTEXT.md` — Prior decisions about config injection pattern and logging conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `reporters/dispatch.py:select_reports()` — Phase 4's entry point; returns the dict of reports to deliver; already handles REPT-04 dual-emission (Monthly + Weekly on last Sunday of month)
- `reporters/base.py:synthesize_section()` — Pattern for Claude API calls with graceful degradation; reuse the same pattern for tweet Claude call in `delivery/tweet.py`
- `config.py:Config` — Already has SMTP fields and Anthropic fields; no new env vars expected for Phase 4 beyond what is documented in `.env.example`
- `logging_setup.py:get_logger(__name__)` — Module-level logger; established pattern across all modules

### Established Patterns
- **Config dependency injection** — `delivery/email.py` and `delivery/tweet.py` both receive `Config` as a parameter; no direct `.env` reads inside delivery modules
- **Never log credentials** — T-03-01 pattern from `reporters/base.py`: log section name / report type / error message, NEVER the API key or SMTP password
- **Re-raise after logging** — Phase 4 delivery failures log then re-raise; Phase 5 scheduler handles run-level exception recording
- **TDD RED/GREEN** — Phase 1–3 used it; Phase 4 should mock `smtplib.SMTP` and `anthropic.Anthropic` for unit tests

### Integration Points
- `delivery/__init__.py` exists as an empty stub — ready for imports
- `templates/` directory exists but is empty — Jinja2 template goes here
- `main.py` will call `select_reports()` then pass the result to Phase 4 delivery functions; the integration wiring happens in Phase 5

</code_context>

<specifics>
## Specific Ideas

- The Jinja2 template file should live at `templates/report_email.html` — the only template file needed for Phase 4.
- Subject line patterns are fixed strings defined in `delivery/email.py` (not in `.env`) — they are formatting conventions, not credentials.
- The hashtag pool is a module-level constant in `delivery/tweet.py` (a Python list/set), not a config value. TWEET-03 calls it a "defined pool" — it is: `["#Bourse", "#ETF", "#Crypto", "#Finance", "#CAC40", "#Bitcoin", "#Investissement", "#Marchés"]`.
- Tweet length enforcement: Claude is instructed in the prompt; `delivery/tweet.py` also asserts the output length is in [240, 270] before writing the file. If outside range, log a warning but write anyway (graceful degradation).

</specifics>

<deferred>
## Deferred Ideas

- **Email retry on transient SMTP failure** — Retry logic (retry once after 3s) was considered but deferred. Phase 5 graceful degradation handles run-level retry strategy.
- **`ENABLE_TWITTER_POST` auto-publish** — v2 requirement (DIST-01). Not in scope for Phase 4.

None additional — discussion stayed within phase scope.

</deferred>

---

*Phase: 4-Delivery & Side Outputs*
*Context gathered: 2026-05-10*
