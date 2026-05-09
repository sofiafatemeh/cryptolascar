---
phase: 01-foundation
plan: "03"
subsystem: database-logging-entrypoint
tags: [sqlite, logging, main, tdd, storage]
dependency_graph:
  requires: [01-01, 01-02]
  provides:
    - db/cache.py (init_db, get_connection, SQLite schema)
    - logging_setup.py (setup_logging, get_logger)
    - main.py (entry point orchestrant config + logging + DB + run_log)
  affects:
    - Tous les modules Phase 2+ qui utilisent init_db() ou get_connection()
    - Tous les modules qui appellent get_logger()
tech_stack:
  added:
    - sqlite3 (stdlib Python — pas SQLAlchemy)
    - logging (stdlib Python)
  patterns:
    - TDD RED/GREEN pour db/cache.py
    - CREATE TABLE IF NOT EXISTS pour idempotence SQLite
    - WAL mode + foreign_keys via PRAGMA
    - Logging structuré ISO 8601 stdout + fichier optionnel
    - Dégradation gracieuse : erreur config = exit(1) propre
key_files:
  created:
    - db/cache.py
    - tests/test_db_cache.py
    - logging_setup.py
    - main.py
  modified: []
decisions:
  - "Chaque connexion :memory: SQLite est indépendante — init_db(':memory:') puis get_connection(':memory:') donnent des DBs séparées (comportement stdlib attendu, tests d'intégration utilisent un fichier tempfile)"
  - "logging standard Python choisi sur structlog pour limiter les dépendances en Phase 1 — structlog reste optionnel pour Phase 2+"
  - "log_run() dans main.py (pas dans db/cache.py) pour séparer l'infrastructure DB de la logique métier d'exécution"
metrics:
  duration: "5 minutes"
  completed: "2026-05-09"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 0
---

# Phase 1 Plan 03: Couche d'exécution — SQLite init, logging structuré, main.py entry point

Initialisation SQLite avec schema complet (tables market_cache et run_log), logging structuré ISO 8601 avec handler fichier optionnel, et point d'entrée main.py qui orchestre config → logging → init_db → log_run au démarrage. Après ce plan, `python main.py` avec un `.env` valide s'exécute sans erreur, crée la DB, insère une entrée run_log et laisse une trace lisible dans les logs.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Tests TDD pour db/cache.py | 6c901fa | tests/test_db_cache.py |
| 1 (GREEN) | Implémenter db/cache.py | ca4abb4 | db/cache.py |
| 2 | Créer logging_setup.py et main.py | a4d8041 | logging_setup.py, main.py |

## TDD Gate Compliance

- RED gate : commit `6c901fa` — `test(01-03): add failing tests for db/cache.py (RED phase TDD)` — ImportError (db.cache non encore implémenté)
- GREEN gate : commit `ca4abb4` — `feat(01-03): implement db/cache.py with SQLite init and schema (GREEN phase TDD)` — 7/7 tests passent

## Verification Results

```
# 1. Tests unitaires DB — 7 passed
python3 -m pytest tests/test_db_cache.py -v
=> 7 passed in 0.04s

# 2. Tous les tests — 13 passed
python3 -m pytest tests/ -v
=> 13 passed in 0.07s

# 3. logging_setup importable
python3 -c "from logging_setup import setup_logging, get_logger; print('OK')"
=> OK

# 4. main.py avec config manquante — exit 1 propre
python3 -c "from main import main; print(main())"
=> ERREUR DE CONFIGURATION : Variable d'environnement manquante ou vide : SMTP_HOST.
=> Exit code : 1

# 5. main.py avec fichier DB réel — exit 0 + log entry
python3 -c "...DB_PATH=/tmp/test.db...from main import main; print(main())"
=> 2026-05-09T... | INFO | cryptolascar.main | CryptoLascar démarrage...
=> 2026-05-09T... | INFO | cryptolascar.main | Base de données SQLite initialisée : /tmp/test.db
=> 2026-05-09T... | INFO | cryptolascar.main | Run démarré à 2026-05-09T...
=> 2026-05-09T... | INFO | cryptolascar.main | Foundation OK — collecteurs, générateurs et delivery seront câblés en Phase 2+
=> Exit code (attendu 0) : 0
=> {'id': 1, 'run_at': '2026-05-09T...Z', 'status': 'success', ...}
```

## Deviations from Plan

None - plan exécuté exactement comme spécifié.

## Threat Model Compliance

| Threat ID | Statut | Implémentation |
|-----------|--------|----------------|
| T-01-07 | Mitigé | logging_setup.py ne logue jamais les valeurs de config — erreur config affiche uniquement le NOM de variable |
| T-01-08 | Accepté | DB locale sur VPS — permissions système Linux |
| T-01-09 | Mitigé | main() retourne exit(1) propre sur ValueError, pas de boucle infinie ni crash non géré |
| T-01-10 | Accepté | run_log contient timestamps et noms de sources uniquement — pas de données sensibles |

## Known Stubs

Tâche 5 de main.py : `"Foundation OK — collecteurs, générateurs et delivery seront câblés en Phase 2+"` — placeholder intentionnel, sera remplacé en Phase 2 par les appels aux collectors et reporters.

## Threat Flags

Aucune nouvelle surface de sécurité non planifiée introduite.

## Self-Check: PASSED

- db/cache.py: FOUND
- tests/test_db_cache.py: FOUND
- logging_setup.py: FOUND
- main.py: FOUND
- Commit 6c901fa: FOUND (TDD RED)
- Commit ca4abb4: FOUND (TDD GREEN)
- Commit a4d8041: FOUND (logging + main)
- 13/13 tests passent
