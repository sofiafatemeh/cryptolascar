---
phase: 03-report-generation
plan: "03-03"
subsystem: reporters
tags: [tdd, weekly-report, markdown-tables, claude-synthesis, graceful-degradation]
dependency_graph:
  requires:
    - "03-01"  # reporters/base.py — synthesize_section, build_section, format_pct, format_currency
  provides:
    - "reporters/weekly.py — build_weekly_report(data, config) -> str"
  affects:
    - "Phase 4 delivery — weekly.py sera invoqué par le scheduler hebdomadaire"
tech_stack:
  added: []
  patterns:
    - "TDD RED/GREEN sur reporters/weekly.py"
    - "Tableaux Markdown générés via _table() helper interne"
    - "Dégradation gracieuse par section (source_failed) + filet global try/except"
key_files:
  created:
    - reporters/weekly.py
    - tests/test_weekly.py
  modified: []
decisions:
  - "Patron _table() helper centralisé pour tous les tableaux Markdown (ETF, Crypto, PEA, Macro)"
  - "6 appels synthesize_section couvrant toutes les sections narratives (LLM-02 respecté)"
  - "data={} → filet global retourne 7 sections '[Section indisponible.]' sans lever (T-03-09)"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-05-10"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 03 Plan 03-03: Weekly Report Builder Summary

**One-liner:** Weekly Wrap Markdown ~800 mots en 7 sections avec tableaux ETF/Crypto/PEA via synthesize_section (TDD RED/GREEN).

## What Was Built

`reporters/weekly.py` exporte `build_weekly_report(data: dict, config: Config) -> str`, un générateur de rapport hebdomadaire structuré en 7 sections conformes à REPT-02 :

1. **Executive Summary** — narration ~120 mots, vue d'ensemble de la semaine
2. **Macro Watch** — tableau taux/inflation FRED + narration Claude
3. **ETF Performance** — tableau multi-tickers (prix, variation) + narration Claude
4. **Crypto Recap** — tableau coins (prix, 24h) + Fear & Greed + narration Claude
5. **PEA Wrap** — tableau PEA France (€) + alerte éligibilité + narration Claude
6. **News Digest** — bullets top 10 headlines (titre + source)
7. **Outlook** — narration ~120 mots sur la semaine à venir

## TDD Gate Compliance

| Gate | Commit | Message |
|------|--------|---------|
| RED  | `23f5a85` | `test(03-03): add failing tests for reporters/weekly.py` |
| GREEN | `fb83ea9` | `feat(03-03): implement reporters/weekly.py — weekly wrap, 7 sections, ~800 words with tables` |

RED gate : `ModuleNotFoundError: No module named 'reporters.weekly'` confirmé avant implémentation.
GREEN gate : 8/8 tests passent ; 56/56 suite complète reste verte.

## Commits

| # | Hash | Type | Description |
|---|------|------|-------------|
| 1 | `23f5a85` | `test` | RED — 8 tests failing pour reporters/weekly.py |
| 2 | `fb83ea9` | `feat` | GREEN — implement reporters/weekly.py, 7 sections + tableaux |

## Tests Couverts (8/8)

| Test | Contrat vérifié |
|------|-----------------|
| `test_build_weekly_report_returns_seven_sections` | >= 7 lignes `## ` dans le rapport |
| `test_build_weekly_report_word_count_in_target_range` | 650 ≤ word_count ≤ 1000 |
| `test_build_weekly_report_contains_markdown_tables` | Au moins une ligne `\|...\|...\|` |
| `test_build_weekly_report_etf_table_lists_all_tickers` | 5 tickers (SPY, QQQ, IWDA.AS, EIMI.AS, CSPX.AS) présents |
| `test_build_weekly_report_calls_synthesize_section_at_least_three_times` | call_count >= 3 |
| `test_build_weekly_report_handles_partial_data` | PEA source_failed=True → section dégradée, 7 sections conservées |
| `test_build_weekly_report_uses_configured_anthropic_model` | config.anthropic_model transmis (pas hardcodé) |
| `test_build_weekly_report_never_raises` | data={} → 7 sections, aucune exception |

## Decisions Made

- **_table() centralisé** : un seul helper pour produire les tableaux Markdown des 4 sections quantitatives (Macro, ETF, Crypto, PEA). Cohérence visuelle garantie.
- **6 appels synthesize_section** : Executive Summary, Macro Watch, ETF Performance, Crypto Recap, PEA Wrap, Outlook — toutes les sections avec données numériques obtiennent une narration Claude.
- **News Digest sans LLM** : les headlines sont affichés en bullets bruts (source + titre) — pas de narration Claude pour limiter la latence et les coûts.
- **Dégradation à deux niveaux** : (1) par section via `source_failed` → message d'indisponibilité ; (2) filet global `try/except` dans `build_weekly_report` → retour de 7 sections fallback.

## Deviations from Plan

None — plan exécuté exactement tel qu'écrit.

## Threat Flags

Aucune nouvelle surface de sécurité identifiée au-delà du threat model du plan.

T-03-09 (DoS via data={}) mitigé : filet `try/except` global confirmé par Test 8.

## Self-Check: PASSED

- `reporters/weekly.py` existe : FOUND
- `tests/test_weekly.py` existe : FOUND
- Commit RED `23f5a85` : FOUND
- Commit GREEN `fb83ea9` : FOUND
- 8/8 tests `test_weekly.py` : PASSED
- 56/56 suite complète : PASSED
