# InvestScan — Data Blueprint

A complete reference for every element in the product: what it shows, where the data comes from, how it's calculated, and how often it refreshes.

---

## Architecture Overview

```
Data Sources                    Backend                         Frontend
-----------                    -------                         --------
yfinance        -->  SQLite DB (investscan.db)  -->  FastAPI REST API  -->  React (Vite + MUI)
nselib              ~99 MB, WAL mode                 localhost:8000         localhost:5173
NSE API             11 tables
nsepython
CCIL (scrape)       live_cache table (4h TTL)
Google News RSS     for external API responses
Gemini 2.0 Flash
```

**Database**: SQLite with 11 tables, ~99 MB. Core tables: `stock_ohlc` (689K rows), `index_daily` (3.7K rows), `quarterly_financials` (8.9K rows), `promoter_holding` (6K rows), `stock_universe` (1,534 rows).

**Stock Universe**: All NSE-listed stocks with market cap >= 500 Cr (~1,534 stocks).

---

## Screen 1: Global Pulse

**API**: `GET /api/macro`
**Backend module**: `app/calculations/macro.py`
**Purpose**: The daily macro scan — everything you check across multiple TradingView tabs, on one screen.

### Market Phase Badge

| Element | What it shows | Source | Refresh | Logic |
|---|---|---|---|---|
| Phase label | One of 5 states: BULLISH, CAUTIOUSLY BULLISH, SIDEWAYS, CAUTIOUSLY BEARISH, BEARISH | Computed from 4 criteria below | Every API call (uses cached index data) | Score from -4 to +4 mapped to 5 labels |
| Phase reason | Plain-English explanation of why this phase | Generated alongside the label | Same as above | Concatenates which criteria are positive/negative |

**Market Phase Scoring (4 criteria, each -1 to +1)**:

| Criterion | +1 if | -1 if | Source |
|---|---|---|---|
| Nifty vs 200-day MA | > 3% above | > 3% below | `index_daily` table (Nifty 50) |
| A/D ratio | > 1.5 | < 0.7 | `live_cache` (nsetools) |
| 52W Highs/Lows ratio | > 2.0 | < 0.5 | `live_cache` (nsetools) |
| FII + DII combined flow | > 0 | < -2,000 Cr | `live_cache` (nsepython) |

**Mapping**: score >= 3 = BULLISH, 2 = CAUTIOUSLY BULLISH, -1 to 1 = SIDEWAYS, -2 = CAUTIOUSLY BEARISH, <= -3 = BEARISH

### World Indices

| Element | What it shows | Source | Refresh | Ticker |
|---|---|---|---|---|
| S&P 500 | US large-cap index value + 1D change % | yfinance | Every 4 hours (live_cache) | ^GSPC |
| Nasdaq | US tech index value + 1D change % | yfinance | Every 4 hours | ^IXIC |
| FTSE 100 | UK index value + 1D change % | yfinance | Every 4 hours | ^FTSE |
| Nikkei 225 | Japan index value + 1D change % | yfinance | Every 4 hours | ^N225 |
| Shanghai | China index value + 1D change % | yfinance | Every 4 hours | 000001.SS |

**Backend**: `app/fetchers/world_indices.py` -> `live_cache` table (key: "world_indices")

### Commodities

| Element | What it shows | Source | Refresh | Ticker |
|---|---|---|---|---|
| Gold | Price in USD + 1D change % | yfinance | Every 4 hours | GC=F |
| Crude Oil | Price in USD + 1D change % | yfinance | Every 4 hours | CL=F |
| Silver | Price in USD + 1D change % | yfinance | Every 4 hours | SI=F |
| Copper | Price in USD + 1D change % | yfinance | Every 4 hours | HG=F |
| Natural Gas | Price in USD + 1D change % | yfinance | Every 4 hours | NG=F |

**Backend**: `app/fetchers/commodities.py` -> `live_cache` table (key: "commodities")

### Macro Indicators

| Element | What it shows | Source | Refresh | Detail |
|---|---|---|---|---|
| Dollar Index (DXY) | USD strength vs basket + 1D change % | yfinance | Every 4 hours | Ticker: DX-Y.NYB |
| US 10Y Yield | US Treasury yield % | yfinance | Every 4 hours | Ticker: ^TNX |
| India 10Y Yield | Indian govt bond yield % | CCIL website scrape | Every 4 hours | Regex on tenorwise yields page |
| INR / USD | Exchange rate | yfinance | Every 4 hours | Ticker: USDINR=X |
| FII Flow (MTD) | Net FII buying/selling in Cr (month-to-date) | nsepython `nse_fiidii()` | Every 4 hours | Latest day's net value |
| DII Flow (MTD) | Net DII buying/selling in Cr (month-to-date) | nsepython `nse_fiidii()` | Every 4 hours | Latest day's net value |

