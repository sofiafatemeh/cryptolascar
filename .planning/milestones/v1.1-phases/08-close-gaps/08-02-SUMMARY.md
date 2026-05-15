---
phase: 08-close-gaps
plan: 02
subsystem: reporters
tags: [chart-transform, etf, pea, fear-greed, tdd, CHART-01, CHART-03, CHART-04]

# Dependency graph
requires:
  - phase: 08-01
    provides: "collectors/etf.py retourne pct_change_1w; collectors/crypto.py retourne history"
provides:
  - "reporters/daily.py _build_chart_panel passe {ticker: {1d, 1w}} à generate_etf_chart"
  - "reporters/weekly.py _build_chart_panel idem"
  - "reporters/monthly.py _build_chart_panel idem"
  - "generate_pea_table reçoit list[dict] dans les 3 reporters"
  - "fg_score extraction ne lève pas AttributeError quand fear_greed=None"
affects: [charts/etf.py, charts/pea.py, delivery/email.py]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_PEA_NAMES + _PEA_ELIGIBILITY: dicts constants module-level dans les 3 reporters"
    - "etf_chart_data dict comprehension: {sym: {'1d': pct_change, '1w': pct_change_1w}} filtrant pct_change is not None"
    - "pea_list list comprehension: [{ticker, name, price, change_1d, change_1w, pea_eligible}] filtrant price is not None"
    - "(... .get('fear_greed') or {}).get('value'): pattern None-safe pour valeurs absentes/None"

key-files:
  created: []
  modified:
    - reporters/daily.py
    - reporters/weekly.py
    - reporters/monthly.py
    - tests/test_reporters_daily.py
    - tests/test_reporters_weekly.py
    - tests/test_reporters_monthly.py

key-decisions:
  - "08-02-A: _PEA_NAMES/_PEA_ELIGIBILITY définis au niveau module (pas inline) — réutilisables par toute évolution future de _build_chart_panel"
  - "08-02-B: etf_chart_data filtre pct_change is not None — conforme T-08-05 (tamper filter avant chart generator)"
  - "08-02-C: pea_list filtre price is not None — évite des entrées vides dans le tableau HTML généré"
  - "08-02-D: _crypto_section daily.py corrigée (Rule 1) — fg = crypto.get('fear_greed', {}) retournait None si valeur=None"

# Metrics
duration: ~5min
completed: 2026-05-15
---

# Phase 8 Plan 02: Close Gaps — Reporter Transform Layer Summary

**Correction de la couche de transformation dans _build_chart_panel des 3 reporters (daily/weekly/monthly) — generate_etf_chart reçoit {ticker: {1d, 1w}} et generate_pea_table reçoit list[dict]; fg_score extraction None-safe.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-15T11:55:17Z
- **Completed:** 2026-05-15T12:00:00Z
- **Tasks:** 1 (TDD: 1 RED commit + 1 GREEN commit)
- **Files modified:** 6

## Accomplishments

- `reporters/daily.py`, `reporters/weekly.py`, `reporters/monthly.py` : correction de `_build_chart_panel` avec :
  - **CHART-03** : `((... .get("fear_greed") or {}).get("value"))` — empêche `AttributeError` quand `fear_greed=None`
  - **CHART-01** : `etf_chart_data = {sym: {"1d": pct_change, "1w": pct_change_1w} ...}` — passage du dict transformé à `generate_etf_chart`
  - **CHART-04** : `pea_list = [{ticker, name, price, change_1d, change_1w, pea_eligible} ...]` — passage de la liste transformée à `generate_pea_table`
  - Ajout des constantes `_PEA_NAMES` et `_PEA_ELIGIBILITY` en tête de chaque fichier
- 9 nouveaux tests (3 par fichier de test) couvrant CHART-01/03/04
- 48 tests au total passent (39 existants + 9 nouveaux)

## Task Commits

1. **RED: Tests CHART-01/03/04** - `9700b96` (test)
2. **GREEN: Implémentation des 3 corrections** - `a938ef2` (feat)

## Files Created/Modified

