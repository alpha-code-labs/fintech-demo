# Investment Scanner — Project Context

## What this is
A tool that automates an investment scanning process. It runs volume/price/delivery filters on Indian stocks, scores them, pulls fundamentals, detects setups, and monitors portfolios for exit signals.

## Project structure
- `backend/` — FastAPI (Python). Serves data via REST API.
- `frontend/` — React (Vite) + MUI. Dark theme financial dashboard.
- `docs/` — Product vision, process flowcharts, data source maps.

## Key files
- `docs/product_vision.txt` — The product spec. Read this first.
- `docs/gordons-complete-flowchart.txt` — The investment process being automated.
- `docs/data-sources-confirmed.txt` — Every data source with Python code.
- `docs/databuilder.md` — Data pipeline spec + 7-milestone implementation roadmap.
- `backend/app/calculations/scanner.py` — Scanner calculation engine (M1).
- `backend/data/dummy/` — Dummy JSON data matching the product mockups.

## Running locally
```
# Backend
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

## 5 Screens
1. Global Pulse — Macro dashboard (GET /api/macro)
2. Signal Scanner — Weekly stock scan (GET /api/scanner)
3. Stock Deep Dive — Per-stock analysis (GET /api/stock/{symbol})
4. Portfolio Monitor — Exit signal tracking (GET /api/portfolio)
5. Weekly Briefing — AI-generated summary (GET /api/briefing)

## Tech choices
- Vite (not CRA)
- MUI with dark theme
- Axios for API calls
- react-router-dom for routing

## Data Pipeline (Phase 0 Backfill)
Scripts in `backend/scripts/` fetch historical data and store it in SQLite (`backend/data/investscan.db`).

```
# Activate venv first
cd backend && source venv/bin/activate

# Run all steps
python -m scripts.run_backfill --all

# Run specific step
python -m scripts.run_backfill --step 0a

# Check progress
python -m scripts.run_backfill --status

# Retry failed items
python -m scripts.run_backfill --step 0a --retry-errors
```

Steps: universe → 0b (Nifty 50) → 0c (broad indices) → 0d (sector indices) → 0a (stock OHLC) → 0e (financials) → 0f (promoter holding) → delivery (delivery %)

Data sources: yfinance (stock OHLC, financials, market cap), nselib (index data, delivery %), NSE API direct (promoter holding).

## Current state
- Frontend: live at Azure Static Web Apps with dummy data
- Backend: FastAPI serving dummy JSON, data pipeline scripts built and tested
- **Phase 0 COMPLETE** — all steps done, 0 errors:
  - Stock universe: 1,534 stocks (≥500 Cr market cap)
  - Stock OHLC: 689,224 rows (2 years), delivery data 95.2% filled
  - Index daily: 3,717 rows (14 indices)
  - Quarterly financials: 8,944 rows (1,525 stocks)
  - Promoter holding: 5,964 rows (1,528 stocks)
  - Database: ~99 MB SQLite
- **M1 COMPLETE** — Scanner Calculation Engine:
  - `GET /api/scanner` returns real data (was dummy JSON)
  - `GET /api/scanner?week_ending=2026-02-13` for historical weeks
  - 3 gates: volume >= 5x, price >= 5%, delivery >= 35%
  - 8-point scoring: volume + price + delivery + 30W MA + 52W MA + golden cross + RS vs Nifty + sector peers
  - ~7s first call, instant cached
- **M2 COMPLETE** — Stock Deep Dive:
  - `GET /api/stock/{symbol}` returns real data (was dummy JSON)
  - Technicals: MAs, RS, consolidation, volume, delivery, golden cross
  - Fundamentals: 4 quarters in Crores with FY labels, promoter holding, basic ROCE
  - Setup detection: earnings surprise, debt reduction, margin expansion, sector cycle
  - Sector context: sector RS vs Nifty, triggered peers from scanner cache
  - P/E from yfinance (M5), Industry P/E not reliably available, AI summary = placeholder (M7)
- **M3 COMPLETE** — Global Pulse (Partial):
  - `GET /api/macro` returns real data for 3 sections (was dummy JSON)
  - Indian indices: Nifty 50, Bank Nifty, Midcap, Smallcap with value, change %, dist from 52W high
  - Sector heatmap: 10 sectors with 1W change %, RS vs Nifty 4W, sorted strongest first
  - Market phase: BULLISH/SIDEWAYS/BEARISH based on Nifty vs 200-day MA
  - Placeholders (null): world indices, commodities, macro indicators, market depth → M5
- **M4 COMPLETE** — Frontend API Switchover:
  - All 5 screens connected to real backend (no more local JSON imports)
  - `api.js` uses axios with `VITE_API_URL` env var, unwraps `response.data`
  - Null guards: delivery_pct, P/E, industry P/E, ai_summary → "--" or "Coming soon"
  - Null guards: world indices, commodities, macro indicators, market depth → "--"
  - Frontend build passes cleanly
- **M5 COMPLETE** — External Data Fetches:
  - `backend/app/fetchers/` package: 4 fetchers + cache layer
  - World indices (5): S&P 500, Nasdaq, FTSE 100, Nikkei 225, Shanghai — from yfinance
  - Commodities (5): Gold, Crude Oil, Silver, Copper, Natural Gas — from yfinance
  - Macro: DXY, US 10Y yield, INR/USD — from yfinance. FII/DII flows — from nsepython. India 10Y — scraped from CCIL
  - **All macro fields are real. Zero placeholders remaining.**
  - Market depth: Advancing/Declining + 52W Highs/Lows — from nsetools
  - `live_cache` SQLite table stores fetcher results. `POST /api/macro/refresh` triggers all fetchers
  - P/E for deep dive: yfinance `trailingPE` with 24h in-memory cache
  - Market phase upgraded: Nifty vs MA + A/D ratio → 5 labels (BULLISH to BEARISH)
- **M6 COMPLETE** — Portfolio Monitor + Exit Signals:
  - `GET /api/portfolio` returns real exit signal data (was dummy JSON)
  - `POST /api/portfolio/holdings` adds a holding (symbol, buy_price, buy_date, quantity, notes)
  - `DELETE /api/portfolio/holdings/{symbol}` removes a holding
  - `portfolio_holdings` table in SQLite (symbol UNIQUE, auto-created)
  - Exit signals: upper wicks (3+ consecutive), below 30W MA, below 52W MA, support break (3-month low)
  - Health bucketing: healthy (0 signals) / warning (1-2) / alert (MA break or 3+)
  - Sector concentration from stock_universe
  - Frontend: Add Holding dialog, Remove buttons, empty state, null guard on market_leverage
  - Market leverage (MTF) = null — needs accumulation from launch (see A4)
- **M7 COMPLETE** — LLM Integration:
  - `GET /api/briefing` returns real data (was dummy JSON)
  - Briefing compiled from: macro (market phase, indices, sectors), scanner (top signals), portfolio (alerts)
  - LLM (Gemini 2.0 Flash) generates world + India narrative text; data-only fallback when no API key
  - AI summary in Deep Dive: `ai_summary` field generated by LLM with 24h cache per stock
  - `backend/app/llm/` package: REST client + prompt templates. Set `GEMINI_API_KEY` env var.
  - **All 5 screens now show 100% real data. Zero dummy JSON remaining.**
- **Next**: Scheduling (daily/weekly cron jobs) — see `docs/databuilder.md`
