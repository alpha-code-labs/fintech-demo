# Pending List — InvestScan

As of March 5, 2026. M1–M7 complete. All 5 screens return real data.

**Goal: Fully functional on localhost for Sandeep to test end-to-end.**

---

## P0: Data Freshness (product is useless without fresh data)

| # | What | Why | How to verify locally |
|---|------|-----|----------------------|
| 1 | ~~Daily stock OHLC + delivery % append~~ | **DONE** — `scripts/daily_ohlc.py` fetches bhavcopy (OHLC + delivery in one call per date). Holiday detection via DATE1 field. Run: `python -m scripts.run_backfill --step daily_ohlc` | Verified: March 4 data appended (1,534 stocks), all API endpoints working |
| 2 | ~~Daily Indian + sector index append~~ | **DONE** — `scripts/daily_indices.py` fetches all 14 indices (Nifty 50 + 3 broad + 10 sector) per date range. nselib primary, yfinance fallback. Run: `python -m scripts.run_backfill --step daily_indices` | Verified: March 4–5 data appended (14 indices), Global Pulse shows current values |
| 3 | ~~Weekly universe refresh~~ | **DONE** — `scripts/refresh_universe.py` re-fetches NSE equity list, checks market cap only for NEW symbols (fast), removes delisted stocks, updates timestamps. Run: `python -m scripts.run_backfill --step refresh_universe` | Verified: 579 new symbols checked, 5 added (>500 Cr), 0 delisted, universe 1534→1539. All API endpoints working. |
| 4 | ~~Scheduling (APScheduler)~~ | **DONE** — `app/scheduler.py` with 4 jobs: daily OHLC (4:30 PM IST Mon-Fri), daily indices (4:45 PM), macro refresh (5:00 PM), weekly universe (Sun 10 AM). Starts/stops with server via FastAPI lifespan. `GET /api/scheduler/status` shows job state. | Verified: scheduler starts with server, all 4 jobs registered with correct next_run times, all 5 API endpoints still working. |

## P1: Feature Gaps Visible During Local Testing

| # | What | Where you'll see it broken | Spec ref |
|---|------|---------------------------|----------|
| 5 | ~~Industry P/E~~ | **DONE** — Scraped from Screener.in: company page → sub-industry link → median P/E of all peers. 24h in-memory cache. Added `beautifulsoup4` to requirements. | Verified: RELIANCE=14.4, TCS=24.0, HDFCBANK=15.8. API endpoint returns real values. |
| 6 | ~~ROCE improvement~~ | **DONE** — Scraped from Screener.in (same visit as industry P/E). Accurate annual ROCE replaces latest quarter's basic approximation. Combined Screener cache avoids duplicate HTTP calls. | Verified: RELIANCE=9.69%, TCS=64.6%, HDFCBANK=7.51%. Matches Screener.in values. |
| 7 | ~~Bulk/block deals~~ | **DONE** — `scripts/daily_deals.py` fetches bulk + block deals from nselib. Stored in `bulk_block_deals` table. Deep Dive "Forced Buying/Selling" setup now auto-detects from real deal data (30-day lookback). Scheduled daily at 5:15 PM IST. Run: `python -m scripts.run_backfill --step daily_deals` | Verified: 1,781 bulk + 38 block deals fetched. DEEDEV shows 140 deals detected. RELIANCE correctly shows no deals. |
| 8 | ~~TradingView chart embed~~ | **DONE** — `TradingViewChart.jsx` component uses free TradingView Advanced Chart widget embed (no API key). Weekly interval, dark theme, 3 MAs (10W, 30W, 52W), volume bars. Integrated into `StockDeepDive.jsx` replacing placeholder. Key levels chips and judgment prompt preserved below chart. | Verified: frontend builds cleanly, deep dive API returns data, chart renders for NSE symbols. |
| 9 | ~~Head & shoulders pattern detection~~ | **DONE** — `_check_head_and_shoulders()` in `portfolio.py`. Detects 3-peak pattern (left shoulder, head, right shoulder) from weekly highs over 10–30 week window. Swing high detection with merging, shoulder symmetry check (10% tolerance), head must be 3%+ above shoulders. Flags when price is within 5% above neckline or below it. Added as exit signal #5. | Verified: RELIANCE detected H&S (neckline 1,336), TCS/HDFCBANK/INFY correctly show no pattern. End-to-end portfolio test passed. |
| 10 | ~~News-based setups (management change, supply disruption, forced buying)~~ | **DONE** — `app/llm/news_setups.py` fetches headlines from Google News RSS (free, no key), sends to Gemini for classification into 3 categories: management change, supply disruption, forced buying. 24h in-memory cache per stock. Graceful fallback when no GEMINI_API_KEY (shows "not detected"). Forced buying from news supplements existing bulk/block deals detection. | Verified: Google News returns 15 headlines per stock. Without API key, gracefully shows "not detected". All 8 setups now categorized (5 data + 2 news + 1 manual). All 5 endpoints working. |
| 11 | ~~Bad news + technical breakdown exit signal~~ | **DONE** — `_check_bad_news_breakdown()` in `portfolio.py`. Only fires when at least one technical exit signal is already active (MA break, support break, wicks, H&S). Fetches headlines via Google News RSS, asks Gemini to identify negative news (earnings miss, regulatory action, fraud, etc.). Combined signal auto-escalates holding to "alert" bucket. 24h cache per stock. Graceful fallback when no GEMINI_API_KEY. | Verified: Without API key, bad news signal gracefully absent while 4 technical signals still fire. All 5 endpoints pass regression. |
| 12 | ~~Business mix change (manual flag)~~ | **DONE** — `stock_flags` SQLite table stores per-stock manual flags. `POST /api/stock/{symbol}/flag/business_mix` sets flag with detail, `DELETE` clears it. Setup detection reads flag from DB — shows detected (green) when flagged, not-detected with "Check on Screener.in" when unflagged. Frontend: SetupCard has Flag/Unflag button on Business Mix Change card, calls API and refreshes data. | Verified: Flag/unflag roundtrip works (set→detected→clear→not_detected). All 8 setups present. All 5 endpoints pass regression. Frontend builds. |

