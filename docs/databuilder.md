# Data Builder — Build Order

Each step fetches or calculates one piece of data. No duplicates — if multiple screens use the same data, it's listed once with all screens noted. Go top to bottom.

---

## PHASE 0: HISTORICAL BACKFILL (one-time, run before anything else)

These are the heavy pulls. Run once to seed the database, then switch to incremental updates.

| # | What to backfill | History needed | Why | Source | Method |
|---|-----------------|---------------|-----|--------|--------|
| 0a | Stock OHLC + volume + delivery % — ALL stocks above 500 Cr, daily data | 2 years minimum | 52W MA needs 1 year. Consolidation detection needs 6+ months of range. Volume 5x average needs 52 weeks. 2 years gives buffer. | yfinance (OHLC+volume) + nselib (delivery) | yf.download() per stock for OHLC, then nselib bhav_copy_with_delivery() per trading date for delivery data. Two-pass approach: yfinance is fast (0.2s/stock), delivery backfill via bhavcopy (1s/date, 494 dates). |
| 0b | Nifty 50 index — daily data | 2 years | 52W MA for Market Phase calculation. Also needed for RS calculation baseline. | nselib (primary), yfinance (fallback) | capital_market.index_data("NIFTY 50", from_date, to_date) with 80-day date chunking. Falls back to yf.download("^NSEI") if nselib fails. |
| 0c | Indian indices — Bank Nifty, Midcap 100, Smallcap 100 | 1 year | Distance from 52W high display. Weekly trend context. | nselib (primary), yfinance (fallback) | capital_market.index_data() per index with 80-day date chunking. Note: correct NSE name is "NIFTY SMALLCAP 100" (not "SMLCAP"). |
| 0d | Sector indices — IT, Pharma, Auto, FMCG, Metal, Realty, Energy, Media, PSE, Infra | 1 year | Sector RS calculation needs 4-week history minimum, 1 year for trend. | nselib (primary), yfinance (fallback) | capital_market.index_data() per sector index with 80-day date chunking. Some indices (e.g. NIFTY INFRA) have nselib bugs and rely on yfinance fallback. |
| 0e | Quarterly financials — all stocks in universe | Last 6 quarters (1.5 years) | Earnings surprise needs YoY. Debt reduction needs 4-6 quarter trend. Margin expansion needs 3-4 quarters. Balance sheet improvement needs cash flow trend. | yfinance | quarterly_income_stmt + quarterly_balance_sheet + quarterly_cashflow per stock. Cash flow from operations stored in `cash_flow_operations` column. |
| 0f | Promoter holding — all stocks in universe | Last 4 quarters | Promoter holding trend (stable, increasing, decreasing). | NSE API (direct) | requests session with cookies → GET corporate-share-holdings-master?symbol=...&index=equities. Returns promoter % and public % per quarter. DII/FII breakdown not available from this endpoint (would need XBRL parsing). |

**Source changes vs original plan:** jugaad-data was planned as primary source for 0a–0d but is broken (NSE changed their API, causing KeyError and cache bugs). Replaced with yfinance (0a) and nselib (0b–0d). nsepython was planned for 0f but its shareholding endpoint doesn't exist; replaced with direct NSE API call.

**Actual results:** 1,534 stocks in universe. 689,224 OHLC rows (656,177 with delivery data = 95.2% coverage). 3,717 index rows (14 indices). 8,944 financial rows. 5,964 promoter rows. SQLite database. Total run time ~65 minutes.

---

## IMPLEMENTATION ROADMAP (build order to make the product functional)

Phases 0–4 above are grouped by data type. But to make screens functional, we interleave them. Phase 2 calculations on Phase 0 data make the Scanner work before any Phase 1 fetches exist. This roadmap is the actual build sequence.

**Current state:** Phase 0 complete. M1–M7 complete. All pending-list items P0–P5 complete. All 5 screens show 100% real data — zero dummy JSON remaining. Global Pulse fetches live world indices, commodities, DXY, US 10Y, India 10Y, INR/USD, FII/DII flows, and market breadth. Deep Dive shows real P/E, Industry P/E, ROCE (from Screener.in), and LLM-generated AI summary. All 8 setups detected. Scanner has proper 8-point scoring (consolidation breakout + sector index RS + peers as separate criteria). Portfolio has 8 exit signals, watchlist, price alerts, SELL/HOLD workflow with trade history. Briefing compiles real macro + scanner + portfolio data with optional LLM narratives + sector trigger counts. Scheduling: 9 APScheduler jobs (daily OHLC, indices, deals, accumulation, macro refresh; weekly universe; quarterly financials, promoter, sectors).

**Delivery data:** Backfilled via nselib bhav_copy_with_delivery(). 95.2% of OHLC rows have delivery_pct. Scanner scoring is full 0-8 (delivery + MAs + golden cross + RS + consolidation + sector index RS + peers).

---

### M1: Scanner Calculation Engine → Screen 2 (Signal Scanner) goes live — **DONE**

The core product. Calculation engine on existing Phase 0 data — no external fetches needed.

