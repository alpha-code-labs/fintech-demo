import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Chip, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Accordion,
  AccordionSummary, AccordionDetails, Divider, Grid
} from '@mui/material';
import { ExpandMore, Storage, Api, Schedule, Code, Layers } from '@mui/icons-material';
import { PageHeader } from '../components/common';

const sectionSx = { mb: 3 };
const tableSx = { '& th': { fontWeight: 700, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.04em', whiteSpace: 'nowrap' }, '& td': { fontSize: '0.8rem' } };
const chipSx = { fontSize: '0.65rem', height: 22, mr: 0.5, mb: 0.5 };

function SectionHeading({ icon: Icon, children }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2, mt: 4 }}>
      {Icon && <Icon sx={{ fontSize: '1.2rem', color: 'primary.main' }} />}
      <Typography variant="h6" sx={{ fontWeight: 700 }}>{children}</Typography>
    </Box>
  );
}

function InfoAccordion({ title, subtitle, defaultExpanded, children }) {
  return (
    <Accordion defaultExpanded={defaultExpanded} sx={{ bgcolor: 'var(--surface-02)', '&:before': { display: 'none' }, border: '1px solid var(--surface-06)', mb: 1 }}>
      <AccordionSummary expandIcon={<ExpandMore />}>
        <Box>
          <Typography sx={{ fontWeight: 600, fontSize: '0.9rem' }}>{title}</Typography>
          {subtitle && <Typography variant="caption" sx={{ color: 'text.secondary' }}>{subtitle}</Typography>}
        </Box>
      </AccordionSummary>
      <AccordionDetails>{children}</AccordionDetails>
    </Accordion>
  );
}

