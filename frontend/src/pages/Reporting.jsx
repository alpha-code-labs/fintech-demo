import { useState, useEffect, useCallback } from 'react';
import {
  Box, Card, CardContent, Typography, Chip, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Grid
} from '@mui/material';
import { Assessment, TrendingUp, TrendingDown } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { getPortfolio } from '../services/api';
import { PageHeader, ChangeIndicator, ErrorBanner } from '../components/common';
import { SkeletonPage } from '../components/common/LoadingSkeleton';

function getDaysHeld(buyDate) {
  if (!buyDate) return null;
  const buy = new Date(buyDate);
  const now = new Date();
  return Math.floor((now - buy) / (1000 * 60 * 60 * 24));
}

function formatCurrency(val) {
  if (val == null) return '--';
  const abs = Math.abs(val);
  if (abs >= 10000000) return `${(val / 10000000).toFixed(2)} Cr`;
  if (abs >= 100000) return `${(val / 100000).toFixed(2)} L`;
  return `₹${val.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

function formatDate(dateStr) {
  if (!dateStr) return '--';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function Reporting() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    getPortfolio()
      .then(setData)
      .catch(() => setError('Failed to load portfolio data'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <SkeletonPage />;
  if (error) return <ErrorBanner message={error} onRetry={fetchData} />;
  if (!data) return null;

  // Flatten all holdings and sort by days held descending
  const allHoldings = [
    ...(data.holdings?.alert || []),
    ...(data.holdings?.warning || []),
    ...(data.holdings?.healthy || []),
  ].map((h) => {
    const daysHeld = getDaysHeld(h.buy_date);
    const qty = h.quantity || 1;
    const investedValue = h.buy_price * qty;
    const currentValue = h.current_price != null ? h.current_price * qty : null;
    const pnlAbs = currentValue != null ? currentValue - investedValue : null;
    return { ...h, daysHeld, investedValue, currentValue, pnlAbs };
  }).sort((a, b) => (b.daysHeld || 0) - (a.daysHeld || 0));

  const totalCount = data.total_holdings || allHoldings.length;
  const inRange = totalCount >= 15 && totalCount <= 25;
  const rangeColor = totalCount === 0 ? 'text.secondary' : inRange ? 'success.main' : 'warning.main';

  const totalInvested = allHoldings.reduce((s, h) => s + h.investedValue, 0);
  const totalCurrent = allHoldings.reduce((s, h) => s + (h.currentValue || 0), 0);
  const totalPnl = data.total_pnl || (totalCurrent - totalInvested);
  const totalPnlPct = data.total_pnl_pct || (totalInvested > 0 ? ((totalCurrent - totalInvested) / totalInvested * 100) : 0);

  const sectorBreakdown = data.sector_concentration || [];

  return (
    <Box>
      <PageHeader title="Reporting" subtitle="Portfolio overview and compliance" />

      {/* Stock count indicator */}
      <Card sx={{ mb: 3, border: `1px solid`, borderColor: inRange ? 'success.main' : totalCount === 0 ? 'var(--surface-08)' : 'warning.main' }}>
        <CardContent sx={{ py: 2, '&:last-child': { pb: 2 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography sx={{ fontSize: '2.5rem', fontWeight: 800, color: rangeColor, lineHeight: 1 }}>
                {totalCount}
              </Typography>
              <Box>
                <Typography sx={{ fontSize: '0.95rem', fontWeight: 600, color: 'text.primary' }}>
                  Stocks Held
                </Typography>
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Summary stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} md={3}>
          <Card>
            <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.05em', mb: 0.5 }}>
                Total Invested
              </Typography>
              <Typography sx={{ fontSize: '1.2rem', fontWeight: 700, color: 'text.primary' }}>
                {formatCurrency(totalInvested)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card>
            <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.05em', mb: 0.5 }}>
                Current Value
              </Typography>
              <Typography sx={{ fontSize: '1.2rem', fontWeight: 700, color: 'text.primary' }}>
                {formatCurrency(totalCurrent)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card>
            <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.05em', mb: 0.5 }}>
                Overall P&L
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
                <Typography sx={{ fontSize: '1.2rem', fontWeight: 700, color: totalPnl >= 0 ? 'success.main' : 'error.main' }}>
                  {totalPnl >= 0 ? '+' : ''}{formatCurrency(totalPnl)}
                </Typography>
                <ChangeIndicator value={totalPnlPct} fontSize="0.85rem" />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card>
            <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.05em', mb: 0.5 }}>
                Sectors
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {sectorBreakdown.length === 0 && (
                  <Typography sx={{ fontSize: '0.85rem', color: 'text.disabled' }}>--</Typography>
                )}
                {sectorBreakdown.map((s) => (
                  <Chip
                    key={s.sector}
                    label={`${s.sector} (${s.count})`}
                    size="small"
                    sx={{ fontSize: '0.65rem', height: 22, bgcolor: 'var(--surface-06)' }}
                  />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Holdings table */}
      <Card>
        <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
          <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid var(--surface-06)' }}>
            <Typography sx={{ fontSize: '0.9rem', fontWeight: 600, color: 'text.primary' }}>
              Holdings by Days Held
            </Typography>
          </Box>
          {allHoldings.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Typography sx={{ color: 'text.secondary' }}>No holdings yet. Add stocks from the Portfolio page.</Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Stock</TableCell>
                    <TableCell sx={{ fontWeight: 600, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Sector</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Buy Date</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Days Held</TableCell>
                    <TableCell align="center" sx={{ fontWeight: 600, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>6M Status</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Qty</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Buy Price</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Current</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>P&L</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Invested</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {allHoldings.map((h) => {
                    const sixMonthDone = h.daysHeld != null && h.daysHeld >= 183;
                    return (
                      <TableRow
                        key={h.symbol}
                        hover
                        sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'var(--surface-04)' } }}
                        onClick={() => navigate(`/stock/${h.symbol}`)}
                      >
                        <TableCell>
                          <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: 'text.primary' }}>{h.symbol}</Typography>
                          <Typography sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>{h.name}</Typography>
                        </TableCell>
                        <TableCell>
                          <Typography sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>{h.sector || '--'}</Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>{formatDate(h.buy_date)}</Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: 'text.primary', fontVariantNumeric: 'tabular-nums' }}>
                            {h.daysHeld != null ? h.daysHeld : '--'}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          {h.daysHeld == null ? (
                            <Typography sx={{ fontSize: '0.7rem', color: 'text.disabled' }}>--</Typography>
                          ) : sixMonthDone ? (
                            <Chip label="Complete" size="small" color="success" sx={{ fontSize: '0.65rem', height: 20 }} />
                          ) : (
                            <Chip label={`${183 - h.daysHeld}d left`} size="small" sx={{ fontSize: '0.65rem', height: 20, bgcolor: 'var(--surface-08)', color: 'text.secondary' }} />
                          )}
                        </TableCell>
                        <TableCell align="right">
                          <Typography sx={{ fontSize: '0.8rem', color: 'text.primary', fontVariantNumeric: 'tabular-nums' }}>
                            {h.quantity || 1}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography sx={{ fontSize: '0.8rem', color: 'text.primary', fontVariantNumeric: 'tabular-nums' }}>
                            ₹{h.buy_price?.toLocaleString('en-IN', { maximumFractionDigits: 2 }) || '--'}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography sx={{ fontSize: '0.8rem', color: 'text.primary', fontVariantNumeric: 'tabular-nums' }}>
                            {h.current_price != null ? `₹${h.current_price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : '--'}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Box>
                            <ChangeIndicator value={h.pnl_pct} fontSize="0.8rem" />
                            {h.pnlAbs != null && (
                              <Typography sx={{ fontSize: '0.65rem', color: h.pnlAbs >= 0 ? 'success.main' : 'error.main', fontVariantNumeric: 'tabular-nums' }}>
                                {h.pnlAbs >= 0 ? '+' : ''}₹{Math.abs(h.pnlAbs).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                              </Typography>
                            )}
                          </Box>
                        </TableCell>
                        <TableCell align="right">
                          <Typography sx={{ fontSize: '0.8rem', color: 'text.primary', fontVariantNumeric: 'tabular-nums' }}>
                            ₹{h.investedValue?.toLocaleString('en-IN', { maximumFractionDigits: 0 }) || '--'}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
