import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box, Card, CardContent, Typography, Chip, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, IconButton,
  Collapse, Grid, ToggleButton, ToggleButtonGroup,
  FormControl, InputLabel, Select, MenuItem
} from '@mui/material';
import {
  KeyboardArrowDown, KeyboardArrowUp, OpenInNew, Sort, FilterList, WarningAmber
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { getScanner } from '../services/api';
import {
  PageHeader, ScoreBadge, ChangeIndicator, SignalChip,
  SectionTitle, ErrorBanner, EmptyState, HowThisWorks
} from '../components/common';
import { SkeletonPage } from '../components/common/LoadingSkeleton';

const MARKET_CAP_RANGES = [
  { label: 'All', value: 'all' },
  { label: 'Large Cap (>20,000 Cr)', value: 'large' },
  { label: 'Mid Cap (5,000–20,000 Cr)', value: 'mid' },
  { label: 'Small Cap (<5,000 Cr)', value: 'small' },
];

function filterByMarketCap(stock, range) {
  if (range === 'all') return true;
  const mc = stock.market_cap_cr;
  if (mc == null) return range === 'small'; // unknown = assume small
  if (range === 'large') return mc >= 20000;
  if (range === 'mid') return mc >= 5000 && mc < 20000;
  if (range === 'small') return mc < 5000;
  return true;
}

// Generate last N Fridays as week-ending options
function getRecentFridays(count = 8) {
  const fridays = [];
  const d = new Date();
  // Go back to most recent Friday
  d.setDate(d.getDate() - ((d.getDay() + 2) % 7));
  for (let i = 0; i < count; i++) {
    fridays.push(d.toISOString().split('T')[0]);
    d.setDate(d.getDate() - 7);
  }
  return fridays;
}

export default function SignalScanner() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState('score');
  const [filterSector, setFilterSector] = useState('all');
  const [filterMarketCap, setFilterMarketCap] = useState('all');
  const [filterMinScore, setFilterMinScore] = useState(0);
  const [selectedWeek, setSelectedWeek] = useState('');
  const weekOptions = useMemo(() => getRecentFridays(13), []);

  const fetchData = useCallback((weekEnding) => {
    setLoading(true);
    setError(null);
    getScanner(weekEnding || undefined)
      .then(setData)
      .catch(() => setError('Failed to load scanner data'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchData(selectedWeek); }, [fetchData, selectedWeek]);

  // Extract unique sectors from signals
  const sectors = useMemo(() => {
    if (!data?.signals) return [];
    const unique = [...new Set(data.signals.map(s => s.sector))].sort();
    return unique;
  }, [data]);

  // Apply filters then sort
  const filteredAndSorted = useMemo(() => {
    if (!data?.signals) return [];
    let result = data.signals.filter(s => {
      if (filterSector !== 'all' && s.sector !== filterSector) return false;
      if (!filterByMarketCap(s, filterMarketCap)) return false;
      if (s.score < filterMinScore) return false;
      return true;
    });
    result.sort((a, b) => {
      switch (sortBy) {
        case 'score': return b.score - a.score;
        case 'volume': return b.vol_vs_avg - a.vol_vs_avg;
        case 'change': return b.change_pct - a.change_pct;
        case 'delivery': return (b.delivery_pct ?? 0) - (a.delivery_pct ?? 0);
        default: return b.score - a.score;
      }
    });
    return result;
  }, [data, sortBy, filterSector, filterMarketCap, filterMinScore]);

  if (loading) return <SkeletonPage />;
  if (error) return <ErrorBanner message={error} onRetry={fetchData} />;
  if (!data) return null;

  const hasActiveFilters = filterSector !== 'all' || filterMarketCap !== 'all' || filterMinScore > 0;

  return (
    <Box>
      <PageHeader
        title="Signal Scanner"
        subtitle="Your weekly volume + price scan — automated"
        right={
          <FormControl size="small" sx={{ minWidth: { xs: 140, sm: 200 } }}>
            <Select
              value={selectedWeek}
              onChange={(e) => setSelectedWeek(e.target.value)}
              displayEmpty
              sx={{
                fontSize: '0.85rem',
                fontWeight: 500,
                '& .MuiSelect-select': { py: 0.75 },
              }}
            >
              <MenuItem value="">Latest week{data.week_ending ? ` (${data.week_ending})` : ''}</MenuItem>
              {weekOptions.map((w) => (
                <MenuItem key={w} value={w}>Week ending: {w}</MenuItem>
              ))}
            </Select>
          </FormControl>
        }
      />

      <HowThisWorks
        title="How This Screen Works"
        sections={[
          {
            heading: 'What this is',
            body: 'The system runs your three filters on all stocks above 500 Cr market cap every week. Stocks that pass all three show up here, ranked by an 8-point scoring system.',
          },
          {
            heading: '3 Gates (must pass all)',
            bullets: [
              'Volume: Weekly traded volume must be >= 5x the 52-week average. A spike in volume is the first sign that something has changed.',
              'Price: Price must be up >= 5% for the week. High volume combined with price going up means the move is viewed positively.',
              'Delivery: Delivery volume must be >= 35%. High delivery means actual buying (shares transferred), not just speculative trading.',
            ],
          },
          {
            heading: '8-Point Scoring',
            body: 'Each stock that passes the 3 gates gets scored on 8 additional criteria. The higher the score, the more signals are aligned in its favour.',
            bullets: [
              'Delivery >= 35%',
              'Above 30-week moving average',
              'Above 52-week moving average',
              'Golden cross (10W MA crossing above 30W/52W)',
              'Relative strength vs Nifty positive (outperforming the market)',
              'Breaking out of 6+ month consolidation',
              'Sector index outperforming Nifty',
              '2+ sector peers also triggered this week',
            ],
          },
          {
            heading: 'Watch for Breakdown',
            body: 'Stocks with high volume but price going DOWN. This is the opposite signal — possible distribution (selling). These appear in a separate section below the main table.',
          },
          {
            heading: 'Week Selector',
            body: 'The dropdown in the header lets you view scanner results for any of the last 13 weeks. When you click Deep Dive from a historical week, the stock analysis is also shown as of that date.',
          },
          {
            heading: 'What stays human',
            body: 'The scanner finds the candidates. You decide which patterns are convincing, whether the fundamentals support the move, and whether to buy.',
          },
        ]}
      />

      {/* Summary Stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 6, sm: 3 }}>
          <Card>
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>Stocks Scanned</Typography>
              <Typography variant="h5">{data.stocks_scanned.toLocaleString()}</Typography>
              <Typography variant="caption">above 500 Cr market cap</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6, sm: 3 }}>
          <Card>
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>Stocks Triggered</Typography>
              <Typography variant="h5" sx={{ color: 'primary.main' }}>{data.stocks_triggered}</Typography>
              <Typography variant="caption">passed all 3 filters</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6, sm: 3 }}>
          <Card>
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>Hit Rate</Typography>
              <Typography variant="h5">{((data.stocks_triggered / data.stocks_scanned) * 100).toFixed(1)}%</Typography>
              <Typography variant="caption">of total universe</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6, sm: 3 }}>
          <Card>
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>Top Score</Typography>
              <Typography variant="h5" sx={{ color: 'success.main' }}>
                {data.signals.length > 0 ? `${Math.max(...data.signals.map(s => s.score))}/8` : '0/8'}
              </Typography>
              <Typography variant="caption">highest this week</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filter Controls */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 1, sm: 2 }, mb: 2, flexWrap: 'wrap' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <FilterList sx={{ fontSize: '1rem', color: 'text.secondary' }} />
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>Filter:</Typography>
        </Box>
        <FormControl size="small" sx={{ minWidth: { xs: 120, sm: 150 }, flex: { xs: '1 1 calc(50% - 8px)', sm: '0 0 auto' } }}>
          <InputLabel sx={{ fontSize: '0.75rem' }}>Sector</InputLabel>
          <Select
            value={filterSector}
            label="Sector"
            onChange={(e) => setFilterSector(e.target.value)}
            sx={selectSx}
          >
            <MenuItem value="all">All Sectors</MenuItem>
            {sectors.map(s => <MenuItem key={s} value={s}>{s}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: { xs: 120, sm: 180 }, flex: { xs: '1 1 calc(50% - 8px)', sm: '0 0 auto' } }}>
          <InputLabel sx={{ fontSize: '0.75rem' }}>Market Cap</InputLabel>
          <Select
            value={filterMarketCap}
            label="Market Cap"
            onChange={(e) => setFilterMarketCap(e.target.value)}
            sx={selectSx}
          >
            {MARKET_CAP_RANGES.map(r => <MenuItem key={r.value} value={r.value}>{r.label}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: { xs: 90, sm: 120 }, flex: { xs: '1 1 calc(50% - 8px)', sm: '0 0 auto' } }}>
          <InputLabel sx={{ fontSize: '0.75rem' }}>Min Score</InputLabel>
          <Select
            value={filterMinScore}
            label="Min Score"
            onChange={(e) => setFilterMinScore(e.target.value)}
            sx={selectSx}
          >
            <MenuItem value={0}>Any</MenuItem>
            {[3, 4, 5, 6, 7, 8].map(s => (
              <MenuItem key={s} value={s}>{`>= ${s}`}</MenuItem>
            ))}
          </Select>
        </FormControl>
        {hasActiveFilters && (
          <Chip
            label={`Showing ${filteredAndSorted.length} of ${data.stocks_triggered}`}
            size="small"
            onDelete={() => { setFilterSector('all'); setFilterMarketCap('all'); setFilterMinScore(0); }}
            sx={{ fontSize: '0.7rem' }}
          />
        )}
      </Box>

      {/* Sort Controls */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2, flexWrap: 'wrap' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Sort sx={{ fontSize: '1rem', color: 'text.secondary' }} />
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>Sort by:</Typography>
        </Box>
        <ToggleButtonGroup
          value={sortBy}
          exclusive
          onChange={(_, val) => val && setSortBy(val)}
          size="small"
          sx={{ flexWrap: 'wrap' }}
        >
          <ToggleButton value="score" sx={toggleSx}>Score</ToggleButton>
          <ToggleButton value="volume" sx={toggleSx}>Volume</ToggleButton>
          <ToggleButton value="change" sx={toggleSx}>Change</ToggleButton>
          <ToggleButton value="delivery" sx={toggleSx}>Delivery</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Gates Explanation */}
      <Card sx={{ mb: 2, borderColor: 'rgba(79,195,247,0.15)' }}>
        <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
          <Typography variant="subtitle2" sx={{ fontSize: '0.7rem', mb: 1 }}>
            How stocks appear here — 3 gates (must pass all)
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Chip label="Weekly Vol >= 5x avg" size="small" variant="outlined" sx={{ borderColor: 'var(--surface-15)' }} />
            <Chip label="Price up >= 5%" size="small" variant="outlined" sx={{ borderColor: 'var(--surface-15)' }} />
            <Chip label="Delivery >= 35%" size="small" variant="outlined" sx={{ borderColor: 'var(--surface-15)' }} />
          </Box>
        </CardContent>
      </Card>

      {/* Signals Table */}
      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell width={40} sx={{ display: { xs: 'none', sm: 'table-cell' } }} />
                <TableCell>Stock</TableCell>
                <TableCell align="right">Price</TableCell>
                <TableCell align="right">Change</TableCell>
                <TableCell align="right" sx={{ display: { xs: 'none', md: 'table-cell' } }}>Vol vs Avg</TableCell>
                <TableCell align="right" sx={{ display: { xs: 'none', md: 'table-cell' } }}>Delivery %</TableCell>
                <TableCell align="center">Score</TableCell>
                <TableCell width={40} />
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredAndSorted.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8}>
                    <EmptyState message={hasActiveFilters ? "No stocks match the current filters" : "No stocks triggered this week"} />
                  </TableCell>
                </TableRow>
              ) : (
                filteredAndSorted.map((stock) => (
                  <StockRow key={stock.symbol} stock={stock} weekEnding={selectedWeek} />
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* Distribution Watchlist */}
      {data.distribution_watchlist && data.distribution_watchlist.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <WarningAmber sx={{ fontSize: '1.1rem', color: 'warning.main' }} />
            <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600 }}>
              Watch for Breakdown
            </Typography>
            <Chip
              label={`${data.distribution_watchlist.length} stocks`}
              size="small"
              sx={{ fontSize: '0.65rem', bgcolor: 'rgba(255,152,0,0.12)', color: 'warning.main' }}
            />
          </Box>
          <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 2 }}>
            High volume + price DOWN — possible distribution. These stocks have unusual selling activity.
          </Typography>
          <Card sx={{ borderColor: 'rgba(255,152,0,0.2)' }}>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Stock</TableCell>
                    <TableCell align="right">Price</TableCell>
                    <TableCell align="right">Change</TableCell>
                    <TableCell align="right" sx={{ display: { xs: 'none', sm: 'table-cell' } }}>Vol vs Avg</TableCell>
                    <TableCell align="right" sx={{ display: { xs: 'none', sm: 'table-cell' } }}>Delivery %</TableCell>
                    <TableCell align="center">MA Status</TableCell>
                    <TableCell width={40} />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.distribution_watchlist.map((stock) => (
                    <DistributionRow key={stock.symbol} stock={stock} weekEnding={selectedWeek} />
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>
        </Box>
      )}
    </Box>
  );
}

