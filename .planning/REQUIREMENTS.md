# Requirements: CryptoLascar — Système d'Analyse Financière Automatisé

**Defined:** 2026-05-09
**Core Value:** L'utilisateur reçoit chaque matin une analyse financière actionnable et sourcée couvrant ETFs, crypto et PEA — sans aucune action manuelle — directement dans sa boîte email.

## v1 Requirements

### Data Collection

- [x] **DATA-01**: Le système collecte les données ETFs (prix, performance, fund flows) via Yahoo Finance et Alpha Vantage
- [ ] **DATA-02**: Le système collecte les données crypto Tier 1+2 (prix, market cap, volume, Fear & Greed) via CoinGecko API
- [ ] **DATA-03**: Le système collecte les données PEA France (CAC 40 / SBF 120 + ETFs PEA Amundi/Lyxor) via Yahoo Finance
- [ ] **DATA-04**: Le système collecte les indicateurs macro (taux, inflation, M2) via FRED API
- [ ] **DATA-05**: Le système collecte les headlines financières via NewsAPI / GNews
- [ ] **DATA-06**: Le système scrape les headlines publiques de Reuters, Bloomberg, CoinDesk, CoinTelegraph, Boursorama, AMF
- [ ] **DATA-07**: Le système vérifie l'éligibilité PEA via liste AMF + Euronext Paris et génère une alerte si changement de statut
- [x] **DATA-08**: Le système respecte les rate limits de toutes les APIs (sleep entre appels) pour éviter les bans

### Report Generation

- [ ] **REPT-01**: Le système génère un Daily Report lun–sam (~300 mots, 6 sections : Macro Snapshot, ETF Radar, Crypto Pulse, PEA Alert, News Feed, One Signal)
- [ ] **REPT-02**: Le système génère un Weekly Wrap le dimanche (~800 mots + tableaux, 7 sections)
- [ ] **REPT-03**: Le système génère un Monthly Close le dernier jour du mois (~2000 mots + tableaux, 7 sections)
- [ ] **REPT-04**: Le Monthly Close coexiste avec le Weekly Wrap si le dernier jour du mois est un dimanche (deux emails envoyés)
- [ ] **REPT-05**: Les rapports sont au format HTML avec fallback plain text

### LLM Synthesis

- [ ] **LLM-01**: Le système utilise l'API Claude (Anthropic) pour générer les sections narratives des rapports (Month in Review, Executive Summary, etc.)
- [ ] **LLM-02**: Le modèle Claude est configurable via ANTHROPIC_MODEL dans .env (défaut : claude-sonnet)

### Email Delivery

- [ ] **MAIL-01**: Le système envoie les rapports via Gmail SMTP (claudesiavach@gmail.com)
- [ ] **MAIL-02**: La liste des destinataires est configurable via RECIPIENT_LIST dans .env (défaut : siavach@hotmail.com)
- [ ] **MAIL-03**: Chaque email a un sujet formaté selon le type de rapport ([DAILY], [WEEKLY WRAP], [MONTHLY CLOSE])
- [ ] **MAIL-04**: Chaque email inclut un footer disclaimer : "Ceci n'est pas un conseil financier. Informations à titre éducatif uniquement."

### Tweet Generation

- [ ] **TWEET-01**: Le système génère un fichier tweet quotidien /tweets/{YYYY-MM-DD}.txt lun–sam, basé sur le ONE SIGNAL du daily
- [ ] **TWEET-02**: Le dimanche, le Weekly Wrap génère aussi un fichier tweet (format bilan de semaine)
- [ ] **TWEET-03**: Le tweet fait 240–270 caractères, ton analyst, en français, avec 3–4 hashtags du pool défini
- [ ] **TWEET-04**: Le Monthly Close ne génère pas de tweet

### Scheduling

- [ ] **SCHED-01**: Le Daily Report est déclenché lun–sam à 07h00 CET (cron : `0 7 * * 1-6`)
- [ ] **SCHED-02**: Le Weekly Wrap est déclenché le dimanche à 08h00 CET (cron : `0 8 * * 0`)
- [ ] **SCHED-03**: Le Monthly Close est déclenché à 08h00 CET le dernier jour calendaire du mois (vérifié en Python via `calendar.monthrange`)