**Backend**: `app/fetchers/macro_indicators.py` -> `live_cache` table (key: "macro_indicators")

### Indian Indices

| Element | What it shows | Source | Refresh | Detail |
|---|---|---|---|---|
| Nifty 50 | Index value, 1D change %, distance from 52W high | yfinance -> `index_daily` | Daily EOD (scheduler 4:45 PM IST) | `dist_from_52w_high = (close / 52w_high - 1) * 100` |
| Bank Nifty | Same as above | Same | Same | Index: NIFTY BANK |
| Nifty Midcap | Same as above | Same | Same | Index: NIFTY MIDCAP 100 |
| Nifty Smallcap | Same as above | Same | Same | Index: NIFTY SMLCAP 100 |

**Backend**: `_calc_indian_indices()` in `macro.py`, reads from `index_daily` table

### Market Depth

| Element | What it shows | Source | Refresh | Logic |
|---|---|---|---|---|
| Advancing | Count of stocks that closed up today | nsetools | Every 4 hours | NSE market statistics |
| Declining | Count of stocks that closed down today | nsetools | Every 4 hours | NSE market statistics |
| A/D Ratio | advancing / declining | Computed | Same | Simple division |
| 52W Highs | Stocks hitting 52-week highs today | nsetools | Every 4 hours | NSE market statistics |
| 52W Lows | Stocks hitting 52-week lows today | nsetools | Every 4 hours | NSE market statistics |

**Backend**: `app/fetchers/market_depth.py` -> `live_cache` table (key: "market_depth"). Also accumulated daily into `daily_accumulation` table for trend charts.

### Sector Heatmap

| Element | What it shows | Source | Refresh | Logic |
|---|---|---|---|---|
| Sector name | One of 10 sectors: IT, Pharma, Auto, FMCG, Metal, Realty, Energy, Media, PSU, Infra | NSE sector indices | N/A | Fixed list mapped to NSE index names |
| 1W Change % | Sector index return over the past week | `index_daily` table | Daily EOD | `(friday_close / prev_friday_close - 1) * 100` |
| RS vs Nifty (4W) | 4-week sector return minus 4-week Nifty return | `index_daily` table | Daily EOD | `sector_4w_return - nifty_4w_return` |

**Sorting**: Sectors sorted by `change_pct` descending (strongest first). RS ranking sorted by `rs_vs_nifty_4w` descending.

**Color coding**: > 1% = green (strong), < 0% = red (weak), in between = neutral.

---

## Screen 2: Signal Scanner

**API**: `GET /api/scanner` (optional param: `?week_ending=YYYY-MM-DD`)
**Backend module**: `app/calculations/scanner.py`
**Purpose**: The weekly volume + price + delivery scan — automated. Runs your three filters on all stocks above 500 Cr.

### Summary Stats

| Element | What it shows | Source | Logic |
|---|---|---|---|
| Stocks Scanned | Total count of stocks in universe | `stock_universe` table | Count of stocks with market_cap >= 500 Cr |
| Stocks Triggered | Count passing all 3 gates | Computed | Count of stocks passing volume + price + delivery gates |
| Hit Rate | Triggered / Scanned as % | Computed | `(triggered / scanned) * 100` |
| Top Score | Highest 8-point score this week | Computed | `max(score)` across all triggered stocks |

### Three Gates (must pass ALL to appear)

| Gate | Threshold | Data source | Logic |
|---|---|---|---|
| Volume | Weekly traded volume >= 5x 52-week average | `stock_ohlc` (daily, resampled to weekly) | Sum daily volumes Mon-Fri for current week. Compare to average weekly volume over prior 52 weeks. |
| Price | Weekly price change >= 5% | `stock_ohlc` (weekly resample) | `(friday_close / prev_friday_close - 1) * 100 >= 5` |
| Delivery | Delivery % >= 35% | `stock_ohlc.delivery_pct` (from NSE delivery data) | Average delivery % across the week's trading days >= 35% |