const selectSx = {
  fontSize: '0.8rem',
  '& .MuiSelect-select': { py: 0.75 },
};

const toggleSx = {
  fontSize: '0.7rem', py: 0.5, px: 1.5, textTransform: 'none',
  borderColor: 'var(--surface-10)',
  '&.Mui-selected': { bgcolor: 'rgba(79,195,247,0.12)', color: 'primary.main' },
};

function StockRow({ stock, weekEnding }) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <>
      <TableRow
        hover
        sx={{
          cursor: 'pointer',
          '& td': { borderBottom: open ? 'none' : undefined },
          transition: 'background-color 0.15s',
        }}
        onClick={() => setOpen(!open)}
      >
        <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>
          <IconButton size="small" sx={{ color: 'text.secondary' }}>
            {open ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
          </IconButton>
        </TableCell>
        <TableCell>
          <Box>
            <Typography sx={{ fontWeight: 600, fontSize: { xs: '0.8rem', sm: '0.9rem' } }}>{stock.name}</Typography>
            <Box sx={{ display: 'flex', gap: 0.5, mt: 0.3, flexWrap: 'wrap' }}>
              <Chip label={stock.symbol} size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'var(--surface-06)' }} />
              <Chip label={stock.sector} size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'var(--surface-06)', display: { xs: 'none', sm: 'inline-flex' } }} />
              {stock.market_cap_cr != null && (
                <Chip
                  label={stock.market_cap_cr >= 10000 ? `${(stock.market_cap_cr / 1000).toFixed(0)}K Cr` : `${stock.market_cap_cr.toLocaleString()} Cr`}
                  size="small"
                  sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'var(--surface-06)', display: { xs: 'none', sm: 'inline-flex' } }}
                />
              )}
            </Box>
          </Box>
        </TableCell>
        <TableCell align="right">
          <Typography sx={{ fontWeight: 500, fontVariantNumeric: 'tabular-nums', fontSize: { xs: '0.8rem', sm: '0.85rem' } }}>₹{stock.price}</Typography>
        </TableCell>
        <TableCell align="right">
          <ChangeIndicator value={stock.change_pct} />
        </TableCell>
        <TableCell align="right" sx={{ display: { xs: 'none', md: 'table-cell' } }}>
          <Typography sx={{ fontWeight: 600, color: stock.vol_vs_avg >= 7 ? 'primary.main' : 'text.primary', fontVariantNumeric: 'tabular-nums' }}>
            {stock.vol_vs_avg}x
          </Typography>
        </TableCell>
        <TableCell align="right" sx={{ display: { xs: 'none', md: 'table-cell' } }}>
          <Typography sx={{
            fontVariantNumeric: 'tabular-nums',
            color: stock.delivery_pct == null ? 'text.disabled' : stock.delivery_pct >= 60 ? 'success.main' : stock.delivery_pct >= 50 ? 'text.primary' : 'warning.main',
            fontWeight: 500,
          }}>
            {stock.delivery_pct != null ? `${stock.delivery_pct}%` : '--'}
          </Typography>
        </TableCell>
        <TableCell align="center">
          <ScoreBadge score={stock.score} size="small" />
        </TableCell>
        <TableCell>
          <Box
            onClick={(e) => { e.stopPropagation(); navigate(`/stock/${stock.symbol}${weekEnding ? `?week=${weekEnding}` : ''}`); }}
            sx={{ display: 'flex', alignItems: 'center', gap: 0.5, cursor: 'pointer', color: 'primary.main', '&:hover': { textDecoration: 'underline' } }}
          >
            <OpenInNew sx={{ fontSize: '0.9rem' }} />
            <Typography sx={{ fontSize: '0.7rem', fontWeight: 500 }}>Deep Dive</Typography>
          </Box>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={8} sx={{ py: 0, px: 0 }}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ p: 2, pl: { xs: 2, sm: 7 }, bgcolor: 'var(--surface-02)', borderBottom: '1px solid var(--surface-06)' }}>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <Typography variant="subtitle2" sx={{ fontSize: '0.7rem', mb: 1 }}>Technical Signals</Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8 }}>
                    <SignalRow label="Delivery ≥ 35%" value={stock.delivery_pct != null && stock.delivery_pct >= 35} detail={stock.delivery_pct != null ? `${stock.delivery_pct}%` : '--'} />
                    <SignalRow label="Above 30W MA" value={stock.signals.above_30w_ma} />
                    <SignalRow label="Above 52W MA" value={stock.signals.above_52w_ma} />
                    <SignalRow label="Golden Cross" value={!!stock.signals.golden_cross} detail={stock.signals.golden_cross || 'No'} />
                    <SignalRow label="RS vs Nifty (4W)" value={stock.signals.rs_vs_nifty_4w > 0} detail={`${stock.signals.rs_vs_nifty_4w > 0 ? '+' : ''}${stock.signals.rs_vs_nifty_4w}%`} />
                  </Box>
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <Typography variant="subtitle2" sx={{ fontSize: '0.7rem', mb: 1 }}>Context</Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8 }}>
                    <SignalRow label="Consolidation breakout" value={stock.signals.consolidation_months >= 6} detail={`${stock.signals.consolidation_months} months`} />
                    <SignalRow label="Sector index vs Nifty" value={stock.signals.sector_index_outperforming} detail={stock.signals.sector_index_rs != null ? `${stock.signals.sector_index_rs > 0 ? '+' : ''}${stock.signals.sector_index_rs}%` : 'N/A'} />
                    <SignalRow label="Peers triggered" value={stock.signals.peers_triggered >= 2} detail={stock.signals.peers_triggered > 0 ? `${stock.signals.peers_triggered} peers` : 'None'} />
                  </Box>
                </Grid>
              </Grid>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

