import { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, Chip, Tooltip
} from '@mui/material';
import {
  Public, ShowChart, Inventory2, CurrencyExchange,
  BarChart, GridView
} from '@mui/icons-material';
import { getMacro } from '../services/api';
import {
  PageHeader, MarketPhaseBadge, StatCard, ChangeIndicator,
  SectionTitle, ErrorBanner, HowThisWorks
} from '../components/common';
import { SkeletonPage } from '../components/common/LoadingSkeleton';

// Null-safe formatters for placeholder data
const fmt = (v) => v != null ? v : '--';
const fmtSuffix = (v, s) => v != null ? `${v}${s}` : '--';

export default function GlobalPulse() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    getMacro()
      .then(setData)
      .catch(() => setError('Failed to load market data'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <SkeletonPage />;
  if (error) return <ErrorBanner message={error} onRetry={fetchData} />;
  if (!data) return null;

  return (
    <Box>
      <PageHeader
        title="Global Pulse"
        subtitle="Your daily macro scan — everything on one screen"
        right={
          <Chip
            label={data.date}
            size="small"
            sx={{ fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}
          />
        }
      />

      <HowThisWorks
        title="How This Screen Works"
        sections={[
          {
            heading: 'What this is',
            body: 'Your daily macro scan on one screen. Everything you currently check across multiple TradingView tabs — global indices, commodities, yields, FII/DII flows, Indian indices, sector strength, and market breadth.',
          },
          {
            heading: 'Market Phase',
            body: 'A structured indicator that answers: is the market bullish, sideways, or bearish? The system scores 4 criteria (Nifty vs 200-day MA, advance/decline ratio, 52W highs vs lows, FII+DII flows) and maps the combined score to one of 5 states.',
            chips: ['BULLISH', 'CAUTIOUSLY BULLISH', 'SIDEWAYS', 'CAUTIOUSLY BEARISH', 'BEARISH'],
          },
          {
            heading: 'Sector Relative Strength',
            body: 'Each sector\'s 4-week return minus Nifty\'s 4-week return. A positive number means the sector is outperforming the broader market — buyers are prioritizing it. Sorted strongest to weakest.',
          },
          {
            heading: 'Market Depth',
            body: 'The index is a mask — market depth is the flashlight. Advancing vs declining stocks tells you breadth. 52W highs vs lows tells you where momentum is concentrated. These numbers reveal what the headline index hides.',
          },
          {
            heading: 'Data Sources',
            bullets: [
              'World indices and commodities: yfinance (refreshed every 4 hours)',
              'Indian indices: NSE (daily end-of-day)',
              'DXY, US 10Y, INR/USD: yfinance | India 10Y: CCIL | FII/DII: NSE',
              'Market depth (A/D, 52W H/L): nsetools (refreshed every 4 hours)',
            ],
          },
          {
            heading: 'Automated',
            body: '100%. No human input needed. All data is auto-refreshed during market hours and end-of-day.',
          },
        ]}
      />

      {/* Market Phase Banner */}
      <Box sx={{ mb: 3 }}>
        <MarketPhaseBadge label={data.market_phase.label} reason={data.market_phase.reason} />
      </Box>

      {/* World Indices + Commodities */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <SectionTitle icon={Public}>World Indices</SectionTitle>
          <Grid container spacing={1.5}>
            {data.world_indices.map((idx) => (
              <Grid size={{ xs: 6, sm: 4 }} key={idx.name}>
                <IndexCard name={idx.name} value={idx.value} change={idx.change_pct} />
              </Grid>
            ))}
          </Grid>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <SectionTitle icon={Inventory2}>Commodities</SectionTitle>
          <Grid container spacing={1.5}>
            {data.commodities.map((c) => (
              <Grid size={{ xs: 6, sm: 4 }} key={c.name}>
                <IndexCard name={c.name} value={c.value} change={c.change_pct} prefix={c.unit} />
              </Grid>
            ))}
          </Grid>
        </Grid>
      </Grid>

      {/* Macro Indicators */}
      <Box sx={{ mb: 3 }}>
        <SectionTitle icon={CurrencyExchange}>Macro Indicators</SectionTitle>
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <StatCard label="Dollar Index (DXY)" value={fmt(data.macro_indicators.dxy.value)} change={data.macro_indicators.dxy.change_pct} />
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <StatCard label="US 10Y Yield" value={fmtSuffix(data.macro_indicators.us_10y.value, '%')} />
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <StatCard label="India 10Y Yield" value={fmtSuffix(data.macro_indicators.india_10y.value, '%')} />
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <StatCard label="INR / USD" value={fmt(data.macro_indicators.inr_usd.value)} prefix={data.macro_indicators.inr_usd.value != null ? '₹' : ''} />
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <FlowCard label="FII Flow (MTD)" value={data.macro_indicators.fii_flow_mtd} />
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <FlowCard label="DII Flow (MTD)" value={data.macro_indicators.dii_flow_mtd} />
          </Grid>
        </Grid>
      </Box>

      {/* Indian Indices */}
      <Box sx={{ mb: 3 }}>
        <SectionTitle icon={ShowChart}>Indian Indices</SectionTitle>
        <Grid container spacing={1.5}>
          {data.indian_indices.map((idx) => (
            <Grid size={{ xs: 12, sm: 6, md: 3 }} key={idx.name}>
              <Card sx={{ height: '100%' }}>
                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                  <Typography variant="subtitle2" sx={{ mb: 0.5, fontSize: '0.7rem' }}>{idx.name}</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mb: 0.5 }}>
                    <Typography variant="h5" sx={{ fontVariantNumeric: 'tabular-nums', fontSize: { xs: '1rem', sm: '1.25rem' } }}>
                      {idx.value != null ? idx.value.toLocaleString('en-IN') : '--'}
                    </Typography>
                    {idx.change_pct != null && <ChangeIndicator value={idx.change_pct} />}
                  </Box>
                  <Tooltip title="Distance from 52-week high" arrow>
                    <Typography
                      variant="caption"
                      sx={{
                        color: idx.dist_from_52w_high < -5 ? 'error.main' : idx.dist_from_52w_high < -2 ? 'warning.main' : 'success.main',
                        fontWeight: 500,
                        cursor: 'help',
                      }}
                    >
                      From 52W High: {idx.dist_from_52w_high}%
                    </Typography>
                  </Tooltip>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Market Depth + Sector Heatmap */}
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 4 }}>
          <SectionTitle icon={BarChart}>Market Depth</SectionTitle>
          <Card>
            <CardContent>
              {data.market_depth.advancing != null ? (
                <>
                  <DepthRow label="Advancing" value={data.market_depth.advancing} total={data.market_depth.advancing + data.market_depth.declining} color="#4caf50" />
                  <DepthRow label="Declining" value={data.market_depth.declining} total={data.market_depth.advancing + data.market_depth.declining} color="#f44336" />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2, pt: 2, borderTop: '1px solid var(--surface-06)' }}>
                    <Box>
                      <Typography variant="caption">A/D Ratio</Typography>
                      <Typography variant="h6" sx={{ color: data.market_depth.ad_ratio > 1 ? 'success.main' : 'error.main' }}>
                        {data.market_depth.ad_ratio}
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                      <Typography variant="caption">52W Highs vs Lows</Typography>
                      <Typography variant="h6" sx={{ color: 'success.main' }}>
                        {data.market_depth.highs_52w} / {data.market_depth.lows_52w}
                      </Typography>
                    </Box>
                  </Box>
                </>
              ) : (
                <Box sx={{ py: 3, textAlign: 'center' }}>
                  <Typography variant="body2" sx={{ color: 'text.disabled' }}>Coming soon</Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 8 }}>
          <SectionTitle icon={GridView}>Sector Heatmap</SectionTitle>
          <Card>
            <CardContent>
              <Grid container spacing={1}>
                {[...data.sector_heatmap]
                  .sort((a, b) => b.change_pct - a.change_pct)
                  .map((s) => (
                    <Grid size={{ xs: 6, sm: 4 }} key={s.name}>
                      <SectorChip sector={s} />
                    </Grid>
                  ))}
              </Grid>
              <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid var(--surface-06)' }}>
                <Typography variant="subtitle2" sx={{ mb: 1, fontSize: '0.7rem' }}>
                  Sector Relative Strength vs Nifty (4-week)
                </Typography>
                {[...data.sector_heatmap]
                  .sort((a, b) => b.rs_vs_nifty_4w - a.rs_vs_nifty_4w)
                  .map((s, i) => (
                    <Box key={s.name} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.4, gap: 1 }}>
                      <Typography variant="body2" sx={{ color: 'text.secondary', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {i + 1}. {s.name}
                      </Typography>
                      <ChangeIndicator value={s.rs_vs_nifty_4w} fontSize="0.8rem" />
                    </Box>
                  ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

function IndexCard({ name, value, change, prefix = '' }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
        <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', mb: 0.3, fontWeight: 500 }}>
          {name}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <Typography sx={{ fontWeight: 600, fontSize: '0.95rem', fontVariantNumeric: 'tabular-nums', color: value == null ? 'text.disabled' : 'text.primary' }}>
            {value != null ? `${prefix}${typeof value === 'number' ? value.toLocaleString('en-IN') : value}` : '--'}
          </Typography>
          {change != null ? <ChangeIndicator value={change} fontSize="0.8rem" /> : <Typography sx={{ fontSize: '0.8rem', color: 'text.disabled' }}>--</Typography>}
        </Box>
      </CardContent>
    </Card>
  );
}

function FlowCard({ label, value }) {
  if (value == null) {
    return (
      <Card sx={{ height: '100%' }}>
        <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
          <Typography variant="subtitle2" sx={{ mb: 1, fontSize: '0.7rem' }}>{label}</Typography>
          <Typography variant="h5" sx={{ color: 'text.disabled' }}>--</Typography>
        </CardContent>
      </Card>
    );
  }
  const isPositive = value > 0;
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Typography variant="subtitle2" sx={{ mb: 1, fontSize: '0.7rem' }}>{label}</Typography>
        <Typography
          variant="h5"
          sx={{
            fontVariantNumeric: 'tabular-nums',
            color: isPositive ? 'success.main' : 'error.main',
          }}
        >
          {isPositive ? '+' : ''}₹{Math.abs(value).toLocaleString('en-IN')} Cr
        </Typography>
      </CardContent>
    </Card>
  );
}

function DepthRow({ label, value, total, color }) {
  const pct = (value / total) * 100;
  return (
    <Box sx={{ mb: 1.5 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
        <Typography variant="body2">{label}</Typography>
        <Typography variant="body2" sx={{ fontWeight: 600, color }}>{value}</Typography>
      </Box>
      <Box sx={{ width: '100%', height: 6, borderRadius: 3, bgcolor: 'var(--surface-06)' }}>
        <Box sx={{ width: `${pct}%`, height: '100%', borderRadius: 3, bgcolor: color, transition: 'width 0.5s ease' }} />
      </Box>
    </Box>
  );
}

function SectorChip({ sector }) {
  const isStrong = sector.change_pct > 1;
  const isWeak = sector.change_pct < 0;
  const bgColor = isStrong ? 'rgba(76,175,80,0.12)' : isWeak ? 'rgba(244,67,54,0.08)' : 'var(--surface-04)';
  const borderColor = isStrong ? 'rgba(76,175,80,0.25)' : isWeak ? 'rgba(244,67,54,0.2)' : 'var(--surface-08)';

  return (
    <Box
      sx={{
        p: 1.5, borderRadius: 2, bgcolor: bgColor, border: `1px solid ${borderColor}`,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        transition: 'all 0.2s',
        '&:hover': { transform: 'translateY(-1px)', boxShadow: '0 2px 8px rgba(0,0,0,0.3)' },
      }}
    >
      <Typography sx={{ fontSize: '0.8rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, minWidth: 0 }}>{sector.name}</Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary' }}>1W</Typography>
        <ChangeIndicator value={sector.change_pct} fontSize="0.8rem" />
      </Box>
    </Box>
  );
}