### 8-Point Scoring (each YES = +1, max 8/8)

| # | Criterion | Data source | Logic |
|---|---|---|---|
| 1 | Delivery % >= 35% | `stock_ohlc.delivery_pct` | Weekly average delivery % >= 35 |
| 2 | Above 30-week MA | `stock_ohlc` | Friday close > 30-week simple moving average of closes |
| 3 | Above 52-week MA | `stock_ohlc` | Friday close > 52-week simple moving average of closes |
| 4 | Golden cross | `stock_ohlc` | 10-week MA crosses above 30-week OR 52-week MA this week (was below last week, above this week) |
| 5 | RS vs Nifty positive | `stock_ohlc` + `index_daily` | `(stock_4w_return - nifty_4w_return) > 0` |
| 6 | Consolidation breakout (6+ months) | `stock_ohlc` | Stock traded within a 15% price range for 6+ months and now broke above the upper bound |
| 7 | Sector outperforming Nifty | `index_daily` | Sector index 4-week return > Nifty 4-week return |
| 8 | 2+ sector peers also triggered | Scanner results | Count of other stocks in same sector that also passed all 3 gates this week >= 2 |

### Per-Stock Row (expanded detail)

| Element | What it shows | Logic |
|---|---|---|
| Stock name + symbol | Company name and NSE ticker | From `stock_universe` |
| Sector chip | Industry classification | From `stock_universe.sector` (yfinance) |
| Market cap chip | Market cap in Cr | From `stock_universe.market_cap_cr` |
| Price | Friday closing price | From weekly resampled `stock_ohlc` |
| Change % | Week-over-week price change | `(close / prev_close - 1) * 100` |
| Vol vs Avg | Volume multiple | `weekly_volume / avg_weekly_volume_52w` |
| Delivery % | Delivery volume as % of traded volume | From `stock_ohlc.delivery_pct` (NSE source) |
| Score badge | 0-8 score | Sum of 8 binary criteria above |
| Technical signals (expanded) | All 8 criteria with YES/NO | Individual checks detailed above |
| Deep Dive link | Navigate to `/stock/{symbol}` | Passes `?week=` param if a historical week is selected |

### Filters and Sort

| Control | Options | Default |
|---|---|---|
| Week ending selector | Last 13 Fridays | Latest week |
| Sort by | Score, Volume, Price Change, Delivery % | Score (descending) |
| Filter: Sector | All + each sector found in results | All |
| Filter: Market Cap | All, Large (>20K Cr), Mid (5K-20K Cr), Small (<5K Cr) | All |
| Filter: Min Score | Any, >= 3 through >= 8 | Any |

### Watch for Breakdown

| Element | What it shows | Logic |
|---|---|---|
| Stocks listed | High volume + price DOWN stocks | Volume >= 5x but price change negative |
| MA Status chips | Below 30W / Below 52W flags | Red chip if below respective MA |

**Caching**: Scanner results are cached in-memory by `week_ending` key. First call ~7s, subsequent calls instant.

---

## Screen 3: Stock Deep Dive

**API**: `GET /api/stock/{symbol}` (optional param: `?week_ending=YYYY-MM-DD`)
**Backend module**: `app/calculations/stock.py`
**Purpose**: Per-stock analysis — chart, technicals, fundamentals, setups, sector context, AI summary.

### Header

| Element | Source | Detail |
|---|---|---|
| Score badge (0-8) | Scanner score for this stock | From scanner cache or computed on-the-fly |
| Stock name + symbol | `stock_universe` | Company name |
| Sector chip | `stock_universe.sector` | yfinance sector classification |
| Market cap chip | `stock_universe.market_cap_cr` | In Crores, from yfinance |
| Price | `stock_ohlc` | Latest Friday close (or historical if `?week_ending=` provided) |
| Price date caption | `stock_ohlc` | "Week ending YYYY-MM-DD" |
| Add to Watchlist button | Write to `watchlist` table | `POST /api/watchlist` |
| Historical data banner | Shown when `?week=` param present | Blue banner with "View latest data" link |

### Technical Chart Card

