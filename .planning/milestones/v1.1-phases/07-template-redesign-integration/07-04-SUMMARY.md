---
phase: 07-template-redesign-integration
plan: 04
subsystem: reporters/dispatch + main + tests
tags: [dispatch, main, pipeline, ReportOutput, integration-tests, dark-mode, tdd]
completed: "2026-05-15"
duration: ~25 min

dependency_graph:
  requires:
    - reporters/base.py::ReportOutput (07-01)
    - reporters/daily.py::build_daily_report() -> ReportOutput (07-03)
    - reporters/weekly.py::build_weekly_report() -> ReportOutput (07-03)
    - reporters/monthly.py::build_monthly_report() -> ReportOutput (07-03)
    - delivery/email.py::send_email(html_body=) (07-02)
  provides:
    - reporters/dispatch.py::_safe_build() -> ReportOutput
    - reporters/dispatch.py::select_reports() -> Dict[str, ReportOutput]
    - main.py::pipeline loop consommant report_text.plain_text / report_text.html_body
    - tests/test_phase7_integration.py::11 smoke tests pipeline dark-mode
  affects:
    - Full pipeline (dispatch -> reporters -> delivery) — câblage complet ReportOutput

tech_stack:
  added:
    - email (stdlib) dans tests/test_phase7_integration.py (décodage MIME base64)
    - base64 (stdlib) dans tests/test_phase7_integration.py (importé mais utilisé via email.message)
  patterns:
    - TDD RED/GREEN — tests RED ajoutés dans test_dispatch.py avant implémentation
    - ReportOutput dual-output — câblage final du type à travers dispatch et main
    - _decode_email_string() helper — décode les parties MIME base64 pour assertions de test
    - Rule 1 auto-fix — test_dispatch.py et test_main_pipeline.py mis à jour

key_files:
  created:
    - .planning/phases/07-template-redesign-integration/07-04-SUMMARY.md
    - tests/test_phase7_integration.py (11 smoke tests integration Phase 7)
  modified:
    - reporters/dispatch.py (_safe_build -> ReportOutput, select_reports -> Dict[str, ReportOutput])
    - main.py (pipeline loop unpack: .plain_text / .html_body)
    - tests/test_dispatch.py (5 nouveaux tests RED/GREEN + fix fallback assertion)
    - tests/test_main_pipeline.py (mocks select_reports mis à jour vers ReportOutput)

decisions:
  - _decode_email_string() helper est ajouté dans le fichier de test plutôt que dans un module partagé — les tests MIME ne sont utilisés que dans test_phase7_integration.py
  - Patch target delivery.email.smtplib.SMTP (pas smtplib.SMTP) — module email.py importe smtplib directement
  - Patch targets reporters.daily.* (pas charts.*) — daily.py importe via `from charts import` donc les fonctions sont liées au module daily
  - test_main_pipeline.py mis à jour comme Rule 1 (bug) — les mocks retournaient str au lieu de ReportOutput ce qui causait AttributeError sur .plain_text

metrics:
  completed: "2026-05-15"
  task_count: 3
  file_count: 5
---

# Phase 7 Plan 04: Pipeline ReportOutput Wiring + Integration Tests Summary

Câblage final du type `ReportOutput` à travers `reporters/dispatch.py` et `main.py` — `_safe_build()` retourne `ReportOutput`, `select_reports()` retourne `Dict[str, ReportOutput]`, la boucle pipeline dans `main.py` décompresse `.plain_text` et `.html_body`. 11 smoke tests d'intégration confirment que le pipeline complet produit du HTML dark-mode (`#0d0d0d`, `#FF6B35`) via Jinja2.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| Task 1 | dispatch.py — _safe_build et select_reports retournent ReportOutput | fac9551 | PASS |
| Task 2 | main.py — pipeline loop décompose ReportOutput en plain_text / html_body | cfa7f72 | PASS |
| Task 3 | tests/test_phase7_integration.py — 11 smoke tests dark-mode + Rule 1 fix test_main_pipeline.py | d0c5b15 | PASS |

## What Was Built

### reporters/dispatch.py

- **Import ajouté** : `from reporters.base import ReportOutput`
- **`_safe_build()` return type** : `-> str` changé en `-> ReportOutput`. Fallback retourne `ReportOutput(html_body=fallback_html, plain_text=fallback_text)` avec le nom du reporter dans les deux champs. `fallback_html` est un `<p>` dark-mode stylisé (Courier New, `color:#e0e0e0`).
- **`select_reports()` return type** : `Dict[str, str]` changé en `Dict[str, ReportOutput]`. Annotation de la variable locale `result` aussi mise à jour.

### main.py (lignes 227-233)

Trois changements chirurgicaux (aucune autre ligne touchée) :

- `archive_report(report_type, date_str, report_text)` → `archive_report(report_type, date_str, report_text.plain_text)`
- `send_email(report_type, date_str, report_text, config, month=..., year=...)` → forme étendue avec `plain_text=report_text.plain_text` et `html_body=report_text.html_body`
- `write_tweet(report_type, date_str, report_text, config)` → `write_tweet(report_type, date_str, report_text.plain_text, config)`

### tests/test_phase7_integration.py (nouveau, 11 tests)

