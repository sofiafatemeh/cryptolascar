---
phase: 02-data-pipeline
plan: "02-06"
subsystem: orchestration
tags: [orchestration, pipeline, integration, tdd, graceful-degradation]
dependency_graph:
  requires: ["02-01", "02-02", "02-03", "02-04", "02-05"]
  provides: ["collect_all", "integration-tests"]
  affects: ["main.py", "tests/test_integration.py"]
tech_stack:
  added: []
  patterns: ["orchestrator-pattern", "graceful-degradation", "tdd-red-green"]
key_files:
  created:
    - tests/test_integration.py
  modified:
    - main.py
decisions:
  - "02-06-A: logger extrait au niveau module (non plus local à main()) pour être accessible dans collect_all()"
  - "02-06-B: import datetime déjà présent — datetime.datetime.now(datetime.timezone.utc) utilisé sans re-import local"
  - "02-06-C: sources_ok/sources_failed sont des listes en interne dans collect_all, convertis en CSV uniquement lors de log_run()"
metrics:
  duration: "4 minutes"
  completed_date: "2026-05-10"
  tasks_completed: 2
  files_changed: 2
---

# Phase 2 Plan 6: Pipeline Orchestration (collect_all) Summary

**One-liner:** Orchestrateur collect_all() câblant les 5 collecteurs dans main.py avec dégradation gracieuse par collecteur et traçabilité sources_ok/sources_failed dans run_log.

## What Was Built

`collect_all(config)` dans `main.py` orchestre les 5 collecteurs ETF, crypto, PEA, macro et news. Chaque collecteur est enveloppé dans un `try/except` individuel — une exception non gérée dans un collecteur n'arrête pas le run (T-02-23 mitigé). Le résultat inclut une clé `_meta` avec `sources_ok`, `sources_failed` et `collected_at`. La fonction `main()` remplace le placeholder "Phase 2+" par un appel réel à `collect_all()` et met à jour `log_run()` avec les valeurs réelles.

3 tests d'intégration vérifient : (1) tous les collecteurs OK → `sources_failed=[]`, (2) un collecteur raise → dégradation gracieuse avec `source_failed=True`, (3) `eligibility_changed=True` propagé depuis le collecteur PEA.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Integration tests (failing) | 96ef4dc | tests/test_integration.py |
| GREEN | collect_all() in main.py | 86444f9 | main.py |

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED — test(02-06) | 96ef4dc | PASSED — ImportError confirmé avant implementation |
| GREEN — feat(02-06) | 86444f9 | PASSED — 3/3 tests + 42/42 suite complète |

## Verification Results

```
python3 -m pytest tests/ -v → 42 passed (39 existants + 3 nouveaux)
grep "def collect_all" main.py → 33:def collect_all(config: "Config") -> dict:
grep "from collectors" main.py → 5 imports (etf, crypto, pea, macro, news)
grep "sources_failed" main.py → présent dans collect_all et main()
python3 -c "from main import collect_all; print('OK')" → OK
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Refactor] logger module-level plutôt que local à main()**
- **Found during:** Task 1
- **Issue:** `collect_all()` référence `logger` au niveau module, mais l'original avait `logger = get_logger(...)` local à `main()`. Déplacer au niveau module permet à `collect_all()` d'y accéder sans re-créer un logger.
- **Fix:** `logger = get_logger("cryptolascar.main")` déplacé au niveau module (ligne 30), supprimé de l'intérieur de `main()`.
- **Files modified:** main.py

**2. [Rule 1 - Refactor] import datetime redondant supprimé**
- **Found during:** Task 1
- **Issue:** Le plan suggérait `import datetime as _dt` à l'intérieur de `collect_all()` alors que `datetime` est déjà importé au top du module.
- **Fix:** Utilisation directe de `datetime.datetime.now(datetime.timezone.utc)` sans re-import local.
- **Files modified:** main.py

## Threat Model Compliance

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-02-22 (Info Disclosure) | logger.error() logue uniquement str(e), jamais les API keys | Mitigé |
| T-02-23 (DoS) | Chaque collecteur dans try/except — un crash n'arrête pas le run | Mitigé |
| T-02-24 (Repudiation) | sources_failed stocké dans run_log pour audit trail | Accepté |

## Known Stubs

Aucun stub — collect_all() orchestre de vrais collecteurs. Les données retournées dépendent des sources réseau (mock en tests uniquement).

## Phase 2 Success Criteria — Final Status

| Critère | Statut |
|---------|--------|
| collect_all() produit dict couvrant ETF, crypto, PEA, macro, news | SATISFAIT |
| Appel dans TTL retourne données cachées (vérifié dans tests unitaires 02-01 à 02-05) | SATISFAIT |
| Échec d'un collecteur retourne résultat partiel avec flag | SATISFAIT |
| Éligibilité PEA fonctionne avec détection de changement | SATISFAIT |
| Rate-limit sleeps présents dans chaque module collecteur | SATISFAIT |

## Self-Check: PASSED

- tests/test_integration.py : FOUND
- main.py (avec collect_all) : FOUND
- Commit 96ef4dc (RED) : FOUND
- Commit 86444f9 (GREEN) : FOUND
- 42 tests passent : CONFIRMED