| Element | Source | Detail |
|---|---|---|
| Open in TradingView link | External URL | `https://www.tradingview.com/chart/?symbol=NSE:{symbol}` |
| Consolidation zone visual | `stock_ohlc` | Price range bar showing low-high band, current price dot, breakout level |
| Consolidation months | Computed | Longest window (4-65 weeks) where `(high - low) / low * 100 <= 15%`. Months = weeks / 4.33 |
| Consolidation range | Computed | [min_low, max_high] during the consolidation window |
| Breakout status | Computed | BREAKOUT (price > range high), BREAKDOWN (price < range low), IN RANGE |
| Key levels chips | Computed | breakout level, 30W MA, 52W MA — all from price calculations |
| Pattern detected chips | `_detect_consolidation_patterns()` | Algorithmically classified from weekly high/low/close data within the consolidation window: VCP (contracting ranges across 3 segments), Darvas Box (tight range < 8% in latter 2/3), Cup & Handle (U-shaped closes with handle pullback), Inv H&S (3-segment lows where middle is deepest) |
| "No consolidation" message | Shown when `consolidation_months = 0` | "Stock price range exceeded 15% in every 4-week window" |

### Chart Judgment Journal

| Element | Source | Detail |
|---|---|---|
| Pattern dropdown | User input | Options: VCP, Darvas Box, Cup & Handle, Inv H&S, Other, None |
| Conviction toggle | User input | High, Medium, Low |
| Notes field | User input | Free text |
| Previous observations | `chart_judgments` SQLite table | `GET /api/stock/{symbol}/judgments` |
| Save / Delete | Write to DB | `POST` / `DELETE /api/stock/{symbol}/judgments` |

**Note**: This is the manual overlay — the system flags candidates, the user records their visual assessment here.

### Technical Signals

| Signal | Source | Logic |
|---|---|---|
| Volume this week | `stock_ohlc` | `weekly_volume / avg_weekly_volume_52w` (expressed as Nx) |
| Delivery % | `stock_ohlc.delivery_pct` | Average delivery % for the week. Color: >= 60% green, >= 50% white, < 50% amber |
| Above 30W MA | `stock_ohlc` | `close > SMA(close, 30 weeks)`. Shows MA value in parentheses |
| Above 52W MA | `stock_ohlc` | `close > SMA(close, 52 weeks)`. Shows MA value in parentheses |
| Golden Cross | `stock_ohlc` | 10W SMA crossed above 30W or 52W SMA this week. Shows which cross occurred |
| RS vs Nifty (4W) | `stock_ohlc` + `index_daily` | `stock_4w_return - nifty_4w_return`. Green if positive |
| Consolidation | `stock_ohlc` | Months in range + price band. "None detected" if < 6 months |
| Breakout above | `stock_ohlc` | Upper bound of consolidation range |
| Breakout Pattern | `_detect_consolidation_patterns()` | VCP, Darvas Box, Cup & Handle, Inv H&S — algorithmically classified from weekly OHLC data within the consolidation window, or "None detected" |

### Sector Context

| Element | Source | Logic |
|---|---|---|
| Sector RS vs Nifty (4W) | `index_daily` | Sector index 4-week return minus Nifty 4-week return |
| Peers triggered table | Scanner cache | Other stocks in same sector that passed all 3 gates this week |
| Peer count summary | Computed | "N peers triggered -- possible sector momentum" |

### Fundamentals

| Field | Source | Detail |
|---|---|---|
| Revenue (Cr) | `quarterly_financials.revenue` | Last 4 quarters, converted to Crores. Source: yfinance |
| Operating Margin % | `quarterly_financials.operating_margin` | `operating_income / revenue * 100` |
| Net Profit (Cr) | `quarterly_financials.net_income` | PAT from yfinance |
| EPS | `quarterly_financials.eps` | Earnings per share from yfinance |
| Total Debt (Cr) | `quarterly_financials.total_debt` | Color inverted — decrease is green |
| ROCE % | Computed + Screener.in | Basic: `operating_income / total_assets * 100`. Overridden by Screener.in ROCE when available (24h cache) |
| Promoter Holding % | `promoter_holding.promoter_pct` | From NSE API via nsepython |
| Quarter labels | Computed | Indian FY format: Q1 FY26 = Apr-Jun 2025 |
| YoY Change | Computed | `(latest_quarter - year_ago_quarter) / abs(year_ago_quarter) * 100` |
| P/E | yfinance `trailingPE` | 24h in-memory cache per stock |
| Industry P/E | yfinance | Not reliably available — may show "--" |
| "Below industry P/E" chip | Computed | Shown when stock P/E < industry P/E |

