---
phase: 03-report-generation
plan: "03-04"
subsystem: reporters
tags: [tdd, monthly-close, dispatcher, rept-03, rept-04, calendar-logic]
dependency_graph:
  requires:
    - "03-01"  # reporters/base.py (synthesize_section, build_section, format_*)
    - "03-02"  # reporters/daily.py (build_daily_report)
    - "03-03"  # reporters/weekly.py (build_weekly_report)
  provides:
    - reporters/monthly.py (build_monthly_report)
    - reporters/dispatch.py (select_reports, is_last_day_of_month, is_sunday)
  affects:
    - Phase 4: delivery/email.py (consomme le dict retourné par select_reports)
    - Phase 5: scheduler/jobs.py (appelle select_reports(date.today(), data, config))
tech_stack:
  added:
    - calendar (stdlib — monthrange pour la logique de dernier jour du mois)
  patterns:
    - TDD RED/GREEN sur deux modules simultanés (test_monthly.py + test_dispatch.py)
    - _safe_build() wrapper pour dégradation gracieuse des builders dans le dispatcher
    - Logique calendaire centralisée (REPT-04) dans dispatch.py
key_files:
  created:
    - reporters/monthly.py
    - reporters/dispatch.py
    - tests/test_monthly.py
    - tests/test_dispatch.py
  modified: []
decisions:
  - "Monthly Close contient 7 sections narratives (~250 mots chacune) + ≥ 2 tableaux Markdown pour atteindre la cible ~2000 mots"
  - "synthesize_section appelé 7 fois dans monthly.py (une par section) — max_tokens=600 pour Month in Review et Forward Look (~250 mots)"
  - "_safe_build() wrapper dans dispatch.py absorbe toute exception d'un builder — le run ne s'annule jamais (REPT-04 + T-03-12)"
  - "select_reports() retourne un dict explicite {monthly, weekly} le dernier dimanche du mois — Phase 4 (delivery) distingue les deux emails sans ambiguïté (T-03-14)"
  - "Alerte éligibilité PEA garantie dans monthly.py même si Claude l'omet (même pattern que daily.py)"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-10T07:11:37Z"
  tasks_completed: 2
  files_created: 4
  tests_added: 14
  tests_total: 77
---

# Phase 03 Plan 04: Monthly Close + Dispatcher (REPT-03 + REPT-04) Summary

Monthly Close builder à 7 sections (~2000 mots, ≥2 tableaux Markdown) + dispatcher calendaire REPT-04 émettant deux documents distincts quand le dernier jour du mois tombe un dimanche.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `7ffd5b3` | test(03-04) | RED — tests TDD pour reporters/monthly.py et reporters/dispatch.py (14 tests, ImportError) |
| `e90f285` | feat(03-04) | GREEN — implémentation reporters/monthly.py + reporters/dispatch.py, 77 tests passent |

## Artifacts

### reporters/monthly.py

- Exporte `build_monthly_report(data: dict, config: Config) -> str`
- 7 sections (REPT-03) : Month in Review, Macro Backdrop, ETF Monthly Performance, Crypto Monthly, PEA Monthly, News & Themes, Forward Look
- `synthesize_section()` appelé 7 fois (≥4 requis)
- ≥2 tableaux Markdown (Macro Backdrop, ETF Monthly Performance, Crypto Monthly, PEA Monthly)
- Dégradation gracieuse totale : `data={}` retourne 7 sections sans lever
- Alerte éligibilité PEA garantie même si Claude l'omet
- Aucun nom de modèle Claude hardcodé — via `config.anthropic_model`

### reporters/dispatch.py

- Exporte `select_reports(today, data, config)`, `is_last_day_of_month(today)`, `is_sunday(today)`
- Logique REPT-04 via `calendar.monthrange` :
  - `last AND sunday` → `{"monthly": ..., "weekly": ...}` (deux documents)
  - `last` seulement → `{"monthly": ...}`
  - `sunday` seulement → `{"weekly": ...}`
  - sinon → `{"daily": ...}`
- `_safe_build()` wrapper : absorbe toute exception d'un builder (T-03-12)

## Tests

| Fichier | Nb tests | Résultat |
|---------|----------|----------|
| tests/test_monthly.py | 7 | 7/7 passés |
| tests/test_dispatch.py | 7 | 7/7 passés |
| **Suite complète** | **77** | **77/77 passés** |

### Cas REPT-04 validés

- `date(2026, 5, 31)` (dimanche ET dernier jour de mai) → `{"monthly": ..., "weekly": ...}` ✓
- `date(2026, 5, 12)` (mardi) → `{"daily": ...}` ✓
- `date(2026, 5, 10)` (dimanche, pas dernier jour) → `{"weekly": ...}` ✓
- `date(2026, 4, 30)` (jeudi, dernier jour d'avril) → `{"monthly": ...}` ✓

## TDD Gate Compliance

| Gate | Commit | Statut |
|------|--------|--------|
| RED — `test(03-04)` | `7ffd5b3` | Conforme — tous les tests échouaient en ImportError |
| GREEN — `feat(03-04)` | `e90f285` | Conforme — 77/77 tests passent |
| REFACTOR | N/A | Pas nécessaire |

## Deviations from Plan

None — plan exécuté exactement comme décrit. L'implémentation suit le squelette fourni dans le PLAN.md avec les ajustements mineurs suivants :

- `synthesize_section` appelé 7 fois dans monthly.py (plan exigeait ≥4) — toutes les sections bénéficient de narration Claude
- `max_tokens=600` appliqué sur Month in Review et Forward Look (sections ~250 mots) pour respecter la contrainte de longueur

## Threat Flags

Aucune nouvelle surface de sécurité introduite au-delà du modèle de menace documenté dans le plan.

## T-03-11 — Fuseau Horaire CET (ACTION REQUISE EN PHASE 5)

**Threat ID T-03-11 — Tampering — Date système incorrecte (fuseau horaire)**

`select_reports()` utilise `date.today()` passé par l'appelant. La logique calendaire est correcte, mais **Phase 5 (scheduler/jobs.py) doit garantir que l'appel est effectué en fuseau horaire CET** (Europe/Paris, UTC+1/UTC+2 selon DST).

**Risque sans mitigation :** Si le cron s'exécute en UTC à 07h00, le Monthly Close du 31 mai pourrait être déclenché le 30 mai à 23h00 UTC (soit le 31 mai à 01h00 CET), ou manqué si le scheduler passe à la date suivante avant l'heure CET cible.

**Action requise en Phase 5 :**
```python
# scheduler/jobs.py — Phase 5 doit utiliser :
import datetime
import zoneinfo

CET = zoneinfo.ZoneInfo("Europe/Paris")
today = datetime.datetime.now(tz=CET).date()
reports = select_reports(today, data, config)
```

**Disposition :** `accept` (documenté ici, mitigation déléguée à Phase 5).

## Known Stubs

Aucun stub — tous les builders produisent du contenu réel via `synthesize_section()`.

## Self-Check: PASSED

- `reporters/monthly.py` existe : FOUND
- `reporters/dispatch.py` existe : FOUND
- `tests/test_monthly.py` existe : FOUND
- `tests/test_dispatch.py` existe : FOUND
- Commit RED `7ffd5b3` existe : FOUND
- Commit GREEN `e90f285` existe : FOUND
- 77 tests passent : CONFIRMED