### Storage & Archiving

- [ ] **STOR-01**: Chaque rapport est archivé en Markdown dans /reports/daily/, /reports/weekly/, /reports/monthly/
- [ ] **STOR-02**: Chaque tweet est sauvegardé dans /tweets/{YYYY-MM-DD}.txt
- [ ] **STOR-03**: Une base SQLite cache les données de marché historiques pour éviter les appels API redondants
- [ ] **STOR-04**: Chaque run est loggué avec timestamp, statut des sources, et erreurs éventuelles

### Infrastructure & Config

- [ ] **INFRA-01**: Tous les credentials et paramètres sont chargés depuis .env via python-dotenv (aucun secret hardcodé)
- [ ] **INFRA-02**: Dégradation gracieuse obligatoire : si une source échoue, le rapport est envoyé avec le gap noté (run non annulé)
- [ ] **INFRA-03**: Le système fonctionne sur VPS Linux avec Python 3.11+
- [ ] **INFRA-04**: Le fichier .env définit toutes les variables de configuration (SMTP, clés API, destinataires, feature flags)

## v2 Requirements

### Distribution étendue

- **DIST-01**: Publication automatique sur Twitter/X via Tweepy (activer via ENABLE_TWITTER_POST=true)
- **DIST-02**: Support SendGrid / Mailgun en alternative à Gmail SMTP

### Monitoring

- **MONIT-01**: Dashboard web minimal pour visualiser le statut des derniers runs
- **MONIT-02**: Alertes temps réel / webhooks sur erreurs critiques (ex. Telegram/Slack)

### Données avancées

- **DATA-ADV-01**: Sentiment Reddit (r/investing, r/CryptoCurrency) via API Reddit
- **DATA-ADV-02**: Sentiment Twitter/X via Nitter ou API officielle
- **DATA-ADV-03**: Google Trends pour keywords crypto/ETF
- **DATA-ADV-04**: Graphiques PNG générés et joints au Monthly Close

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-publication Twitter/X en v1 | Contrôle éditorial conservé, risque d'erreur publique — décision explicite |
| Interface web / dashboard | Système headless uniquement en v1 |
| Alertes temps réel / webhooks | Cadence cron suffisante pour v1 |
| OpenAI / GPT | Claude uniquement pour la synthèse — cohérence stack |
| Mobile app | Non pertinent pour un système automatisé headless |
| Backtesting / simulation | Hors périmètre de l'analyse de marché courante |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 2 | Complete (02-01) |
| DATA-02 | Phase 2 | Pending |
| DATA-03 | Phase 2 | Pending |
| DATA-04 | Phase 2 | Pending |
| DATA-05 | Phase 2 | Pending |
| DATA-06 | Phase 2 | Pending |
| DATA-07 | Phase 2 | Pending |
| DATA-08 | Phase 2 | Complete (02-01) |
| REPT-01 | Phase 3 | Pending |
| REPT-02 | Phase 3 | Pending |
| REPT-03 | Phase 3 | Pending |
| REPT-04 | Phase 3 | Pending |
| REPT-05 | Phase 4 | Pending |
| LLM-01 | Phase 3 | Pending |
| LLM-02 | Phase 3 | Pending |
| MAIL-01 | Phase 4 | Pending |
| MAIL-02 | Phase 4 | Pending |
| MAIL-03 | Phase 4 | Pending |
| MAIL-04 | Phase 4 | Pending |
| TWEET-01 | Phase 4 | Pending |
| TWEET-02 | Phase 4 | Pending |
| TWEET-03 | Phase 4 | Pending |
| TWEET-04 | Phase 4 | Pending |
| SCHED-01 | Phase 5 | Pending |
| SCHED-02 | Phase 5 | Pending |
| SCHED-03 | Phase 5 | Pending |
| STOR-01 | Phase 4 | Pending |
| STOR-02 | Phase 4 | Pending |
| STOR-03 | Phase 1 | Pending |
| STOR-04 | Phase 1 | Pending |
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 5 | Pending |
| INFRA-03 | Phase 1 | Pending |
| INFRA-04 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-09*
*Last updated: 2026-05-09 after roadmap creation — all 34 requirements mapped*
