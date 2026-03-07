# InvestScan — Investment Scanner

A tool that automates stock scanning, scoring, and portfolio monitoring for Indian equities. Built for investors who follow a systematic volume-price-delivery screening process.

## What you'll see

This is a working demo with sample data. It shows 5 screens:

1. **Global Pulse** — Market overview: world indices, commodities, macro indicators, Indian indices, sector heatmap, and a market phase indicator (bullish/sideways/bearish)

2. **Signal Scanner** — Stocks that passed the weekly volume + price + delivery filters, sorted by an 8-point score. Click any stock to see the full analysis.

3. **Stock Deep Dive** — Everything about one stock: technical signals, sector context with peers, quarterly fundamentals, setup detection (which of 8 investment setups might explain the move), and an AI-generated summary.

4. **Portfolio Monitor** — Your 15 current holdings grouped by health status: Healthy (no issues), Warning (early exit signals), and Alert (needs review now). Shows sector concentration and market leverage.

5. **Weekly Briefing** — A weekend summary pulling together market, sectors, new signals, and portfolio alerts. Read in 2 minutes and you know the full picture.

## How to run the demo

You need two terminal windows.

**Terminal 1 — Start the backend:**
```
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

**Terminal 2 — Start the frontend:**
```
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** in your browser.

## How to click through the main flow

1. You land on **Global Pulse** — scan the market phase, check indices and sectors
2. Click **Signal Scanner** in the sidebar — see which stocks triggered this week
3. Click the arrow icon on any stock (e.g., ABCL) to open **Stock Deep Dive**
4. Review technicals, fundamentals, detected setups, and the AI summary
5. Click **Portfolio** in the sidebar — see your holdings grouped by health
6. Expand the "ALERT" holding (STU Auto) to see its exit signals
7. Click **Briefing** in the sidebar — read the weekly summary

The whole walkthrough takes about 5 minutes.

## Tech stack

- **Frontend:** React + Vite + Material UI (dark theme)
- **Backend:** FastAPI (Python) serving sample data from JSON files
- **No database, no auth, no external APIs** — this is a demo with sample data

## Troubleshooting

- **Backend won't start?** Make sure Python 3.9+ is installed. Run `pip install -r requirements.txt` first.
- **Frontend won't start?** Make sure Node.js 18+ is installed. Run `npm install` first.
- **Pages show "Failed to load"?** The backend isn't running. Start it first.
- **Port already in use?** Kill the process on port 8000 or 5173 and try again.