| Calculation | Input tables | Method | Status |
|-------------|-------------|--------|--------|
| Weekly OHLC aggregation | stock_ohlc | Resample daily → weekly candles (Friday close) | Done |
| 52W average weekly volume | stock_ohlc | Rolling 52-week mean of weekly volume per stock | Done |
| Volume spike (gate: >= 5x) | above | Current week volume / 52W avg | Done |
| Weekly price change (gate: >= 5%) | stock_ohlc | (Friday close - prev Friday close) / prev | Done |
| Delivery % gate (>= 35%) | stock_ohlc | Average daily delivery_pct for the week | Done |
| Moving averages: 10W, 30W, 52W | stock_ohlc | Simple moving average of weekly closes | Done |
| Golden crossover | MAs above | 10W crosses above 30W or 52W this week | Done |
| Relative strength vs Nifty (4W) | stock_ohlc + index_daily | (stock 4W return) - (Nifty 50 4W return) | Done |
| Consolidation detection | stock_ohlc | Price in <=15% band for 6+ months, breakout above | Done |
| Sector context + peers | stock_universe + index_daily | Group triggered stocks by sector, count peers (>= 2). Sector index 4W RS vs Nifty calculated from index_daily via SECTOR_TO_INDEX mapping. | Done |
| Signal score (0–8) | all above | Sum of 8 binary signals: delivery_50pct + above_30w + above_52w + golden_cross + rs_positive + consolidation_breakout + sector_index_outperforming + peers_triggered | Done |

**3 Gates:** Volume >= 5x 52W avg, price change >= 5%, delivery >= 35%. Must pass all 3 to be included.

**8-Point Score:** (1) delivery >= 50% (2) above 30W MA (3) above 52W MA (4) golden crossover (5) RS vs Nifty > 0 (6) 6+ month consolidation breakout (7) sector index outperforming Nifty (8) 2+ peers triggered.

**API:** `GET /api/scanner` (latest week) and `GET /api/scanner?week_ending=YYYY-MM-DD` (historical). ~7s first call, instant on cache.

**Files created:** `backend/app/db.py`, `backend/app/calculations/__init__.py`, `backend/app/calculations/scanner.py`
**Rewritten:** `backend/app/api/routes/scanner.py` (from dummy JSON → real calculations)
**Frontend:** No changes needed (API response shape matches existing dummy data)

---

### M2: Stock Deep Dive → Screen 3 goes live (~80%) — **DONE**

Reuses scanner calculations for a single stock. Adds fundamentals + setup detection.

| What | Source | Notes | Status |
|------|--------|-------|--------|
| Technical signals (all 7) | Single-stock calculation | MAs, RS, consolidation, volume, delivery, golden cross | Done |
| Fundamentals table (4 quarters) | quarterly_financials | Revenue, margin, profit, EPS, debt, cash flow from operations, asset turnover. Converted to Crores. FY quarter labels (Q3 FY26). | Done |
| Promoter holding (4 quarters) | promoter_holding | promoter_pct matched to nearest financial quarter | Done |
| Setup: Earnings surprise | quarterly_financials | Net income YoY >= 50% AND revenue also grew | Done |
| Setup: Debt reduction | quarterly_financials | total_debt declining 3+ consecutive quarters | Done |
| Setup: Margin expansion | quarterly_financials | operating_margin trending up 3+ quarters | Done |
| Setup: Balance sheet improvement | quarterly_financials | Asset turnover trend + ROCE trend + cash flow from operations trend over 3+ quarters. Any one or more improving triggers detection. | Done |
| Setup: Sector of the cycle | M1 scanner cache | 2+ peers triggered in same sector | Done |
| Sector RS vs Nifty | index_daily | Sector index 4W return minus Nifty 4W return. Mapped 10 sectors to NSE indices. | Done |
| P/E, Industry P/E | yfinance + Screener.in | P/E from yfinance trailingPE (24h cache). Industry P/E scraped from Screener.in (24h cache). | Done |
| ROCE | Screener.in | Accurate annual ROCE scraped from Screener.in (same visit as industry P/E, shared cache). | Done |
| AI summary | Gemini 2.0 Flash | LLM-generated factual summary with 24h in-memory cache per stock. Fallback to null when no API key. | Done |

**API:** `GET /api/stock/{symbol}` — returns real data. ~7s first call (scanner cache cold), instant on subsequent calls.

**Files created:** `backend/app/calculations/stock.py`
**Rewritten:** `backend/app/api/routes/stock.py` (from dummy JSON → real calculations)

---

### M3: Global Pulse (Partial) → Screen 1 goes live (~40%) — DONE

Uses existing index_daily data. No external fetches yet.

| What | Real or placeholder | Source | Status |
|------|-------------------|--------|--------|
| Indian indices (4) + distance from 52W high | Real | index_daily | DONE |
| Sector heatmap (10 sectors) + RS vs Nifty | Real | index_daily | DONE |
| Market phase (4-criteria voting) | Real | index_daily + live_cache | DONE |
| World indices (5) | Placeholder | Needs yfinance fetch (M5) | DONE (null) |
| Commodities (5) | Placeholder | Needs yfinance fetch (M5) | DONE (null) |
| Macro indicators (DXY, yields, INR/USD, FII/DII) | Placeholder | Needs external fetch (M5) | DONE (null) |
| Market depth (A/D, 52W highs/lows) | Placeholder | Needs nsetools fetch (M5) | DONE (null) |