**Refresh**: Quarterly financials updated 1st of Feb/May/Aug/Nov. Promoter holding updated 2nd of same months.

### Setup Detection (9 setups)

| # | Setup | Detection method | Source | Detail |
|---|---|---|---|---|
| 1 | Earnings Surprise | Auto | `quarterly_financials` | Net profit up 50%+ YoY. Cross-checked with revenue to filter one-time items |
| 2 | Debt Reduction | Auto | `quarterly_financials` | Total debt declining across 3+ consecutive quarters |
| 3 | Margin Expansion | Auto | `quarterly_financials` | Operating margin trending up over 3+ quarters |
| 4 | Sector of the Cycle | Auto | Scanner + `index_daily` | Sector RS positive + 2+ peers triggered in same week |
| 5 | Balance Sheet Improvement | Auto | `quarterly_financials` | ROCE trending up over 3+ quarters |
| 6 | Management Change | News scan | Google News RSS + Gemini LLM | 15 recent headlines classified by LLM. 24h cache per stock |
| 7 | Supply Disruption | News scan | Google News RSS + Gemini LLM | Same as above — factory shutdowns, sanctions, disasters |
| 8 | Forced Buying/Selling | Data + News | NSE bulk/block deals + news | `bulk_block_deals` table + news classification |
| 9 | Business Mix Change | Manual flag | User action | System flags hint (margins up, revenue flat). User confirms via Flag button after checking segment data |

**Backend**: `_detect_setups()` in `stock.py`, `app/llm/news_setups.py` for news-based detection.

### AI Summary

| Element | Source | Detail |
|---|---|---|
| Summary text | Gemini 2.0 Flash | 2-3 sentence factual summary. Input: full stock data dict. Temperature: 0.3 |
| Disclaimer | Static text | "This summary is generated by AI from the data above. It restates facts -- it does not give opinions or recommendations." |
| Fallback | When no API key | "Coming soon" message |

**Backend**: `app/llm/summaries.py`. Env var: `GEMINI_API_KEY`. 24h in-memory cache per stock.

---

## Screen 4: Portfolio Monitor

**API**: `GET /api/portfolio`
**Backend module**: `app/calculations/portfolio.py`
**Purpose**: Exit signal tracking. Groups holdings into healthy/warning/alert buckets.

### Holdings (3 buckets)

| Bucket | Criteria | Visual |
|---|---|---|
| Alert | MA break (below 30W or 52W) OR bad news signal OR 3+ signals active | Red border, "REVIEW" status |
| Warning | 1-2 signals active (but no MA break and < 3 total) | Amber border, "WATCH" status |
| Healthy | 0 exit signals | No border, no status badge |

### Per-Holding Card

| Element | Source | Detail |
|---|---|---|
| Symbol + name | `portfolio_holdings` + `stock_universe` | User-added holding |
| Sector | `stock_universe.sector` | yfinance classification |
| Buy price | `portfolio_holdings.buy_price` | User-entered |
| Current price | `stock_ohlc` (latest close) | Most recent trading day close |
| P&L % | Computed | `(current - buy) / buy * 100` |
| Days held | Computed | `today - buy_date` in days |
| 6-month indicator | Computed | "Complete" chip (green) if >= 183 days, else "Xd left" chip |
| Quantity | `portfolio_holdings.quantity` | User-entered |
| Buy thesis | `portfolio_holdings.buy_thesis` | One of the 9 setups |
| Setup review | Computed + stored | Whether original setup is still valid |

### Exit Signals (per holding)

| # | Signal | Source | Logic |
|---|---|---|---|
| 1 | Upper wicks (3+ consecutive weeks) | `stock_ohlc` | `(high - close) / (high - low) > 0.6` for 3+ consecutive weeks |
| 2 | Below 30W MA | `stock_ohlc` | `current_close < SMA(close, 30 weeks)` |
| 3 | Below 52W MA | `stock_ohlc` | `current_close < SMA(close, 52 weeks)` |
| 4 | Support break (13-week low) | `stock_ohlc` (weekly resample) | `current_close < min(weekly close, last 13 weeks)` |
| 5 | Head & Shoulders | `stock_ohlc` | 3-peak reversal pattern detection from weekly highs |
| 6 | Bad news + technical breakdown | Google News RSS + Gemini LLM | Only fires when a technical exit signal is already active. News classified by LLM |

### Holding Actions

