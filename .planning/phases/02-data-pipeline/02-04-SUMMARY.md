---
phase: 02-data-pipeline
plan: "02-04"
subsystem: data-collection
tags: [fred, macro, httpx, sqlite, tdd, cache, rate-limiting]

requires:
  - phase: 01-foundation
    provides: db/cache.py (get_connection, init_db), config.py (Config), logging_setup.py

provides:
  - collectors/macro.py avec collect_macro(config) -> dict
  - Cache SQLite 24h pour 4 séries FRED (DGS10, DGS2, CPIAUCSL, M2SL)
  - tests/test_macro.py avec 5 tests TDD (RED+GREEN validés)

affects:
  - reporters/daily.py (consommera collect_macro pour taux d'intérêt et inflation)
  - reporters/weekly.py (indicateurs macro hebdomadaires)
  - reporters/monthly.py (tendances macro mensuelles)

tech-stack:
  added: []
  patterns:
    - "FRED API via httpx avec params dict — clé API jamais loguée"
    - "Cache SQLite TTL 24h par série (source='fred', symbol=series_id)"
    - "Rate limit : FRED_SLEEP_SECONDS=1.0 après chaque appel HTTP"
    - "Dégradation gracieuse : clé vide → fred_failed=True ; exception série → partial=True"

key-files:
  created:
    - collectors/macro.py
    - tests/test_macro.py
  modified: []

key-decisions:
  - "02-04-A: time.sleep(1.0s) après chaque appel FRED réussi (et non avant) — simplifie la logique first_call"
  - "02-04-B: first_api_call bool pour éviter sleep avant le tout premier appel FRED — conserve 1s entre les appels suivants"
  - "02-04-C: patch('httpx.get') dans les tests (non 'collectors.macro.httpx.get') car httpx importé au niveau module"

patterns-established:
  - "Pattern FRED: params dict httpx avec series_id/api_key/file_type/sort_order/limit — reproduire pour autres collectors FRED"
  - "Pattern cache: _get_cached() / _upsert_cache() séparés, appelés par collect_macro — même structure que ETF/crypto"

requirements-completed: [DATA-04, DATA-08]

duration: 2min
completed: 2026-05-09
---

# Phase 2 Plan 04: Macro/FRED Collector Summary

**collect_macro() via FRED API avec cache SQLite 24h : DGS10, DGS2, CPIAUCSL, M2SL — dégradation gracieuse et rate limit 1s/appel**

## Performance

- **Duration:** 2 min (141 secondes)
- **Started:** 2026-05-09T21:04:04Z
- **Completed:** 2026-05-09T21:06:25Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 2

## Accomplishments

- Collecteur FRED complet avec les 4 séries macro : DGS10 (taux 10Y), DGS2 (taux 2Y), CPIAUCSL (inflation), M2SL (masse monétaire)
- Cache SQLite 24h par série — une série en cache ne déclenche aucun appel HTTP
- Sleep 1.0s entre chaque appel FRED (rate limiting T-02-15 respecté)
- Dégradation gracieuse totale : clé manquante, échec série individuelle, échec total — jamais d'exception propagée
- Sécurité : clé API jamais loguée, requêtes SQL paramétrées (T-02-13, T-02-14)
- 5/5 tests TDD passent ; 34/34 tests totaux passent

## Task Commits

1. **Task 1: RED — tests/test_macro.py (5 tests échouants)** — `411d23e` (test)
2. **Task 2: GREEN — collectors/macro.py (implémentation complète)** — `a68331b` (feat)

## TDD Gate Compliance

- RED gate confirmé : `test(02-04)` commit `411d23e` — ImportError avant implémentation
- GREEN gate confirmé : `feat(02-04)` commit `a68331b` — 5/5 tests passent

## Files Created/Modified

- `collectors/macro.py` — collect_macro(), _fetch_fred_series(), _get_cached(), _upsert_cache(), constantes FRED
- `tests/test_macro.py` — 5 tests TDD : cache_hit, cache_miss, missing_key, partial_failure, never_raises

## Decisions Made

- **02-04-A :** time.sleep(1.0s) placé après chaque appel FRED réussi (pattern symétrique avec le call). Logique `first_api_call` bool pour éviter sleep inutile avant le tout premier appel — 4 séries = max 4 sleeps.
- **02-04-B :** `first_api_call = True` réinitialisé par série — si toutes les séries sont en cache, aucun sleep n'est effectué.
- **02-04-C :** Tests utilisent `patch("httpx.get")` (non `"collectors.macro.httpx.get"`) car httpx est importé au niveau module dans macro.py et les tests le patchent globalement.

## Deviations from Plan

Aucune — plan exécuté exactement tel qu'écrit. L'implémentation de `collectors/macro.py` suit le template fourni dans le plan à la ligne près.

## Threat Surface Scan

Aucun nouveau vecteur d'attaque non couvert par le threat_model du plan :
- T-02-13 (api_key dans logs) : mitigé — logger.error() ne logue que series_id et str(e)
- T-02-14 (SQL injection) : mitigé — toutes les requêtes utilisent des placeholders `?`
- T-02-15 (DoS rate limit) : mitigé — FRED_SLEEP_SECONDS=1.0 appliqué systématiquement
- T-02-16 (clé absente) : accepté — log warning, fred_failed=True, collecte macro optionnelle

## Issues Encountered

Aucun problème rencontré.

## Next Phase Readiness

- collectors/macro.py prêt à être importé par reporters/daily.py, weekly.py, monthly.py
- Toutes les 4 séries FRED disponibles via result["series"]["DGS10"]["value"] etc.
- Cache 24h en place — reporters peuvent appeler collect_macro sans surcharger FRED

---
*Phase: 02-data-pipeline*
*Completed: 2026-05-09*