- `reporters/daily.py` — `_PEA_NAMES`, `_PEA_ELIGIBILITY`, correction `_build_chart_panel` (3 fixes) + `_crypto_section` fg None-safe (Rule 1)
- `reporters/weekly.py` — `_PEA_NAMES`, `_PEA_ELIGIBILITY`, correction `_build_chart_panel` (3 fixes)
- `reporters/monthly.py` — `_PEA_NAMES`, `_PEA_ELIGIBILITY`, correction `_build_chart_panel` (3 fixes)
- `tests/test_reporters_daily.py` — 3 nouveaux tests Phase 8 + alias `make_config` public
- `tests/test_reporters_weekly.py` — 3 nouveaux tests Phase 8 + alias `make_config` public
- `tests/test_reporters_monthly.py` — 3 nouveaux tests Phase 8 + alias `make_config` public

## Decisions Made

- **08-02-A:** `_PEA_NAMES`/`_PEA_ELIGIBILITY` au niveau module — séparation claire des données de configuration et de la logique de transformation
- **08-02-B:** Filtre `pct_change is not None` dans `etf_chart_data` — conforme au threat model T-08-05
- **08-02-C:** Filtre `price is not None` dans `pea_list` — évite les lignes vides dans `generate_pea_table`
- **08-02-D:** Correction Rule 1 dans `_crypto_section` daily.py — `fear_greed=None` causait AttributeError dans la section narrative, pas seulement dans le chart panel

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _crypto_section dans daily.py : fear_greed=None causait AttributeError**
- **Found during:** Phase GREEN (exécution des tests — l'erreur apparaissait dans `_crypto_section`, pas dans `_build_chart_panel`)
- **Issue:** `fg = crypto.get("fear_greed", {})` retourne `None` quand la clé existe mais sa valeur est `None`. Le défaut `{}` n'est utilisé que quand la clé est **absente**. Ensuite `fg.get("label", "n/a")` lève `AttributeError: 'NoneType' object has no attribute 'get'`. Cette exception était propagée jusqu'au `try/except` global de `build_daily_report`, qui déclenchait le fallback total — empêchant `_build_chart_panel` d'être atteint.
- **Fix:** Changement de `fg = crypto.get("fear_greed", {})` en `fg = crypto.get("fear_greed") or {}` dans `_crypto_section` de `daily.py` (weekly.py et monthly.py avaient déjà le pattern correct)
- **Files modified:** `reporters/daily.py`
- **Commit:** `a938ef2` (inclus dans le commit feat Task 1 GREEN)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug None-safety dans `_crypto_section`)
**Impact sur le plan:** La correction était nécessaire pour que les tests CHART-01/04 puissent vérifier `_build_chart_panel`. Elle ne sortait pas du périmètre du plan — le pattern `or {}` après `.get("fear_greed")` est la même sécurité demandée pour CHART-03.

## TDD Gate Compliance

- RED gate : commit `9700b96` (test) — 9 tests ajoutés, 6 échouant correctement
- GREEN gate : commit `a938ef2` (feat) — 48 tests passent

## Threat Surface Scan

Aucune nouvelle surface réseau. Les modifications sont strictement dans la couche de transformation (dict → chart generators). Conformité avec T-08-05, T-08-06, T-08-07 du threat model du plan.

## Known Stubs

Aucun. Les 3 transformations sont câblées sur les vraies données collectées par la couche Phase 8 Plan 01.

## Next Phase Readiness

- **08-03 (Wave 3)** peut démarrer : la couche reporters est maintenant correcte
- `generate_etf_chart` reçoit `{TICKER: {"1d": float, "1w": float}}` — conforme au contrat `charts/etf.py`
- `generate_pea_table` reçoit `list[dict]` — conforme au contrat `charts/pea.py`
- `fear_greed=None` ne provoque plus d'erreur dans aucun reporter

## Self-Check: PASSED

- reporters/daily.py — FOUND
- reporters/weekly.py — FOUND
- reporters/monthly.py — FOUND
- 08-02-SUMMARY.md — FOUND
- Commit 9700b96 (RED) — FOUND
- Commit a938ef2 (GREEN) — FOUND
- 48 tests passing — VERIFIED
