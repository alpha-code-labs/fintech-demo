import { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, Chip, Button,
  Table, TableBody, TableCell, TableHead, TableRow, Divider,
  FormControl, InputLabel, Select, MenuItem, TextField, IconButton,
  ToggleButton, ToggleButtonGroup
} from '@mui/material';
import {
  ShowChart, Insights, Groups, BarChart, AutoAwesome,
  Bookmark,
  CheckCircle, Cancel, HelpOutline, Delete, NoteAlt
} from '@mui/icons-material';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useSnackbar } from 'notistack';
import { getStock, flagBusinessMix, unflagBusinessMix, addToWatchlist, getJudgments, addJudgment, deleteJudgment } from '../services/api';
import {
  PageHeader, ScoreBadge, ChangeIndicator, SectionTitle,
  ErrorBanner, HowThisWorks
} from '../components/common';
import { SkeletonPage } from '../components/common/LoadingSkeleton';

export default function StockDeepDive() {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const weekEnding = searchParams.get('week') || null;
  const { enqueueSnackbar } = useSnackbar();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    getStock(symbol, weekEnding)
      .then(setData)
      .catch(() => setError(`Failed to load data for ${symbol}`))
      .finally(() => setLoading(false));
  }, [symbol, weekEnding]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <SkeletonPage />;
  if (error) return <ErrorBanner message={error} onRetry={fetchData} />;
  if (!data) return null;


  return (
    <Box>
      {weekEnding && (
        <Box sx={{ mb: 2, p: 1.5, borderRadius: 1, bgcolor: 'rgba(79,195,247,0.08)', border: '1px solid rgba(79,195,247,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="body2" sx={{ color: 'primary.main', fontWeight: 500 }}>
            Viewing historical data as of week ending {weekEnding} (from Signal Scanner)
          </Typography>
          <Button size="small" variant="outlined" onClick={() => navigate(`/stock/${symbol}`)} sx={{ textTransform: 'none', fontSize: '0.75rem' }}>
            View latest data
          </Button>
        </Box>
      )}
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 3, flexWrap: 'wrap', gap: { xs: 1.5, md: 2 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 1, md: 2 } }}>
          <ScoreBadge score={data.score} size="large" />
          <Box>
            <Typography variant="h4" sx={{ fontSize: { xs: '1.3rem', sm: '2.125rem' } }}>{data.name}</Typography>
            <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5, flexWrap: 'wrap' }}>
              <Chip label={data.symbol} size="small" sx={{ fontWeight: 600 }} />
              <Chip label={data.sector} size="small" variant="outlined" sx={{ borderColor: 'var(--surface-15)' }} />
              {data.market_cap != null && <Chip label={`₹${data.market_cap.toLocaleString()} Cr`} size="small" variant="outlined" sx={{ borderColor: 'var(--surface-15)', display: { xs: 'none', sm: 'inline-flex' } }} />}
            </Box>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: { xs: 1.5, md: 2 }, flexDirection: { xs: 'row-reverse', sm: 'row' }, width: { xs: '100%', sm: 'auto' }, justifyContent: { xs: 'flex-end', sm: 'flex-start' } }}>
          <Button variant="contained" size="small" startIcon={<Bookmark />} onClick={() => {
            addToWatchlist({ symbol: data.symbol })
              .then(() => enqueueSnackbar(`${data.name} added to watchlist`, { variant: 'success' }))
              .catch((err) => {
                const msg = err.response?.data?.detail || 'Failed to add to watchlist';
                enqueueSnackbar(msg, { variant: 'warning' });
              });
          }} sx={{ textTransform: 'none', whiteSpace: 'nowrap', fontSize: { xs: '0.7rem', sm: '0.8125rem' } }}>
            Watchlist
          </Button>
          <Box sx={{ textAlign: 'right' }}>
            <Typography variant="h4" sx={{ fontVariantNumeric: 'tabular-nums', fontSize: { xs: '1.3rem', sm: '2.125rem' } }}>₹{data.price}</Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              {data.price_date ? `Week ending ${data.price_date}` : 'Last weekly close'}
            </Typography>
          </Box>
        </Box>
      </Box>

      <HowThisWorks
        title="How This Screen Works"
        sections={[
          {
            heading: 'What this is',
            body: 'Everything you normally pull up across TradingView, Screener.in, and Google — in one place. The system assembles the technical signals, sector context, fundamental data, and setup detection for a single stock.',
          },
          {
            heading: 'Technical Signals',
            body: 'Moving averages (30W, 52W), golden cross, relative strength vs Nifty, and consolidation breakout detection. These are calculated from 15 months of daily OHLC data.',
          },
          {
            heading: 'Consolidation & Breakout Patterns',
            body: 'The system detects when a stock has been trading within a 15% price range for 6+ months. When it breaks above that range, it\'s flagged as a consolidation breakout. The system also algorithmically classifies the pattern shape into VCP, Darvas Box, Cup & Handle, or Inverted Head & Shoulders.',
          },
          {
            heading: 'Chart Judgment Journal',
            body: 'Pattern detection is algorithmic — but your visual assessment matters. The journal lets you record what pattern you see, your conviction level, and notes. This is the manual overlay where your judgment is captured.',
          },
          {
            heading: 'Fundamentals',
            body: 'Last 4 quarters of financial data (revenue, margins, profit, debt, ROCE, promoter holding) auto-pulled from exchange filings. Quarter labels use Indian FY format. P/E from market data.',
          },
          {
            heading: 'Setup Detection (9 setups)',
            body: 'The system checks which of the 9 high-probability setups might explain this stock\'s move. 5 are detected purely from financial data, 2 from news headlines (classified by AI), 1 from exchange deal data, and 1 requires your manual confirmation (business mix change).',
            chips: ['Earnings Surprise', 'Debt Reduction', 'Margin Expansion', 'Sector of the Cycle', 'Balance Sheet', 'Management Change', 'Supply Disruption', 'Forced Buying/Selling', 'Business Mix Change'],
          },
          {
            heading: 'AI Summary',
            body: 'A 2-3 sentence factual summary generated by AI (Gemini 2.0 Flash) that pulls together the technical, fundamental, and sector data. It restates facts — it does not give opinions or recommendations.',
          },
          {
            heading: 'What stays human',
            body: 'Chart pattern judgment (is the breakout convincing?), management quality assessment, whether the stock is "operated", network checks, and the final buy decision.',
          },
        ]}
      />

      {/* Chart + Key Levels */}
      <Card sx={{ mb: 3, borderColor: 'rgba(79,195,247,0.15)' }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1, mb: 2 }}>
            <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>Technical Chart</Typography>
            <Button
              variant="outlined"
              size="small"
              startIcon={<ShowChart />}
              href={`https://www.tradingview.com/chart/?symbol=NSE:${data.symbol}`}
              target="_blank"
              rel="noopener noreferrer"
              sx={{ textTransform: 'none', fontSize: '0.8rem' }}
            >
              Open in TradingView
            </Button>
          </Box>
          {data.technical.consolidation_months > 0 && data.technical.consolidation_range ? (
            <ConsolidationZone
              low={data.technical.consolidation_range[0]}
              high={data.technical.consolidation_range[1]}
              months={data.technical.consolidation_months}
              currentPrice={data.price}
              breakoutLevel={data.technical.breakout_level}
            />
          ) : (
            <Box sx={{ mt: 2, p: 1.5, borderRadius: 1, bgcolor: 'var(--surface-02)', border: '1px solid var(--surface-06)' }}>
              <Typography variant="subtitle2" sx={{ fontSize: '0.75rem', mb: 0.5 }}>Consolidation Zone</Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                No consolidation detected — stock price range exceeded 15% in every 4-week window
              </Typography>
            </Box>
          )}
          <Box sx={{ display: 'flex', gap: 1, mt: 1.5, flexWrap: 'wrap' }}>
            {data.key_levels && Object.entries(data.key_levels).filter(([, val]) => val != null).map(([key, val]) => (
              <Chip key={key} label={`${key.replace(/_/g, ' ')}: ₹${val}`} size="small" variant="outlined" sx={{ fontSize: '0.7rem', borderColor: 'rgba(79,195,247,0.3)', color: 'primary.main' }} />
            ))}
          </Box>
          {data.technical.detected_patterns && data.technical.detected_patterns.length > 0 && (
            <Box sx={{ display: 'flex', gap: 1, mt: 1.5, flexWrap: 'wrap', alignItems: 'center' }}>
              <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', fontWeight: 600 }}>Pattern detected:</Typography>
              {data.technical.detected_patterns.map((p) => (
                <Chip key={p} label={p} size="small" sx={{ fontSize: '0.7rem', height: 22, bgcolor: 'rgba(76,175,80,0.15)', color: 'success.main', fontWeight: 600 }} />
              ))}
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Chart Judgment Journal */}
      <ChartJudgmentJournal symbol={data.symbol} />

      <Grid container spacing={3}>
        {/* Technical Signals */}
        <Grid size={{ xs: 12, md: 6 }}>
          <SectionTitle icon={Insights}>Technical Signals</SectionTitle>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                <TechRow label="Volume this week" value={`${data.technical.vol_vs_avg}x average`} highlight />
                <TechRow label="Delivery %" value={data.technical.delivery_pct != null ? `${data.technical.delivery_pct}%` : '--'} color={data.technical.delivery_pct == null ? 'text.disabled' : data.technical.delivery_pct >= 60 ? 'success.main' : 'warning.main'} />
                <Divider sx={{ borderColor: 'var(--surface-04)' }} />
                <TechRow label="Above 30W MA" value={data.technical.above_30w_ma ? `YES (MA at ₹${data.technical.ma_30w})` : 'NO'} ok={data.technical.above_30w_ma} />
                <TechRow label="Above 52W MA" value={data.technical.above_52w_ma ? `YES (MA at ₹${data.technical.ma_52w})` : 'NO'} ok={data.technical.above_52w_ma} />
                <TechRow label="Golden Cross" value={data.technical.golden_cross || 'No'} ok={!!data.technical.golden_cross} />
                <TechRow label="RS vs Nifty (4W)" value={`${data.technical.rs_vs_nifty_4w > 0 ? '+' : ''}${data.technical.rs_vs_nifty_4w}%`} ok={data.technical.rs_vs_nifty_4w > 0} />
                <Divider sx={{ borderColor: 'var(--surface-04)' }} />
                <TechRow label="Consolidation" value={data.technical.consolidation_months ? `${data.technical.consolidation_months} months (₹${data.technical.consolidation_range[0]}–${data.technical.consolidation_range[1]})` : 'None detected'} />
                {data.technical.breakout_level != null && <TechRow label="Breakout above" value={`₹${data.technical.breakout_level}`} color="primary.main" />}
                <TechRow label="Breakout Pattern" value={data.technical.detected_patterns?.length > 0 ? data.technical.detected_patterns.join(', ') : 'None detected'} ok={data.technical.detected_patterns?.length > 0} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Sector Context */}
        <Grid size={{ xs: 12, md: 6 }}>
          <SectionTitle icon={Groups}>Sector Context</SectionTitle>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="body2">{data.sector} sector RS vs Nifty (4W)</Typography>
                <ChangeIndicator value={data.sector_context.sector_rs_vs_nifty_4w} />
              </Box>
              <Typography variant="subtitle2" sx={{ fontSize: '0.7rem', mb: 1 }}>
                Peers also triggered this week
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Stock</TableCell>
                    <TableCell align="right">Change</TableCell>
                    <TableCell align="right">Volume</TableCell>
                    <TableCell align="center">Score</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.sector_context.peers_triggered.map((peer) => (
                    <TableRow
                      key={peer.symbol}
                      hover
                      sx={{ cursor: 'pointer', '&:last-child td': { border: 0 } }}
                      onClick={() => navigate(`/stock/${peer.symbol}`)}
                    >
                      <TableCell>
                        <Typography sx={{ fontSize: '0.85rem', fontWeight: 500 }}>{peer.name}</Typography>
                      </TableCell>
                      <TableCell align="right"><ChangeIndicator value={peer.change_pct} /></TableCell>
                      <TableCell align="right">
                        <Typography sx={{ fontVariantNumeric: 'tabular-nums', fontSize: '0.85rem' }}>{peer.vol_vs_avg}x</Typography>
                      </TableCell>
                      <TableCell align="center"><ScoreBadge score={peer.score} size="small" /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Box sx={{ mt: 1.5, p: 1, borderRadius: 1, bgcolor: 'rgba(76,175,80,0.06)', border: '1px solid rgba(76,175,80,0.15)' }}>
                <Typography variant="caption" sx={{ color: 'success.main' }}>
                  {data.sector_context.peers_triggered.length} peers triggered — possible sector momentum
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Fundamentals */}
        <Grid size={{ xs: 12 }}>
          <SectionTitle icon={BarChart}>Fundamentals (auto-pulled quarterly data)</SectionTitle>
          <Card>
            <CardContent>
              <Box sx={{ overflowX: 'auto' }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Metric</TableCell>
                      {data.fundamentals.quarters.map((q) => (
                        <TableCell key={q.label} align="right">{q.label}</TableCell>
                      ))}
                      <TableCell align="right">YoY Change</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <FundRow label="Revenue (Cr)" field="revenue" quarters={data.fundamentals.quarters} prefix="₹" />
                    <FundRow label="Operating Margin" field="operating_margin" quarters={data.fundamentals.quarters} suffix="%" />
                    <FundRow label="Net Profit (Cr)" field="net_profit" quarters={data.fundamentals.quarters} prefix="₹" />
                    <FundRow label="EPS" field="eps" quarters={data.fundamentals.quarters} prefix="₹" />
                    <FundRow label="Total Debt (Cr)" field="total_debt" quarters={data.fundamentals.quarters} prefix="₹" invertColor />
                    <FundRow label="ROCE" field="roce" quarters={data.fundamentals.quarters} suffix="%" />
                    <FundRow label="Promoter Holding" field="promoter_holding" quarters={data.fundamentals.quarters} suffix="%" />
                  </TableBody>
                </Table>
              </Box>
              <Box sx={{ display: 'flex', gap: { xs: 2, md: 3 }, mt: 2, pt: 2, borderTop: '1px solid var(--surface-06)', flexWrap: 'wrap' }}>
                <Box>
                  <Typography variant="caption">P/E</Typography>
                  <Typography variant="h6" sx={{ fontVariantNumeric: 'tabular-nums', color: data.fundamentals.pe != null ? 'text.primary' : 'text.disabled' }}>
                    {data.fundamentals.pe != null ? `${data.fundamentals.pe}x` : '--'}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption">Industry P/E</Typography>
                  <Typography variant="h6" sx={{ fontVariantNumeric: 'tabular-nums', color: 'text.secondary' }}>
                    {data.fundamentals.industry_pe != null ? `${data.fundamentals.industry_pe}x` : '--'}
                  </Typography>
                </Box>
                {data.fundamentals.pe != null && data.fundamentals.industry_pe != null && data.fundamentals.pe < data.fundamentals.industry_pe && (
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Chip label="Below industry P/E" size="small" sx={{ bgcolor: 'rgba(76,175,80,0.12)', color: 'success.main', fontWeight: 500 }} />
                  </Box>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Setup Detection */}
        <Grid size={{ xs: 12 }}>
          <SectionTitle icon={AutoAwesome}>Setup Detection</SectionTitle>
          <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
            Which of the 9 setups might explain this move?
          </Typography>
          <Grid container spacing={2}>
            {data.setups.detected.map((s) => (
              <Grid size={{ xs: 12, sm: 6 }} key={s.setup}>
                <SetupCard setup={s} detected symbol={data.symbol} onToggleFlag={fetchData} enqueueSnackbar={enqueueSnackbar} />
              </Grid>
            ))}
            {data.setups.not_detected.map((s) => (
              <Grid size={{ xs: 12, sm: 6 }} key={s.setup}>
                <SetupCard setup={s} detected={false} symbol={data.symbol} onToggleFlag={fetchData} enqueueSnackbar={enqueueSnackbar} />
              </Grid>
            ))}
          </Grid>
        </Grid>

        {/* AI Summary */}
        <Grid size={{ xs: 12 }}>
          <SectionTitle icon={AutoAwesome}>AI Summary</SectionTitle>
          <Card sx={{ borderColor: 'rgba(79,195,247,0.15)' }}>
            <CardContent>
              {data.ai_summary ? (
                <>
                  <Typography variant="body1" sx={{ lineHeight: 1.7, fontStyle: 'italic', color: 'text.secondary' }}>
                    "{data.ai_summary}"
                  </Typography>
                  <Divider sx={{ my: 2, borderColor: 'var(--surface-06)' }} />
                  <Typography variant="caption" sx={{ color: 'text.disabled' }}>
                    This summary is generated by AI from the data above. It restates facts — it does not give opinions or recommendations.
                  </Typography>
                </>
              ) : (
                <Box sx={{ py: 2, textAlign: 'center' }}>
                  <Typography variant="body2" sx={{ color: 'text.disabled' }}>Coming soon — AI summary will be available in a future update</Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>


    </Box>
  );
}

function TechRow({ label, value, ok, color, highlight }) {
  let valueColor = color || 'text.primary';
  if (ok === true) valueColor = 'success.main';
  if (ok === false) valueColor = 'text.secondary';

  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <Typography variant="body2" sx={{ color: 'text.secondary' }}>{label}</Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        {ok !== undefined && (
          ok ? <CheckCircle sx={{ fontSize: '0.9rem', color: 'success.main' }} /> :
               <Cancel sx={{ fontSize: '0.9rem', color: 'var(--muted-20)' }} />
        )}
        <Typography sx={{ fontWeight: highlight ? 700 : 500, color: valueColor, fontSize: '0.85rem', fontVariantNumeric: 'tabular-nums' }}>
          {value}
        </Typography>
      </Box>
    </Box>
  );
}

function FundRow({ label, field, quarters, prefix = '', suffix = '', invertColor = false }) {
  const first = quarters[0]?.[field];
  const last = quarters[quarters.length - 1]?.[field];
  const yoy = first && last ? ((first - last) / Math.abs(last) * 100) : null;

  return (
    <TableRow sx={{ '&:last-child td': { border: 0 } }}>
      <TableCell>
        <Typography variant="body2">{label}</Typography>
      </TableCell>
      {quarters.map((q) => (
        <TableCell key={q.label} align="right">
          <Typography sx={{ fontVariantNumeric: 'tabular-nums', fontSize: '0.85rem' }}>
            {prefix}{q[field]}{suffix}
          </Typography>
        </TableCell>
      ))}
      <TableCell align="right">
        {yoy !== null && (
          <ChangeIndicator
            value={invertColor ? -yoy : yoy}
            suffix="%"
            fontSize="0.85rem"
          />
        )}
      </TableCell>
    </TableRow>
  );
}

function SetupCard({ setup, detected, symbol, onToggleFlag, enqueueSnackbar }) {
  const sourceConfig = {
    auto: { label: 'AUTO-DETECTED', color: '#4caf50', icon: CheckCircle },
    news: { label: 'FROM NEWS SCAN', color: '#4fc3f7', icon: HelpOutline },
    data: { label: 'FROM DATA', color: '#ff9800', icon: HelpOutline },
    manual: { label: 'MANUAL CHECK', color: 'var(--muted-40)', icon: HelpOutline },
  };
  const config = sourceConfig[setup.source] || sourceConfig.manual;
  const isBusinessMix = setup.setup === 'Business Mix Change';

  const handleToggle = () => {
    const action = detected
      ? unflagBusinessMix(symbol)
      : flagBusinessMix(symbol, 'Business mix change confirmed by user after reviewing Screener.in segment data.');
    action
      .then(() => {
        enqueueSnackbar(detected ? 'Business mix flag removed' : 'Business mix change flagged', { variant: 'success' });
        onToggleFlag();
      })
      .catch(() => enqueueSnackbar('Failed to update flag', { variant: 'error' }));
  };

  return (
    <Card sx={{
      opacity: detected ? 1 : 0.6,
      borderColor: detected ? `${config.color}30` : 'var(--surface-06)',
    }}>
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          {detected
            ? <CheckCircle sx={{ fontSize: '1rem', color: 'success.main' }} />
            : <Cancel sx={{ fontSize: '1rem', color: 'var(--muted-20)' }} />
          }
          <Typography sx={{ fontWeight: 600, fontSize: '0.9rem', flex: 1 }}>{setup.setup}</Typography>
          {isBusinessMix && (
            <Button
              size="small"
              variant={detected ? 'outlined' : 'contained'}
              color={detected ? 'error' : 'warning'}
              onClick={handleToggle}
              sx={{ fontSize: '0.6rem', minWidth: 0, px: 1, py: 0.25, textTransform: 'none' }}
            >
              {detected ? 'Unflag' : 'Flag'}
            </Button>
          )}
        </Box>
        <Typography variant="body2" sx={{ color: 'text.secondary', mb: 1, lineHeight: 1.5 }}>
          {setup.detail}
        </Typography>
        <Chip
          label={config.label}
          size="small"
          sx={{ fontSize: '0.6rem', fontWeight: 600, color: config.color, bgcolor: `${config.color}12`, height: 20 }}
        />
      </CardContent>
    </Card>
  );
}

function ConsolidationZone({ low, high, months, currentPrice, breakoutLevel }) {
  // Show range with 10% padding on each side for visual context
  const range = high - low;
  const padded_low = low - range * 0.3;
  const padded_high = high + range * 0.3;
  const total = padded_high - padded_low;

  const zoneLeft = ((low - padded_low) / total) * 100;
  const zoneWidth = ((high - low) / total) * 100;
  const pricePos = Math.min(100, Math.max(0, ((currentPrice - padded_low) / total) * 100));

  const aboveZone = currentPrice > high;
  const belowZone = currentPrice < low;
  const inZone = !aboveZone && !belowZone;

  return (
    <Box sx={{ mt: 2, p: 2, borderRadius: 1, bgcolor: 'var(--surface-02)', border: '1px solid var(--surface-06)' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="subtitle2" sx={{ fontSize: '0.75rem' }}>
            Consolidation Zone
          </Typography>
          <Chip
            label={`${months} months`}
            size="small"
            sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'rgba(79,195,247,0.1)', color: 'primary.main' }}
          />
        </Box>
        <Chip
          label={aboveZone ? 'BREAKOUT' : belowZone ? 'BREAKDOWN' : 'IN RANGE'}
          size="small"
          sx={{
            height: 20, fontSize: '0.6rem', fontWeight: 700,
            bgcolor: aboveZone ? 'rgba(76,175,80,0.15)' : belowZone ? 'rgba(244,67,54,0.15)' : 'rgba(255,152,0,0.15)',
            color: aboveZone ? 'success.main' : belowZone ? 'error.main' : 'warning.main',
          }}
        />
      </Box>

      {/* Price range bar */}
      <Box sx={{ position: 'relative', height: 32, mb: 1, overflow: 'hidden' }}>
        {/* Background track */}
        <Box sx={{ position: 'absolute', top: 12, left: 0, right: 0, height: 8, borderRadius: 1, bgcolor: 'var(--surface-04)' }} />

        {/* Consolidation zone (shaded area) */}
        <Box sx={{
          position: 'absolute', top: 4, height: 24, borderRadius: 1,
          left: `${zoneLeft}%`, width: `${zoneWidth}%`,
          bgcolor: 'rgba(79,195,247,0.12)',
          border: '1px solid rgba(79,195,247,0.3)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {zoneWidth > 15 && (
            <Typography sx={{ fontSize: '0.55rem', color: 'primary.main', opacity: 0.7 }}>
              ₹{low}–{high}
            </Typography>
          )}
        </Box>

        {/* Breakout level line */}
        {breakoutLevel && (
          <Box sx={{
            position: 'absolute', top: 2, bottom: 2,
            left: `${Math.min(100, Math.max(0, ((breakoutLevel - padded_low) / total) * 100))}%`,
            width: 1, bgcolor: 'rgba(76,175,80,0.5)',
            '&::after': {
              content: '"▲"', position: 'absolute', top: -10, left: -4,
              fontSize: '0.5rem', color: 'success.main',
            },
          }} />
        )}

        {/* Current price marker */}
        <Box sx={{
          position: 'absolute', top: 0,
          left: `${pricePos}%`, transform: 'translateX(-50%)',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
        }}>
          <Box sx={{
            width: 10, height: 10, borderRadius: '50%',
            bgcolor: aboveZone ? 'success.main' : belowZone ? 'error.main' : 'warning.main',
            border: '2px solid',
            borderColor: aboveZone ? 'success.dark' : belowZone ? 'error.dark' : 'warning.dark',
            zIndex: 1,
          }} />
          <Box sx={{ width: 2, height: 14, bgcolor: aboveZone ? 'success.main' : belowZone ? 'error.main' : 'warning.main', opacity: 0.6 }} />
        </Box>
      </Box>

      {/* Labels */}
      <Box sx={{ display: 'flex', justifyContent: 'center', px: 0.5 }}>
        <Typography sx={{ fontSize: '0.65rem', color: 'text.secondary', fontWeight: 500 }}>
          Current: ₹{currentPrice}
          {aboveZone && ` (+${((currentPrice / high - 1) * 100).toFixed(1)}% above range)`}
          {belowZone && ` (${((currentPrice / low - 1) * 100).toFixed(1)}% below range)`}
        </Typography>
      </Box>
    </Box>
  );
}

const PATTERN_OPTIONS = ['VCP', 'Darvas Box', 'Cup & Handle', 'Inv H&S', 'Other', 'None'];
const CONVICTION_OPTIONS = ['High', 'Medium', 'Low'];

function ChartJudgmentJournal({ symbol }) {
  const { enqueueSnackbar } = useSnackbar();
  const [judgments, setJudgments] = useState([]);
  const [pattern, setPattern] = useState('');
  const [conviction, setConviction] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchJudgments = useCallback(() => {
    getJudgments(symbol).then(setJudgments).catch(() => {});
  }, [symbol]);

  useEffect(() => { fetchJudgments(); }, [fetchJudgments]);

  const handleSave = () => {
    if (!pattern || !conviction) {
      enqueueSnackbar('Please select both pattern and conviction', { variant: 'warning' });
      return;
    }
    setSaving(true);
    addJudgment(symbol, { pattern, conviction, notes })
      .then((entry) => {
        setJudgments((prev) => [entry, ...prev]);
        setPattern('');
        setConviction('');
        setNotes('');
        enqueueSnackbar('Judgment saved', { variant: 'success' });
      })
      .catch(() => enqueueSnackbar('Failed to save judgment', { variant: 'error' }))
      .finally(() => setSaving(false));
  };

  const handleDelete = (id) => {
    deleteJudgment(symbol, id)
      .then(() => {
        setJudgments((prev) => prev.filter((j) => j.id !== id));
        enqueueSnackbar('Judgment removed', { variant: 'success' });
      })
      .catch(() => enqueueSnackbar('Failed to delete', { variant: 'error' }));
  };

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <NoteAlt sx={{ fontSize: '1rem', color: 'primary.main' }} />
          <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>Chart Judgment Journal</Typography>
        </Box>

        {/* Entry form */}
        <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'flex-start', mb: 2, flexDirection: { xs: 'column', sm: 'row' } }}>
          <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'flex-start', width: { xs: '100%', sm: 'auto' } }}>
            <FormControl size="small" sx={{ minWidth: { xs: '100%', sm: 150 } }}>
              <InputLabel sx={{ fontSize: '0.75rem' }}>Pattern Seen</InputLabel>
              <Select
                value={pattern}
                label="Pattern Seen"
                onChange={(e) => setPattern(e.target.value)}
                sx={{ fontSize: '0.85rem' }}
              >
                {PATTERN_OPTIONS.map((p) => <MenuItem key={p} value={p}>{p}</MenuItem>)}
              </Select>
            </FormControl>

            <Box>
              <Typography variant="caption" sx={{ color: 'text.secondary', mb: 0.5, display: 'block' }}>Conviction</Typography>
              <ToggleButtonGroup
                value={conviction}
                exclusive
                onChange={(_, val) => val && setConviction(val)}
                size="small"
              >
                {CONVICTION_OPTIONS.map((c) => (
                  <ToggleButton
                    key={c}
                    value={c}
                    sx={{
                      textTransform: 'none', fontSize: '0.75rem', px: 1.5, py: 0.4,
                      '&.Mui-selected': {
                        bgcolor: c === 'High' ? 'rgba(76,175,80,0.15)' : c === 'Medium' ? 'rgba(255,152,0,0.15)' : 'rgba(244,67,54,0.15)',
                        color: c === 'High' ? 'success.main' : c === 'Medium' ? 'warning.main' : 'error.main',
                      },
                    }}
                  >
                    {c}
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
            </Box>
          </Box>

          <TextField
            size="small"
            label="Notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            multiline
            minRows={1}
            maxRows={3}
            sx={{ flex: 1, minWidth: { xs: 0, sm: 200 }, width: { xs: '100%', sm: 'auto' }, '& .MuiInputBase-input': { fontSize: '0.85rem' } }}
          />

          <Button
            variant="contained"
            size="small"
            onClick={handleSave}
            disabled={saving || !pattern || !conviction}
            sx={{ textTransform: 'none', fontSize: '0.8rem' }}
          >
            Save
          </Button>
        </Box>

        {/* Previous entries */}
        {judgments.length > 0 && (
          <Box>
            <Divider sx={{ mb: 1.5 }} />
            <Typography variant="caption" sx={{ color: 'text.secondary', mb: 1, display: 'block' }}>
              Previous observations ({judgments.length})
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {judgments.map((j) => (
                <Box
                  key={j.id}
                  sx={{
                    p: 1.5, borderRadius: 1, bgcolor: 'var(--surface-03)',
                    border: '1px solid var(--surface-06)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1,
                  }}
                >
                  <Box sx={{ flex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5, flexWrap: 'wrap' }}>
                      <Chip label={j.pattern} size="small" sx={{ height: 22, fontSize: '0.7rem', fontWeight: 600 }} />
                      <Chip
                        label={j.conviction}
                        size="small"
                        sx={{
                          height: 22, fontSize: '0.7rem', fontWeight: 500,
                          bgcolor: j.conviction === 'High' ? 'rgba(76,175,80,0.15)' : j.conviction === 'Medium' ? 'rgba(255,152,0,0.15)' : 'rgba(244,67,54,0.15)',
                          color: j.conviction === 'High' ? 'success.main' : j.conviction === 'Medium' ? 'warning.main' : 'error.main',
                        }}
                      />
                      <Typography variant="caption" sx={{ color: 'text.disabled', fontSize: '0.65rem' }}>
                        {new Date(j.created_at + 'Z').toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </Typography>
                    </Box>
                    {j.notes && (
                      <Typography variant="body2" sx={{ fontSize: '0.8rem', color: 'text.secondary' }}>
                        {j.notes}
                      </Typography>
                    )}
                  </Box>
                  <IconButton size="small" onClick={() => handleDelete(j.id)} sx={{ color: 'text.disabled', '&:hover': { color: 'error.main' } }}>
                    <Delete sx={{ fontSize: '0.9rem' }} />
                  </IconButton>
                </Box>
              ))}
            </Box>
          </Box>
        )}

        {judgments.length === 0 && (
          <Typography variant="caption" sx={{ color: 'text.disabled' }}>
            No chart observations recorded yet. Analyze the chart on TradingView and record your findings here.
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
