---
phase: 08-close-gaps
plan: 03
subsystem: tests + planning
tags: [boundary-tests, chart-verification, CHART-01, CHART-02, CHART-03, CHART-04, CHART-05]

# Dependency graph
requires:
  - phase: 08-02
    provides: "_build_chart_panel correctement transformé dans les 3 reporters"
  - phase: 08-01
    provides: "collectors/etf.py pct_change_1w + collectors/crypto.py history"
provides:
  - "tests/test_chart_boundary.py: 11 tests d'intégration boundary collector→chart (sans mock des générateurs)"
  - ".planning/phases/06-chart-generation/06-VERIFICATION.md: vérification formelle CHART-01..05"
affects: [tests/test_chart_boundary.py, .planning/phases/06-chart-generation/]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Boundary integration tests: fournir des dicts collector-shaped, appeler _build_chart_panel, asserter img tag ou fallback"
    - "Interception sélective: patch('reporters.daily.generate_pea_table', side_effect=capturing) pour capturer l'argument sans bloquer le rendu réel"

key-files:
  created:
    - tests/test_chart_boundary.py
    - .planning/phases/06-chart-generation/06-VERIFICATION.md
  modified: []

key-decisions:
  - "08-03-A: tests boundary sans mock des générateurs de chart — objectif délibéré pour vérifier le contrat de données réel"
  - "08-03-B: 06-VERIFICATION.md documente séparément le rôle de chaque phase (08-01 collecte, 08-02 transform, 06 générateurs)"

# Metrics
duration: ~10min
completed: 2026-05-15
---

# Phase 8 Plan 03: Close Gaps — Boundary Tests et Phase 6 VERIFICATION Summary

**11 tests boundary exercent le vrai transform _build_chart_panel sans mocker les générateurs de charts; 06-VERIFICATION.md confirme formellement CHART-01..05 satisfaits; suite complète 321 tests au vert.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-15T14:04:00Z
- **Completed:** 2026-05-15T12:13:12Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments

- `tests/test_chart_boundary.py` — 11 tests d'intégration boundary:
  - `TestEtfBoundary` (3 tests): CHART-01 — tickers valides produisent `<img>`, empty → ETF_FALLBACK, filtre None correct
  - `TestPeaBoundary` (3 tests): CHART-04 — prix valides produisent `<table>`, empty → PEA_FALLBACK, _PEA_ELIGIBILITY correct
  - `TestChart03Boundary` (3 tests): CHART-03 — fear_greed=None sans AttributeError, GAUGE_FALLBACK affiché, rapport non effondré
  - `TestCryptoSparklineBoundary` (2 tests): CHART-02 — history list valide produit `<img>`, history vide → CRYPTO_FALLBACK

- `.planning/phases/06-chart-generation/06-VERIFICATION.md` — vérification formelle:
  - CHART-01: PASS (ETF transform + pct_change_1w collecté en 08-01)
  - CHART-02: PASS (sparklines history via CoinGecko market_chart en 08-01)
  - CHART-03: PASS (fg_score or{} fix en 08-02)
  - CHART-04: PASS (pea_list list comprehension en 08-02)
  - CHART-05: PASS (try/except par générateur + fallbacks HTML)

- Suite complète: **321 tests passent** (aucune régression)

## Task Commits

1. **Tâche 1: Tests boundary** - `af786c2` (test) — commit de base du worktree (créé en phase préalable)
2. **Tâche 2: 06-VERIFICATION.md** - `7b10c1b` (docs)

## Files Created/Modified

- `tests/test_chart_boundary.py` (200 lignes) — 11 tests boundary, 4 classes de test
- `.planning/phases/06-chart-generation/06-VERIFICATION.md` (142 lignes) — vérification formelle CHART-01..05

## Decisions Made

- **08-03-A:** Tests boundary sans mock des générateurs de chart — la stratégie délibérée pour exercer le vrai contrat de données `collector → _build_chart_panel → generate_*`; les mocks existants dans les autres suites cachaient les bugs de transformation
- **08-03-B:** `06-VERIFICATION.md` documente la séparation des responsabilités : Phase 6 (générateurs corrects), Phase 8 plan 01 (collecteurs), Phase 8 plan 02 (reporters transform)

## Deviations from Plan

### Contexte de l'exécution

La Tâche 1 (`tests/test_chart_boundary.py`) était déjà présente dans le commit de base `af786c2` du worktree, créée par un agent de wave antérieure. Le plan 08-03 était prévu en Wave 3 avec `depends_on: [08-02]`, et le commit `af786c2` portait déjà le message `test(08-03)`.

**Action prise:** Tâche 1 vérifiée (11 tests passent, >= 9 requis, aucun mock de chart generator dans les assertions de présence d'img) → confirmée conforme. Tâche 2 exécutée normalement.

Aucun bug auto-corrigé.

## Threat Surface Scan

Aucune nouvelle surface réseau. Les fichiers créés sont un fichier de test Python et un document de vérification Markdown — pas d'endpoints, pas d'accès fichiers en production, pas de changements de schéma.

## Known Stubs

Aucun stub dans les fichiers créés. Les tests exercent le code de production réel.

## Self-Check: PASSED

- tests/test_chart_boundary.py — FOUND
- .planning/phases/06-chart-generation/06-VERIFICATION.md — FOUND
- Commit af786c2 (Task 1 — base) — FOUND
- Commit 7b10c1b (Task 2) — FOUND
- 321 tests passing — VERIFIED
- grep -c "def test_" tests/test_chart_boundary.py → 11 (>= 9 requis) — VERIFIED
- grep -c "CHART-0[12345]" 06-VERIFICATION.md → 12 — VERIFIED
- grep -c "PASS" 06-VERIFICATION.md → 11 (>= 5 requis) — VERIFIED
- grep -c "Bug history" 06-VERIFICATION.md → 4 (>= 3 requis) — VERIFIED