**Details:**
- `GET /api/macro` returns real data for Indian indices, sector heatmap, and market phase
- Indian indices: Nifty 50, Bank Nifty, Midcap, Smallcap with latest value, 1-day change %, distance from 52W high
- Sector heatmap: 10 sectors sorted by RS vs Nifty 4W (strongest first), with 1-week change %
- Market phase: 4-criteria voting system — (1) Nifty vs 200-day MA, (2) A/D ratio, (3) 52W highs/lows ratio, (4) FII+DII combined flow. Each votes +1/0/-1, sum maps to BULLISH / CAUTIOUSLY BULLISH / SIDEWAYS / CAUTIOUSLY BEARISH / BEARISH
- Placeholders return `null` values matching the response shape — frontend can show "--" or "Coming soon"

**Files created:** `backend/app/calculations/macro.py`
**Rewritten:** `backend/app/api/routes/macro.py` (from dummy JSON → real calculations)

---

### M4: Frontend API Switchover → All screens connected to real backend — DONE

| What | Status |
|------|--------|
| Rewrite `frontend/src/services/api.js` from JSON imports → axios calls | DONE |
| Backend URL as env variable (`VITE_API_URL` in `.env`) | DONE |
| Null guards: delivery_pct, pe, industry_pe, ai_summary → "--" or "Coming soon" | DONE |
| Null guards: world indices, commodities, macro indicators, market depth → "--" | DONE |
| Null guards: consolidation (none detected), key_levels (filter nulls) | DONE |
| ChangeIndicator null/NaN safety | DONE |

**Details:**
- `api.js` uses axios with `VITE_API_URL` env var, unwraps `response.data` so components need zero changes to their data access patterns
- All 5 screens connected to real backend — 3 return real calculated data (macro, scanner, stock), 2 return dummy JSON from backend (portfolio, briefing)
- Frontend build passes with no errors

**Files rewritten:** `frontend/src/services/api.js`
**Files modified:** `GlobalPulse.jsx`, `StockDeepDive.jsx`, `SignalScanner.jsx`, `ChangeIndicator.jsx`

**After M4:** Core product works. Scanner + Deep Dive show real data. Global Pulse partially real.

---

### M5: External Data Fetches → Screen 1 (Global Pulse) goes to 100% — DONE

Built `backend/app/fetchers/` package. Each fetcher writes to a `live_cache` table (key, JSON, timestamp). Macro route reads cache. Refresh triggered by `POST /api/macro/refresh`, not per-request.

| Fetcher | Source | Data | Status |
|---------|--------|------|--------|
| world_indices.py | yfinance | ^GSPC, ^IXIC, ^FTSE, ^N225, 000001.SS | DONE |
| commodities.py | yfinance | GC=F, CL=F, SI=F, HG=F, NG=F | DONE |
| macro_indicators.py | yfinance + nsepython + CCIL scrape | DXY, US 10Y, India 10Y, INR/USD, FII/DII | DONE |
| market_depth.py | nsetools | Advance/Decline counts, 52W high/low counts | DONE |

