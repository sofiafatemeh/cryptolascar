---
phase: 02-data-pipeline
plan: "02-05"
subsystem: data-collection
tags: [newsapi, beautifulsoup4, httpx, sqlite, scraping, cache, graceful-degradation]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: db/cache.py (get_connection, init_db), config.py (Config.newsapi_key), logging_setup.py
provides:
  - collectors/news.py avec collect_news(config) retournant headlines NewsAPI + BS4 scrapés
  - Cache SQLite 2h source="news" symbol="headlines"
  - Dégradation gracieuse avec flags newsapi_failed, scrape_failed, partial
affects:
  - reporters/daily.py (consommera collect_news pour la section actualités)
  - reporters/weekly.py (idem)

# Tech tracking
tech-stack:
  added: [beautifulsoup4 (html.parser), httpx (déjà présent)]
  patterns:
    - Cache hit/miss SQLite avec TTL paramétrable
    - Scraping BS4 par sélecteurs CSS simples sans JS
    - Sleep inter-domaines pour rate limiting (T-02-19)
    - Flags d'erreur structurés dans le dict de retour

key-files:
  created:
    - collectors/news.py
    - tests/test_news.py
  modified: []

key-decisions:
  - "02-05-A: patch('httpx.get') au niveau module (non 'collectors.news.httpx.get') — cohérent avec 02-04-B"
  - "02-05-B: Sleep uniquement entre domains (pas avant le premier) — logique first_request bool cohérente avec 02-04-A"
  - "02-05-C: Clé NewsAPI jamais loguée (T-02-17) — uniquement str(exc) dans logger.error()"

patterns-established:
  - "TDD RED/GREEN: test ImportError avant implémentation, 5/5 tests passent en GREEN"
  - "Scraping BS4 non-crashant: chaque source dans try/except, log warning, continue"
  - "Cache upsert paramétré: INSERT OR REPLACE avec (source, symbol) — pattern identique aux autres collectors"

requirements-completed: [DATA-05, DATA-06, DATA-08]

# Metrics
duration: 3min
completed: 2026-05-10
---

# Phase 2 Plan 05: News Collector Summary

**Collecteur de titres financiers via NewsAPI (10 articles) + scraping BS4 de CoinDesk/CoinTelegraph/Boursorama/AMF (5 par site), cache SQLite 2h, dégradation gracieuse complète**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-10T05:59:13Z
- **Completed:** 2026-05-10T06:01:45Z
- **Tasks:** 2 (RED + GREEN TDD)
- **Files modified:** 2

## Accomplishments

- `collect_news(config)` retourne un dict structuré avec jusqu'à 35 headlines (dedupliqués par URL)
- Cache SQLite 2h source="news" symbol="headlines" — requêtes paramétrées (T-02-21)
- Scraping BS4 de 4 sources financières avec sleep 1.0s inter-domaines (T-02-19)
- Dégradation gracieuse : `newsapi_failed`, `scrape_failed`, `partial` flags — never raises
- Clé NewsAPI non loguée (T-02-17) — conformité threat model complète

## Task Commits

Chaque tâche a été commitée atomiquement :

1. **Task 1 (RED): tests/test_news.py** - `0f6edd0` (test)
2. **Task 2 (GREEN): collectors/news.py** - `f3b3f74` (feat)

## TDD Gate Compliance

- RED gate : commit `0f6edd0` — `test(02-05): add failing tests for collect_news (RED TDD gate)` — 5 tests, ImportError confirmé
- GREEN gate : commit `f3b3f74` — `feat(02-05): implement collectors/news.py with NewsAPI + BS4 scraping (GREEN TDD gate)` — 5/5 tests passent

## Files Created/Modified

- `collectors/news.py` — `collect_news(config: Config) -> dict`, scrapers BS4 x4, cache layer, dégradation gracieuse
- `tests/test_news.py` — 5 tests pytest avec fixtures tmp_config et mocks httpx

## Decisions Made

- **02-05-A :** `patch("httpx.get")` au niveau module (non `"collectors.news.httpx.get"`) — cohérent avec la décision 02-04-B prise pour httpx dans macro.py
- **02-05-B :** Sleep inter-domaines uniquement (pas avant le premier) via logique `first_request` bool — cohérent avec 02-04-A
- **02-05-C :** La clé NewsAPI est envoyée dans les query params HTTPS (T-02-17) — jamais loguée, uniquement `str(exc)` dans `logger.error()`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — collect_news retourne des données réelles (ou liste vide lors de dégradation), aucune valeur hardcodée.

## Threat Flags

Aucun nouveau vecteur non couvert par le plan détecté.

| Flag | File | Description |
|------|------|-------------|
| (none) | — | Toutes les surfaces couvertes par T-02-17 à T-02-21 |

## User Setup Required

Variable `NEWSAPI_KEY` dans `.env` (optionnelle — si absente, `newsapi_failed=True` et scraping seul est utilisé).

## Next Phase Readiness

- `collect_news(config)` prêt pour intégration dans `reporters/daily.py` et `reporters/weekly.py`
- Pipeline data Phase 2 complet : ETF, Crypto, PEA, Macro, News — 39/39 tests passent
- Phase 3 (Reporters) peut démarrer

---
*Phase: 02-data-pipeline*
*Completed: 2026-05-10*
