# CryptoLascar — Système d'Analyse Financière Automatisé

## What This Is

Système d'intelligence financière autonome livrant chaque matin un rapport structuré par email sur trois domaines — ETFs mondiaux, cryptomonnaies, et actions/ETFs PEA France — avec synthèse narrative générée par Claude (Anthropic). Tourne en continu sur un VPS Linux, déclenché par cron, sans intervention manuelle. Un tweet quotidien (fichier texte) est généré en parallèle du rapport daily.

## Core Value

L'utilisateur reçoit chaque matin une analyse financière actionnable et sourcée couvrant ETFs, crypto et PEA — sans aucune action manuelle — directement dans sa boîte email.

## Requirements

### Validated

- [x] Cache SQLite pour données historiques (éviter re-fetch inutile) — Validated in Phase 1: Foundation
- [x] Logging structuré (timestamp, statut sources, erreurs par run) — Validated in Phase 1: Foundation
- [x] Configuration 100% via .env (aucun credential hardcodé) — Validated in Phase 1: Foundation

### Validated

- [x] Collecte de données ETFs via Yahoo Finance / Alpha Vantage (prix, flux, performances) — Validated in Phase 2: Data Pipeline
- [x] Collecte de données crypto via CoinGecko API (prix, Fear & Greed, on-chain signals) — Validated in Phase 2: Data Pipeline
- [x] Collecte de données PEA France (CAC 40 / SBF 120 via Yahoo Finance + éligibilité AMF) — Validated in Phase 2: Data Pipeline
- [x] Collecte de données macro via FRED API (taux, inflation, M2) — Validated in Phase 2: Data Pipeline
- [x] Collecte de headlines financières via NewsAPI / GNews + scraping (Reuters, CoinDesk, Boursorama) — Validated in Phase 2: Data Pipeline
- [x] Rapport Daily généré lun–sam à 07h00 CET (~300 mots, 6 sections) — Validated in Phase 3: Report Generation
- [x] Rapport Weekly Wrap généré dimanche à 08h00 CET (~800 mots + tableaux) — Validated in Phase 3: Report Generation
- [x] Rapport Monthly Close généré le dernier jour du mois à 08h00 CET (~2000 mots + tableaux) — Validated in Phase 3: Report Generation
- [x] Synthèse narrative des sections textuelles via Claude API (claude-sonnet) — Validated in Phase 3: Report Generation
- [x] Envoi email via Gmail SMTP (HTML + fallback plain text) — Validated in Phase 4: Delivery & Side Outputs
- [x] Génération d'un fichier tweet quotidien /tweets/{YYYY-MM-DD}.txt (lun–sam + dimanche weekly) — Validated in Phase 4: Delivery & Side Outputs
- [x] Archivage des rapports en Markdown dans /reports/daily/, /reports/weekly/, /reports/monthly/ — Validated in Phase 4: Delivery & Side Outputs

### Active

- [ ] Scheduler via APScheduler ou cron système (3 triggers: daily, sunday, end-of-month)
- [ ] Dégradation gracieuse si source indisponible (rapport partiel envoyé, gap noté)

### Out of Scope

- Auto-publication Twitter/X via Tweepy — fichier tweet généré seulement, pas de posting automatique (décision explicite v1)
- Interface web / dashboard — système headless uniquement
- Alertes temps réel / webhooks — cadence cron suffisante
- SendGrid / Mailgun — Gmail SMTP uniquement en v1
- OpenAI / GPT — Claude (Anthropic) uniquement pour la synthèse

## Context

- Fresh build (v2 naming = spec révisée, aucun héritage de code v1)
- Déploiement cible : VPS Linux always-on (Hetzner / OVH) avec Python 3.11+
- Utilisateur unique destinataire en v1 (liste extensible via RECIPIENT_LIST dans .env)
- Éligibilité PEA : croisement avec liste AMF + Euronext Paris, alerte si changement de statut
- Rapport Monthly Close peut coexister avec Weekly Wrap le dernier dimanche du mois (deux emails)
- Le tweet du dimanche est basé sur le ONE SIGNAL du Weekly Wrap, pas de tweet pour Monthly Close

## Constraints

- **Tech stack**: Python 3.11+, httpx + BeautifulSoup4 + playwright (JS), pandas + yfinance + pycoingecko, smtplib + Jinja2, APScheduler, SQLite — défini dans le spec
- **Rate limits**: Respecter les limites API (CoinGecko free tier, Alpha Vantage, FRED, NewsAPI) — sleep entre appels obligatoire
- **Sécurité**: Zéro credential hardcodé — variables d'environnement uniquement via python-dotenv
- **Résilience**: Dégradation gracieuse obligatoire — un run ne peut pas être annulé par une source indisponible
- **LLM**: Claude API (Anthropic) pour synthèse narrative — modèle configurable, défaut claude-sonnet

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Claude (Anthropic) pour synthèse narrative | Cohérence avec l'environnement de dev, qualité rédactionnelle | — Pending |
| Gmail SMTP uniquement | Simplicité v1, zéro coût, configurable via app password | — Pending |
| Tweets fichier-seulement (pas d'auto-post) | Contrôle éditorial conservé, risque d'erreur publique évité | — Pending |
| SQLite pour cache historique | Zéro infrastructure, adapté à un usage VPS mono-instance | — Pending |
| APScheduler ou cron système | Flexibilité : cron si VPS permanent, APScheduler si process long-running | — Pending |

## Evolution

Ce document évolue à chaque transition de phase et à chaque milestone.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-10 — Phase 4 complete: delivery/email.py (Gmail SMTP + Jinja2), delivery/tweet.py (Claude tweet generator), 103 tests total*