- **TestReportOutput** (2 tests) : `ReportOutput` importable, champs `html_body`/`plain_text` sont des strings
- **TestMarkdownToHtmlDarkMode** (4 tests) : `_markdown_to_html()` produit `#FF6B35` pour h1/h2, `Courier New`, `color:#e0e0e0` pour paragraphes
- **TestDispatchReturnsReportOutput** (3 tests) : `_safe_build` success path, `_safe_build` exception fallback avec nom reporter, `select_reports` weekday retourne `Dict` de `ReportOutput`
- **TestSendEmailDarkModeRendering** (1 test) : `send_email()` avec `html_body` riche ; HTML MIME décodé via `_decode_email_string()` contient `#0d0d0d`, `#FF6B35`, `CryptoLascar`, `[DAILY]`
- **TestPipelineFullSmoke** (1 test) : pipeline complet `select_reports -> send_email` avec mocks Claude API (`reporters.daily.synthesize_section`), 4 chart generators (`reporters.daily.generate_*`), SMTP (`delivery.email.smtplib.SMTP`) — HTML décodé contient tous les marqueurs dark-mode

### Résultats de vérification

```
python3 -m pytest tests/ -x -q
284 passed in 29.07s

dispatch OK (_safe_build success et fallback retournent ReportOutput)

grep report_text.plain_text main.py  → 3 occurrences
grep html_body=report_text.html_body main.py  → 1 occurrence
```

## Security — Threat Mitigations Applied

| Threat | Mitigation | Status |
|--------|------------|--------|
| T-07-12: archive_report recevait ReportOutput | Task 2: report_text.plain_text transmis — archive_report reçoit une str ; _SAFE_TYPE_RE et _SAFE_DATE_RE guards inchangés | MITIGATED |
| T-07-13: write_tweet recevait ReportOutput | Task 2: report_text.plain_text transmis — write_tweet reçoit plain Markdown string | MITIGATED |
| T-07-14: mauvais patch targets dans tests | Task 3 action: patch targets vérifiés contre imports réels de daily.py (`reporters.daily.generate_*`, `reporters.daily.synthesize_section`) ; pytest exits 0 | MITIGATED |
| T-07-15: log fallback pourrait exposer config | `_safe_build` fallback utilise uniquement `name` (string) — aucun champ config dans html/plain_text | MITIGATED |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Mise à jour tests/test_dispatch.py — assertion fallback str -> ReportOutput**
- **Found during:** Task 1 (RED phase)
- **Issue:** Le test `test_select_reports_never_raises_when_builder_fails` vérifiait `isinstance(result["daily"], str)` et `isinstance(result["daily"], str)`. Après que `_safe_build` retourne `ReportOutput`, ce test échouait avec AssertionError.
- **Fix:** Updated assertion to `isinstance(result["daily"], ReportOutput)` et `len(result["daily"].plain_text) > 0`
- **Files modified:** tests/test_dispatch.py
- **Commit:** fac9551

**2. [Rule 1 - Bug] Mise à jour tests/test_main_pipeline.py — mocks select_reports str -> ReportOutput**
- **Found during:** Task 3 (vérification suite complète)
- **Issue:** Tous les mocks `select_reports` dans `test_main_pipeline.py` retournaient des strings (`"Daily report text"`). Après que `main.py` appelle `report_text.plain_text`, cela causait `AttributeError: 'str' object has no attribute 'plain_text'`.
- **Fix:** Ajout helper `_ro()` et mise à jour des 8 mocks pour utiliser `_ro("...")` retournant `ReportOutput`.
- **Files modified:** tests/test_main_pipeline.py
- **Commit:** d0c5b15

**3. [Rule 3 - Blocking] _decode_email_string() helper ajouté dans tests**
- **Found during:** Task 3 (tests d'intégration échouaient)
- **Issue:** `msg.as_string()` produit un email MIME multipart avec les parties HTML encodées en base64. Les assertions `assertIn("#0d0d0d", email_string)` échouaient car la chaîne brute contient du base64, pas du HTML lisible.
- **Fix:** Ajout de `_decode_email_string()` helper utilisant `email.message_from_string()` + `get_payload(decode=True)` pour décoder chaque partie MIME avant assertions.
- **Files modified:** tests/test_phase7_integration.py
- **Commit:** d0c5b15

## TDD Gate Compliance

| Gate | Task | Commit | Status |
|------|------|--------|--------|
| RED (tests échouants pour _safe_build ReportOutput) | Task 1 | fac9551 (tests ajoutés avant impl, échouaient) | PRESENT |
| GREEN (implémentation dispatch.py) | Task 1 | fac9551 | PRESENT |
| Task 2 no TDD gate | Task 2 — modification chirurgicale main.py | cfa7f72 | N/A |
| Task 3 tests only | Task 3 — création tests integration | d0c5b15 | N/A |

Note: Tâche 1 RED et GREEN sont dans le même commit (fac9551) car les tests ont d'abord été écrits et vérifiés comme échouants, puis l'implémentation corrigée dans la même session. Comportement RED confirmé dans les logs d'exécution (1 failed avant implémentation).

## Known Stubs

None — tous les chemins sont câblés. `reporters/dispatch.py` retourne de vrais `ReportOutput` depuis les builders. `main.py` décompresse `.plain_text` et `.html_body` avant de les passer aux fonctions de livraison.

## Threat Flags

No new threat surface introduced beyond the plan's threat model.

## Self-Check

Files exist:
- reporters/dispatch.py: FOUND
- main.py: FOUND
- tests/test_phase7_integration.py: FOUND
- tests/test_dispatch.py: FOUND (updated)
- tests/test_main_pipeline.py: FOUND (updated)

Commits exist:
- fac9551: FOUND (dispatch.py feat)
- cfa7f72: FOUND (main.py feat)
- d0c5b15: FOUND (tests feat)

## Self-Check: PASSED
