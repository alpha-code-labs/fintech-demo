# Demo Build for Gordon — Step-by-Step Plan

## Objective

Create a standalone demo version of InvestScan for Gordon to validate. Self-contained with dummy data, no backend dependency, hosted on Azure. Each screen includes a "How this works" section explaining the logic using Gordon's own words from the Investment Process doc.

---

## ~~Step 1: Create Demo Project~~ — DONE

- ~~Copy the entire project folder to a new location (e.g., `investscan-demo/`)~~
- ~~Remove `.git` and initialise a fresh Git repo~~
- ~~Create a new GitHub repo~~ — https://github.com/alpha-code-labs/fintech-demo.git
- ~~Push initial commit~~

## ~~Step 2: Strip Backend — Switch to Static Dummy Data~~ — DONE

- ~~Frontend will import JSON files directly (no API calls)~~
- ~~Create `frontend/src/data/` folder with curated dummy JSON files:~~
  - ~~`macro.json` — Global Pulse data~~
  - ~~`scanner.json` — Signal Scanner results~~
  - ~~`portfolio.json` — Portfolio holdings with exit signals~~
  - ~~`briefing.json` — Weekly Briefing content~~
  - ~~`stocks/` folder — One JSON per stock for Deep Dive~~
- ~~Update `api.js` to return dummy data from local imports instead of axios calls~~

## ~~Step 3: Curate Demo Stock Universe (8-10 Stocks)~~ — DONE

10 real Indian stocks selected across different sectors:

| Stock | Sector | Purpose in Demo |
|---|---|---|
| PERSISTENT | IT | Scanner signal — 8/8 score, VCP pattern, golden cross |
| AUROPHARMA | Pharma | Scanner signal — Cup & Handle, earnings surprise |
| HDFCBANK | Banking | Portfolio healthy — 220 days held, 6-month complete |
| TATAMOTORS | Auto | Portfolio alert — below 30W MA, 5 exit signals |
| TITAN | Consumer Cyclical | Portfolio warning — 3 weeks upper wicks |
| HINDALCO | Metal | Scanner signal — Darvas Box, sector cycle play |
| IRCON | Infra | Portfolio healthy — 45 days held, recently added |
| DEEPAKNTR | Chemical | Scanner signal — Inv H&S, sector recovery |
| ONGC | Energy | Portfolio alert + Watch for Breakdown |
| HINDUNILVR | FMCG | Portfolio healthy — golden cross, steady compounder |

Each stock's dummy data crafted to demonstrate specific features.

## ~~Step 4: Build Dummy Data Files~~ — DONE

All JSON files created with curated data:

### macro.json (Global Pulse)
- Indian indices with realistic values
- Sector heatmap with mix of positive/negative sectors
- World indices and commodities populated
- Market phase showing a clear state (e.g., BULLISH)
- Market depth with advancing/declining ratios
- FII/DII flows

### scanner.json (Signal Scanner)
- 6 stocks passing all 3 gates (volume >= 5x, price >= 5%, delivery >= 35%)
- Varying scores (3/8 to 8/8) to show scoring spread
- 1 Watch for Breakdown candidate (ONGC)
- 4 stocks with detected breakout patterns (VCP, Cup & Handle, Darvas Box, Inv H&S)

### stocks/*.json (Deep Dive)
- 10 JSON files — one per demo stock
- Technical: mix of above/below MAs, golden cross on PERSISTENT and HINDUNILVR
- Consolidation: 4 stocks with consolidation + pattern classification
- Fundamentals: 4 quarterly financials each, promoter holding, ROCE
- Setups: spread across all 9 setup types
- Sector context: peers triggered for IT, Pharma, Metal, Chemical
- AI summary: pre-written for each stock

### portfolio.json (Portfolio)
- 10 holdings: alert (2), warning (2), healthy (6)
- Mix of days held: IRCON 45d, HDFCBANK 220d+
- Exit signals: upper wicks, below MAs, support break, bad news
- buy_date, quantity, buy_thesis, setup_review on all holdings
- Sector concentration across 10 sectors
- Market leverage with INCREASING trend (62 data points)
- Total holdings: 18 (within 15-25 range)

### briefing.json (Weekly Briefing)
- Full world and India narrative paragraphs
- 5 sector notes referencing demo stocks
- 4 top signals with pattern breakout notes
- 3 portfolio alerts (2 alert, 1 warning)

## Step 5: "How This Works" Sections

Add an expandable/collapsible section on each page explaining the logic. References Gordon's Investment Process doc where applicable.

**Layout and placement: TBD — to be discussed.**

Content per page:

### Global Pulse
- What each section tracks and why
- Market phase logic (Nifty vs 200-day MA + A/D ratio)
- How sector RS is calculated (4-week return vs Nifty)
- Source of each data point (yfinance, NSE, CCIL)

### Signal Scanner
- The 3 gates: volume >= 5x, price >= 5%, delivery >= 35%
- Gordon's words: "I typically run screens to filter stocks where weekly volume is 5x annual average..."
- 8-point scoring breakdown with what each point means
- Watch for Breakdown logic
- Week-ending selector purpose

### Stock Deep Dive
- Technical signals: what each row means and thresholds
- Consolidation detection: 6+ months within 15% band
- Breakout patterns: how VCP, Darvas Box, Cup & Handle, Inv H&S are detected algorithmically
- Gordon's words: "Literally 99% of all big moves follow some variation or base setup of these patterns"
- Setup detection: all 9 setups with data sources
- Chart Judgment Journal: manual overlay for Gordon's visual assessment

### Portfolio Monitor
- Exit signal logic: upper wicks, MA breaks, support break, bad news, H&S pattern
- Gordon's words from paras 67-72
- Health bucketing: how alert/warning/healthy is determined
- 6-month holding period compliance
- Market leverage proxy explanation
- Sell/Hold/Add More workflow

### Reporting
- 15-25 stock target reference
- Gordon's words: "Portfolio: 15-25 stocks (15 when aggressive, 25 when diversifying)"
- Days held tracking and 6-month compliance
- P&L calculations

### Weekly Briefing
- How the briefing is compiled (macro + scanner + portfolio data)
- LLM integration for narrative generation

## Step 6: Host on Azure

- Configure Azure Static Web Apps for the demo frontend
- Add `staticwebapp.config.json` for SPA routing
- Deploy from the new GitHub repo
- Share URL with Gordon

## Step 7: Review Checklist Before Sharing

- [ ] Every page loads with no errors or empty states
- [ ] All 10 demo stocks accessible from scanner and deep dive
- [ ] Portfolio shows all 3 buckets populated
- [ ] Reporting page shows holdings table
- [ ] "How this works" sections are accurate and reference Gordon's doc
- [ ] Dark and light mode both work
- [ ] Mobile layout is functional
- [ ] No references to localhost, debug info, or placeholder text
