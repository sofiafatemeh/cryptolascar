# Phase 2: Data Pipeline - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Build all data collectors (ETF, crypto, PEA, macro, news/scraping) with rate limiting, SQLite caching, and PEA eligibility checking. Every collector returns a Python dict (JSON-serializable) covering the agreed asset universe. Phase 3 report generators consume this layer directly.

**Modules to produce:**
- `collectors/etf.py` — ETF prices and performance via yfinance + Alpha Vantage
- `collectors/crypto.py` — Crypto prices + Fear & Greed via CoinGecko + Alternative.me
- `collectors/pea.py` — PEA France prices + eligibility check
- `collectors/macro.py` — Macro indicators via FRED API
- `collectors/news.py` — Headlines via NewsAPI + BeautifulSoup4 scraping

**NOT in scope for Phase 2:** Report generation, email delivery, tweet generation, scheduling, graceful degradation end-to-end (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### Univers d'actifs

- **D-01:** ETF tickers (monde/thématiques, via yfinance): `SPY`, `QQQ` (US), `IWDA.AS`, `EIMI.AS` (world iShares), `CSPX.AS` (S&P500 EUR). Alpha Vantage used as supplemental/fallback for fund flow data.
- **D-02:** Crypto Tier 1+2 (via CoinGecko API): `bitcoin`, `ethereum`, `binancecoin`, `solana`, `ripple`, `cardano`, `avalanche-2`, `dogecoin` — top 8 by market cap. Fear & Greed Index collected separately via Alternative.me API (`https://api.alternative.me/fng/`).
- **D-03:** Macro indicators via FRED API: `DGS10` (10Y Treasury yield), `DGS2` (2Y yield), `CPIAUCSL` (CPI), `M2SL` (M2 money supply).
- **D-04:** PEA France tickers (via yfinance): `^FCHI` (CAC 40), `^SBF120`, `CW8.PA` (Amundi MSCI World), `PAEEM.PA` (Amundi EM), `PANX.PA` (Amundi Nasdaq). These are collected by the PEA collector alongside eligibility check.

### Éligibilité PEA

- **D-05:** PEA eligibility reference = static Python dict/set of known-eligible ISINs embedded in `collectors/pea.py`. No network dependency for this check. Updated manually when AMF/Euronext publishes changes.
- **D-06:** When a PEA status change is detected, the collector returns `eligibility_changed: True` in its result dict. Phase 3 surfaces this in the PEA Alert section of the report. Also logged via `get_logger()`.
- **D-07:** Last known PEA status is persisted in SQLite `market_cache` table (source=`"pea_eligibility"`, symbol=ticker). Each run compares current check against the cached last-known status to detect changes.

### News & Scraping

- **D-08:** Two-layer news collection: (1) NewsAPI (and/or GNews) for structured headlines via API; (2) BeautifulSoup4 scraping on freely accessible pages — CoinDesk, CoinTelegraph, Boursorama, AMF communiqués. No playwright in Phase 2 (added only if needed in a later phase).
- **D-09:** Volume cap: 5 headlines per scraped source + ~10 from NewsAPI. Total ≤ 35 headlines per run.
- **D-10:** Collector output format per headline: `{title: str, url: str, source: str, published_at: str}`. Title + URL only — no paragraph extraction.
- **D-11:** Graceful degradation if NewsAPI is unavailable or rate-limited: continue with scraped headlines only, add `newsapi_failed: True` flag to the returned dict. Run is never cancelled by a news failure.

### Claude's Discretion

- **Cache TTL per source** — hardcoded defaults: crypto 1h, ETF prices 4h, PEA prices 4h, macro (FRED) 24h, news 2h. These are baked into each collector, not configurable via `.env` in Phase 2.
- **Rate-limit sleeps** — minimum 1.5s between CoinGecko API calls (free tier limit); 0.5s between Alpha Vantage calls; 1s between FRED calls. BeautifulSoup4 scraping: 1s between requests per domain.
- **Collector return type** — each collector returns a plain Python `dict` (JSON-serializable). This dict is stored as `data_json` in `market_cache` and passed directly to Phase 3 report builders.
- **Alpha Vantage quota handling** — Alpha Vantage free tier is limited to 25 calls/day. If quota is exhausted, fall back to yfinance-only for ETF data and log `alpha_vantage_failed: True`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Foundation
- `.planning/REQUIREMENTS.md` — DATA-01 through DATA-08 define all data collection requirements for this phase
- `.planning/ROADMAP.md §Phase 2` — Success criteria and dependency on Phase 1
- `.planning/PROJECT.md` — Core constraints: rate limits, graceful degradation, zero hardcoded credentials

### Phase 1 Infrastructure (reuse these)
- `db/cache.py` — `init_db()`, `get_connection()`, `market_cache` schema (source, symbol, data_json, fetched_at, expires_at)
- `config.py` — `Config` dataclass with all API keys (coingecko_api_key, alpha_vantage_key, fred_api_key, newsapi_key)
- `logging_setup.py` — `get_logger(name)` for structured logging in each collector
- `.planning/phases/01-foundation/01-03-SUMMARY.md` — SQLite patterns and decisions from Phase 1

### External APIs
- CoinGecko free tier rate limit: 30 calls/min (no key), or higher with API key
- Alternative.me Fear & Greed: `https://api.alternative.me/fng/` — no auth required
- FRED API: `https://api.stlouisfed.org/fred/series/observations` — requires `FRED_API_KEY`
- Alpha Vantage free tier: 25 API calls/day — `ALPHA_VANTAGE_KEY` required

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `db/cache.py:get_connection()` — Use to read/write `market_cache`. All collectors should check cache before hitting external APIs.
- `db/cache.py:init_db()` — Called by `main.py` at startup; collectors don't need to call it.
- `config.py:Config` — Passed to each collector as a dependency (avoid re-loading `.env` in collectors).
- `logging_setup.py:get_logger(name)` — Each collector module calls `get_logger(__name__)` at module level.

### Established Patterns
- **SQLite WAL mode** — Enabled globally by `get_connection()`; collectors benefit from concurrent reads.
- **`CREATE TABLE IF NOT EXISTS` idiom** — If Phase 2 needs a new table (e.g., `pea_eligibility_log`), follow this pattern for idempotent migrations.
- **Config via dependency injection** — `main.py` loads `Config` once and passes it down; no collector reads `.env` directly.
- **TDD RED/GREEN** — Phase 1 used it; Phase 2 should follow the same pattern for each collector.

### Integration Points
- Each collector's output dict is stored in `market_cache.data_json` (JSON string). Phase 3 will call `get_connection()` and read from this table — the schema is fixed.
- `main.py` will orchestrate collector calls and write to `run_log` after each run. Collectors return data; they don't write to `run_log` themselves.
- `collectors/__init__.py` exists as an empty package stub — ready for module imports.

</code_context>

<specifics>
## Specific Ideas

- Fear & Greed from Alternative.me (not CoinGecko) — separate HTTP call, no auth required.
- ETFs are split across two collectors: `etf.py` for world ETFs, `pea.py` for PEA-specific tickers + eligibility.
- PEA eligibility static list lives in `collectors/pea.py` — the list of known-eligible ISINs for the tracked tickers (CW8.PA, PAEEM.PA, PANX.PA, ^FCHI, ^SBF120).
- AMF scraping target for news: AMF communiqués publics at `https://www.amf-france.org/` (freely accessible, no JS required).
- The `market_cache` TTL check pattern: query WHERE source=X AND symbol=Y AND expires_at > now() — if found, return cached; otherwise fetch and upsert.

</specifics>

<deferred>
## Deferred Ideas

- **playwright support for JS-heavy news sites** — Possible in a later phase if BeautifulSoup4 coverage proves insufficient. Noted but excluded from Phase 2.
- **Configurable TTLs via `.env`** — TTLs are hardcoded in Phase 2. Could be made configurable in Phase 5 or a future maintenance phase.
- **Alpha Vantage fund flow data** — Full fund flow collection via Alpha Vantage requires premium tier. Phase 2 uses Alpha Vantage as supplemental/fallback for price data only; fund flows may be deferred to v2.
- **Reddit/Twitter sentiment** — DATA-ADV-01 and DATA-ADV-02 are v2 requirements. Not in scope.

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-Data Pipeline*
*Context gathered: 2026-05-09*