**Details:**
- `live_cache` table in SQLite: key, data (JSON), fetched_at. 4-hour freshness for fetcher calls, 24-hour for macro route reads.
- `POST /api/macro/refresh` triggers all 4 fetchers. Call daily via cron or manually.
- P/E in deep dive: yfinance `ticker.info["trailingPE"]` with 24h in-memory cache per stock. Industry P/E not reliably available from yfinance.
- Market phase: 4-criteria voting system — (1) Nifty vs 200-day MA ±3%, (2) A/D ratio from market_depth cache (>1.5 bullish, <0.7 bearish), (3) 52W highs/lows ratio from market_depth cache (>2.0 bullish, <0.5 bearish), (4) FII+DII combined flow from macro_indicators cache (positive bullish, <-2000 Cr bearish). Each criterion votes +1/0/-1, sum ≥3 → BULLISH, 2 → CAUTIOUSLY BULLISH, -1 to 1 → SIDEWAYS, -2 → CAUTIOUSLY BEARISH, ≤-3 → BEARISH.
- FII/DII flows: nsepython `nse_fiidii()` returns latest day's net value in Crores (e.g. FII -3,296 Cr, DII +8,594 Cr).
- India 10Y yield: scraped from CCIL tenorwise indicative yields page (https://www.ccilindia.com/tenorwise-indicative-yields). Regex extracts 10Y row yield value.
- **All macro fields are now real. Zero placeholders remaining.**
- `daily_accumulation` table implemented — stores A/D ratio, 52W highs/lows, FII/DII daily flows, and F&O participant OI (market leverage proxy). Scheduled at 5:30 PM IST Mon-Fri. Macro endpoint includes `ad_trend`, `hl_trend`, `fii_dii_trend`. Portfolio endpoint includes `market_leverage` with client long/short contracts, L/S ratio, and 3-month trend.

**Files created:** `backend/app/fetchers/__init__.py`, `cache.py`, `world_indices.py`, `commodities.py`, `macro_indicators.py`, `market_depth.py`
**Files modified:** `backend/app/calculations/macro.py` (placeholders → cache reads + market phase upgrade), `backend/app/calculations/stock.py` (P/E fetch), `backend/app/api/routes/macro.py` (added refresh endpoint), `backend/requirements.txt` (added yfinance, nsetools)

---

### M6: Portfolio Monitor + Exit Signals → Screen 4 goes live (100%) — **DONE**

SQLite tables: `portfolio_holdings` (symbol UNIQUE, buy_price, buy_date, quantity, notes, buy_thesis), `watchlist`, `price_alerts`, `trade_history`. Single-user, no auth for MVP.

| Calculation | Method | Status |
|-------------|--------|--------|
| P&L per holding | (current_price - buy_price) / buy_price | Done |
| Exit #1: Upper wick detection | (high - close) / (high - low) > 0.6 for 3+ consecutive weeks | Done |
| Exit #2: MA break (30W) | current close < 30W MA | Done |
| Exit #3: MA break (52W) | current close < 52W MA | Done |
| Exit #4: Support break | Price below lowest weekly close of past 3 months (~13 weeks) | Done |
| Exit #5: Head & Shoulders | 3-peak pattern detection (10-30 week window), shoulder symmetry, neckline proximity | Done |
| Exit #6: Bad news + breakdown | LLM scans Google News RSS headlines when at least one technical signal active | Done |
| Exit #7: Market leverage elevated | Fires on all holdings when F&O participant OI trend is INCREASING over 3 months | Done |
| Exit #8: Original setup ended | Re-checks buy thesis (earnings, debt, margins, sector) against current data | Done |
| Health bucketing | healthy (0 signals) / warning (1-2) / alert (MA break, bad news, or 3+) | Done |
| Sector concentration | Group holdings by sector from stock_universe | Done |
| Watchlist | Separate tracking list (no buy price/P&L). CRUD with current price from stock_ohlc. | Done |
| Price Alerts | Above/below target price with auto-triggered detection from current prices | Done |
| SELL/HOLD workflow | sell_holding() logs P&L to trade_history then deletes. hold_decision() logs snapshot. | Done |

**API:**
- `GET /api/portfolio` — real exit signal calculations (8 signals, 3 buckets)
- `POST /api/portfolio/holdings` — add holding (symbol, buy_price, buy_date, quantity, notes, buy_thesis)
- `DELETE /api/portfolio/holdings/{symbol}` — remove holding
- `POST /api/portfolio/sell` — log SELL with P&L, remove from portfolio
- `POST /api/portfolio/hold` — log HOLD decision with current price snapshot
- `GET /api/portfolio/history` — trade decision log (SELL/HOLD entries, newest first)
- `GET /api/watchlist` — watchlist items with current price, name, sector, market cap
- `POST /api/watchlist` — add to watchlist (symbol, optional notes)
- `DELETE /api/watchlist/{symbol}` — remove from watchlist
- `GET /api/alerts` — all price alerts with triggered status auto-checked
- `POST /api/alerts` — create price alert (symbol, above/below, target_price, notes)
- `DELETE /api/alerts/{id}` — delete alert
- Duplicate symbol returns 400. Missing symbol returns 404.

**Details:**
- 5 SQLite tables auto-created on first access: portfolio_holdings, watchlist, price_alerts, trade_history, stock_flags
- Exit signals computed from 65 weeks of weekly OHLC data (same lookback as scanner)
- MAs calculated independently per held stock (not full universe — fast for small portfolios)
- `market_leverage` populated from F&O participant OI data (daily_accumulation table). Client long/short contracts, L/S ratio, 3-month trend. Fires exit signal when trend is INCREASING.
- Bad news detection requires GEMINI_API_KEY; gracefully absent without it
- Buy thesis options: earnings_surprise, debt_reduction, margin_expansion, sector_cycle, supply_disruption, forced_buying, management_change, other
- Empty portfolio returns valid response shape with zeros

**Files created:** `backend/app/calculations/portfolio.py`
**Rewritten:** `backend/app/api/routes/portfolio.py` (from dummy JSON → real CRUD + calculations + watchlist + alerts + sell/hold)
**Modified:** `backend/app/calculations/__init__.py` (export), `frontend/src/services/api.js` (addHolding, removeHolding, sellHolding, holdDecision, getTradeHistory, watchlist CRUD, alerts CRUD), `frontend/src/pages/PortfolioMonitor.jsx` (Add Holding with thesis, SELL/HOLD buttons, SetAlertDialog, Watchlist section, Price Alerts section, Decision Log section), `frontend/src/pages/StockDeepDive.jsx` (Add to Watchlist calls API, ConsolidationZone component)

---

### M7: LLM Integration → Screen 5 (Briefing) goes live, Screen 3 complete — **DONE**

| What | Method | Status |
|------|--------|--------|
| AI summary (Deep Dive) | Gemini 2.0 Flash via REST API. Input: technical + fundamental data. Output: 2-3 sentence factual summary. 24h in-memory cache per stock. | Done |
| Weekly Briefing | Real data from macro/scanner/portfolio. LLM generates world + India narrative paragraphs. Data-only fallback when no API key. | Done |
| ~~Delivery % backfill~~ **DONE** | Completed: `scripts/backfill_delivery.py` using nselib `bhav_copy_with_delivery(trade_date)`. 494/494 dates, 0 errors, 656K/689K rows (95.2%) updated. Scanner score is now 0-8. | Done |

**API:**
- `GET /api/briefing` — real data from macro + scanner + portfolio (was dummy JSON)
- `GET /api/stock/{symbol}` — `ai_summary` field now populated by LLM (was null)

**Details:**
- `backend/app/llm/` package: Gemini REST client + prompt templates
- `GEMINI_API_KEY` env var required for LLM features. Without it, ai_summary returns null and briefing narratives use data-only fallback text.
- Briefing data is 100% real even without LLM: week_ending, market_phase, sectors (from heatmap), top_signals (from scanner), portfolio_alerts (from portfolio)
- LLM only enhances the `world` and `india` narrative paragraphs
- Stock AI summary prompt: factual, 2-3 sentences, no opinions/recommendations
- No new pip dependencies — uses `requests` (already installed) for Gemini REST API

**Files created:** `backend/app/llm/__init__.py`, `client.py`, `summaries.py`, `backend/app/calculations/briefing.py`
**Rewritten:** `backend/app/api/routes/briefing.py` (from dummy JSON → real calculations)
**Modified:** `backend/app/calculations/stock.py` (ai_summary from LLM), `backend/app/calculations/__init__.py` (export)

---

### Scheduling (after M7) — **DONE**

Implemented via APScheduler (`app/scheduler.py`). 9 jobs start/stop with FastAPI lifespan. Status: `GET /api/scheduler/status`.

| When | What runs | APScheduler job |
|------|----------|-----------------|
| Daily 4:30 PM IST Mon-Fri | Stock OHLC update (step 3) | `_job_daily_ohlc` |
| Daily 4:45 PM IST Mon-Fri | Index update (steps 11, 12) | `_job_daily_indices` |
| Daily 5:00 PM IST Mon-Fri | Macro refresh — world indices, commodities, DXY, yields, FII/DII, market depth (steps 4-10, 13, 14, 18) | `_job_macro_refresh` |
| Daily 5:15 PM IST Mon-Fri | Bulk/block deals (step 21) | `_job_daily_deals` |
| Daily 5:30 PM IST Mon-Fri | Daily accumulation — A/D ratio, 52W highs/lows, FII/DII flows, F&O participant OI (A1-A4) | `_job_daily_accumulation` |
| Weekly Sunday 10:00 AM IST | Universe refresh (step 1) | `_job_weekly_universe` |
| Quarterly 1st Feb/May/Aug/Nov 6:00 AM | Financials refresh (steps 15-16) | `_job_quarterly_financials` |
| Quarterly 2nd Feb/May/Aug/Nov 6:00 AM | Promoter holding refresh (step 17) | `_job_quarterly_promoter` |
| Quarterly 3rd Feb/May/Aug/Nov 6:00 AM | Sector classification refresh (step 2) | `_job_quarterly_sectors` |

**Not scheduled (on-demand):** Scanner recalculation (runs on API call, cached), exit signals (computed per portfolio request), LLM generation (per request with 24h cache), industry P/E + ROCE (per deep dive request with 24h Screener.in cache). WhatsApp/Email delivery deferred.

---

### Screen Activation Summary

| Milestone | What | Screens Activated |
|-----------|------|-------------------|
| **M1** | Scanner calculation engine — **DONE** | Screen 2 (Scanner) — 100% |
| **M2** | Deep Dive calculations — **DONE** | Screen 3 (Deep Dive) — 80% |
| **M3** | Global Pulse from index data — **DONE** | Screen 1 (Global Pulse) — 40% |
| **M4** | Frontend API switchover — **DONE** | All screens connected to real backend |
| **M5** | External data fetches — **DONE** | Screen 1 — 100%, Screen 3 P/E |
| **M6** | Portfolio CRUD + 8 exit signals + watchlist + alerts + SELL/HOLD — **DONE** | Screen 4 (Portfolio) — 100% |
| **M7** | LLM + briefing — **DONE** | Screen 5 (Briefing) — 100%, Screen 3 — 100% |

**After M4:** Core product works (Scanner + Deep Dive with real data).
**After M6:** 4 of 5 screens fully functional. Only Briefing remains.
**After M7:** All 5 screens fully functional. Set `GEMINI_API_KEY` for LLM narratives.
**After P0–P5:** All pending-list items resolved. Scheduling, data freshness, feature gaps, and product vision audit gaps complete. Product matches product_vision.txt.

---

## PHASE 1: FETCH RAW DATA (external sources, ongoing)

After backfill, these run on a schedule — some daily, some weekly.

**Implementation status:** Items 1–14, 17–21, 23 are implemented. Item 1: `scripts/refresh_universe.py` (weekly, scheduled Sun 10 AM). Item 2: `scripts/refresh_sectors.py` (quarterly). Item 3: `scripts/daily_ohlc.py` (daily 4:30 PM IST). Items 4–10, 13–14, 18: M5 fetchers (`backend/app/fetchers/`). Item 8 uses CCIL scrape (not RBI). Item 10 uses nsepython `nse_fiidii()`. Items 11–12: `scripts/daily_indices.py` (daily 4:45 PM IST). Items 15–16: `scripts/refresh_financials.py` (quarterly, includes income statement + balance sheet + cash flow). Item 17: `scripts/refresh_promoter.py` (quarterly). Items 19–20: Screener.in scrape (industry P/E + ROCE, 24h cache). Item 21: `scripts/daily_deals.py` (daily 5:15 PM IST). Item 22: replaced with F&O participant OI proxy (`app/fetchers/market_leverage.py`). Item 23: TradingView embed widget (no fetch). All scheduled via APScheduler (9 jobs).

| # | What to fetch | Frequency | Source | Library / Method | Used by |
|---|--------------|-----------|--------|-----------------|---------|
| 1 | Stock universe — all stocks above 500 Cr market cap | Weekly (stocks rarely cross the threshold day to day) | NSE equity list CSV + yfinance for market cap | NSE CSV download + yf.Ticker(symbol).info["marketCap"] | Scanner, Deep Dive, Portfolio |
| 2 | Sector classification — which stock belongs to which sector | Monthly (almost never changes) | NSE equity list CSV (industry column) | Same CSV as step 1 | Scanner, Deep Dive, Portfolio |
| 3 | Stock OHLC + volume + delivery % — incremental update, latest data only | Daily after market close (3:45 PM IST) | yfinance (OHLC+volume), nselib (delivery %) | yf.download() for latest day. Delivery % via nselib price_volume_and_deliverable_position_data(). Append to backfill data from 0a. *(jugaad-data broken — see Phase 0 notes)* | Scanner, Deep Dive, Portfolio |
| 4 | World indices — S&P 500, Nasdaq, FTSE, Nikkei, Shanghai | Daily (or every 5 min during market hours) | yfinance | yf.download(tickers, period="1d") | Global Pulse, Briefing |
| 5 | Commodities — Gold, Crude, Silver, Copper, Natural Gas | Daily | yfinance | yf.download(tickers, period="1d") | Global Pulse, Briefing |
| 6 | Dollar Index (DXY) | Daily | yfinance | yf.download("DX-Y.NYB", period="1d") | Global Pulse |
| 7 | US 10Y Yield | Daily | FRED API (free key) | fredapi — Fred.get_series("DGS10"). Backup: yfinance ^TNX | Global Pulse |
| 8 | India 10Y Yield | Daily | RBI data | Scrape RBI or Investing.com. *(jugaad-data broken — see Phase 0 notes)* | Global Pulse |
| 9 | INR/USD | Daily | yfinance | yf.download("INR=X", period="1d") | Global Pulse |
| 10 | FII/DII Flows | Daily after market close | nsepython | nse_fiidii(). Backup: nselib | Global Pulse, Briefing |
| 11 | Indian indices — latest values + change | Daily after market close | nselib (primary), yfinance (fallback) | capital_market.index_data() latest day. Append to backfill data from 0b, 0c. *(jugaad-data broken — see Phase 0 notes)* | Global Pulse, Scanner, Briefing |
| 12 | Sector indices — latest values + change | Daily after market close | nselib (primary), yfinance (fallback) | capital_market.index_data() latest day. Append to backfill data from 0d. *(jugaad-data broken — see Phase 0 notes)* | Global Pulse, Scanner, Deep Dive, Briefing |
| 13 | Advance/Decline — advancing vs declining stocks today | Daily after market close | nsetools | Nse().get_advances_declines() | Global Pulse |
| 14 | 52W Highs vs Lows — count of stocks hitting 52W high/low today | Daily after market close | nsetools | Nse().get_52_week_high(), Nse().get_52_week_low() | Global Pulse |
| 15 | Quarterly financials — revenue, net profit, EPS, operating margin | When results are declared (~every 3 months per stock) | yfinance | yf.Ticker(symbol).quarterly_income_stmt. Backup: Screener.in scrape. Append to 0e. | Deep Dive |
| 16 | Balance sheet + cash flow — total debt, assets, cash flow from operations | When results are declared | yfinance | yf.Ticker(symbol).quarterly_balance_sheet + quarterly_cashflow. Cash flow from operations ("Operating Cash Flow" row). Backup: Screener.in scrape. Append to 0e. | Deep Dive |
| 17 | Promoter holding | Quarterly (when shareholding pattern is filed) | NSE API (direct) | requests session → GET corporate-share-holdings-master?symbol=...&index=equities. Append to 0f. *(nsepython shareholding endpoint doesn't work — see Phase 0 notes)* | Deep Dive |
| 18 | P/E ratio (stock) | Daily (price changes daily, so P/E changes) | yfinance | yf.Ticker(symbol).info["trailingPE"] | Deep Dive |
| 19 | Industry P/E | Monthly (doesn't move much) | Screener.in scrape | requests + BeautifulSoup on screener.in/company/{symbol} | Deep Dive |
| 20 | ROCE | Quarterly (derived from financials) | Screener.in scrape | Same page as step 19. Backup: calculate from yfinance | Deep Dive |
| 21 | Bulk/block deals | Daily after market close | NSE data | nselib capital_market.block_deals_data() | Deep Dive (forced buying/selling setup) |
| 22 | Market margin borrowing (MTF) | Daily after market close | NSE MTF daily report | Scrape NSE MTF CSV, aggregate total | Portfolio |
| 23 | TradingView chart | No fetch — embedded widget | TradingView free widget | HTML embed / react-ts-tradingview-widgets | Deep Dive |

---

## ACCUMULATE FROM DAY ONE (no historical source exists)

These data points have **no backfill available**. The APIs only give today's value. We must start collecting daily from day one and build our own history.

| # | What to accumulate | Why we need history | What we get today | What we're missing |
|---|-------------------|--------------------|--------------------|-------------------|
| A1 | Advance/Decline ratio (daily count) | To show A/D trend over weeks/months. Market Phase uses sustained A/D patterns, not just today. | Today's count only (step 13) | Every previous day's count. Start storing from launch. |
| A2 | 52W Highs vs Lows count (daily count) | To show if new highs are expanding or contracting over time. Important market breadth signal. | Today's count only (step 14) | Every previous day's count. Start storing from launch. |
| A3 | FII/DII daily flow breakdown | nsepython gives MTD totals. For daily flow trend charts, need daily figures. | MTD aggregate (step 10) | Daily breakdown history. Start storing from launch. |
| A4 | Market margin borrowing (MTF total) | To show if leverage is increasing or decreasing over 3 months. | Today's report only (step 22) | 3+ months of daily totals. Start storing from launch. |

**Impact:** Until we have ~30 days of accumulated data, trend analysis for these 4 elements will be limited. The screens will show today's values but not trends. This is fine for launch — trends fill in over time.

---

## PHASE 2: CALCULATE (derived from Phase 0 + Phase 1 data)

| # | What to calculate | Calculated from | History required | Method | Used by |
|---|------------------|----------------|-----------------|--------|---------|
| 24 | Volume spike — is this week's volume >= 5x the 52-week average? | 0a + 3 (stock OHLC + volume) | 52 weeks of weekly volume | 52-week rolling average of weekly volume, compare current week | Scanner |
| 25 | Moving averages — 10W, 30W, 52W for each stock | 0a + 3 (stock OHLC) | 52 weeks of weekly closes | Rolling mean of weekly close prices | Scanner, Deep Dive, Portfolio |
| 26 | Golden crossover — did 10W MA cross above 30W or 52W MA? | Step 25 (MAs) | 2 weeks of MA values | Compare current vs previous week MA positions | Scanner, Deep Dive |
| 27 | Relative strength vs Nifty — 4-week stock return vs 4-week Nifty return | 0a + 3 (stock OHLC) + 0b + 11 (Nifty) | 4 weeks of prices | (stock 4W return) - (Nifty 4W return) | Scanner, Deep Dive |
| 28 | Consolidation detection — has price stayed in a band for 6+ months? | 0a + 3 (stock OHLC) | 6-14 months of weekly prices | Check if high-low range within X% for 26+ weeks, flag breakout above range | Scanner, Deep Dive |
| 29 | Sector heatmap — % change per sector + RS vs Nifty | 0d + 12 (sector indices) + 0b + 11 (Nifty) | 4 weeks of sector + Nifty data | Sector index % change, sector 4W return minus Nifty 4W return | Global Pulse, Briefing |
| 30 | Market Phase — 4-criteria voting | 0b + 11 (Nifty 200-day MA) + 13 (A/D ratio) + 14 (52W H/L) + 10 (FII+DII flow) | 200 days of Nifty for MA + current A/D, H/L, flows | 4 criteria each vote +1/0/-1: (1) Nifty vs 200-day MA ±3%, (2) A/D ratio, (3) 52W H/L ratio, (4) FII+DII combined flow. Sum maps to 5 labels. | Global Pulse, Briefing |
| 31 | Signal score — 8-point ranking for each triggered stock | Steps 24-28 + Step 29 | All underlying history from those steps | Sum of 8 binary signals | Scanner, Deep Dive, Briefing |
| 32 | Peers triggered — other stocks in same sector that also passed filters | Step 31 (scanner results) + Step 2 (sector classification) | Current week only | Group triggered stocks by sector, count peers | Scanner, Deep Dive |
| 33 | Setup: Earnings surprise | 0e + 15 (quarterly financials) | 4 quarters (YoY comparison) | Net profit YoY change >= 50%, cross-check with revenue growth | Deep Dive |
| 34 | Setup: Debt reduction | 0e + 16 (balance sheet) | 4-6 quarters | Total debt declining over 4-6 consecutive quarters | Deep Dive |
| 35 | Setup: Margin expansion | 0e + 15 (quarterly financials) | 3-4 quarters | Operating margin trending up over 3-4 quarters | Deep Dive |
| 36 | Setup: Sector of the cycle | Step 32 (peers triggered) | Current week | 3+ stocks in same sector triggered in same week + sector RS rising | Deep Dive |
| 36b | Setup: Balance sheet improvement | 0e + 15-16 (quarterly financials + cash flow) | 3+ quarters | Asset turnover trending up OR ROCE trending up OR cash flow from operations improving. Any one triggers detection. | Deep Dive |
| 37 | Exit: Upper wicks | 0a + 3 (stock OHLC) | 4 weeks of weekly candles | (High - Close) / (High - Low) > threshold, 3-4 consecutive weeks | Portfolio |
| 38 | Exit: Price below 30W MA | Step 25 (MAs) | 30 weeks for MA | Current close < 30W MA | Portfolio |
| 39 | Exit: Price below 52W MA | Step 25 (MAs) | 52 weeks for MA | Current close < 52W MA | Portfolio |
| 40 | Exit: Support level break | 0a + 3 (stock OHLC) | 6-12 months for swing lows | Price drops below previous swing low | Portfolio |
| 41 | Exit: Head & Shoulders flag | 0a + 3 (stock OHLC) | 3-6 months for pattern | Detect three-peak pattern from price data, flag for human review | Portfolio |
| 42 | P&L per holding | Step 3 (current price) + user portfolio (buy price) | None | (current - buy) / buy * 100 | Portfolio |
| 43 | Sector concentration | User portfolio + Step 2 (sector classification) | None | Count holdings per sector, calculate % | Portfolio |

---

## PHASE 3: GENERATE (LLM + notification services)

No historical data needed — these run on current week's data.

| # | What to generate | Input | Method | Used by |
|---|-----------------|-------|--------|---------|
| 44 | Setup: Management change | Stock symbol + recent news | LLM scans NSE filings + news for board changes, key appointments | Deep Dive |
| 45 | Setup: Supply disruption | Stock symbol + sector + recent news | LLM scans news for factory shutdowns, trade restrictions, disasters | Deep Dive |
| 46 | Setup: Forced buying/selling | Step 21 (bulk/block deals) + news | LLM checks index rebalancing + unusual bulk deals + promoter issues | Deep Dive |
| 47 | Exit: Bad news + technical breakdown | News + Steps 37-41 (exit signals) | LLM scans news, combined with any technical exit signal firing | Portfolio |
| 48 | AI Summary per stock | Steps 24-36 (all technicals + fundamentals + setups) | LLM generates one-paragraph factual summary, no opinions | Deep Dive |
| 49 | Weekly Briefing — world summary | Step 4 (world indices) + Step 5 (commodities) | LLM generates narrative paragraph from the week's data | Briefing |
| 50 | Weekly Briefing — India summary | Steps 10-14 (FII/DII, indices, A/D, 52W) | LLM generates narrative paragraph from the week's data | Briefing |
| 51 | Weekly Briefing — sector highlights | Step 29 (sector heatmap) | LLM generates 2-3 line sector summary | Briefing |
| 52 | WhatsApp delivery | Steps 49-51 (briefing text) + portfolio alerts | WhatsApp Cloud API (already built) | Briefing |
| 53 | Email delivery | Steps 49-51 (briefing text) + portfolio alerts | SendGrid or AWS SES | Briefing |

---

## PHASE 4: USER-ENTERED DATA (no fetch needed)

| # | What | Entry method | Used by |
|---|------|-------------|---------|
| 54 | Portfolio holdings — stock symbol, buy price, buy date, quantity | User inputs via Portfolio screen | Portfolio, Briefing |
| 55 | Setup: Business mix change — manual confirmation | User flags after checking Screener.in segment data | Deep Dive |

---

## Summary

**Data steps by phase:**

| Phase | Steps | Count | What it does |
|-------|-------|-------|-------------|
| Phase 0: Backfill | 0a–0f | 6 | One-time heavy pull of 2 years of historical data — **DONE** |
| Phase 1: Fetch | 1–23 | 23 | Ongoing daily/weekly data from external APIs |
| Accumulate | A1–A4 | 4 | Collect daily from day one — no backfill exists |
| Phase 2: Calculate | 24–43 + 36b | 21 | Math on top of fetched + historical data |
| Phase 3: Generate | 44–53 | 10 | LLM summaries + notification delivery |
| Phase 4: User-entered | 54–55 | 2 | Manual input from Gordon |
| **Total** | | **66** | |

**Implementation order (see Roadmap above):** M1 → M2 → M3 → M4 → M5 → M6 → M7. Core product (Scanner + Deep Dive) works after M4. All 5 screens after M7.

---

## Data Refresh Schedule (Implemented)

| When | What runs | Implementation |
|------|----------|----------------|
| **Daily 4:30 PM IST** Mon-Fri | Stock OHLC + delivery % (step 3) | `_job_daily_ohlc` → `scripts/daily_ohlc.py` |
| **Daily 4:45 PM IST** Mon-Fri | Indian + sector indices (steps 11, 12) | `_job_daily_indices` → `scripts/daily_indices.py` |
| **Daily 5:00 PM IST** Mon-Fri | World indices, commodities, DXY, yields, FII/DII, market depth (steps 4-10, 13, 14, 18) | `_job_macro_refresh` → `POST /api/macro/refresh` |
| **Daily 5:15 PM IST** Mon-Fri | Bulk/block deals (step 21) | `_job_daily_deals` → `scripts/daily_deals.py` |
| **Daily 5:30 PM IST** Mon-Fri | A/D ratio, 52W highs/lows, FII/DII daily, F&O participant OI (A1-A4) | `_job_daily_accumulation` → `scripts/daily_accumulation.py` |
| **Weekly Sunday 10 AM IST** | Universe refresh — new stocks, delisted removal (step 1) | `_job_weekly_universe` → `scripts/refresh_universe.py` |
| **Quarterly 1st Feb/May/Aug/Nov** | Financials refresh (steps 15-16) | `_job_quarterly_financials` → `scripts/refresh_financials.py` |
| **Quarterly 2nd Feb/May/Aug/Nov** | Promoter holding refresh (step 17) | `_job_quarterly_promoter` → `scripts/refresh_promoter.py` |
| **Quarterly 3rd Feb/May/Aug/Nov** | Sector classification refresh (step 2) | `_job_quarterly_sectors` → `scripts/refresh_sectors.py` |
| **On-demand (per API request)** | Scanner (cached), exit signals, LLM summaries (24h cache), P/E + Industry P/E + ROCE (24h Screener.in cache) | Computed on request, not scheduled |
| **One-time at launch** | Phase 0 backfill (0a-0f) | `python -m scripts.run_backfill --all` |
| **Not yet implemented** | WhatsApp delivery (step 52), Email delivery (step 53) | Deferred — distribution channels |