function DistributionRow({ stock, weekEnding }) {
  const navigate = useNavigate();

  return (
    <TableRow hover sx={{ cursor: 'pointer' }} onClick={() => navigate(`/stock/${stock.symbol}${weekEnding ? `?week=${weekEnding}` : ''}`)}>
      <TableCell>
        <Box>
          <Typography sx={{ fontWeight: 600, fontSize: '0.85rem' }}>{stock.name}</Typography>
          <Box sx={{ display: 'flex', gap: 0.5, mt: 0.3 }}>
            <Chip label={stock.symbol} size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'var(--surface-06)' }} />
            <Chip label={stock.sector} size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'var(--surface-06)' }} />
          </Box>
        </Box>
      </TableCell>
      <TableCell align="right">
        <Typography sx={{ fontWeight: 500, fontSize: '0.85rem', fontVariantNumeric: 'tabular-nums' }}>₹{stock.price}</Typography>
      </TableCell>
      <TableCell align="right">
        <ChangeIndicator value={stock.change_pct} />
      </TableCell>
      <TableCell align="right" sx={{ display: { xs: 'none', sm: 'table-cell' } }}>
        <Typography sx={{ fontWeight: 600, fontSize: '0.85rem', color: 'primary.main', fontVariantNumeric: 'tabular-nums' }}>
          {stock.vol_vs_avg}x
        </Typography>
      </TableCell>
      <TableCell align="right" sx={{ display: { xs: 'none', sm: 'table-cell' } }}>
        <Typography sx={{ fontVariantNumeric: 'tabular-nums', fontSize: '0.85rem', fontWeight: 500 }}>
          {stock.delivery_pct != null ? `${stock.delivery_pct}%` : '--'}
        </Typography>
      </TableCell>
      <TableCell align="center">
        <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
          {stock.below_30w_ma && (
            <Chip label="< 30W" size="small" sx={{ height: 20, fontSize: '0.6rem', bgcolor: 'rgba(244,67,54,0.15)', color: 'error.main' }} />
          )}
          {stock.below_52w_ma && (
            <Chip label="< 52W" size="small" sx={{ height: 20, fontSize: '0.6rem', bgcolor: 'rgba(244,67,54,0.15)', color: 'error.main' }} />
          )}
          {!stock.below_30w_ma && !stock.below_52w_ma && (
            <Typography variant="caption" sx={{ color: 'text.disabled' }}>OK</Typography>
          )}
        </Box>
      </TableCell>
      <TableCell>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'primary.main' }}>
          <OpenInNew sx={{ fontSize: '0.9rem' }} />
          <Typography sx={{ fontSize: '0.7rem', fontWeight: 500 }}>Deep Dive</Typography>
        </Box>
      </TableCell>
    </TableRow>
  );
}

function SignalRow({ label, value, detail }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <SignalChip label={label} value={value} />
      {detail && (
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>{detail}</Typography>
      )}
    </Box>
  );
}
