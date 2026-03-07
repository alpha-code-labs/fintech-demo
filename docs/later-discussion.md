# Later Discussion

## UI Polish — From Product Walkthrough

1. ~~**Sector heatmap chips missing "1W" label**~~ — DONE. Added "1W" label next to change % on each sector chip.
2. ~~**Scanner needs week-ending selector**~~ — DONE. Added a dropdown in the page header showing last 13 Fridays. Selecting a week fetches that week's scanner data. Default shows "Latest week". Filter applies to both signalled stocks and Watch for Breakdown sections.
3. ~~**Deep Dive link needs a label**~~ — DONE. Added "Deep Dive" text label next to the icon in both the main signalled stocks rows and Watch for Breakdown rows.
4. ~~**Delivery % scoring threshold should be 35%, not 50%**~~ — DONE. Changed `DELIVERY_SCORE_PCT` from 50.0 to 35.0 in scanner.py to match the gate threshold.
5. ~~**Show all 8 scoring criteria in expanded stock detail**~~ — DONE. Added "Delivery ≥ 35%" as the first SignalRow in the expanded detail. All 8 scoring criteria now visible together.
6. ~~**Remove "possibly speculative" delivery commentary**~~ — DONE. Removed the hardcoded warning block entirely from the expanded stock detail.
7. ~~**Fix "How stocks appear here" card**~~ — DONE. (a) Changed chip to "Delivery >= 35%". (b) Moved card above the signals table, after sort controls.
8. ~~**Deep Dive price needs a label**~~ — DONE. Added "Week ending [date]" caption below the price. Backend now returns `price_date` from the weekly OHLC data.
9. ~~**Add Chart Judgment Journal below Technical Chart**~~ — DONE. Built ChartJudgmentJournal component with pattern dropdown, conviction toggle, notes field, timestamps. Data persists in `chart_judgments` SQLite table. API: GET/POST/DELETE `/api/stock/{symbol}/judgments`.
10. ~~**Remove YOUR JUDGMENT HERE text from Technical Chart**~~ — DONE. Removed the hardcoded prompt text block. Replaced by Chart Judgment Journal (item 9).
11. ~~**Consolidation Zone — remove padded scale numbers**~~ — DONE. Removed the left and right padded scale numbers. Only the centered "Current: ₹X" label remains.
12. **Consolidation Zone — green breakout area overflows** — DONE. The green zone on the far right of the consolidation visual is extending beyond its designated space. Fix the overflow.
13. ~~**Consolidation Zone — show explanation when absent**~~ — DONE. Shows "No consolidation detected — stock price range exceeded 15% in every 4-week window" when consolidation_months is 0.
14. ~~**Setup Detection header says "8 setups" — should be 9**~~ — DONE. Changed "8 setups" to "9 setups" in the Setup Detection header.
15. ~~**Forced Buying/Selling appears twice**~~ — DONE. Merged into a single card. When news detects but deals don't, the not_detected entry is removed and a single detected entry is created. When both detect, news detail is appended to the deals card.
16. ~~**Remove "YOUR JUDGMENT ON THIS STOCK" card**~~ — DONE. Deleted the entire card from the bottom of Deep Dive.
17. ~~**Remove key_levels chips from AI Summary**~~ — DONE. Removed the 3 duplicate chips from the AI Summary card.
18. ~~**Remove Add to Portfolio, Flag, and Dismiss buttons from Deep Dive**~~ — DONE. Removed all three buttons. Only Add to Watchlist remains.
19. ~~**Move Add to Watchlist button to top**~~ — DONE. Moved to top header next to the price. Bottom action buttons section removed entirely.
20. ~~**Add "Add to Portfolio" button in Watchlist tab**~~ — DONE. Added button in each watchlist row. Opens Add Holding dialog with symbol pre-filled.
21. ~~**Always show all 3 holding buckets on Portfolio Monitor**~~ — DONE. Alert and Warning sections now always visible with empty state messages when no stocks in that bucket.
22. ~~**Remove green "ok" StatusBadge from Healthy holdings**~~ — DONE. Removed the StatusBadge from healthy holding rows.
23. ~~**Add Holding dialog — replace free-text Symbol with searchable dropdown**~~ — DONE. Replaced with MUI Autocomplete backed by `GET /api/stock/universe` (~1,534 stocks). Searchable by name or symbol.
24. ~~**Add Holding dialog — fix Buy Thesis dropdown**~~ — DONE. Added Balance Sheet Improvement and Business Mix Change. Removed "Other". Now 9 setups + "None (skip)".
25. ~~**Add "Add More" button to holding cards**~~ — DONE. Added "Add More" button on Alert/Warning holding cards. Opens MUI dialog (quantity + buy price). Backend computes weighted average: new_avg = (old_qty × old_price + new_qty × new_price) / (old_qty + new_qty), updates quantity and buy_price. Logged to Decision Log as "ADD" entry.
26. ~~**Hold button uses browser prompt instead of modal**~~ — DONE. Replaced native browser `prompt()` with a styled MUI dialog matching Sell and Set Alert. Multiline reason field, Cancel/Confirm buttons.
27. ~~**Deep Dive should use Scanner's selected week**~~ — DONE. When navigating from Scanner to Deep Dive, the selected week is passed as `?week=YYYY-MM-DD` query param. Backend computes technicals as of that date. A blue banner shows "Viewing historical data as of week ending [date] (from Signal Scanner)" with a "View latest data" button. Direct access (no query param) uses latest data as before. Chart Judgment Journal persists across both views (keyed by symbol only).
28. ~~**6-month holding period indicator + sell warning**~~ — DONE. All three holding buckets (Alert, Warning, Healthy) now use the same expandable HoldingCard with full action buttons. Each card shows days held. Holdings >= 183 days show "6-month holding period complete" label. Sell on holdings < 6 months triggers compliance warning dialog. Backend now returns `buy_date` in portfolio API response.
29. ~~**Add Reporting page for portfolio overview**~~ — DONE. New "Reporting" sidebar item below Portfolio (Assessment icon). Shows total stocks held count (15-25 target reference). Summary stat cards: total invested, current value, overall P&L, sector breakdown. Holdings table sorted by days held (descending) with symbol, name, sector, buy date, days held, 6-month status, quantity, buy/current price, P&L (₹ and %), invested value. Rows clickable to Deep Dive. Backend now returns `quantity` in portfolio API response.
30. ~~**Breakout pattern detection in Deep Dive**~~ — DONE. Algorithmic detection of 4 patterns (VCP, Darvas Box, Cup & Handle, Inverted H&S) within the existing consolidation window. `_detect_consolidation_patterns()` in stock.py classifies the consolidation shape from OHLC data. Green pattern chips shown in Technical Chart card. "Breakout Pattern" row added to Technical Signals section. Only fires when consolidation is detected (6+ months); no consolidation = "None detected".



