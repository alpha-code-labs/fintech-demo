# Data Sources by Screen

| Screen | Element | Data Source |
|--------|---------|-------------|
| Global Pulse | S&P 500, Nasdaq, FTSE, Nikkei, Shanghai | yfinance (^GSPC, ^IXIC, ^FTSE, ^N225, 000001.SS) |
| Global Pulse | Gold, Crude, Silver, Copper, Natural Gas | yfinance (GC=F, CL=F, SI=F, HG=F, NG=F) |
| Global Pulse | Dollar Index (DXY) | yfinance (DX-Y.NYB) |
| Global Pulse | US 10Y Yield | FRED API (series: DGS10). Backup: yfinance ^TNX |
| Global Pulse | India 10Y Yield | jugaad-data (RBI). Backup: scrape Investing.com |
| Global Pulse | INR/USD | yfinance (INR=X) |
| Global Pulse | FII/DII Flows | nsepython — nse_fiidii(). Backup: nselib |
| Global Pulse | Nifty 50, Bank Nifty, Midcap, Smallcap | jugaad-data — index_df() |
| Global Pulse | Sector indices (IT, Pharma, Auto, etc.) | jugaad-data — index_df() per sector |
| Global Pulse | Advance/Decline ratio | nsetools — get_advances_declines(). Backup: NseIndiaApi |
| Global Pulse | 52W Highs vs Lows count | nsetools — get_52_week_high(), get_52_week_low() |
| Global Pulse | Sector heatmap (% change + RS) | Calculated from sector index data |
| Global Pulse | Market Phase indicator | Calculated from indices + A/D + FII/DII |
| Signal Scanner | Stock universe (all >500 Cr) | NSE equity list CSV + yfinance for market cap |
| Signal Scanner | Weekly OHLC prices | jugaad-data — stock_df(). Backup: yfinance |
| Signal Scanner | Traded volume | jugaad-data — stock_df() |
| Signal Scanner | Delivery volume + delivery % | jugaad-data — stock_df(). Backup: NSE bhavcopy CSV, nselib |
| Signal Scanner | Volume spike (5x avg) | Calculated from 52 weeks of volume data |
| Signal Scanner | Moving averages (10W, 30W, 52W) | Calculated from weekly closing prices |
| Signal Scanner | Golden crossover detection | Calculated from MAs |
| Signal Scanner | Relative strength vs Nifty | Calculated (4-week stock return vs Nifty return) |
| Signal Scanner | Consolidation detection (6+ months) | Calculated from price range analysis |
| Signal Scanner | Signal score (8-point) | Calculated from all above signals |
| Stock Deep Dive | Chart (weekly candles + MAs + volume) | TradingView free widget embed |
| Stock Deep Dive | Technical signals summary | Same calculations as Scanner |
| Stock Deep Dive | Sector RS vs Nifty | Calculated from sector index data |
| Stock Deep Dive | Peers triggered this week | Cross-reference from Scanner results |
| Stock Deep Dive | Revenue, Net Profit, EPS, Operating Margin | yfinance — quarterly_income_stmt. Backup: Screener.in scrape |
| Stock Deep Dive | Total Debt | yfinance — balance_sheet. Backup: Screener.in scrape |
| Stock Deep Dive | ROCE | Calculated from financials. Backup: Screener.in scrape |
| Stock Deep Dive | Promoter Holding | NSE API via nsepython. Backup: Screener.in |
| Stock Deep Dive | P/E (stock) | yfinance — info["trailingPE"] |
| Stock Deep Dive | Industry P/E | Screener.in scrape. Backup: NSE quote page |
| Stock Deep Dive | Sector classification | NSE equity list CSV (industry column) |
| Stock Deep Dive | Setup: Earnings surprise | Calculated (quarterly profit YoY/QoQ comparison) |
| Stock Deep Dive | Setup: Debt reduction | Calculated (total debt trend over 4-6 quarters) |
| Stock Deep Dive | Setup: Margin expansion | Calculated (operating margin trend) |
| Stock Deep Dive | Setup: Sector of the cycle | Calculated (multiple peers triggering in same week) |
| Stock Deep Dive | Setup: Business mix change | Cannot auto-detect — manual check on Screener.in |
| Stock Deep Dive | Setup: Management change | News scan via LLM (Gemini/Claude) |
| Stock Deep Dive | Setup: Forced buying/selling | NSE bulk/block deal data + index rebalancing announcements |
| Stock Deep Dive | Setup: Supply disruption | News scan via LLM (Gemini/Claude) |
| Stock Deep Dive | AI Summary | LLM API (Gemini Flash or Claude) |
| Portfolio Monitor | Holdings list + buy price + current price | User-entered + live price from yfinance/jugaad-data |
| Portfolio Monitor | P&L calculation | Calculated (current price vs buy price) |
| Portfolio Monitor | Exit: Upper wicks (consecutive weeks) | Calculated from weekly OHLC (High - Close vs range) |
| Portfolio Monitor | Exit: Price below 30W MA | Calculated (same MA data as Scanner) |
| Portfolio Monitor | Exit: Price below 52W MA | Calculated (same MA data as Scanner) |
| Portfolio Monitor | Exit: Support level break | Calculated from historical swing lows |
| Portfolio Monitor | Exit: Head & Shoulders pattern | Semi-auto flag from price data, human confirms |
| Portfolio Monitor | Exit: Bad news + technical breakdown | News scan via LLM + technical checks |
| Portfolio Monitor | Sector concentration | Calculated from holdings + sector classification |
| Portfolio Monitor | Market margin borrowing | NSE MTF daily report scrape + aggregation |
| Weekly Briefing | Market phase + change from last week | Calculated from Screen 1 data |
| Weekly Briefing | World summary paragraph | LLM API (Gemini Flash or Claude) |
| Weekly Briefing | India summary paragraph | LLM API (Gemini Flash or Claude) |
| Weekly Briefing | Sector highlights | Calculated from Screen 1 sector data |
| Weekly Briefing | Top signals list | From Screen 2 Scanner results |
| Weekly Briefing | Portfolio alerts | From Screen 4 exit signal detection |
| Weekly Briefing | WhatsApp delivery | WhatsApp Cloud API (already built) |
| Weekly Briefing | Email delivery | Email service (SendGrid / SES) |