## P2: Accumulation — Start Collecting Now (no backfill possible)

These have no historical source. Every day you don't collect = lost data forever.

| # | What | Why it matters | Spec ref |
|---|------|---------------|----------|
| 13 | ~~A/D ratio daily count~~ | **DONE** — `daily_accumulation` table stores daily A/D counts + 52W highs/lows. `scripts/daily_accumulation.py` reads from market_depth fetcher (nsetools) and stores in DB. Idempotent (skips if today's data exists). Scheduled at 5:30 PM IST Mon-Fri (after macro refresh). CLI: `python -m scripts.run_backfill --step daily_accumulation`. Macro endpoint now includes `ad_trend` (last 30 days). Run: `python -m scripts.run_backfill --step daily_accumulation` | Verified: Stored 2026-03-05 data (27 adv, 23 decl, ratio 1.17). Idempotency works. Macro endpoint returns ad_trend. Scheduler has 6 jobs. All 5 endpoints pass regression. |
| 14 | ~~52W Highs/Lows daily count~~ | **DONE** — Stored alongside A/D data in `daily_accumulation` table (metric='52w_hl'). Same script (`daily_accumulation_store`), same schedule, same CLI command. Macro endpoint now includes `hl_trend` (last 30 days) alongside `ad_trend`. | Verified: 2026-03-05 data stored (19 highs, 212 lows, ratio 0.1). Macro endpoint returns both `ad_trend` and `hl_trend`. All 5 endpoints pass regression. |
| 15 | ~~FII/DII daily flow breakdown~~ | **DONE** — Stored in `daily_accumulation` table (metric='fii_dii') alongside A/D and 52W data. Same script (`daily_accumulation_store`), same schedule (5:30 PM IST), same CLI command. Reads FII/DII net values from `_fetch_fii_dii()` (nsepython). Macro endpoint now includes `fii_dii_trend` (last 30 days) with value1=FII net (Cr), value2=DII net (Cr). | Verified: 2026-03-05 data stored (FII -8,753 Cr, DII +12,068 Cr). Idempotency works. Macro endpoint returns `fii_dii_trend`. All 5 endpoints pass regression. Frontend builds. |
| 16 | ~~MTF daily total~~ | **DONE** — Implemented using F&O participant-wise open interest (nsepython `get_fao_participant_oi`) as a market leverage proxy. NSE does not expose MTF data via any programmatic API. Client (retail) long/short contracts stored in `daily_accumulation` table (metric='market_leverage'). New fetcher: `app/fetchers/market_leverage.py`. Portfolio endpoint `market_leverage` field now populated with client long contracts, L/S ratio, and 3-month trend (INCREASING/DECREASING/STABLE). Frontend updated to show retail F&O leverage + L/S ratio + trend chip. Shows "ACCUMULATING" until 7+ data points collected. Scheduled via macro refresh (5:00 PM) + daily accumulation (5:30 PM). | Verified: 2026-03-05 data stored (Client long 8.85M, short 5.99M, L/S 1.48). Idempotency works. Portfolio endpoint returns leverage data. All 5 endpoints pass regression. Frontend builds. |

## P3: Quarterly Data Refresh

| # | What | When to run | Spec ref |
|---|------|------------|----------|
| 17 | ~~Quarterly financials refresh~~ | **DONE** — `scripts/refresh_financials.py` re-fetches yfinance quarterly_income_stmt + quarterly_balance_sheet for all stocks in universe. INSERT OR REPLACE adds new quarters, updates existing. CLI: `python -m scripts.run_backfill --step refresh_financials`. Scheduled quarterly at 6:00 AM IST on 1st of Feb/May/Aug/Nov (after results season). Reuses `_extract_financials()` from backfill_financials.py. | Verified: 5-stock test — fetches 5-6 quarters per stock, INSERT OR REPLACE works correctly. Scheduler shows 7 jobs with quarterly_financials next run 2026-05-01. All 5 endpoints pass regression. Frontend builds. |
| 18 | ~~Promoter holding refresh~~ | **DONE** — `scripts/refresh_promoter.py` re-fetches NSE corporate-share-holdings-master API for all stocks in universe. INSERT OR REPLACE adds new quarters, updates existing. CLI: `python -m scripts.run_backfill --step refresh_promoter`. Scheduled quarterly at 6:00 AM IST on 2nd of Feb/May/Aug/Nov (day after financials). Reuses `_fetch_shareholding()` and `_get_nse_session()` from backfill_promoter.py. Auto-refreshes NSE session on 403. | Verified: 3-stock test — NSE returns 4 quarters per stock, INSERT OR REPLACE works. Scheduler shows 8 jobs with quarterly_promoter next run 2026-05-02. All 5 endpoints pass regression. Frontend builds. |
| 19 | ~~Sector classification refresh~~ | **DONE** — `scripts/refresh_sectors.py` re-fetches sector and industry from yfinance for all stocks in universe. Updates `stock_universe` table in-place. Skips update if yfinance returns empty sector (avoids blanking data). Logs any reclassifications. CLI: `python -m scripts.run_backfill --step refresh_sectors`. Scheduled quarterly at 6:00 AM IST on 3rd of Feb/May/Aug/Nov. | Verified: 3-stock test — yfinance returns correct sectors matching DB. Scheduler shows 9 jobs with quarterly_sectors next run 2026-05-03. All 5 endpoints pass regression. Frontend builds. |

## Removed from Local Testing Scope

These are deployment/distribution items — not needed for local testing:

| What | Why deferred |
|------|-------------|
| Backend deployment (Azure) | Testing locally first, deploy after everything works |
| Set GEMINI_API_KEY on server | Already set in local `.env` — works on localhost |
| WhatsApp delivery (Step 52) | Distribution channel, not core product logic |
| Email delivery (Step 53) | Distribution channel, not core product logic |
| ~~Market margin borrowing / MTF (Step 22)~~ | **Implemented** as F&O participant OI proxy (item 16). Trend fills in over time. |

## P4: Product Vision Gaps

Gaps found by auditing `product_vision.txt` against actual implementation. Excludes delivery channels (WhatsApp/Email) which are already deferred above.

| # | What | Screen | Detail |
|---|------|--------|--------|
| 20 | ~~Scanner filters (Sector / Market Cap / Score ≥ X)~~ | Signal Scanner | **DONE** — Backend: `market_cap_cr` added to scanner signal response from `stock_universe`. Frontend: 3 filter dropdowns (Sector, Market Cap [Large >20K Cr / Mid 5K–20K / Small <5K], Min Score [>=3 to >=8]). Active filter count chip with clear-all. Filters combine with existing sort controls. Empty state shows filter-specific message. Market cap chip shown on each stock row. |
| 21 | ~~"High volume + price DOWN" distribution watch list~~ | Signal Scanner | **DONE** — Backend: scanner now returns `distribution_watchlist` alongside `signals`. Filters stocks with vol >=5x avg AND price change <0, sorted by volume, capped at top 20. Each entry includes symbol, name, sector, market_cap_cr, price, change_pct, vol_vs_avg, delivery_pct, below_30w_ma, below_52w_ma. Frontend: "Watch for Breakdown" section with warning icon below main scanner table. Shows stock name, price, change (red), volume multiplier, delivery %, and MA status chips (< 30W / < 52W in red). Click navigates to Deep Dive. |
| 22 | ~~Consolidation zone shading on chart~~ | Stock Deep Dive | **DONE** — TradingView embed widget doesn't support custom overlays, so a `ConsolidationZone` visual component is rendered directly below the chart. Shows a horizontal price range bar with: shaded consolidation zone (blue), current price marker (colored dot — green if breakout, red if breakdown, orange if in range), breakout level indicator, duration chip, and BREAKOUT/BREAKDOWN/IN RANGE status chip. Only appears when consolidation is detected (months > 0). Backend already provides `consolidation_range`, `consolidation_months`, and `breakout_level`. |
| 23 | ~~Watchlist as separate concept from Portfolio~~ | Stock Deep Dive / Portfolio Monitor | **DONE** — Backend: `watchlist` SQLite table (symbol UNIQUE, notes, added_at). CRUD: `GET /api/watchlist` (returns items with current price, name, sector, market_cap from stock_universe + stock_ohlc), `POST /api/watchlist` (add symbol + optional notes), `DELETE /api/watchlist/{symbol}`. Frontend Deep Dive: "Add to Watchlist" button now calls API (was just a snackbar). Shows success or "already in watchlist" warning. Frontend Portfolio Monitor: Watchlist section at bottom with count badge. Shows stock name, symbol, sector, market cap, current price, notes. Click navigates to Deep Dive. Remove button per item. Empty state with guidance. Watchlist = tracking interest (no buy price/quantity), Portfolio = active holdings with P&L. |
| 24 | ~~"Set Alert" button / notification system~~ | Portfolio Monitor | **DONE** — Backend: `price_alerts` SQLite table (symbol, alert_type [above/below], target_price, notes, triggered flag, created_at). CRUD: `GET /api/alerts` (returns all alerts with current price + auto-checks triggered status), `POST /api/alerts`, `DELETE /api/alerts/{id}`. Triggered detection: compares current price from stock_ohlc against target, auto-marks triggered in DB. Frontend: "Set Alert" button on every holding card (warning + alert buckets). SetAlertDialog with "Price goes above" / "Price drops below" toggle, target price input, optional notes. Price Alerts section on Portfolio Monitor shows all alerts with triggered status (red TRIGGERED chip, bell icon). AlertRow shows symbol, alert condition, current price, delete button. Click navigates to Deep Dive. |
| 25 | ~~Exit signal #8: "Has the original setup ended?"~~ | Portfolio Monitor | **DONE** — Backend: `buy_thesis` column added to `portfolio_holdings` (8 options: earnings_surprise, debt_reduction, margin_expansion, sector_cycle, supply_disruption, forced_buying, management_change, other). `_check_setup_still_valid()` re-checks each thesis against current data: earnings (YoY net income trend), debt (quarterly total_debt trend), margins (operating margin trend), sector (scanner peer count). Event-driven theses (supply/management/forced) prompt manual review. When thesis no longer valid, fires as exit signal #8 ("Original setup may have ended") and can escalate holding to alert bucket. Frontend: Add Holding dialog has "Buy Thesis" dropdown. HoldingCard shows Setup Review box with INTACT (green) or WEAKENING (red) chip plus reason and detail. Holdings without thesis show no review. |
| 26 | ~~SELL / HOLD decision workflow~~ | Portfolio Monitor | **DONE** — Backend: `trade_history` SQLite table logs every SELL/HOLD decision with buy_price, sell_price, P&L %, reason, timestamps. `sell_holding()` calculates P&L, logs to trade_history, then deletes from portfolio_holdings. `hold_decision()` logs HOLD with current price snapshot. `get_trade_history()` returns all entries joined with stock_universe (newest first). API routes: `POST /api/portfolio/sell`, `POST /api/portfolio/hold`, `GET /api/portfolio/history`. Frontend: HoldingCard buttons changed from [Remove] to [SELL] [HOLD — I see something different] [Set Alert] [View Details]. `SellDialog` with sell price + reason fields. "Decision Log" section on Portfolio Monitor shows trade history with SELL (red) / HOLD (blue) chips, P&L %, and reason. `handleSell` and `handleHold` handlers with data refresh. |

## P5: Product Vision Audit Gaps

Gaps found by auditing `product_vision.txt` against actual implementation (March 5, 2026).

| # | What | Screen | Detail |
|---|------|--------|--------|
| 27 | ~~Consolidation breakout missing from 8-point score~~ | Signal Scanner | **DONE** — Removed 2 "free" gate points from score formula. Added `(consolidation_months >= 6)` as scoring criterion #6. Score now matches product vision: delivery_high + above_30w + above_52w + golden_cross + rs_positive + consolidation_breakout + sector_peers + (reserved for sector index RS in #28). Score range 0-8 validated. Slot 8 reserved as `+ 0` placeholder for P5 #28. |
| 28 | ~~Sector index outperformance vs Nifty as separate score point from peer count~~ | Signal Scanner | **DONE** — Added `SECTOR_TO_INDEX` mapping (11 yfinance sectors → NSE sector index names). New `_load_sector_index_data()` loads all sector indices from `index_daily`. New `_resample_to_weekly_index_multi()` resamples sector indices to weekly. New `_calc_sector_index_rs()` calculates 4-week RS vs Nifty for each sector index. Score criterion #7 is now "sector index outperforming Nifty" (`sector_index_rs > 0`), criterion #8 is "multiple peers triggered" (`peers_triggered >= 2`) — properly separated. Signal response includes `sector_index_rs` (float) and `sector_index_outperforming` (bool). Frontend shows "Sector index vs Nifty" with RS % detail. |
| 29 | ~~Market leverage elevated not triggering exit signal~~ | Portfolio Monitor | **DONE** — Market leverage computed once before the holdings loop via `_get_market_leverage()`. When `trend_3m == "INCREASING"`, fires exit signal #7 ("Market-wide margin leverage elevated and rising") on every holding. Signal contributes to health bucketing (can push holdings into warning/alert). Only fires when 7+ daily data points exist and leverage is trending up >5%. Currently "ACCUMULATING" (1 data point) — signal will activate automatically as daily accumulation data builds up. Reused pre-computed leverage in response to avoid duplicate DB call. |
| 30 | ~~Briefing sectors missing "stocks triggered per sector"~~ | Weekly Briefing | **DONE** — Added `_YFINANCE_TO_HEATMAP` mapping (11 yfinance sector names → heatmap display names like "Technology" → "IT"). `_build_sector_notes()` now accepts scanner signals, counts triggered stocks per sector using the mapping, and appends "N stocks triggered" to each sector's note. Each sector entry now includes a `triggered` count field. Also updated `_build_top_signals()` to use new `sector_index_outperforming` field instead of old `sector_strong`. Sectors with triggered stocks are prioritized in the "emerging" slot selection. |

---

## GAPS — Missing data or logic

Cross-validated against Gordon's original investment process document (.docx), flowchart, product vision, and databuilder (March 5, 2026).

**1. ~~Market Phase doesn't use all proposed criteria~~ — DONE**
- Gordon says: Market phase should consider Nifty vs MA, A/D ratio, 52W highs vs lows, FII/DII flows
- Product vision proposes: All 4 criteria (lines 173-188)
- ~~Implemented: Only Nifty vs 200-day MA + A/D ratio (`macro.py:162-200`)~~
- ~~Missing: 52W highs vs lows ratio and FII/DII combined flow are NOT part of the market phase calculation~~
- **Fixed:** `_calc_market_phase()` now uses a 4-criterion voting system: (1) Nifty vs 200-day MA, (2) A/D ratio, (3) 52W highs/lows ratio, (4) FII+DII combined flow. Each votes +1 (bullish), -1 (bearish), or 0 (neutral). Score maps to 5 labels: BULLISH (≥3), CAUTIOUSLY BULLISH (2), SIDEWAYS (-1 to 1), CAUTIOUSLY BEARISH (-2), BEARISH (≤-3). All data already existed in `market_depth` and `macro_indicators` caches — just needed to be read. All 5 endpoints pass, frontend builds clean.

**2. MTF (Margin Trading Facility) replaced with proxy**
- Gordon says: "Significant borrowing undertaken by market participants to invest in the markets"
- Databuilder step 22: "Market margin borrowing (MTF) — NSE MTF daily report"
- Implemented: F&O participant OI as proxy (`market_leverage.py`). The actual NSE MTF daily report is NOT fetched.
- Impact: F&O OI is a reasonable proxy but not the exact data Gordon described

**3. ~~"High volume + price DOWN" watchlist exists in backend but not surfaced in frontend~~ — DONE (was already implemented)**
- Gordon says: "high vol + stock down = bad signal"
- Flowchart Phase 1: "Check if high volume + price DOWN = bad signal. Skip or add to 'watch for breakdown' list."
- **Already implemented end-to-end:** Backend `scanner.py:194-223` computes `distribution_watchlist` (stocks with ≥5x volume + price DOWN, up to 20, sorted by volume). API route passes it through. Frontend `SignalScanner.jsx:257-297` renders "Watch for Breakdown" section with warning styling, table showing price, change%, vol vs avg, delivery%, and MA status (below 30W/52W chips). `DistributionRow` component (lines 420-470) with click-to-navigate to deep dive. Section only appears when watchlist has items. Verified: 11 stocks in current week's distribution watchlist.

**4. ~~Business mix change — no UI mechanism for manual flagging~~ — DONE (was already implemented)**
- Gordon says: "change in the business mix to a high growth or a high margin product"
- Product vision: "Needs segment revenue data. Manual check needed."
- **Already implemented end-to-end:** Backend `stock.py:1001` reads flag via `get_stock_flag()`, `stock.py:1049/1071` sets/clears flags in `stock_flags` table. API routes `POST/DELETE /api/stock/{symbol}/flag/business_mix` in `stock.py:21-31`. Frontend `api.js:17-18` has `flagBusinessMix()`/`unflagBusinessMix()`. `StockDeepDive.jsx:357-374` `SetupCard` component detects Business Mix Change setups, shows toggle button to flag/unflag, calls API, and refreshes on success.

**5. ~~Sector cohort analysis (large/mid/small/micro distance from 52W highs)~~ — DONE (was already implemented)**
- Gordon says: "How far are various pockets / cohorts of the market (large, mid, small, micro) from their 52 week highs or lows. Market depth is like a flashlight."
- **Already implemented:** Indian Indices section (`GlobalPulse.jsx:108-135`) shows all 4 cohorts (Nifty 50, Bank Nifty, Midcap, Smallcap) with "From 52W High: X%" color-coded (red >5% below, orange 2-5%, green near high). Market Depth section (`GlobalPulse.jsx:142-163`) shows A/D ratio and 52W highs vs lows counts. Both pieces answer Gordon's cohort flashlight question.

**6. WhatsApp/Email delivery — deferred**
- Product vision line 562: "Delivered via: In-app + WhatsApp message (optional) + Email (optional)"
- Databuilder steps 52-53: Listed but marked "Deferred — distribution channels"
- This was always optional, not core to Gordon's process

---

## NOT GAPS — Correctly handled limitations

- **4 chart patterns** (VCP, Darvas, iH&S, Cup & Handle): Gordon explicitly says this is visual/manual. Product correctly leaves it human.
- **"Operated stock" identification**: Gordon's human judgment. Not automatable.
- **Network checks**: Gordon's personal process. Not automatable.
- **Industry P/E**: Scraped from Screener.in (best available free source). Gordon didn't specify a source.
- **"There is always a bull market somewhere"**: Qualitative insight. Sector heatmap + global indices enable this view.

---

## Summary — 5 actionable gaps (ranked by impact)

1. **Market Phase missing 2 criteria** — 52W H/L ratio and FII/DII flows should inform the phase label
2. **Distribution watchlist not shown in frontend** — backend computes it, frontend ignores it
3. **MTF data uses proxy** — F&O OI instead of actual NSE MTF report
4. **Business mix change has no frontend UI** — backend supports it via flags, no button to use it
5. **WhatsApp/Email** — deferred, low priority

Everything else from Gordon's original investment process document is implemented.

---

## Gaps — Gordon's .docx vs Actual Code

Validated directly against `/Users/sandeepnair/Desktop/2026, 02 - Investment Process.docx` and the codebase (March 5, 2026).

**1. ~~Setup "Balance sheet improvement" — partially detected~~ — DONE**
- [Para 58] Gordon says: "More efficient asset turns or better working capital management. Releases valuable cash and expands ROCE"
- **Fixed:** Added `_check_balance_sheet_improvement()` in `stock.py` — checks 3 signals over 3+ consecutive quarters: (a) asset turnover ratio (revenue/total_assets) trending up, (b) ROCE trending up, (c) cash flow from operations improving. Any one or more triggers detection. Wired into `_detect_setups()` as setup 3b alongside existing Margin Expansion.
- **Asset turnover:** Computed from existing DB data (revenue/total_assets per quarter). Added `asset_turnover` field to quarterly fundamentals response.
- **Cash flow from operations:** Added `cash_flow_operations` column to `quarterly_financials` table (ALTER TABLE on existing DB + schema updated in `scripts/db.py`). Updated `_extract_financials()` in `backfill_financials.py` to pull `Operating Cash Flow` from yfinance `quarterly_cashflow`. Updated INSERT in both backfill + refresh scripts. Existing rows are null — will be populated on next quarterly refresh. Added `cash_flow_operations` field to quarterly fundamentals response.
- All 5 endpoints pass, frontend builds clean.

**2. Market leverage — proxy, not actual data**
- [Para 72] Gordon says: "Significant borrowing undertaken by market participants to invest in the markets"
- Code: `market_leverage.py` uses `nsepython.get_fao_participant_oi()` — F&O participant open interest (retail long contracts) as a proxy.
- What Gordon described: Market-wide margin borrowing — i.e., MTF (Margin Trading Facility) data from the NSE MTF daily report, which shows how much money investors have borrowed from brokers to buy stocks.
- Difference: F&O OI measures derivatives positioning. MTF measures actual borrowed money used to buy stocks in the cash segment. They're related but not the same signal.

---

That's it. Two gaps. Everything else in the document maps to implemented code.

---

## Gap Analysis — Gordon's Answers Summary vs Actual Code

**Fully captured (6/9):**
1. Indian markets only (NSE) — Universe is NSE EQ-series only, no BSE
2. Above 500 Cr market cap — Implemented in config, currently 1,534 stocks
3. Weekly charts — Scanner uses weekly resampling (Friday close), all gates and scoring are weekly
4. Dashboard output — All covered: world, India, sectors, stocks, chart link, fundamentals, AI summary
5. Chart judgment stays human — Two explicit "YOUR JUDGMENT" prompts on Deep Dive page
6. Daily workflow — Global Pulse mirrors his TradingView scan order (world → macro → India → sectors → stocks)

**Partially captured (2/9):**
7. 6-month hold compliance — held_months is tracked and displayed, but there's no warning when selling before 6 months. Could add a simple "This holding is only X months old (6-month minimum)" warning in the sell dialog.
8. BSE — He said NSE/BSE but we only cover NSE. Most large stocks are dual-listed so this is likely fine, but worth mentioning to Gordon.

**Not captured (1/9):**
9. Portfolio size 15-25 stocks — No limit or guidance. He said 15 when aggressive, 25 when diversifying. Could add a warning when exceeding 25 holdings.

**Not in scope (correctly excluded):**
- IRR calculation from contract notes — he does this in his spreadsheet
- Mutual fund international exposure — separate from this tool
- Network/qualitative checks — stays human
- Position sizing — stays human

Will revisit after full product walkthrough is complete.

---

## UI Polish — From Product Walkthrough

1. **Sector heatmap chips missing "1W" label** — The sector chips on Global Pulse show change % but don't indicate it's a 1-week change. User has no way to know the timeframe. Add a label like "1W change" or a subtitle.