## Gordon's Post-Scanner Workflow

Source: "2026, 02 - Investment Process.docx" (paragraphs referenced below)

### Step 1: Scanner Flags (BUILT)
Volume >= 5x + Price >= 5% + Delivery >= 35% -> stock enters the watchlist.

Gordon's words (para 20): "I typically run screens to filter stocks where weekly volume is 5x annual average and where the price has jumped atleast 5-10% with this volume increase."

### Step 2: Breakout Pattern Check (PARTIALLY BUILT)
Gordon names 4 specific patterns he looks for (para 28):
- **VCP (Volatility Contraction Pattern)** -- he calls it "Minervini Volatility Contraption Pattern" -- NOT built
- **Darvas Box** -- NOT built
- **Inverted Head & Shoulders** -- NOT built
- **Cup & Handle** -- NOT built

We currently detect **consolidation breakout** (months of sideways movement), which is the broader concept Gordon describes (para 24: "Breakouts from long consolidations"). But we don't detect the 4 specific patterns he names.

Gordon's words (para 28): "Literally 99% of all big moves follow some variation or base setup of these patterns."

### Step 3: Other Technical Signals (BUILT)
Gordon names these explicitly:
- **Above 30W and 52W moving averages** (para 32) -- BUILT
- **Golden cross** (para 33) -- BUILT
- **Relative strength vs market** (para 34) -- BUILT

