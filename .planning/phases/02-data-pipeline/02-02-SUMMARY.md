---
phase: 02-data-pipeline
plan: "02-02"
subsystem: collectors
tags: [tdd, crypto, coingecko, fear-greed, cache, sqlite, httpx]
dependency_graph:
  requires: [db/cache.py, config.py, logging_setup.py]
  provides: [collectors/crypto.py]
  affects: [reporters/daily.py, reporters/weekly.py]
tech_stack:
  added: [httpx]
  patterns: [sqlite-cache-ttl, graceful-degradation, tdd-red-green, batch-api-call]
key_files:
  created:
    - collectors/crypto.py
    - tests/test_crypto.py
  modified: []
decisions:
  - "Batch unique CoinGecko pour les 8 coins (1 requête au lieu de 8) — minimise le nombre d'appels et le risque de rate limit"
  - "time.sleep(CG_SLEEP_SECONDS) même après batch unique — conformité rate limit conservative"
  - "coingecko_api_key jamais loguée — seul le message d'erreur générique est émis (T-02-05)"
  - "SQL paramétré (INSERT OR REPLACE) — protection injection SQLite (T-02-06)"
metrics:
  duration: "56 secondes"
  completed_date: "2026-05-09"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 2 Plan 02: Crypto Collector (TDD) Summary

**One-liner:** Collecte crypto CoinGecko batch (8 coins) + Fear & Greed Alternative.me, cache SQLite 1h, dégradation gracieuse totale via httpx.

## What Was Built

`collectors/crypto.py` implémente `collect_crypto(config: Config) -> dict` en cycle TDD complet (RED → GREEN) :

- **Batch CoinGecko** : appel unique `/coins/markets` pour 8 coins (bitcoin, ethereum, binancecoin, solana, ripple, cardano, avalanche-2, dogecoin), sleep 1.5s après
- **Fear & Greed** : appel séparé `https://api.alternative.me/fng/?limit=1`, sans authentification
- **Cache SQLite** : TTL 1h, source `coingecko` par coin + source `fear_greed` pour l'index
- **Dégradation gracieuse** : flags `coingecko_failed`, `fear_greed_failed`, `partial` — jamais d'exception propagée
- **Sécurité** : requêtes SQL paramétrées, API key jamais loguée

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | `6492b88` | 5 tests en ImportError — gate confirmé |
| GREEN (feat) | `0f7789d` | 5/5 tests passent — gate confirmé |

## Commits

| Task | Type | Hash | Description |
|------|------|------|-------------|
| Task 1 (RED) | test | `6492b88` | tests/test_crypto.py — 5 tests en échec (ImportError) |
| Task 2 (GREEN) | feat | `0f7789d` | collectors/crypto.py — implémentation complète |

## Test Coverage

| Test | Scénario | Résultat |
|------|----------|---------|
| test_cache_hit_skips_coingecko | Cache valide pour tous les coins → httpx.get non appelé | PASS |
| test_cache_miss_fetches_coingecko_and_writes_cache | Cache vide → CoinGecko + FNG appelés, cache écrit | PASS |
| test_coingecko_failure_sets_flag | CoinGecko échoue → coingecko_failed=True, FNG quand même collecté | PASS |
| test_fear_greed_failure_sets_flag | Alternative.me échoue → fear_greed_failed=True, coins populés | PASS |
| test_collect_crypto_never_raises | Toutes les APIs échouent → retourne dict sans exception | PASS |

**Total suite :** 23/23 tests passent (tests/test_config.py + test_db_cache.py + test_etf.py + test_crypto.py)

## Deviations from Plan

None — plan exécuté exactement tel qu'écrit.

## Threat Surface Scan

Menaces couvertes selon le threat model du plan :

| Threat ID | Mitigation | Fichier | Statut |
|-----------|-----------|---------|--------|
| T-02-05 | coingecko_api_key jamais loguée | collectors/crypto.py | Mitigé |
| T-02-06 | SQL paramétré INSERT OR REPLACE | collectors/crypto.py:73 | Mitigé |
| T-02-07 | CG_SLEEP_SECONDS=1.5 après batch | collectors/crypto.py:162 | Mitigé |
| T-02-08 | Alternative.me accepté comme informationnel | collectors/crypto.py | Accepté |

Aucune nouvelle surface de menace non couverte par le plan.

## Known Stubs

Aucun — `collect_crypto` retourne des données réelles (ou flags d'échec explicites).

## Self-Check: PASSED

- [x] `collectors/crypto.py` existe et contient `def collect_crypto`
- [x] `tests/test_crypto.py` existe avec 5 fonctions de test
- [x] Commit RED `6492b88` présent dans git log
- [x] Commit GREEN `0f7789d` présent dans git log
- [x] 23/23 tests passent
- [x] `CG_SLEEP_SECONDS = 1.5` défini et appelé
- [x] `alternative.me/fng` présent dans l'URL
- [x] `INSERT OR REPLACE INTO market_cache` (SQL paramétré)
