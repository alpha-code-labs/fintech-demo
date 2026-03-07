# UI Assumptions

Assumptions made where the product vision was unclear or silent.

| # | What was unclear | Assumption | Why | How to change later |
|---|-----------------|------------|-----|-------------------|
| 1 | No landing page described — vision jumps straight to 5 screens | Skip landing page. Global Pulse IS the landing page. Gordon knows what this is — he doesn't need a marketing page. | Gordon is the only user for this demo. A landing page would slow him down. | Add a `/welcome` route later if needed for external audiences. |
| 2 | Chart on Stock Deep Dive says "TradingView chart" but no TradingView integration specified | Show a placeholder chart area with a "Chart loads here — TradingView integration planned" note, plus display the key levels and consolidation range as data. | TradingView embed requires API keys and licensing. Demo shouldn't block on this. | Swap placeholder with TradingView widget or lightweight chart library. |
| 3 | "Add to Watchlist" vs "Add to Portfolio" — no watchlist screen exists | Keep the buttons but show a success toast. No separate watchlist screen for MVP. | Vision only defines 5 screens. Watchlist is implied but not specified. | Add a `/watchlist` screen when Gordon confirms he wants it. |
| 4 | Scanner shows "23 stocks triggered" but dummy data only has 6 | Show the 6 stocks. Header says "23 triggered" (matching the JSON) but table shows 6 visible rows with a note "showing top signals". | 6 stocks is enough to demonstrate the UI. Full 23 would be repetitive for a demo. | Add more dummy stocks to scanner.json if needed. |
| 5 | Mobile layout not mentioned anywhere | Build responsive: sidebar collapses to bottom nav on mobile. | Financial dashboards are desktop-first but Gordon might check on phone. | Adjust breakpoints based on Gordon's actual device usage. |
| 6 | No authentication or user concept | No login. App loads directly into Global Pulse as "demo mode". | This is a demo for one person (Gordon). Auth would add friction. | Add auth when moving to real users. |
| 7 | Color coding for change percentages not specified | Green for positive, red for negative, white/gray for zero. Standard financial convention. | Every financial platform uses this convention. Gordon expects it. | Adjust colors if Gordon has different preferences. |
| 8 | "Dismiss" and "Flag for Later" buttons on Stock Deep Dive — no persistence described | Buttons show success toast but don't persist state. | Demo mode — no backend persistence needed to demonstrate the concept. | Wire to backend when real data flow is built. |
| 9 | Weekly Briefing delivery channels (WhatsApp, Email) mentioned but not in scope | Show "Delivered via" options as display-only badges, not functional. | Demo scope is the web app. Notification channels come later. | Integrate WhatsApp/Email when backend notification service is built. |
| 10 | Sector heatmap described as colored blocks but no specific visualization | Use colored cards/chips with sector name + % change. Color intensity maps to performance. | Simple, clean, works at any screen size. Heatmap grids can be hard to read on mobile. | Upgrade to treemap visualization if Gordon prefers. |
