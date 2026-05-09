# CryptoLascar — Project Instructions

## Project

Système d'analyse financière automatisé (Python 3.11+, VPS Linux). Génère des rapports financiers quotidiens/hebdomadaires/mensuels par email couvrant ETFs, crypto, et PEA France. Synthèse narrative via Claude API. Scheduled via cron.

**Core Value**: L'utilisateur reçoit chaque matin une analyse financière actionnable et sourcée couvrant ETFs, crypto et PEA — sans aucune action manuelle.

## Tech Stack

- **Language**: Python 3.11+
- **Data**: yfinance, pycoingecko, httpx, BeautifulSoup4, playwright
- **LLM**: Anthropic Python SDK (claude-sonnet, configurable via ANTHROPIC_MODEL)
- **Email**: smtplib + Jinja2 templates (Gmail SMTP)
- **Scheduler**: APScheduler ou cron système
- **Storage**: SQLite (cache + historique) + fichiers Markdown
- **Config**: python-dotenv (.env)

## Key Constraints

- **Zéro credential hardcodé** — tout via .env
- **Dégradation gracieuse obligatoire** — un run ne s'annule jamais, même si une source échoue
- **Rate limits** — sleep obligatoire entre appels API (CoinGecko free tier, Alpha Vantage, etc.)
- **Éligibilité PEA** — croiser avec liste AMF + Euronext Paris, alerter si changement

## GSD Workflow

This project uses GSD for phased execution.

**Current phase**: See `.planning/STATE.md`
**Roadmap**: `.planning/ROADMAP.md`
**Requirements**: `.planning/REQUIREMENTS.md`

### GSD Commands

```
/gsd-discuss-phase [N]   # Clarify approach before planning
/gsd-plan-phase [N]      # Create PLAN.md for a phase
/gsd-execute-phase [N]   # Execute the plan
/gsd-progress            # Check current status
```

### Workflow Rules

- **Never skip phases** — each phase depends on the previous
- **Commit after each phase** — artifacts are committed atomically
- **No hardcoded secrets** — use .env for all credentials
- **Test graceful degradation** — mock API failures in Phase 2+ tests

## Directory Structure

```
cryptolascar/
├── .env                    # Credentials and config (git-ignored)
├── .env.example            # Documented variable list
├── main.py                 # Entry point
├── collectors/             # Data collection modules
│   ├── etf.py
│   ├── crypto.py
│   ├── pea.py
│   ├── macro.py
│   └── news.py
├── reporters/              # Report builders
│   ├── daily.py
│   ├── weekly.py
│   └── monthly.py
├── delivery/               # Email + tweet output
│   ├── email.py
│   └── tweet.py
├── scheduler/              # Cron / APScheduler setup
│   └── jobs.py
├── db/                     # SQLite models and cache
│   └── cache.py
├── templates/              # Jinja2 HTML email templates
├── reports/                # Archived reports (Markdown)
│   ├── daily/
│   ├── weekly/
│   └── monthly/
├── tweets/                 # Generated tweet files
└── .planning/              # GSD planning artifacts
```

## Environment Variables

See `.env.example` for the full list. Key variables:

```
SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD
RECIPIENT_LIST                    # comma-separated
ANTHROPIC_API_KEY
ANTHROPIC_MODEL                   # default: claude-sonnet-4-6
COINGECKO_API_KEY
ALPHA_VANTAGE_KEY
FRED_API_KEY
NEWSAPI_KEY
```