| Action | API | Detail |
|---|---|---|
| Sell | `POST /api/portfolio/sell` | Logs to `trade_history`, removes from `portfolio_holdings`. Compliance warning if < 6 months |
| Hold | `POST /api/portfolio/hold` | Logs hold decision with reason to `trade_history` |
| Add More | `POST /api/portfolio/add-more` | Updates quantity + weighted average: `new_avg = (old_qty * old_price + new_qty * new_price) / (old_qty + new_qty)` |
| Remove | `DELETE /api/portfolio/holdings/{symbol}` | Removes without logging to trade history |

### Portfolio Health Summary

| Element | Source | Logic |
|---|---|---|
| Healthy / Warning / Alert counts | Computed | Count of holdings in each bucket |
| Sector concentration | `stock_universe.sector` | Group holdings by sector, show count and % |
| Total holdings count | `portfolio_holdings` | Count of all holdings |

### Market Leverage

| Element | Source | Detail |
|---|---|---|
| Margin borrowing (Cr) | nsetools (client positions) | F&O participant open interest as proxy. Actual MTF data not programmatically available from NSE |
| 3-month trend | `daily_accumulation` | INCREASING / DECREASING / STABLE based on 3-month slope |
| Long/Short ratio | nsetools | Client long contracts / client short contracts |

### Watchlist Tab

| Element | Source | Detail |
|---|---|---|
| Watchlist items | `watchlist` table | Added from Deep Dive's "Add to Watchlist" button |
| Add to Portfolio button | Opens Add Holding dialog | Pre-fills symbol |
| Remove button | `DELETE /api/watchlist/{symbol}` | Removes from watchlist |

### Alerts Tab

| Element | Source | Detail |
|---|---|---|
| Price alerts | `price_alerts` table | User-created alerts (symbol, type: above/below, target price) |
| Create alert | `POST /api/alerts` | User sets target price and direction |
| Delete alert | `DELETE /api/alerts/{id}` | Removes alert |

### Decision Log Tab

| Element | Source | Detail |
|---|---|---|
| Trade history | `trade_history` table | All BUY, SELL, ADD, HOLD actions with timestamps, prices, reasons |

---

## Screen 5: Weekly Briefing

**API**: `GET /api/briefing`
**Backend module**: `app/calculations/briefing.py`
**Purpose**: Weekend summary. Compiles data from all other screens into one readable brief.

### Compiled from

| Section | Source | How it's built |
|---|---|---|
| Market phase | `get_global_pulse()` | Same phase label + change vs last week |
| World narrative | Gemini 2.0 Flash | LLM generates 2-3 sentences from world indices + commodities + macro data |
| India narrative | Gemini 2.0 Flash | LLM generates 2-3 sentences from Indian indices + sectors + market depth |
| Sector notes | `get_global_pulse()` | Top 3 sectors selected: strongest, weakest, and one emerging. References demo stocks in those sectors |
| Top signals (3-4) | `run_scanner()` | Highest-scoring triggered stocks with key pattern/driver notes |
| Portfolio alerts | `get_portfolio()` | Holdings in alert or warning state |

**Fallback**: When no Gemini API key is set, data-only summaries are returned (numbers without narrative prose).

### Per-Element Detail

| Element | Source | Detail |
|---|---|---|
| Week ending date | Scanner's week_ending | The Friday that the scan covers |
| Market phase | Same as Global Pulse | 5-state label |
| Market phase change | Computed | "unchanged", "upgraded", or "downgraded" vs previous week |
| World text | Gemini LLM | Factual narrative from global data. Temperature 0.3 |
| India text | Gemini LLM | Factual narrative from Indian market data. Temperature 0.3 |
| Sector cards (5) | `sector_heatmap` + scanner data | Name + note explaining what's happening in that sector |
| Top signals cards (3-4) | Scanner top N by score | Symbol, name, sector, score badge, pattern/driver note |
| Portfolio alerts | Portfolio holdings in alert/warning | Symbol, name, status badge, note explaining the signals |
| Quick actions | Navigation links | "Open Dashboard", "View All Signals", "Review Portfolio" |
| WhatsApp / Email chips | Placeholder | Delivery channels — not yet connected |

---

## Screen 6: Reporting

**API**: `GET /api/portfolio` (same as Portfolio Monitor)
**Backend module**: `app/calculations/portfolio.py`
**Purpose**: Portfolio overview — stock count compliance, P&L summary, holdings by tenure.