### Step 4: Sentiment / Sector Context (BUILT)
- **Sector relative strength** (para 40) -- BUILT
- **Broader index movement** (para 42) -- BUILT (market phase)
- **Market depth**: advancing vs declining, 52W highs vs lows (para 44) -- BUILT

### Step 5: Fundamental Setups (BUILT)
Gordon names 8 setups explicitly (paras 52-59):

| # | Setup (Gordon's words) | Our Status |
|---|---|---|
| 1 | Business mix change -- "change in the business mix to a high growth or a high margin product" | Manual flag by user (no auto-detection -- needs segment data) |
| 2 | Management change -- "New management drives sentiment change" | BUILT -- Google News RSS + Gemini LLM classification |
| 3 | Sector of the cycle -- sector-wide fundamental drivers | BUILT -- sector RS + peers triggered |
| 4 | Forced buying or selling -- "Index inclusion (forced buying by ETFs) or forced selling" | BUILT -- bulk/block deals from NSE |
| 5 | Sudden and big earnings surprise -- "30-100% in a very short time" | BUILT -- QoQ profit jump detection |
| 6 | Debt reduction -- "Debt is the only real number on a balance sheet" | BUILT -- compares debt across quarters |
| 7 | Balance sheet improvement -- "More efficient asset turns or better working capital management. Releases valuable cash and expands ROCE" | BUILT -- basic ROCE calculation |
| 8 | Supply disruptions -- "supply disruption drives prices higher due to availability issues" | BUILT -- Google News RSS + Gemini LLM classification |

**Status: 8 of 8 built. 6 from financial data, 2 from news (Google News RSS + Gemini LLM).**

### Step 6: Exit Signals (BUILT)
Gordon names these explicitly (paras 67-72):
- **Long upper wicks** on weekly candles for 3-4 weeks (para 67) -- BUILT
- **Head & Shoulder pattern** (para 68) -- BUILT (portfolio.py:640, detects 3-peak pattern from weekly highs)
- **Breaking through long term moving averages** (para 69) -- BUILT (below 30W MA, below 52W MA)
- **Breaking a previous support price** (para 70) -- BUILT (3-month low)
- **Bad news + above signals** (para 71) -- BUILT (portfolio.py:747, Google News RSS + Gemini LLM, only fires when a technical exit signal is already active)
- **Significant borrowing by market participants** (para 72) -- BUILT as proxy (portfolio.py:1141, uses F&O participant open interest instead of actual MTF data)

### Step 7: Human Judgment (NOT BUILT -- BY DESIGN)
From gordons-answers-summary.txt:
- **Chart reading** -- "I look at the chart myself, the scanner just tells me where to look"
- **Management quality** -- qualitative assessment
- **"Operated" stock check** -- suspicious patterns with no news
- **Network/contacts** -- talks to people in the industry
- **Position sizing** -- based on conviction level

Gordon's words (para 28): "Till date I have been looking at this manually -- there is some judgement I exercise here"

---

## Summary of Gaps

| Gap | Source (Gordon's doc) | What's needed |
|---|---|---|
| ~~Breakout patterns: VCP, Darvas Box, Cup & Handle, Inv H&S~~ | Para 28 | ~~DONE — Item 30. Algorithmic detection within consolidation window~~ |
| Market participant borrowing (MTF) | Para 72 | Proxy built (F&O OI), actual NSE MTF report not available programmatically |
| ~~6-month hold rule~~ | gordons-answers-summary.txt | ~~DONE — Item 28. Days held shown on all cards, 6-month label, compliance warning on early sell~~ |
| ~~15-25 stock portfolio limit~~ | gordons-answers-summary.txt | ~~DONE — Item 29. Reporting page shows stock count with 15-25 target visibility~~ |

---

## Cleanup Work for Excel

1. In elements sheet, need to add the new section "Add Chart Judgment Journal" in Deep Dive section.
2. Update "Portfolio Page Logic" sheet in For Gordon.xlsx when all pending changes (items 20-28) are implemented.
