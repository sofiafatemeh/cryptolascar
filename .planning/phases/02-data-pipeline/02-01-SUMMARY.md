---
phase: "02-data-pipeline"
plan: "02-01"
subsystem: "collectors"
tags: [etf, yfinance, alpha-vantage, sqlite-cache, tdd, graceful-degradation]
completed_date: "2026-05-09"
duration_minutes: 8

dependency_graph:
  requires:
    - "01-03: db/cache.py (get_connection, init_db)"
    - "01-02: config.py (Config dataclass, alpha_vantage_key)"
    - "01-03: logging_setup.py (get_logger)"
  provides:
    - "collectors/etf.py: collect_etf(config) -> dict"
  affects:
    - "reporters/daily.py (consommateur futur)"
    - "tests/test_etf.py"

tech_stack:
  added:
    - "yfinance>=0.2.40 (installé en Phase 2, déclaré dans requirements.txt)"
    - "httpx>=0.27.0 (déjà dans requirements.txt, utilisé pour Alpha Vantage)"
  patterns:
    - "TDD: RED commit avant GREEN commit"
    - "Cache SQLite TTL 4h avec INSERT OR REPLACE"
    - "Dégradation gracieuse par ticker (partial=True)"
    - "Fallback AV avec détection quota Note/Information"
    - "Requêtes SQL paramétrées (mitigation T-02-02)"

key_files:
  created:
    - "collectors/etf.py"
    - "tests/test_etf.py"
  modified: []

decisions:
  - "02-01: Test cache hit pré-remplit tous les tickers ETF (pas seulement SPY) pour assert_not_called() correct"
  - "02-01: av_failed initialisé à True si alpha_vantage_key vide — pas d'appel AV inutile"
  - "02-01: yfinance installé via pip --break-system-packages (VPS sans venv actif)"

metrics:
  duration_minutes: 8
  tasks_completed: 2
  files_created: 2
  files_modified: 0
  tests_added: 5
  tests_passing: 18
---

# Phase 2 Plan 01: ETF Collector (TDD) Summary

ETF collector avec yfinance primaire, Alpha Vantage supplément, cache SQLite 4h, et dégradation gracieuse par ticker.

## What Was Built

`collectors/etf.py` expose `collect_etf(config: Config) -> dict` qui collecte les prix ETF (SPY, QQQ, IWDA.AS, EIMI.AS, CSPX.AS) depuis yfinance avec un cache SQLite de 4 heures. Alpha Vantage enrichit les données si une clé est fournie. La fonction ne propage jamais d'exception.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED — tests échouent (ImportError) | `8719aeb` | PASSED |
| GREEN — 5 tests passent | `dfef2a2` | PASSED |
| REFACTOR | Non requis | N/A |

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RED: Write failing tests | `8719aeb` | tests/test_etf.py |
| 2 | GREEN: Implement collectors/etf.py | `dfef2a2` | collectors/etf.py, tests/test_etf.py |

## Test Coverage

| Test | Description | Status |
|------|-------------|--------|
| test_cache_hit_skips_yfinance | Cache valide → yfinance non appelé | PASSED |
| test_cache_miss_fetches_yfinance_and_writes_cache | Cache miss → yfinance appelé + upsert | PASSED |
| test_alpha_vantage_quota_sets_flag | Réponse AV {"Note":...} → alpha_vantage_failed=True | PASSED |
| test_yfinance_failure_sets_partial | Exception yfinance pour SPY → partial=True, price=None | PASSED |
| test_collect_etf_never_raises | Défaillance totale → retourne dict sans lever | PASSED |

## Verification Checks

```
collect_etf function present:    collectors/etf.py:143
INSERT OR REPLACE INTO market_cache: collectors/etf.py:76
alpha_vantage_key usage (not hardcoded): collectors/etf.py:173,200,202
time.sleep calls: 1 (AV_SLEEP_SECONDS=0.5)
Full test suite: 18/18 passed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Correction test_cache_hit_skips_yfinance**
- **Trouvé pendant:** Tâche 2 (GREEN) — premier run pytest
- **Problème:** Le test pré-insérait uniquement "SPY" en cache, puis assertait `mock_yf.Ticker.assert_not_called()` — mais les 4 autres tickers (QQQ, IWDA.AS, EIMI.AS, CSPX.AS) sans cache déclenchaient bien des appels yfinance, ce qui faisait échouer l'assertion.
- **Correction:** Pré-remplissage de TOUS les tickers ETF dans le cache avant d'appeler collect_etf — l'assertion devient correcte.
- **Fichiers modifiés:** tests/test_etf.py
- **Commit:** `dfef2a2`

**2. [Rule 3 - Blocker] Installation de yfinance manquante**
- **Trouvé pendant:** Tâche 2 (GREEN) — import
- **Problème:** `ModuleNotFoundError: No module named 'yfinance'` — le paquet était dans requirements.txt mais non installé dans l'environnement système.
- **Correction:** `pip install yfinance httpx --break-system-packages`
- **Fichiers modifiés:** Aucun (installation système)
- **Commit:** N/A (installation de dépendance)

## Security Notes (STRIDE)

| Threat | Mitigation | Verified |
|--------|-----------|---------|
| T-02-01 (api_key dans logs) | `logger.warning("... %s: %s", symbol, e)` — pas de api_key | Oui |
| T-02-02 (SQL injection) | Requêtes paramétrées `(?,?,?,?,?)` uniquement | Oui |
| T-02-03 (DoS quota AV) | sleep 0.5s + gestion gracieuse quota épuisé | Oui |
| T-02-04 (Spoofing yfinance) | Accept — données informatives, pas d'auth possible | Accepté |

## Known Stubs

Aucun stub — collect_etf retourne des données réelles (ou None avec error flag en cas d'échec).

## Self-Check: PASSED

- collectors/etf.py: FOUND
- tests/test_etf.py: FOUND
- Commit 8719aeb (RED): FOUND
- Commit dfef2a2 (GREEN): FOUND
- 18/18 tests passed: CONFIRMED