### Elements

| Element | Source | Logic |
|---|---|---|
| Stocks Held count | `portfolio_holdings` | Total count. Color: green if 15-25 (target range), amber otherwise |
| Total Invested | Computed | `sum(buy_price * quantity)` across all holdings |
| Current Value | Computed | `sum(current_price * quantity)` across all holdings |
| Overall P&L | Computed | `current_value - invested_value`. Both absolute and % |
| Sectors breakdown | `stock_universe.sector` | Chips showing sector name + count |
| Holdings table | All holdings sorted by days held (desc) | Columns: Stock, Sector, Buy Date, Days Held, 6M Status, Qty, Buy Price, Current, P&L, Invested |
| 6M Status column | Computed | "Complete" if >= 183 days held, "Xd left" otherwise |
| Row click | Navigation | Navigates to `/stock/{symbol}` for Deep Dive |

---

## Data Refresh Schedule

### Daily (Mon-Fri, automated via scheduler)

| Time (IST) | What | Detail |
|---|---|---|
| 4:30 PM | Stock OHLC + delivery | Appends today's OHLC + delivery data for all stocks -> `stock_ohlc` |
| 4:45 PM | Index daily | Appends today's close for all 14 indices -> `index_daily` |
| 5:00 PM | Macro refresh | Fetches world indices, commodities, DXY, yields, FII/DII -> `live_cache` |
| 5:15 PM | Bulk/block deals | Fetches today's deals from NSE -> `bulk_block_deals` |
| 5:30 PM | Market depth accumulation | Stores today's A/D ratio + 52W H/L counts -> `daily_accumulation` |

### Weekly

| Time | What | Detail |
|---|---|---|
| Sunday 10:00 AM | Stock universe refresh | Adds new stocks >= 500 Cr, removes delisted -> `stock_universe` |

### Quarterly (Feb, May, Aug, Nov)

| Day | What | Detail |
|---|---|---|
| 1st @ 6 AM | Quarterly financials | Refreshes revenue, profit, debt, margins for all stocks -> `quarterly_financials` |
| 2nd @ 6 AM | Promoter holding | Refreshes promoter/public/FII/DII % -> `promoter_holding` |
| 3rd @ 6 AM | Sector classification | Updates sector assignments -> `stock_universe.sector` |

### On-Demand

| Trigger | What | Detail |
|---|---|---|
| `POST /api/macro/refresh` | All macro fetchers | Force-refreshes world, commodities, macro, market depth |
| Stock Deep Dive visit | News setups + AI summary | Google News RSS + Gemini LLM. 24h cache per stock |
| Stock Deep Dive visit | P/E ratio | yfinance trailingPE. 24h in-memory cache per stock |

---

## API Endpoints Summary

### Read APIs

| Endpoint | Returns | Caching |
|---|---|---|
| `GET /api/macro` | Global Pulse data (all sections) | live_cache 4h for external data |
| `GET /api/scanner` | Scanner results for latest or specified week | In-memory by week_ending |
| `GET /api/scanner?week_ending=YYYY-MM-DD` | Historical week's scanner results | Same |
| `GET /api/stock/{symbol}` | Full Deep Dive analysis | Computed on-the-fly (except P/E and news: 24h cache) |
| `GET /api/stock/{symbol}?week_ending=YYYY-MM-DD` | Historical Deep Dive | Same |
| `GET /api/stock/universe` | All ~1,534 stocks (symbol, name, sector) | In-memory, refreshed on first call |
| `GET /api/stock/{symbol}/judgments` | Chart pattern judgments for a stock | Direct DB read |
| `GET /api/portfolio` | Holdings + exit signals + sector concentration | Computed on-the-fly |
| `GET /api/portfolio/history` | Trade history (buys, sells, adds, holds) | Direct DB read |
| `GET /api/watchlist` | Watchlist items | Direct DB read |
| `GET /api/alerts` | Price alerts | Direct DB read |
| `GET /api/briefing` | Weekly briefing with narratives | Computed on-the-fly + LLM |

### Write APIs

