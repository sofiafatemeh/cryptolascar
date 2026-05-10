---
phase: 03-report-generation
plan: "03-01"
subsystem: reporters
tags: [llm, tdd, shared-client, formatters, graceful-degradation]
dependency_graph:
  requires: []
  provides: [reporters/base.py, synthesize_section, build_section, format_pct, format_currency]
  affects: [reporters/daily.py, reporters/weekly.py, reporters/monthly.py]
tech_stack:
  added: [anthropic>=0.30.0]
  patterns: [tdd-red-green, graceful-degradation, threat-model-T-03-01]
key_files:
  created:
    - reporters/base.py
    - tests/test_reporters_base.py
  modified: []
decisions:
  - "Le mock est appliqué sur 'reporters.base.Anthropic' (import dans le module) plutot que 'anthropic.Anthropic' pour isoler correctement les tests"
  - "synthesize_section prend config comme kwarg nommé pour matcher le contrat des tests"
  - "FALLBACK_TEMPLATE contient 'indisponible' pour satisfaire l'assertion du Test 3"
  - "Installation de anthropic via pip --break-system-packages (package absent du worktree)"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-10T06:55:05Z"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
  tests_added: 6
  tests_total: 48
---

# Phase 03 Plan 01: reporters/base.py — Client Claude Partage et Helpers Summary

**One-liner:** Client Claude partage avec dégradation gracieuse (FALLBACK_TEMPLATE), protection T-03-01 (clé API non loggée), et helpers de formatage (format_pct, format_currency, build_section).

## What Was Built

`reporters/base.py` constitue le socle narratif de tous les reporters Phase 3. Il expose :

- `synthesize_section(prompt, config, system="", max_tokens=1024)` — appelle l'API Claude Anthropic en lisant `config.anthropic_model` (jamais hardcodé). En cas d'echec, retourne `FALLBACK_TEMPLATE` sans lever (T-03-02).
- `build_section(title, body)` — assemble une section Markdown `## {title}\n\n{body}\n`.
- `format_pct(value)` — formate un pourcentage avec signe explicite (`+1.23%`, `-0.50%`).
- `format_currency(value, symbol)` — formate en devise avec separateur milliers (`$60,000`).

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED | 02a2252 | test(03-01): add failing tests for reporters/base.py LLM client |
| GREEN | 757bab5 | feat(03-01): implement reporters/base.py shared Claude client and helpers |

- RED : 6 tests en ImportError (`No module named 'reporters.base'`) — gate valide
- GREEN : 6/6 tests passent, suite complete 48/48 — gate valide

## Test Results

```
tests/test_reporters_base.py::test_synthesize_section_calls_claude_with_configured_model PASSED
tests/test_reporters_base.py::test_synthesize_section_returns_text_content PASSED
tests/test_reporters_base.py::test_synthesize_section_graceful_fallback_on_api_failure PASSED
tests/test_reporters_base.py::test_synthesize_section_never_logs_api_key PASSED
tests/test_reporters_base.py::test_format_pct_format_currency PASSED
tests/test_reporters_base.py::test_build_section_assembles_header_and_body PASSED

6 passed — suite complete : 48 passed
```

## Threat Model Compliance

| Threat ID | Status | Evidence |
|-----------|--------|---------|
| T-03-01 | Mitige | `logger.warning("Claude synthesis failed: %s", e)` — seul `str(e)` est logue, jamais `config.anthropic_api_key`. Test 4 (caplog) verifie que la cle n'apparait pas dans les logs. |
| T-03-02 | Mitige | `try/except Exception` global retourne `FALLBACK_TEMPLATE` sans propagation. Test 3 verifie la chaine fallback non vide contenant 'indisponible'. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Package anthropic absent du worktree**
- **Found during:** Task 2 (GREEN) — `ModuleNotFoundError: No module named 'anthropic'`
- **Issue:** Le package `anthropic>=0.30.0` (dans `requirements.txt`) n'etait pas installe dans l'environnement Python du worktree.
- **Fix:** `pip3 install "anthropic>=0.30.0" --break-system-packages` — version 0.100.0 installee.
- **Files modified:** aucun (installation systeme)
- **Impact:** Aucun — l'implementation reste identique au plan.

## Known Stubs

Aucun stub — tous les exports sont pleinement implementes et testes.

## Threat Flags

Aucune surface de securite nouvelle detectee au-dela du perimetre du plan.

## Self-Check: PASSED

- [x] `reporters/base.py` existe et exporte les 4 symboles
- [x] `tests/test_reporters_base.py` existe avec 6 tests
- [x] Commit RED 02a2252 verifie : `test(03-01): add failing tests for reporters/base.py LLM client`
- [x] Commit GREEN 757bab5 verifie : `feat(03-01): implement reporters/base.py shared Claude client and helpers`
- [x] 6/6 tests test_reporters_base.py passent
- [x] 48/48 tests suite complete passent
- [x] `config.anthropic_model` utilise (pas de modele hardcode)
- [x] Cle API absente des logs (T-03-01)
