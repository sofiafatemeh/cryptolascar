---
phase: 05-scheduling-resilience
verified: 2026-05-13T23:50:00Z
status: human_needed
score: 6/7 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Re-installer le crontab avec la version corrigée de install_cron.sh (cron monthly = 1 8 * * *) et confirmer crontab -l"
    expected: "crontab -l affiche '1 8 * * *' pour main.py --mode monthly (offset CR-02 actif)"
    why_human: "Le crontab installé montre 0 8 * * * (ancienne version) mais install_cron.sh contient maintenant 1 8 * * * (post CR-02). La divergence ne peut être résolue qu'en réinstallant via la vérification humaine."
---

# Phase 5 : Scheduling & Resilience — Rapport de Vérification

**Objectif de la phase :** Le pipeline complet tourne de façon autonome selon le calendrier (3 triggers cron), se dégrade gracieusement si une source échoue, et un smoke test end-to-end confirme que le système est prêt pour la production.
**Vérifié :** 2026-05-13T23:50:00Z
**Statut :** human_needed
**Re-vérification :** Non — vérification initiale

---

## Critères de succès du ROADMAP

Source d'autorité : `.planning/ROADMAP.md`, Phase 5, section `Success Criteria`.

| # | Critère | Statut | Preuve |
|---|---------|--------|--------|
| SC-1 | Entrées cron pour daily lun-sam 07h00, weekly dim 08h00, monthly dernier jour 08h00 installées et vérifiées avec `crontab -l` | ? UNCERTAIN | Crontab installé montre les 3 entrées (SUMMARY.md task 2 + vérification `crontab -l` live), mais divergence entre script et crontab installé pour l'entrée monthly (détail ci-dessous) |
| SC-2 | Un run complet se termine sans exception non gérée et livre l'email dans la boîte réceptrice | ✓ VERIFIED | Smoke test humain : exit 0, email reçu à siavach@hotmail.com, archive reports/daily/2026-05-13.md confirmée, run_log status="success" |
| SC-3 | Quand une source est hors ligne, le run se termine, rapport partiel envoyé, log note la source échouée | ✓ VERIFIED | collect_all() encapsule chaque collecteur dans try/except (main.py:87-94) ; smoke test avec clés API absentes → status="success" avec sources_ok="etf(partial),crypto(partial),pea(partial),macro(partial),news" |
| SC-4 | Le système récupère automatiquement au prochain run schedulé sans intervention manuelle | ✓ VERIFIED | Par design : le cron relance à la prochaine occurrence ; outer try/except (main.py:237-249) garantit exit 1 + log_run "error", pas de corruption d'état |

---

## Vérités observables (must-haves fusionnés des plans 05-01 et 05-02)

| # | Vérité | Statut | Preuve |
|---|--------|--------|--------|
| 1 | `python main.py --mode daily` exécute le pipeline complet et retourne exit 0 | ✓ VERIFIED | Smoke test humain exit 0 + run_log "success" confirmé ; 10 tests unitaires couvrent ce chemin |
| 2 | `python main.py --mode weekly` retourne exit 0, pipeline weekly exécuté | ✓ VERIFIED | test_mode_weekly_success PASSED ; wiring select_reports/send_email/write_tweet/archive_report vérifié dans main.py |
| 3 | `python main.py --mode monthly` sort 0 tôt (run_log "skipped") quand aujourd'hui n'est pas le dernier jour du mois | ✓ VERIFIED | main.py:202-208 ; test_mode_monthly_skip_non_last_day PASSED |
| 4 | `python main.py --mode monthly` exécute le pipeline complet le dernier jour du mois | ✓ VERIFIED | main.py:213-235 ; test_mode_monthly_last_day PASSED |
| 5 | Exception dans reporter/delivery → log erreur, run_log status="error", exit 1 | ✓ VERIFIED | main.py:237-249 outer try/except ; test_mode_daily_send_email_failure et test_mode_daily_archive_failure PASSED |
| 6 | Chaque run écrit exactement une entrée run_log | ✓ VERIFIED | 3 chemins distincts (success, skipped, error) — chacun contient un seul appel log_run ; T7 (REPT-04 dual) : 2 rapports → 1 seul log_run |
| 7 | scheduler/install_cron.sh contient exactement les 3 entrées crontab correctes de D-02 | ? UNCERTAIN | SCHED-03 requiert `0 8 * * *` ; install_cron.sh contient `1 8 * * *` (CRON_MONTHLY offset post-CR-02). Le crontab installé correspond à `0 8 * * *` mais a été installé avant le commit CR-02. Divergence entre script et crontab live. |