| Endpoint | Action |
|---|---|
| `POST /api/macro/refresh` | Force-refresh all macro data |
| `POST /api/portfolio/holdings` | Add a holding (symbol, buy_price, buy_date, quantity, buy_thesis) |
| `DELETE /api/portfolio/holdings/{symbol}` | Remove a holding |
| `POST /api/portfolio/sell` | Sell a holding (logs to trade history) |
| `POST /api/portfolio/hold` | Record hold decision |
| `POST /api/portfolio/add-more` | Add more shares (weighted avg) |
| `POST /api/stock/{symbol}/flag/business_mix` | Flag business mix change |
| `DELETE /api/stock/{symbol}/flag/business_mix` | Remove flag |
| `POST /api/stock/{symbol}/judgments` | Save chart pattern judgment |
| `DELETE /api/stock/{symbol}/judgments/{id}` | Delete a judgment |
| `POST /api/watchlist` | Add to watchlist |
| `DELETE /api/watchlist/{symbol}` | Remove from watchlist |
| `POST /api/alerts` | Create price alert |
| `DELETE /api/alerts/{id}` | Delete price alert |

---

## Database Tables

| Table | Rows | Purpose | Primary Key |
|---|---|---|---|
| `stock_universe` | 1,534 | All stocks >= 500 Cr market cap | symbol |
| `stock_ohlc` | 689,224 | Daily OHLC + delivery (2 years) | (symbol, date) |
| `index_daily` | 3,717 | Daily close for 14 indices | (index_name, date) |
| `quarterly_financials` | 8,944 | Revenue, profit, debt, margins | (symbol, quarter_end) |
| `promoter_holding` | 5,964 | Promoter/public/FII/DII % | (symbol, quarter_end) |
| `bulk_block_deals` | Variable | NSE bulk and block deals | (date, symbol, deal_type, client_name, buy_sell) |
| `daily_accumulation` | Variable | A/D, 52W H/L, FII/DII trends | (date, metric) |
| `live_cache` | 5 keys | External API response cache | key |
| `portfolio_holdings` | User-managed | Current holdings | symbol (UNIQUE) |
| `trade_history` | User-managed | Buy/sell/add/hold log | id (autoincrement) |
| `watchlist` | User-managed | Watchlisted stocks | symbol (UNIQUE) |
| `price_alerts` | User-managed | Price alerts | id (autoincrement) |
| `chart_judgments` | User-managed | Chart pattern observations | id (autoincrement) |
| `backfill_progress` | Pipeline state | Data backfill resume tracking | (step, item) |

---

## Data Sources

| Source | What it provides | Access method | Cost |
|---|---|---|---|
| **yfinance** | Stock OHLC, market cap, P/E, financials, world indices, commodities, DXY, yields, INR/USD | Python library (free Yahoo Finance API) | Free |
| **nselib** | Delivery volume % | Python library (NSE data) | Free |
| **NSE API (direct)** | Promoter holding | HTTP requests to NSE website | Free |
| **nsepython** | FII/DII flows, index data | Python library | Free |
| **nsetools** | Advancing/declining, 52W highs/lows | Python library | Free |
| **CCIL** | India 10Y government bond yield | HTML scrape (regex on tenorwise yields page) | Free |
| **Google News RSS** | News headlines for setup detection | RSS feed (15 recent headlines per stock) | Free |
| **Gemini 2.0 Flash** | AI summaries, news classification, briefing narratives | REST API | Free tier / Pay per use. Env var: `GEMINI_API_KEY` |

---

## What's Automated vs. What Stays Human

### Fully Automated
- Macro dashboard (all sections)
- Market phase indicator
- Volume + price + delivery screening (all stocks)
- Moving averages + golden cross detection
- Relative strength calculations
- Consolidation detection + breakout flagging
- Pattern detection (VCP, Darvas Box, Cup & Handle, Inv H&S)
- Signal scoring (8-point system)
- Fundamental data pulls (revenue, margins, debt, ROCE, P/E, promoter holding)
- Setup detection from numbers (earnings surprise, debt reduction, margin expansion, sector cycle, balance sheet)
- Exit signal detection (upper wicks, MA breaks, support break)
- Weekly briefing generation
- Portfolio health bucketing

### Semi-Automated (system flags, human validates)
- Setup detection from news (management change, supply disruption, forced buying) — LLM classifies headlines
- Head & Shoulders exit pattern — system flags potential, confirm visually
- Business mix change — system hints (margins up, revenue flat), user confirms after checking segment data

### Stays 100% Human
- Chart pattern judgment (which pattern? is it convincing?)
- Management quality assessment
- "Operated stock" identification
- Network / industry contacts
- Position sizing decisions
- Final buy decisions
- Final sell decisions
