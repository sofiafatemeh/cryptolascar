---
phase: 03-report-generation
plan: "03-02"
subsystem: reporters
tags: [tdd, daily-report, claude-synthesis, graceful-degradation, rept-01]
dependency_graph:
  requires:
    - "03-01"  # reporters/base.py — synthesize_section, build_section, helpers
  provides:
    - "reporters/daily.py — build_daily_report(data, config) -> str"
  affects:
    - "Phase 04 — delivery (email/tweet utilisera build_daily_report)"
tech_stack:
  added: []
  patterns:
    - "TDD RED/GREEN avec pytest + unittest.mock.patch"
    - "Dégradation gracieuse par source_failed check dans chaque sous-section"
    - "Délégation narration à synthesize_section (aucun appel Claude direct)"
    - "Garantie mot-clé PEA alerte via post-processing si eligibility_changed"
key_files:
  created:
    - reporters/daily.py
    - tests/test_daily.py
  modified: []
decisions:
  - "Chaque section a sa propre fonction privée _xxx_section pour testabilité et lisibilité"
  - "Le mot-clé alerte/changement en PEA Alert est garanti par post-processing sur le body retourné par Claude, même si Claude l'omet (contrat test 7 respecté)"
  - "Smoke test confirme fourchette [250, 400] mots avec filler ~50 mots/section"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-10T07:01:51Z"
  tasks_completed: 2
  files_created: 2
  tests_added: 7
  tests_total: 55
---

# Phase 03 Plan 02: Daily Report Builder Summary

**One-liner:** `build_daily_report(data, config)` Markdown 6-sections ~300 mots avec narration Claude mockable et dégradation gracieuse par `source_failed`.

## What Was Built

`reporters/daily.py` expose la fonction publique `build_daily_report(data: dict, config: Config) -> str` qui construit le rapport quotidien en 6 sections dans l'ordre figé par REPT-01 :

1. **Macro Snapshot** — taux DGS10/DGS2, inflation CPI, M2 (source FRED)
2. **ETF Radar** — prix et variations ETFs (SPY, QQQ, IWDA.AS, etc.)
3. **Crypto Pulse** — top coins + Fear & Greed index
4. **PEA Alert** — ETFs PEA France + alerte si changement d'éligibilité
5. **News Feed** — top 7 titres + synthèse thèmes
6. **One Signal** — point d'attention principal du jour

Chaque section narrative est déléguée à `synthesize_section` (Plan 03-01). Le modèle Claude n'est jamais hardcodé — lu depuis `config.anthropic_model` (LLM-02).

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED  | `8efeeb3` — `test(03-02): add failing tests for reporters/daily.py` | ModuleNotFoundError confirmé |
| GREEN | `60a7a72` — `feat(03-02): implement reporters/daily.py` | 7/7 tests passent |

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `8efeeb3` | test | add failing tests for reporters/daily.py (7 tests, gate RED) |
| `60a7a72` | feat | implement reporters/daily.py — daily report builder, 6 sections, ~300 words |

## Test Results

- `tests/test_daily.py` : **7/7 passent**
- Suite complète `tests/` : **55/55 passent**

### Tests couverts

| Test | Description |
|------|-------------|
| `test_build_daily_report_returns_string_with_six_sections` | 6 titres exacts présents dans le rapport |
| `test_build_daily_report_word_count_in_target_range` | Fourchette [250, 400] mots respectée |
| `test_build_daily_report_calls_synthesize_section` | synthesize_section appelé >= 1 fois |
| `test_build_daily_report_uses_configured_model_via_config` | Config passée a `anthropic_model="claude-sonnet-4-6"` |
| `test_build_daily_report_graceful_when_synthesize_returns_fallback` | 6 sections présentes même avec FALLBACK_TEMPLATE |
| `test_build_daily_report_handles_missing_subsections` | Macro Snapshot avec "indisponible" si source_failed=True |
| `test_build_daily_report_includes_pea_alert_when_eligibility_changed` | PEA Alert contient "alerte"/"changement" si eligibility_changed=True |

## Deviations from Plan

None - plan executed exactly as written.

## Threat Surface Scan

Aucune nouvelle surface de sécurité non couverte par le threat model du plan.

Les mitigations T-03-06 (dégradation gracieuse `source_failed`) et T-03-07 (logs sans clé API) sont implémentées et vérifiables :
- T-03-06 : chaque `_xxx_section()` checke `source_failed` avant tout appel
- T-03-07 : le `except` global logue `%s` de l'exception (jamais la config)

## Known Stubs

None — toutes les sections sont pleinement câblées via `synthesize_section`.

## Self-Check: PASSED

Vérification post-commit :
- `reporters/daily.py` : FOUND
- `tests/test_daily.py` : FOUND
- Commit RED `8efeeb3` : FOUND
- Commit GREEN `60a7a72` : FOUND
- 7/7 tests `test_daily.py` : PASSED
- 55/55 tests suite complète : PASSED