**Score :** 6/7 vérités confirmées

---

## Artefacts requis

| Artefact | Description attendue | Statut | Détails |
|----------|---------------------|--------|---------|
| `scheduler/utils.py` | `is_last_day_of_month()` importable, 5 cas comportement OK | ✓ VERIFIED | Existe, 23 lignes, importable, tous 5 cas validés : jan-31→True, jan-30→False, fév-28(non-leap)→True, fév-29(leap)→True, déc-31→True |
| `main.py` | --mode argparse, pipeline complet câblé, garde mensuel, outer try/except | ✓ VERIFIED | 254 lignes, argparse présent, select_reports/send_email/write_tweet/archive_report/is_last_day_of_month tous importés et utilisés |
| `tests/test_main_pipeline.py` | 10 tests couvrant tous les branches --mode | ✓ VERIFIED | 434 lignes, 10 fonctions de test, 10/10 PASSED |
| `scheduler/install_cron.sh` | 3 entrées D-02, chmod +x, idempotent, rappel timezone | ⚠️ PARTIAL | Existe, exécutable (-rwxrwxr-x). Contient `0 7 * * 1-6` (SCHED-01 OK), `0 8 * * 0` (SCHED-02 OK), mais `1 8 * * *` pour CRON_MONTHLY (déviation post-CR-02 vs SCHED-03 qui exige `0 8 * * *`). Timezone reminder présent (3 occurrences "Europe/Paris"). |

---

## Vérification des liens clés

| De | Vers | Via | Statut | Détails |
|----|------|-----|--------|---------|
| `main.py` | `reporters/dispatch.py` | `select_reports(today, data, config)` | ✓ WIRED | main.py:35 (import) + main.py:213 (appel) |
| `main.py` | `delivery/email.py` | `send_email(report_type, date_str, ...)` | ✓ WIRED | main.py:36 (import) + main.py:228 (appel) |
| `main.py` | `delivery/tweet.py` | `write_tweet(report_type, date_str, ...)` | ✓ WIRED | main.py:37 (import) + main.py:230 (appel) |
| `main.py` | `delivery/email.py` | `archive_report(report_type, date_str, ...)` | ✓ WIRED | main.py:36 (import) + main.py:227 (appel) |
| `main.py` | `main.log_run` | `status="error"` dans outer except | ✓ WIRED | main.py:242-248 ; grep "\"error\"" retourne ligne 244 |
| `scheduler/install_cron.sh` | `crontab` | `(crontab -l 2>/dev/null; ...) \| crontab -` | ✓ WIRED | install_cron.sh:26 ; pattern présent |

---

## Trace de flux de données (Niveau 4)

Non applicable pour cette phase — les artefacts produits sont un utilitaire calendaire, une CLI, un script bash et des tests d'intégration, pas des composants qui rendent des données dynamiques dans une UI.

---

## Vérifications comportementales (Spot-checks)

| Comportement | Commande | Résultat | Statut |
|--------------|----------|----------|--------|
| scheduler.utils importable, 5 cas corrects | `python3 -c "from scheduler.utils import is_last_day_of_month; ..."` | Tous 5 assertions passées | ✓ PASS |
| main.py câblage pipeline | `python3 -c "src=open('main.py').read(); [assert fn in src for fn in [...]]"` | Toutes assertions passées | ✓ PASS |
| Suite complète de tests | `python3 -m pytest tests/ -q` | 121 passed, 0 failed, 19.77s | ✓ PASS |
| Entrées cron dans le script | `grep -c "0 7 \* \* 1-6" install_cron.sh` (x3 patterns) | SCHED-01 OK, SCHED-02 OK, SCHED-03 déviation (`1 8` au lieu de `0 8`) | ⚠️ WARNING |
| Crontab installé | `crontab -l` | Montre `0 8 * * *` pour monthly (conforme SCHED-03, mais ancien — installé avant CR-02) | ? UNCERTAIN |
| Fuseau horaire VPS | `timedatectl \| grep "Time zone"` | `Europe/Paris (CEST, +0200)` | ✓ PASS |
| Archive smoke test | `ls reports/daily/2026-05-13.md` | Fichier existe, 1033 octets, contenu structuré | ✓ PASS |
| run_log dernier run | `sqlite3 cryptolascar.db "SELECT status FROM run_log ORDER BY run_at DESC LIMIT 1"` | `success` | ✓ PASS |

---

## Couverture des exigences

