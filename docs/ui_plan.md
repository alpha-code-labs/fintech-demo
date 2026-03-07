# UI Plan — InvestScan

## Persona

**Gordon Dsouza** — Experienced investor, 25%+ annual returns.
- Non-technical. Judges by feel: "does this look real? does it make sense?"
- Currently uses TradingView, Screener.in, Google, Excel across multiple tabs
- Wants one place to see everything, but decisions stay with him
- Checks macro daily, scans weekly, monitors portfolio ongoing

## Top 3 User Journeys

### Journey 1: Weekly Scan → Deep Dive → Watchlist
1. Open app → land on Global Pulse (market context)
2. Navigate to Signal Scanner → see 23 stocks triggered this week
3. Sort by score, click top stock (ABCL, 8/8)
4. Review deep dive: technicals, fundamentals, setups, AI summary
5. Click "Add to Watchlist" or "Add to Portfolio"

### Journey 2: Portfolio Monitoring → Exit Decision
1. Open app → navigate to Portfolio Monitor
2. See 15 holdings grouped: Healthy / Warning / Alert
3. Notice STU Auto in ALERT with 5 exit signals
4. Click to expand — see all signals, decide to sell or hold
5. Check portfolio health summary (sector concentration, leverage)

### Journey 3: Weekend Review
1. Open Weekly Briefing on Saturday
2. Read market summary: world → India → sectors → signals → alerts
3. Click through to top signals or portfolio alerts
4. Done in 5 minutes — full picture of the week

## Navigation Structure

Persistent left sidebar (desktop) / bottom nav (mobile):
1. **Global Pulse** — `/` — Daily macro dashboard
2. **Signal Scanner** — `/scanner` — Weekly stock scan results
3. **Stock Deep Dive** — `/stock/:symbol` — Per-stock analysis (accessed via scanner click)
4. **Portfolio** — `/portfolio` — Holdings + exit signals
5. **Weekly Briefing** — `/briefing` — Weekend summary

## Screen List (MVP)

| # | Screen | Route | Purpose |
|---|--------|-------|---------|
| 1 | Global Pulse | `/` | Market phase + indices + commodities + macro + sectors |
| 2 | Signal Scanner | `/scanner` | Triggered stocks table with scores + expandable details |
| 3 | Stock Deep Dive | `/stock/:symbol` | Chart area + technicals + fundamentals + setups + AI summary |
| 4 | Portfolio Monitor | `/portfolio` | Holdings by health status + exit signals + portfolio health |
| 5 | Weekly Briefing | `/briefing` | Narrative summary with links to signals + alerts |

## Component Inventory

### Layout
- `Sidebar` — nav with 5 items, branding, active state
- `Layout` — sidebar + main content wrapper
- `PageHeader` — title + subtitle + date/meta
- `NotificationToast` — success/error/info toasts (Snackbar)

### Data Display
- `StatCard` — single metric with label, value, change%, trend arrow
- `IndexRow` — name + value + change% with color coding
- `SectorHeatmapBar` — colored bar for sector performance
- `DataTable` — sortable table with expandable rows
- `StockRow` — scanner result row (expandable to show signals)
- `HoldingCard` — portfolio holding with status badge + signals
- `FundamentalsTable` — quarterly comparison table
- `SetupBadge` — detected/not-detected setup indicator
- `ScoreBadge` — circular score display (e.g., 8/8)
- `MarketPhaseBadge` — BULLISH/SIDEWAYS/BEARISH indicator
- `SignalChip` — YES/NO signal indicator with icon

### Feedback & States
- `SkeletonCard` — loading placeholder for cards
- `SkeletonTable` — loading placeholder for tables
- `EmptyState` — illustration + message for empty lists
- `ErrorBanner` — retry-able error display
- `SuccessToast` — action confirmation

### Interactive
- `SortControls` — sort dropdown for tables
- `FilterChips` — sector/score filters
- `ActionButtons` — Add to Watchlist / Portfolio / Dismiss

## Sample Data Requirements

All data exists in `backend/data/dummy/`. Key realistic elements:
- 6 stocks in scanner (scores 3-8, different sectors)
- 15 portfolio holdings (11 healthy, 2 warning, 1 alert)
- Macro data with real index names and plausible values
- 3 quarters of fundamental data for ABCL
- 4 detected setups, 4 not-detected for ABCL
- Weekly briefing with narrative text
- Sector heatmap with 9 sectors

## Design System Tokens

### Colors
- Background: `#0a0e17` (body), `#111827` (cards)
- Card border: `rgba(255,255,255,0.08)`
- Primary: `#4fc3f7` (actions, links, active nav)
- Success/Green: `#4caf50` (positive change, healthy)
- Warning/Orange: `#ff9800` (watch status, caution)
- Error/Red: `#f44336` (alert status, negative change)
- Text primary: `#ffffff`
- Text secondary: `rgba(255,255,255,0.7)`
- Text muted: `rgba(255,255,255,0.5)`

### Typography
- Font: Inter, Roboto, sans-serif
- Page title: 24px, weight 600
- Section title: 18px, weight 600
- Body: 14px, weight 400
- Caption/label: 12px, weight 500, uppercase for labels
- Numbers/data: 14px, monospace feel (tabular nums)

### Spacing
- Page padding: 24px
- Section gap: 24px
- Card padding: 20px
- Card gap: 16px
- Inline gap: 8-12px

### Components
- Card radius: 12px
- Badge radius: 6px
- Button radius: 8px
- Transition: 200ms ease

## Build Order

1. Design system (tokens + reusable components)
2. Global Pulse (most visual, sets the tone)
3. Signal Scanner (core workflow — table with expandable rows)
4. Stock Deep Dive (most complex — multiple sections)
5. Portfolio Monitor (grouped holdings + signals)
6. Weekly Briefing (narrative layout)
7. Polish pass (states, responsiveness, transitions)
8. Documentation (walkthrough, screen map, copy source)
