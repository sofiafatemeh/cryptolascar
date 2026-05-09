# Phase 2: Data Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09
**Phase:** 2-Data Pipeline
**Areas discussed:** Univers d'actifs, Éligibilité PEA, Scraping news

---

## Univers d'actifs

### ETF tickers

| Option | Description | Selected |
|--------|-------------|----------|
| Core mondial + thématiques US | SPY/QQQ (US), IWDA/EIMI (world), CSPX (S&P500 EUR) | ✓ |
| Focus US uniquement | SPY, QQQ, VTI, IVV — simplification max | |
| Je vais lister mes tickers | Description manuelle des tickers | |

**User's choice:** Core mondial + thématiques US
**Notes:** ETFs PEA (Amundi/Lyxor) sont couverts dans le collecteur PEA séparé.

### Crypto Tier 1+2

| Option | Description | Selected |
|--------|-------------|----------|
| BTC + ETH + top 8 par market cap | BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOGE + Fear & Greed via Alternative.me | ✓ |
| BTC + ETH uniquement | Couverture des 2 majors, moins de rate limits | |
| Je vais lister mes coins | Description manuelle | |

**User's choice:** BTC + ETH + top 8 par market cap
**Notes:** Fear & Greed via Alternative.me (API séparée, gratuite, pas CoinGecko).

### Indicateurs macro FRED

| Option | Description | Selected |
|--------|-------------|----------|
| Taux + Inflation + M2 | DGS10, DGS2, CPIAUCSL, M2SL | ✓ |
| Taux seulement | DGS10, DGS2, FEDFUNDS | |
| Suite complète | + USD index, unemployment, PCE | |

**User's choice:** Taux + Inflation + M2
**Notes:** Couverture standard, équilibre appels FRED / données utiles.

### ETFs PEA France

| Option | Description | Selected |
|--------|-------------|----------|
| CAC40 + top ETFs PEA | ^FCHI, ^SBF120, CW8.PA, PAEEM.PA, PANX.PA | ✓ |
| CAC40 uniquement | ^FCHI seulement | |
| Je vais lister mes positions PEA | Tickers manuels | |

**User's choice:** CAC40 + top ETFs PEA
**Notes:** CW8 (MSCI World), PAEEM (Emerging Markets), PANX (Nasdaq) — standard PEA Amundi/Lyxor.

---

## Éligibilité PEA

### Source de la liste AMF/Euronext

| Option | Description | Selected |
|--------|-------------|----------|
| Liste statique en code | Dict/set Python des ISINs éligibles — mise à jour manuelle | ✓ |
| Téléchargée depuis AMF à chaque run | Scraping automatique — fragile, dépendance réseau | |
| Importée en SQLite, rafraîchie hebdo | Job séparé — équilibré mais plus complexe | |

**User's choice:** Liste statique en code
**Notes:** Simplicité maximale, zéro dépendance réseau pour le check éligibilité.

### Mécanisme d'alerte changement PEA

| Option | Description | Selected |
|--------|-------------|----------|
| Log + flag dans la structure de données | `eligibility_changed: True/False` dans le dict retourné | ✓ |
| Log uniquement | Alerte dans les logs, pas dans le rapport | |
| Email dédié immédiat | Email séparé dès la détection (Phase 4 scope) | |

**User's choice:** Log + flag dans la structure de données
**Notes:** Phase 3 affiche le flag dans la section PEA Alert du rapport.

### Mémorisation du statut PEA précédent

| Option | Description | Selected |
|--------|-------------|----------|
| Dans SQLite market_cache | source="pea_eligibility" — cohérent avec Phase 1 | ✓ |
| Fichier JSON plat | pea_status.json à la racine | |
| Pas de mémoire | Comparaison uniquement avec la liste statique | |

**User's choice:** Dans SQLite market_cache
**Notes:** Réutilise l'infrastructure SQLite Phase 1, pas de nouveau mécanisme de persistance.

---

## Scraping news

### Profondeur de collecte

| Option | Description | Selected |
|--------|-------------|----------|
| NewsAPI + scraping pages libres | NewsAPI/GNews + BeautifulSoup4 (CoinDesk, CoinTelegraph, Boursorama, AMF) | ✓ |
| NewsAPI / GNews seulement | Zéro scraping — plus simple | |
| NewsAPI + scraping + playwright | + playwright pour JS-heavy — overhead important VPS | |

**User's choice:** NewsAPI + scraping pages libres
**Notes:** Reuters/Bloomberg exclus (paywall). Playwright reporté à une phase ultérieure si nécessaire.

### Volume de headlines

| Option | Description | Selected |
|--------|-------------|----------|
| 5 headlines par source | 5 par source scrapée + 10 via NewsAPI → ~30 max | ✓ |
| 10 headlines par source | Plus de couverture, plus de tokens LLM | |
| Top 3 uniquement | Minimal, runs ultra-rapides | |

**User's choice:** 5 headlines par source
**Notes:** Équilibre couverture / tokens LLM Phase 3.

### Format des headlines

| Option | Description | Selected |
|--------|-------------|----------|
| Titre + URL uniquement | Moins de risque copyright, plus rapide | ✓ |
| Titre + URL + extrait | Plus de contexte pour Claude, parsing plus complexe | |
| Titre + URL + résumé NewsAPI | description field de NewsAPI pour headlines API | |

**User's choice:** Titre + URL uniquement
**Notes:** Claude peut synthétiser à partir des titres seuls.

### Dégradation si NewsAPI down

| Option | Description | Selected |
|--------|-------------|----------|
| Continuer avec scraping seul | Dégradation gracieuse, flag newsapi_failed: True | ✓ |
| Retourner une liste vide | Run note que les news sont indisponibles | |
| Utiliser le cache SQLite si disponible | Réutiliser headlines récentes en cache | |

**User's choice:** Continuer avec scraping seul
**Notes:** Cohérent avec INFRA-02 (dégradation gracieuse obligatoire).

---

## Claude's Discretion

- **Cache TTL par source** — Hardcoded: crypto 1h, ETF 4h, PEA 4h, macro 24h, news 2h. Non configurable via .env en Phase 2.
- **Sleeps rate-limit** — 1.5s entre appels CoinGecko, 0.5s Alpha Vantage, 1s FRED, 1s scraping par domaine.
- **Format de retour des collecteurs** — Dict Python JSON-serializable dans tous les cas.
- **Alpha Vantage fallback** — Si quota 25 calls/day atteint : fallback yfinance-only, flag alpha_vantage_failed: True.

## Deferred Ideas

- playwright pour sites JS-heavy — possible phase ultérieure si couverture BeautifulSoup4 insuffisante
- TTLs configurables via .env — Phase 5 ou phase de maintenance ultérieure
- Fund flows Alpha Vantage (premium tier) — v2
- Reddit/Twitter sentiment — DATA-ADV-01 et DATA-ADV-02, v2 requirements