| Exigence | Plan source | Description | Statut | Preuve |
|----------|------------|-------------|--------|--------|
| SCHED-01 | 05-01, 05-02 | Daily Report lun-sam 07h00 CET (`0 7 * * 1-6`) | ✓ SATISFIED | install_cron.sh ligne 12 : `0 7 * * 1-6` ; crontab -l confirme |
| SCHED-02 | 05-01, 05-02 | Weekly Wrap dimanche 08h00 CET (`0 8 * * 0`) | ✓ SATISFIED | install_cron.sh ligne 13 : `0 8 * * 0` ; crontab -l confirme |
| SCHED-03 | 05-01, 05-02 | Monthly Close 08h00 CET dernier jour (`0 8 * * *` en cron, garde Python) | ? UNCERTAIN | install_cron.sh contient `1 8 * * *` (déviation post-CR-02) ; crontab installé a `0 8 * * *` (conforme spec) mais pre-date le fix CR-02 |
| INFRA-02 | 05-01, 05-02 | Dégradation gracieuse : source échoue → rapport partiel envoyé, run non annulé | ✓ SATISFIED | collect_all() encapsule par collecteur (main.py:76-93) ; outer try/except delivery (main.py:237-249) ; smoke test exit 0 avec collecteurs partiels |

---

## Anti-patterns détectés

| Fichier | Ligne | Pattern | Sévérité | Impact |
|---------|-------|---------|----------|--------|
| `main.py` | 219-223 | `except locale.Error: pass` — échec silencieux sans log | ⚠️ Warning | Sujet email mensuel peut être en anglais sans avertissement en production (WR-01 du code review non corrigé) |
| `main.py` | 219 | `import locale` à l'intérieur d'une boucle `for` | ℹ️ Info | Non-conforme PEP 8 ; fonctionnellement inoffensif (Python cache les imports) |
| `scheduler/install_cron.sh` | 17 | `grep -q "$PROJECT_DIR"` — check idempotent trop large | ⚠️ Warning | Peut faussement indiquer "déjà installé" si un autre script dans le même répertoire est dans le crontab (WR-03 du code review non corrigé) |
| `main.py` | 183-207 | `collect_all()` s'exécute avant la garde mensuelle | ⚠️ Warning | Gaspillage quotas API les jours non-dernier du mois pour `--mode monthly` (WR-02 non corrigé) |
| `scheduler/install_cron.sh` | 14 | `1 8 * * *` pour CRON_MONTHLY au lieu de `0 8 * * *` | ⚠️ Warning | Divergence par rapport à SCHED-03 (`0 8 * * *`) et par rapport au crontab actuellement installé ; toute réinstallation du script installerait l'offset d'une minute |

---

## Vérification humaine requise

### 1. Reconciliation du crontab monthly (SCHED-03)

**Test :** Exécuter `bash scheduler/install_cron.sh` après avoir d'abord supprimé les entrées actuelles (`crontab -r`), puis vérifier `crontab -l`.

**Attendu :** `crontab -l` affiche `1 8 * * *` pour `--mode monthly` (conforme à la correction CR-02 qui évite le doublon du dernier dimanche du mois) — OU décider de revenir à `0 8 * * *` dans le script et mettre à jour le crontab en conséquence pour aligner le script et le crontab installé.

**Pourquoi humain :** Le crontab actuellement installé (`0 8 * * *`) et le script (`1 8 * * *`) sont incohérents. SCHED-03 exige `0 8 * * *` mais CR-02 a intentionnellement changé le script en `1 8 * * *` pour éviter la livraison en double le dernier dimanche du mois. Il s'agit d'un compromis délibéré qui nécessite une décision humaine : accepter la déviation de SCHED-03 (`1 8` au lieu de `0 8`) comme CR-02 l'a recommandé, ou conserver `0 8` et accepter le risque de double livraison.

---

## Résumé des écarts

Aucun écart bloquant l'objectif de la phase. Les 4 critères de succès du ROADMAP sont atteints.

Un point d'incertitude nécessite une décision humaine : la divergence entre `install_cron.sh` (CRON_MONTHLY = `1 8 * * *`, correction CR-02) et le crontab installé (`0 8 * * *`, ancienne version pré-fix). Le pipeline fonctionne dans les deux cas — la différence est d'une minute et affecte uniquement le comportement le dernier dimanche du mois (risque de double livraison weekly si `0 8 * * *` est conservé).

Les avertissements WR-01 (locale silencieux), WR-02 (guard position), WR-03 (idempotent trop large) identifiés lors du code review restent non corrigés dans le code source mais n'empêchent pas l'objectif de phase d'être atteint.

---

_Vérifié : 2026-05-13T23:50:00Z_
_Vérificateur : Claude (gsd-verifier)_
