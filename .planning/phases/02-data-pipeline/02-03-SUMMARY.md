---
phase: "02-data-pipeline"
plan: "02-03"
subsystem: "collectors"
tags: [pea, yfinance, eligibility, tdd, cache, sqlite]

dependency_graph:
  requires:
    - "01-03 (db/cache.py, config.py, logging_setup.py)"
    - "yfinance (pip)"
  provides:
    - "collectors/pea.py — collect_pea(config) → dict"
    - "PEA_ELIGIBLE_ISINS statique"
    - "Détection changement éligibilité AMF"
  affects:
    - "reporters/daily.py (consommateur futur)"
    - "main.py (orchestrateur futur)"

tech_stack:
  added:
    - "yfinance (déjà installé via Phase 02-01)"
  patterns:
    - "TDD RED/GREEN avec pytest + unittest.mock.patch"
    - "Cache SQLite TTL 4h (source='yfinance_pea')"
    - "Éligibilité persistée sans TTL (source='pea_eligibility')"
    - "Requêtes SQL paramétrées (mitigation T-02-09)"
    - "Dégradation gracieuse (partial=True, jamais d'exception)"

key_files:
  created:
    - "collectors/pea.py"
    - "tests/test_pea.py"
  modified: []

decisions:
  - "02-03-A: Indices (^FCHI, ^SBF120) exclus du check d'éligibilité (PEA_ELIGIBILITY_STATUS=None) — les indices ne sont pas des titres investissables"
  - "02-03-B: Éligibilité persistée sans TTL (expires_at=2099) — le statut AMF ne change pas selon un calendrier prévisible"
  - "02-03-C: logger.warning() utilisé pour les changements d'éligibilité — niveau approprié pour une anomalie à surveiller sans bloquer le run"

metrics:
  duration: "~3 minutes"
  completed_date: "2026-05-09"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
  tests_added: 6
  tests_total: 29
---

# Phase 2 Plan 3: PEA France Collector Summary

**One-liner:** Collecteur PEA France avec yfinance (cache 4h) + vérification d'éligibilité AMF statique et détection de changement persistée en SQLite.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Write failing tests for collect_pea | c497cbe | tests/test_pea.py |
| 2 (GREEN) | Implement collectors/pea.py | 97e8ec6 | collectors/pea.py |

## TDD Gate Compliance

- RED gate : `test(02-03): add failing tests for collect_pea (RED TDD gate)` — commit c497cbe
- GREEN gate : `feat(02-03): implement collectors/pea.py with yfinance prices + PEA eligibility (GREEN TDD gate)` — commit 97e8ec6
- Sequence confirmée : RED avant GREEN dans l'historique git.

## Verification Results

```
pytest tests/test_pea.py -v   → 6 passed
pytest tests/ -v              → 29 passed
```

Critères de succès du plan :
- collect_pea(config: Config) -> dict : CONFIRME
- PEA_TICKERS = ["^FCHI", "^SBF120", "CW8.PA", "PAEEM.PA", "PANX.PA"] : CONFIRME (D-04)
- PEA_ELIGIBLE_ISINS statique dans collectors/pea.py : CONFIRME (D-05)
- eligibility_changed dans le résultat : CONFIRME (D-06)
- Éligibilité persistée source="pea_eligibility" : CONFIRME (D-07)
- 6 tests dans tests/test_pea.py : CONFIRME

## Implementation Notes

`collect_pea(config)` suit ce flux :

1. **Prix** — Pour chaque ticker dans PEA_TICKERS :
   - Cache hit (source="yfinance_pea", expires_at > utcnow) → retour direct
   - Cache miss → `yf.Ticker(ticker).fast_info` → calcul pct_change → upsert cache (TTL 4h)
   - Exception yfinance → enregistre price=None, partial=True (jamais de propagation)

2. **Éligibilité** — Pour chaque ticker avec statut booléen (skip None pour les indices) :
   - Premier run (pas de ligne en cache) → upsert sans alerte
   - Statut inchangé → upsert silencieux
   - Statut changé → logger.warning + eligibility_changed=True + upsert

3. **Résultat** — dict avec : prices, eligibility, eligibility_changed, partial, source_used

Mitigation T-02-09 (Tampering) : toutes les requêtes SQLite utilisent des placeholders `?` paramétrés — pas d'interpolation de chaînes SQL.

## Deviations from Plan

Aucune — plan exécuté exactement tel qu'écrit.

## Known Stubs

Aucun — collect_pea retourne des données réelles (yfinance) ou des erreurs explicites.

## Threat Flags

Aucun nouveau vecteur d'attaque non prévu dans le threat model du plan.

## Self-Check: PASSED

- collectors/pea.py : FOUND
- tests/test_pea.py : FOUND
- commit c497cbe (RED) : FOUND
- commit 97e8ec6 (GREEN) : FOUND
- 6/6 tests tests/test_pea.py passent : CONFIRMED
- 29/29 tests suite complète passent : CONFIRMED