function DataTable({ columns, rows }) {
  return (
    <TableContainer>
      <Table size="small" sx={tableSx}>
        <TableHead>
          <TableRow>
            {columns.map((c) => <TableCell key={c} align={c === columns[0] ? 'left' : 'left'}>{c}</TableCell>)}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={i} sx={{ '&:last-child td': { border: 0 } }}>
              {row.map((cell, j) => (
                <TableCell key={j}>
                  <Typography variant="body2" sx={{ fontSize: '0.8rem', whiteSpace: j === 0 ? 'nowrap' : 'normal' }}>{cell}</Typography>
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

export default function DataBlueprint() {
  return (
    <Box>
      <PageHeader
        title="Data Blueprint"
        subtitle="Complete technical reference — every element, its source, logic, and refresh cycle"
      />

      {/* Architecture Overview */}
      <Card sx={sectionSx}>
        <CardContent>
          <Typography sx={{ fontWeight: 700, fontSize: '0.9rem', mb: 2 }}>Architecture Overview</Typography>
          <Box sx={{ p: 2, borderRadius: 1, bgcolor: 'var(--surface-04)', fontFamily: 'monospace', fontSize: '0.75rem', lineHeight: 1.8, whiteSpace: 'pre', overflowX: 'auto' }}>
{`Data Sources         Backend                        Frontend
-----------         -------                        --------
yfinance      -->   SQLite DB (~99 MB)   -->   FastAPI REST API   -->   React + MUI
nselib              11 tables                  26 endpoints            6 screens
NSE API             689K stock rows            JSON responses          Dark/Light theme
nsepython           live_cache (4h TTL)
CCIL (scrape)
Google News RSS
Gemini 2.0 Flash`}
          </Box>
          <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip label="Stock Universe: 1,534 stocks (>= 500 Cr)" size="small" sx={chipSx} />
            <Chip label="OHLC: 689,224 rows (2 years)" size="small" sx={chipSx} />
            <Chip label="Indices: 14 tracked" size="small" sx={chipSx} />
            <Chip label="Financials: 8,944 quarterly rows" size="small" sx={chipSx} />
          </Box>
        </CardContent>
      </Card>

      {/* Screen 1: Global Pulse */}
      <SectionHeading icon={Layers}>Screen 1: Global Pulse</SectionHeading>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
        API: <code>GET /api/macro</code> | Module: <code>app/calculations/macro.py</code>
      </Typography>

      <InfoAccordion title="Market Phase" subtitle="5-state indicator: BULLISH to BEARISH">
        <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
          Scores 4 criteria from -1 to +1 each, then maps the total (-4 to +4) to a label.
        </Typography>
        <DataTable
          columns={['Criterion', '+1 if', '-1 if', 'Source']}
          rows={[
            ['Nifty vs 200-day MA', '> 3% above', '> 3% below', 'index_daily (yfinance)'],
            ['A/D ratio', '> 1.5', '< 0.7', 'live_cache (nsetools)'],
            ['52W Highs/Lows ratio', '> 2.0', '< 0.5', 'live_cache (nsetools)'],
            ['FII + DII combined', '> 0 Cr', '< -2,000 Cr', 'live_cache (nsepython)'],
          ]}
        />
        <Box sx={{ mt: 2, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          <Chip label=">= 3: BULLISH" size="small" color="success" sx={chipSx} />
          <Chip label="2: CAUTIOUSLY BULLISH" size="small" sx={{ ...chipSx, bgcolor: 'rgba(76,175,80,0.2)' }} />
          <Chip label="-1 to 1: SIDEWAYS" size="small" sx={{ ...chipSx, bgcolor: 'rgba(255,152,0,0.2)' }} />
          <Chip label="-2: CAUTIOUSLY BEARISH" size="small" sx={{ ...chipSx, bgcolor: 'rgba(244,67,54,0.2)' }} />
          <Chip label="<= -3: BEARISH" size="small" color="error" sx={chipSx} />
        </Box>
      </InfoAccordion>

      <InfoAccordion title="World Indices" subtitle="5 global indices from yfinance, 4h cache">
        <DataTable
          columns={['Index', 'Shows', 'Ticker', 'Refresh']}
          rows={[
            ['S&P 500', 'Value + 1D change %', '^GSPC', 'Every 4 hours'],
            ['Nasdaq', 'Value + 1D change %', '^IXIC', 'Every 4 hours'],
            ['FTSE 100', 'Value + 1D change %', '^FTSE', 'Every 4 hours'],
            ['Nikkei 225', 'Value + 1D change %', '^N225', 'Every 4 hours'],
            ['Shanghai', 'Value + 1D change %', '000001.SS', 'Every 4 hours'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Commodities" subtitle="5 commodities from yfinance, 4h cache">
        <DataTable
          columns={['Commodity', 'Shows', 'Ticker', 'Refresh']}
          rows={[
            ['Gold', 'USD price + 1D change %', 'GC=F', 'Every 4 hours'],
            ['Crude Oil', 'USD price + 1D change %', 'CL=F', 'Every 4 hours'],
            ['Silver', 'USD price + 1D change %', 'SI=F', 'Every 4 hours'],
            ['Copper', 'USD price + 1D change %', 'HG=F', 'Every 4 hours'],
            ['Natural Gas', 'USD price + 1D change %', 'NG=F', 'Every 4 hours'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Macro Indicators" subtitle="Yields, FX, flows">
        <DataTable
          columns={['Indicator', 'Shows', 'Source', 'Detail']}
          rows={[
            ['Dollar Index (DXY)', 'Value + 1D change %', 'yfinance', 'Ticker: DX-Y.NYB'],
            ['US 10Y Yield', 'Yield %', 'yfinance', 'Ticker: ^TNX'],
            ['India 10Y Yield', 'Yield %', 'CCIL website', 'HTML scrape with regex on tenorwise yields page'],
            ['INR / USD', 'Exchange rate', 'yfinance', 'Ticker: USDINR=X'],
            ['FII Flow (MTD)', 'Net buying/selling in Cr', 'nsepython', 'nse_fiidii() — latest day net value'],
            ['DII Flow (MTD)', 'Net buying/selling in Cr', 'nsepython', 'nse_fiidii() — latest day net value'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Indian Indices" subtitle="4 indices from index_daily table, daily EOD">
        <DataTable
          columns={['Index', 'Shows', 'Refresh', 'Logic']}
          rows={[
            ['Nifty 50', 'Value, 1D change %, dist from 52W high', 'Daily EOD (4:45 PM IST)', '(close / 52w_high - 1) * 100'],
            ['Bank Nifty', 'Same', 'Same', 'Same'],
            ['Nifty Midcap 100', 'Same', 'Same', 'Same'],
            ['Nifty Smallcap 100', 'Same', 'Same', 'Same'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Market Depth" subtitle="Advancing/declining + 52W highs/lows from nsetools">
        <DataTable
          columns={['Element', 'Shows', 'Source', 'Logic']}
          rows={[
            ['Advancing', 'Stocks that closed up today', 'nsetools', 'NSE market statistics'],
            ['Declining', 'Stocks that closed down today', 'nsetools', 'NSE market statistics'],
            ['A/D Ratio', 'Breadth indicator', 'Computed', 'advancing / declining'],
            ['52W Highs', 'Stocks at 52-week highs', 'nsetools', 'NSE market statistics'],
            ['52W Lows', 'Stocks at 52-week lows', 'nsetools', 'NSE market statistics'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Sector Heatmap" subtitle="10 sectors, sorted strongest first">
        <DataTable
          columns={['Element', 'Logic', 'Source']}
          rows={[
            ['1W Change %', '(friday_close / prev_friday_close - 1) * 100', 'index_daily table'],
            ['RS vs Nifty (4W)', 'sector_4w_return - nifty_4w_return', 'index_daily table'],
            ['Color coding', '> 1% = green (strong), < 0% = red (weak)', 'Computed'],
            ['Sorting', 'By change_pct descending', 'Computed'],
          ]}
        />
        <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          {['IT', 'Pharma', 'Auto', 'FMCG', 'Metal', 'Realty', 'Energy', 'Media', 'PSU', 'Infra'].map(s => (
            <Chip key={s} label={s} size="small" sx={chipSx} />
          ))}
        </Box>
      </InfoAccordion>

      {/* Screen 2: Signal Scanner */}
      <SectionHeading icon={Layers}>Screen 2: Signal Scanner</SectionHeading>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
        API: <code>GET /api/scanner</code> | Module: <code>app/calculations/scanner.py</code> | Optional: <code>?week_ending=YYYY-MM-DD</code>
      </Typography>

      <InfoAccordion title="3 Gates" subtitle="Must pass ALL to appear in results" defaultExpanded>
        <DataTable
          columns={['Gate', 'Threshold', 'Data', 'Logic']}
          rows={[
            ['Volume', '>= 5x 52-week average', 'stock_ohlc (daily -> weekly)', 'Sum Mon-Fri volumes, compare to avg weekly vol over prior 52 weeks'],
            ['Price', '>= 5% weekly change', 'stock_ohlc (weekly resample)', '(friday_close / prev_friday_close - 1) * 100'],
            ['Delivery', '>= 35%', 'stock_ohlc.delivery_pct (NSE)', 'Average delivery % across the week\'s trading days'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="8-Point Scoring" subtitle="Each YES = +1 point, max 8/8" defaultExpanded>
        <DataTable
          columns={['#', 'Criterion', 'Logic', 'Data Source']}
          rows={[
            ['1', 'Delivery >= 35%', 'Weekly avg delivery >= 35', 'stock_ohlc.delivery_pct'],
            ['2', 'Above 30W MA', 'close > SMA(close, 30 weeks)', 'stock_ohlc'],
            ['3', 'Above 52W MA', 'close > SMA(close, 52 weeks)', 'stock_ohlc'],
            ['4', 'Golden cross', '10W MA crossed above 30W or 52W this week', 'stock_ohlc'],
            ['5', 'RS vs Nifty positive', 'stock_4w_return - nifty_4w_return > 0', 'stock_ohlc + index_daily'],
            ['6', 'Consolidation breakout', 'Price within 15% range for 6+ months, now above', 'stock_ohlc'],
            ['7', 'Sector outperforming', 'Sector index 4W return > Nifty 4W return', 'index_daily'],
            ['8', '2+ peers triggered', 'Other same-sector stocks also passed 3 gates', 'Scanner results'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Watch for Breakdown" subtitle="High volume + price DOWN">
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          {'Stocks where weekly volume >= 5x average but price change is negative. Possible distribution (selling).'}
          Shows MA status chips (below 30W / below 52W) for quick assessment.
        </Typography>
      </InfoAccordion>

      <InfoAccordion title="Filters & Sort" subtitle="Client-side filtering on scanner results">
        <DataTable
          columns={['Control', 'Options', 'Default']}
          rows={[
            ['Week ending', 'Last 13 Fridays', 'Latest week'],
            ['Sort by', 'Score, Volume, Price Change, Delivery %', 'Score (descending)'],
            ['Sector filter', 'All + each sector in results', 'All'],
            ['Market cap', 'All, Large (>20K Cr), Mid (5K-20K), Small (<5K)', 'All'],
            ['Min score', 'Any, >= 3 through >= 8', 'Any'],
          ]}
        />
      </InfoAccordion>

      {/* Screen 3: Stock Deep Dive */}
      <SectionHeading icon={Layers}>Screen 3: Stock Deep Dive</SectionHeading>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
        API: <code>GET /api/stock/{'{symbol}'}</code> | Module: <code>app/calculations/stock.py</code> | Optional: <code>?week_ending=YYYY-MM-DD</code>
      </Typography>

      <InfoAccordion title="Technical Signals" subtitle="Calculated from 15 months of daily OHLC data">
        <DataTable
          columns={['Signal', 'Logic', 'Source']}
          rows={[
            ['Volume vs avg', 'weekly_vol / avg_weekly_vol_52w', 'stock_ohlc'],
            ['Delivery %', 'Average delivery for the week', 'stock_ohlc.delivery_pct (NSE)'],
            ['Above 30W MA', 'close > SMA(close, 30 weeks)', 'stock_ohlc'],
            ['Above 52W MA', 'close > SMA(close, 52 weeks)', 'stock_ohlc'],
            ['Golden cross', '10W SMA crossed above 30W or 52W this week', 'stock_ohlc'],
            ['RS vs Nifty (4W)', 'stock_4w_return - nifty_4w_return', 'stock_ohlc + index_daily'],
            ['Consolidation', 'Longest window where (high-low)/low <= 15%. Months = weeks/4.33', 'stock_ohlc'],
            ['Breakout pattern', 'VCP, Darvas Box, Cup & Handle, Inv H&S — algorithmically classified from weekly OHLC data within the consolidation window', '_detect_consolidation_patterns()'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Fundamentals" subtitle="4 quarters of financial data, auto-pulled">
        <DataTable
          columns={['Field', 'Source', 'Refresh']}
          rows={[
            ['Revenue (Cr)', 'quarterly_financials (yfinance)', 'Quarterly (1st of Feb/May/Aug/Nov)'],
            ['Operating margin %', 'operating_income / revenue * 100', 'Same'],
            ['Net Profit (Cr)', 'quarterly_financials.net_income', 'Same'],
            ['EPS', 'quarterly_financials.eps', 'Same'],
            ['Total Debt (Cr)', 'quarterly_financials.total_debt', 'Same'],
            ['ROCE %', 'Basic: operating_income / total_assets * 100. Overridden by Screener.in ROCE when available (24h cache)', 'Computed + Screener.in'],
            ['Promoter Holding %', 'promoter_holding (NSE API via nsepython)', 'Quarterly (2nd of Feb/May/Aug/Nov)'],
            ['P/E', 'yfinance trailingPE', 'On-demand, 24h cache'],
            ['Industry P/E', 'yfinance', 'Not reliably available — may show "--"'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Setup Detection" subtitle="9 setups: 5 from data, 2 from news, 1 from deals, 1 manual">
        <DataTable
          columns={['#', 'Setup', 'Method', 'Source', 'Detail']}
          rows={[
            ['1', 'Earnings Surprise', 'Auto', 'quarterly_financials', 'Net profit up 50%+ YoY, cross-checked with revenue'],
            ['2', 'Debt Reduction', 'Auto', 'quarterly_financials', 'Total debt declining 3+ consecutive quarters'],
            ['3', 'Margin Expansion', 'Auto', 'quarterly_financials', 'Operating margin trending up 3+ quarters'],
            ['4', 'Sector of the Cycle', 'Auto', 'Scanner + index_daily', 'Sector RS positive + 2+ peers triggered same week'],
            ['5', 'Balance Sheet Improvement', 'Auto', 'quarterly_financials', 'ROCE trending up 3+ quarters'],
            ['6', 'Management Change', 'News scan', 'Google News RSS + Gemini LLM', '15 recent headlines classified by AI'],
            ['7', 'Supply Disruption', 'News scan', 'Google News RSS + Gemini LLM', 'Factory shutdowns, sanctions, disasters'],
            ['8', 'Forced Buying/Selling', 'Data + News', 'NSE bulk/block deals + news', 'Index rebalancing, block deals, pledges'],
            ['9', 'Business Mix Change', 'Manual', 'User action', 'System hints (margins up, revenue flat). User confirms via Flag button'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="AI Summary" subtitle="Gemini 2.0 Flash, 24h cache per stock">
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          2-3 sentence factual summary generated from the full stock data. Temperature 0.3 (factual).
          Restates facts — does not give opinions or recommendations. Falls back to "Coming soon" when no API key.
          Env var: <code>GEMINI_API_KEY</code>.
        </Typography>
      </InfoAccordion>

      <InfoAccordion title="Chart Judgment Journal" subtitle="Manual overlay for visual assessment">
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          User records pattern seen (VCP, Darvas Box, Cup & Handle, Inv H&S, Other, None),
          conviction level (High/Medium/Low), and notes. Stored in <code>chart_judgments</code> SQLite table.
          API: <code>GET/POST/DELETE /api/stock/{'{symbol}'}/judgments</code>.
        </Typography>
      </InfoAccordion>

      {/* Screen 4: Portfolio Monitor */}
      <SectionHeading icon={Layers}>Screen 4: Portfolio Monitor</SectionHeading>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
        API: <code>GET /api/portfolio</code> | Module: <code>app/calculations/portfolio.py</code>
      </Typography>

      <InfoAccordion title="Exit Signals" subtitle="6 signals monitored per holding" defaultExpanded>
        <DataTable
          columns={['#', 'Signal', 'Logic', 'Source']}
          rows={[
            ['1', 'Upper wicks (3+ weeks)', '(high - close) / (high - low) > 0.6 for 3+ consecutive weeks', 'stock_ohlc'],
            ['2', 'Below 30W MA', 'current_close < SMA(close, 30 weeks)', 'stock_ohlc'],
            ['3', 'Below 52W MA', 'current_close < SMA(close, 52 weeks)', 'stock_ohlc'],
            ['4', 'Support break', 'current_close < min(weekly close, last 13 weeks)', 'stock_ohlc (weekly resample)'],
            ['5', 'Head & Shoulders', '3-peak reversal pattern from weekly highs', 'stock_ohlc'],
            ['6', 'Bad news + breakdown', 'Negative news (AI classified) + active technical signal', 'Google News RSS + Gemini LLM'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Health Bucketing" subtitle="3 states based on signal count">
        <DataTable
          columns={['Bucket', 'Criteria', 'Action suggested']}
          rows={[
            ['Healthy', '0 exit signals', 'No action needed'],
            ['Warning', '1-2 signals (no MA break, < 3 total)', 'Watch closely'],
            ['Alert', 'MA break (30W or 52W) OR bad news signal OR 3+ signals', 'Review position now'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Holding Actions" subtitle="Write APIs for portfolio management">
        <DataTable
          columns={['Action', 'API', 'Detail']}
          rows={[
            ['Sell', 'POST /api/portfolio/sell', 'Logs to trade_history, removes holding. Compliance warning if < 6 months'],
            ['Hold', 'POST /api/portfolio/hold', 'Records hold decision with reason'],
            ['Add More', 'POST /api/portfolio/add-more', 'Weighted avg: (old_qty * old_price + new_qty * new_price) / (old_qty + new_qty)'],
            ['Remove', 'DELETE /api/portfolio/holdings/{symbol}', 'Removes without logging'],
            ['Add Holding', 'POST /api/portfolio/holdings', 'Adds new holding (symbol, price, date, qty, thesis)'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Market Leverage" subtitle="Market-wide borrowing as risk indicator">
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          Uses F&O participant open interest (client long vs short contracts) as a proxy for margin borrowing.
          Actual NSE MTF (Margin Trading Facility) data is not available programmatically.
          Trend: INCREASING / DECREASING / STABLE based on 3-month slope.
          Stored in <code>daily_accumulation</code> table.
        </Typography>
      </InfoAccordion>

      {/* Screen 5: Weekly Briefing */}
      <SectionHeading icon={Layers}>Screen 5: Weekly Briefing</SectionHeading>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
        API: <code>GET /api/briefing</code> | Module: <code>app/calculations/briefing.py</code>
      </Typography>

      <InfoAccordion title="Briefing Compilation" subtitle="Assembled from all other screens">
        <DataTable
          columns={['Section', 'Source', 'How it\'s built']}
          rows={[
            ['Market phase', 'get_global_pulse()', 'Same label + week-over-week change'],
            ['World narrative', 'Gemini 2.0 Flash', 'AI generates 2-3 sentences from indices + commodities + macro'],
            ['India narrative', 'Gemini 2.0 Flash', 'AI generates 2-3 sentences from Indian indices + sectors + depth'],
            ['Sector notes (5)', 'sector_heatmap + scanner', 'Strongest, weakest, emerging sectors with triggered stock references'],
            ['Top signals (3-4)', 'run_scanner()', 'Highest-scoring stocks with pattern/driver notes'],
            ['Portfolio alerts', 'get_portfolio()', 'Holdings in Alert or Warning state'],
          ]}
        />
        <Typography variant="caption" sx={{ color: 'text.disabled', mt: 1, display: 'block' }}>
          Fallback: When no Gemini API key, returns data-only summaries without narrative prose.
        </Typography>
      </InfoAccordion>

      {/* Screen 6: Reporting */}
      <SectionHeading icon={Layers}>Screen 6: Reporting</SectionHeading>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
        API: <code>GET /api/portfolio</code> (same as Portfolio Monitor) | Module: <code>app/calculations/portfolio.py</code>
      </Typography>

      <InfoAccordion title="Reporting Elements" subtitle="Portfolio overview and compliance">
        <DataTable
          columns={['Element', 'Logic', 'Detail']}
          rows={[
            ['Stocks Held count', 'Count of portfolio_holdings', 'Green if 15-25 (target), amber otherwise'],
            ['Total Invested', 'sum(buy_price * quantity)', 'Across all holdings'],
            ['Current Value', 'sum(current_price * quantity)', 'Latest market close'],
            ['Overall P&L', 'current_value - invested_value', 'Both absolute (Cr/L) and %'],
            ['Sector breakdown', 'Group by stock_universe.sector', 'Chips with sector name + count'],
            ['Holdings table', 'All holdings sorted by days held desc', 'Includes 6M status, P&L, invested value'],
            ['6M Status', 'days_held >= 183 = Complete', 'Compliance tracking for 6-month hold rule'],
          ]}
        />
      </InfoAccordion>

      {/* Data Refresh Schedule */}
      <SectionHeading icon={Schedule}>Data Refresh Schedule</SectionHeading>

      <InfoAccordion title="Daily (Mon-Fri, automated)" subtitle="Scheduled via APScheduler" defaultExpanded>
        <DataTable
          columns={['Time (IST)', 'What', 'Detail']}
          rows={[
            ['4:30 PM', 'Stock OHLC + delivery', 'Appends today\'s data for all stocks -> stock_ohlc'],
            ['4:45 PM', 'Index daily', 'Appends close for all 14 indices -> index_daily'],
            ['5:00 PM', 'Macro refresh', 'World indices, commodities, DXY, yields, FII/DII -> live_cache'],
            ['5:15 PM', 'Bulk/block deals', 'Today\'s deals from NSE -> bulk_block_deals'],
            ['5:30 PM', 'Market depth', 'A/D ratio + 52W H/L snapshot -> daily_accumulation'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Weekly" subtitle="Sunday">
        <DataTable
          columns={['Time', 'What', 'Detail']}
          rows={[
            ['Sunday 10 AM', 'Stock universe refresh', 'Adds new stocks >= 500 Cr, removes delisted'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Quarterly" subtitle="Feb, May, Aug, Nov">
        <DataTable
          columns={['Day', 'What', 'Detail']}
          rows={[
            ['1st @ 6 AM', 'Quarterly financials', 'Revenue, profit, debt, margins for all stocks'],
            ['2nd @ 6 AM', 'Promoter holding', 'Promoter/public/FII/DII % from NSE API'],
            ['3rd @ 6 AM', 'Sector classification', 'Updates sector assignments in stock_universe'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="On-Demand" subtitle="Triggered by user action or page visit">
        <DataTable
          columns={['Trigger', 'What', 'Detail']}
          rows={[
            ['POST /api/macro/refresh', 'All macro fetchers', 'Force-refresh world, commodities, macro, depth'],
            ['Deep Dive visit', 'News setups + AI summary', 'Google News RSS + Gemini LLM. 24h cache per stock'],
            ['Deep Dive visit', 'P/E ratio', 'yfinance trailingPE. 24h in-memory cache'],
          ]}
        />
      </InfoAccordion>

      {/* API Endpoints */}
      <SectionHeading icon={Api}>API Endpoints (26 total)</SectionHeading>

      <InfoAccordion title="Read APIs (12 endpoints)" subtitle="GET requests returning JSON">
        <DataTable
          columns={['Endpoint', 'Returns', 'Caching']}
          rows={[
            ['GET /api/macro', 'Global Pulse (all sections)', 'live_cache 4h for external data'],
            ['GET /api/scanner', 'Scanner results (latest or ?week_ending=)', 'In-memory by week'],
            ['GET /api/stock/{symbol}', 'Full Deep Dive analysis', 'On-the-fly (P/E + news: 24h)'],
            ['GET /api/stock/universe', 'All 1,534 stocks', 'In-memory, refreshed on first call'],
            ['GET /api/stock/{symbol}/judgments', 'Chart judgments', 'Direct DB read'],
            ['GET /api/portfolio', 'Holdings + exit signals', 'Computed on-the-fly'],
            ['GET /api/portfolio/history', 'Trade history', 'Direct DB read'],
            ['GET /api/watchlist', 'Watchlist items', 'Direct DB read'],
            ['GET /api/alerts', 'Price alerts', 'Direct DB read'],
            ['GET /api/briefing', 'Weekly briefing', 'Computed + LLM'],
            ['GET /api/scheduler/status', 'Job status + next run times', 'Live'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Write APIs (14 endpoints)" subtitle="POST/DELETE requests">
        <DataTable
          columns={['Endpoint', 'Action']}
          rows={[
            ['POST /api/macro/refresh', 'Force-refresh all macro data'],
            ['POST /api/portfolio/holdings', 'Add holding (symbol, price, date, qty, thesis)'],
            ['DELETE /api/portfolio/holdings/{symbol}', 'Remove holding'],
            ['POST /api/portfolio/sell', 'Sell holding (logs to trade history)'],
            ['POST /api/portfolio/hold', 'Record hold decision'],
            ['POST /api/portfolio/add-more', 'Add shares (weighted avg)'],
            ['POST /api/stock/{symbol}/flag/business_mix', 'Flag business mix change'],
            ['DELETE /api/stock/{symbol}/flag/business_mix', 'Remove flag'],
            ['POST /api/stock/{symbol}/judgments', 'Save chart judgment'],
            ['DELETE /api/stock/{symbol}/judgments/{id}', 'Delete judgment'],
            ['POST /api/watchlist', 'Add to watchlist'],
            ['DELETE /api/watchlist/{symbol}', 'Remove from watchlist'],
            ['POST /api/alerts', 'Create price alert'],
            ['DELETE /api/alerts/{id}', 'Delete alert'],
          ]}
        />
      </InfoAccordion>

      {/* Database */}
      <SectionHeading icon={Storage}>Database (SQLite, 14 tables)</SectionHeading>

      <InfoAccordion title="Core Data Tables" subtitle="Backfilled from data pipeline" defaultExpanded>
        <DataTable
          columns={['Table', 'Rows', 'Purpose', 'Primary Key']}
          rows={[
            ['stock_universe', '1,534', 'All stocks >= 500 Cr market cap', 'symbol'],
            ['stock_ohlc', '689,224', 'Daily OHLC + delivery (2 years)', '(symbol, date)'],
            ['index_daily', '3,717', 'Daily close for 14 indices', '(index_name, date)'],
            ['quarterly_financials', '8,944', 'Revenue, profit, debt, margins', '(symbol, quarter_end)'],
            ['promoter_holding', '5,964', 'Promoter/public/FII/DII %', '(symbol, quarter_end)'],
            ['bulk_block_deals', 'Variable', 'NSE bulk and block deals', '(date, symbol, ...)'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="Cache & Accumulation Tables" subtitle="External data and trends">
        <DataTable
          columns={['Table', 'Purpose', 'Detail']}
          rows={[
            ['live_cache', 'External API response cache', '5 keys: world_indices, commodities, macro_indicators, market_depth, market_leverage. 4h TTL'],
            ['daily_accumulation', 'Trend data (no backfill)', 'A/D ratio, 52W H/L, FII/DII, market leverage — daily snapshots'],
            ['backfill_progress', 'Data pipeline state', 'Resume capability for initial data load'],
          ]}
        />
      </InfoAccordion>

      <InfoAccordion title="User Data Tables" subtitle="Created by portfolio and stock modules">
        <DataTable
          columns={['Table', 'Purpose', 'Key']}
          rows={[
            ['portfolio_holdings', 'Current stock holdings', 'symbol (UNIQUE)'],
            ['trade_history', 'Buy/sell/add/hold log', 'id (autoincrement)'],
            ['watchlist', 'Watchlisted stocks', 'symbol (UNIQUE)'],
            ['price_alerts', 'Price alerts', 'id (autoincrement)'],
            ['chart_judgments', 'Chart pattern observations', 'id (autoincrement)'],
          ]}
        />
      </InfoAccordion>

      {/* Data Sources */}
      <SectionHeading icon={Code}>Data Sources (8 total)</SectionHeading>

      <Card sx={sectionSx}>
        <CardContent>
          <DataTable
            columns={['Source', 'Provides', 'Access', 'Cost']}
            rows={[
              ['yfinance', 'Stock OHLC, market cap, P/E, financials, world indices, commodities, DXY, yields, INR/USD', 'Python library', 'Free'],
              ['nselib', 'Delivery volume %', 'Python library', 'Free'],
              ['NSE API (direct)', 'Promoter holding', 'HTTP requests', 'Free'],
              ['nsepython', 'FII/DII flows, index data', 'Python library', 'Free'],
              ['nsetools', 'Advancing/declining, 52W highs/lows', 'Python library', 'Free'],
              ['CCIL', 'India 10Y govt bond yield', 'HTML scrape', 'Free'],
              ['Google News RSS', 'News headlines for setup detection', 'RSS feed (15 per stock)', 'Free'],
              ['Gemini 2.0 Flash', 'AI summaries, news classification, briefing narratives', 'REST API', 'Free tier / Pay per use'],
            ]}
          />
        </CardContent>
      </Card>

      {/* Automated vs Human */}
      <SectionHeading icon={Layers}>Automated vs. Human</SectionHeading>

      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%', borderColor: 'rgba(76,175,80,0.2)' }}>
            <CardContent>
              <Typography sx={{ fontWeight: 700, fontSize: '0.85rem', color: 'success.main', mb: 1.5 }}>Fully Automated</Typography>
              {[
                'Macro dashboard (all sections)',
                'Market phase indicator',
                'Volume + price + delivery screening',
                'Moving averages + golden cross',
                'Relative strength calculations',
                'Consolidation + breakout detection',
                'Pattern classification (4 types)',
                '8-point signal scoring',
                'Fundamental data pulls',
                'Setup detection (from numbers)',
                'Exit signal detection',
                'Weekly briefing generation',
                'Portfolio health bucketing',
              ].map((item, i) => (
                <Typography key={i} variant="body2" sx={{ fontSize: '0.8rem', color: 'text.secondary', mb: 0.5, pl: 1.5, position: 'relative', '&::before': { content: '"+"', position: 'absolute', left: 0, color: 'success.main', fontWeight: 700 } }}>
                  {item}
                </Typography>
              ))}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%', borderColor: 'rgba(255,152,0,0.2)' }}>
            <CardContent>
              <Typography sx={{ fontWeight: 700, fontSize: '0.85rem', color: 'warning.main', mb: 1.5 }}>Semi-Automated</Typography>
              {[
                'Setup detection from news (AI classifies headlines)',
                'Head & Shoulders exit pattern (system flags, you confirm)',
                'Business mix change (system hints, you verify segment data)',
                'Sector cycle detection (system spots peers, you assess)',
              ].map((item, i) => (
                <Typography key={i} variant="body2" sx={{ fontSize: '0.8rem', color: 'text.secondary', mb: 0.5, pl: 1.5, position: 'relative', '&::before': { content: '"~"', position: 'absolute', left: 0, color: 'warning.main', fontWeight: 700 } }}>
                  {item}
                </Typography>
              ))}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%', borderColor: 'rgba(79,195,247,0.2)' }}>
            <CardContent>
              <Typography sx={{ fontWeight: 700, fontSize: '0.85rem', color: 'primary.main', mb: 1.5 }}>Stays 100% Human</Typography>
              {[
                'Chart pattern judgment (is it convincing?)',
                'Management quality assessment',
                '"Operated stock" identification',
                'Network / industry contacts',
                'Position sizing decisions',
                'Final buy decisions',
                'Final sell decisions',
              ].map((item, i) => (
                <Typography key={i} variant="body2" sx={{ fontSize: '0.8rem', color: 'text.secondary', mb: 0.5, pl: 1.5, position: 'relative', '&::before': { content: '"-"', position: 'absolute', left: 0, color: 'primary.main', fontWeight: 700 } }}>
                  {item}
                </Typography>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

    </Box>
  );
}
