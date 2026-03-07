import { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, Chip, Button,
  Collapse, IconButton, LinearProgress, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, Autocomplete,
  FormControl, InputLabel, Select, MenuItem
} from '@mui/material';
import {
  AccountBalance, Shield, Warning, ErrorOutline,
  KeyboardArrowDown, KeyboardArrowUp, TrendingUp, PieChart,
  Add, Delete, Bookmark, Visibility, NotificationsActive, Notifications,
  Sell, PanTool, History
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useSnackbar } from 'notistack';
import {
  getPortfolio, addHolding, removeHolding, sellHolding, holdDecision, addMoreShares, getTradeHistory,
  getWatchlist, removeFromWatchlist, getAlerts, createAlert, deleteAlert, getStockUniverse
} from '../services/api';
import {
  PageHeader, ChangeIndicator, StatusBadge, SectionTitle,
  ErrorBanner, EmptyState, HowThisWorks
} from '../components/common';
import { SkeletonPage } from '../components/common/LoadingSkeleton';

function getDaysHeld(buyDate) {
  if (!buyDate) return null;
  const buy = new Date(buyDate);
  const now = new Date();
  return Math.floor((now - buy) / (1000 * 60 * 60 * 24));
}

export default function PortfolioMonitor() {
  const [data, setData] = useState(null);
  const [watchlist, setWatchlist] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [tradeHistory, setTradeHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [addOpen, setAddOpen] = useState(false);
  const [prefillSymbol, setPrefillSymbol] = useState('');
  const [alertOpen, setAlertOpen] = useState(null);
  const [sellOpen, setSellOpen] = useState(null); // { symbol, name, current_price } or null
  const [addMoreOpen, setAddMoreOpen] = useState(null); // { symbol, name } or null
  const [holdOpen, setHoldOpen] = useState(null); // symbol or null
  const [complianceWarn, setComplianceWarn] = useState(null); // { symbol, name, current_price, daysHeld } or null
  const { enqueueSnackbar } = useSnackbar();

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([getPortfolio(), getWatchlist(), getAlerts(), getTradeHistory()])
      .then(([portfolioData, watchlistData, alertsData, historyData]) => {
        setData(portfolioData);
        setWatchlist(watchlistData);
        setAlerts(alertsData);
        setTradeHistory(historyData);
      })
      .catch(() => setError('Failed to load portfolio data'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleAdd = (formData) => {
    addHolding(formData)
      .then(() => {
        enqueueSnackbar(`${formData.symbol.toUpperCase()} added to portfolio`, { variant: 'success' });
        setAddOpen(false);
        fetchData();
      })
      .catch((err) => {
        const msg = err.response?.data?.detail || 'Failed to add holding';
        enqueueSnackbar(msg, { variant: 'error' });
      });
  };

  const handleRemove = (symbol) => {
    removeHolding(symbol)
      .then(() => {
        enqueueSnackbar(`${symbol} removed from portfolio`, { variant: 'info' });
        fetchData();
      })
      .catch(() => enqueueSnackbar('Failed to remove holding', { variant: 'error' }));
  };

  const handleWatchlistRemove = (symbol) => {
    removeFromWatchlist(symbol)
      .then(() => {
        enqueueSnackbar(`${symbol} removed from watchlist`, { variant: 'info' });
        fetchData();
      })
      .catch(() => enqueueSnackbar('Failed to remove from watchlist', { variant: 'error' }));
  };

  const handleSell = (sellData) => {
    sellHolding(sellData)
      .then((res) => {
        const pnl = res.trade?.pnl_pct;
        enqueueSnackbar(
          `${sellData.symbol} sold${pnl != null ? ` (${pnl > 0 ? '+' : ''}${pnl}%)` : ''}`,
          { variant: pnl >= 0 ? 'success' : 'warning' }
        );
        setSellOpen(null);
        fetchData();
      })
      .catch((err) => {
        enqueueSnackbar(err.response?.data?.detail || 'Failed to sell', { variant: 'error' });
      });
  };

  const handleHold = (holdData) => {
    holdDecision(holdData)
      .then(() => {
        enqueueSnackbar(`${holdData.symbol}: HOLD decision logged`, { variant: 'info' });
        setHoldOpen(null);
        fetchData();
      })
      .catch(() => enqueueSnackbar('Failed to log hold decision', { variant: 'error' }));
  };

  const handleAddMore = (data) => {
    addMoreShares(data)
      .then((res) => {
        enqueueSnackbar(`${data.symbol}: Added ${data.quantity} shares. New avg: ₹${res.result.new_avg}`, { variant: 'success' });
        setAddMoreOpen(null);
        fetchData();
      })
      .catch(() => enqueueSnackbar('Failed to add more shares', { variant: 'error' }));
  };

  const handleSellClick = (sellData) => {
    const daysHeld = getDaysHeld(sellData.buy_date);
    if (daysHeld != null && daysHeld < 183) {
      setComplianceWarn({ ...sellData, daysHeld });
    } else {
      setSellOpen(sellData);
    }
  };

  const handleCreateAlert = (alertData) => {
    createAlert(alertData)
      .then(() => {
        enqueueSnackbar(`Alert set for ${alertData.symbol}`, { variant: 'success' });
        setAlertOpen(null);
        fetchData();
      })
      .catch((err) => {
        const msg = err.response?.data?.detail || 'Failed to create alert';
        enqueueSnackbar(msg, { variant: 'error' });
      });
  };

  const handleDeleteAlert = (alertId) => {
    deleteAlert(alertId)
      .then(() => {
        enqueueSnackbar('Alert removed', { variant: 'info' });
        fetchData();
      })
      .catch(() => enqueueSnackbar('Failed to remove alert', { variant: 'error' }));
  };

  if (loading) return <SkeletonPage />;
  if (error) return <ErrorBanner message={error} onRetry={fetchData} />;
  if (!data) return null;

  const { healthy = [], warning = [], alert = [] } = data.holdings;
  const isEmpty = data.total_holdings === 0;

  return (
    <Box>
      <PageHeader
        title="Portfolio Monitor"
        subtitle="Your exit signal tracker"
        right={
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            {!isEmpty && <Chip label={`${data.total_holdings} Active Holdings`} size="small" sx={{ fontWeight: 500 }} />}
            <Button variant="contained" size="small" startIcon={<Add />} onClick={() => setAddOpen(true)}>
              Add Holding
            </Button>
          </Box>
        }
      />

      <HowThisWorks
        title="How This Screen Works"
        sections={[
          {
            heading: 'What this is',
            body: 'Shows all your current holdings. The system checks for exit signals every day and groups stocks into three buckets: Healthy (no signals), Warning (1-2 early signals), and Alert (MA break, bad news, or 3+ signals). The system detects — you decide whether to sell.',
          },
          {
            heading: 'Exit Signals Monitored',
            bullets: [
              'Upper wicks: 3+ consecutive weekly candles with long upper wicks — signals a month of selling pressure',
              'Below 30-week MA: Price has broken below the 30-week moving average — a key support level',
              'Below 52-week MA: Price has broken below the 52-week moving average — a more serious break',
              'Support break: Price has fallen below the lowest weekly close of the last 13 weeks',
              'Head & Shoulders: Classic reversal pattern detected from weekly highs',
              'Bad news + technical breakdown: Negative news confirmed by AI, combined with an active technical signal',
            ],
          },
          {
            heading: '6-Month Holding Period',
            body: 'Each holding shows days held and a 6-month compliance indicator. Selling before 6 months triggers a compliance warning. This is tracked because the system is designed for medium-to-long-term holds.',
          },
          {
            heading: 'Market Leverage',
            body: 'Tracks market-wide borrowing (margin trading) as a risk indicator. When market participants borrow significantly to invest, it creates fragility. Currently uses F&O open interest as a proxy.',
          },
          {
            heading: 'Tabs',
            bullets: [
              'Watchlist: Stocks from the scanner you\'re monitoring but haven\'t bought yet',
              'Alerts: Price alerts you\'ve set (above/below a target price)',
              'Decision Log: Complete history of your buy, sell, hold, and add-more decisions',
            ],
          },
          {
            heading: 'What stays human',
            body: 'The sell decision is always yours. The system surfaces the signals so you can make an informed choice. The Hold button lets you record why you\'re staying despite exit signals.',
          },
        ]}
      />

      {isEmpty ? (
        <Card sx={{ py: 6, textAlign: 'center' }}>
          <CardContent>
            <AccountBalance sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" sx={{ mb: 1 }}>No holdings yet</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
              Add stocks to your portfolio to track exit signals and P&L
            </Typography>
            <Button variant="contained" startIcon={<Add />} onClick={() => setAddOpen(true)}>
              Add Your First Holding
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Portfolio Summary */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid size={{ xs: 6, sm: 3 }}>
              <Card>
                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                  <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>Portfolio Value</Typography>
                  <Typography variant="h5" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                    ₹{(data.portfolio_value / 100000).toFixed(1)}L
                  </Typography>
                  <Typography variant="caption">{data.total_holdings} stocks</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <Card>
                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                  <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>Total P&L</Typography>
                  <Typography variant="h5" sx={{ color: data.total_pnl >= 0 ? 'success.main' : 'error.main', fontVariantNumeric: 'tabular-nums' }}>
                    {data.total_pnl >= 0 ? '+' : ''}₹{(data.total_pnl / 100000).toFixed(1)}L
                  </Typography>
                  <ChangeIndicator value={data.total_pnl_pct} />
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <Card>
                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                  <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>Healthy</Typography>
                  <Typography variant="h5" sx={{ color: 'success.main' }}>{healthy.length}</Typography>
                  <Typography variant="caption">No exit signals</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <Card>
                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                  <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>Need Attention</Typography>
                  <Typography variant="h5" sx={{ color: warning.length + alert.length > 0 ? 'warning.main' : 'success.main' }}>
                    {warning.length + alert.length}
                  </Typography>
                  <Typography variant="caption">{warning.length} watch, {alert.length} alert</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Portfolio Health Bar */}
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Typography variant="subtitle2" sx={{ fontSize: '0.7rem', mb: 1 }}>Portfolio Health</Typography>
              <Box sx={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden' }}>
                <Box sx={{ width: `${(healthy.length / data.total_holdings) * 100}%`, bgcolor: 'success.main', transition: 'width 0.5s' }} />
                <Box sx={{ width: `${(warning.length / data.total_holdings) * 100}%`, bgcolor: 'warning.main', transition: 'width 0.5s' }} />
                <Box sx={{ width: `${(alert.length / data.total_holdings) * 100}%`, bgcolor: 'error.main', transition: 'width 0.5s' }} />
              </Box>
              <Box sx={{ display: 'flex', gap: 3, mt: 1 }}>
                <LegendItem color="#4caf50" label={`Healthy (${healthy.length})`} />
                <LegendItem color="#ff9800" label={`Watch (${warning.length})`} />
                <LegendItem color="#f44336" label={`Alert (${alert.length})`} />
              </Box>
            </CardContent>
          </Card>

          {/* Alert Holdings */}
          <Box sx={{ mb: 3 }}>
            <SectionTitle icon={ErrorOutline}>
              <Box component="span" sx={{ color: 'error.main' }}>Alert — Review Now</Box>
            </SectionTitle>
            {alert.length === 0 ? (
              <EmptyState message="No holdings in alert — all clear" />
            ) : (
              alert.map((h) => (
                <HoldingCard key={h.symbol} holding={h} status="alert" onRemove={handleRemove} onSetAlert={setAlertOpen} onSell={handleSellClick} onHold={setHoldOpen} onAddMore={setAddMoreOpen} />
              ))
            )}
          </Box>

          {/* Warning Holdings */}
          <Box sx={{ mb: 3 }}>
            <SectionTitle icon={Warning}>
              <Box component="span" sx={{ color: 'warning.main' }}>Warning — Early Signals</Box>
            </SectionTitle>
            {warning.length === 0 ? (
              <EmptyState message="No holdings with early warning signals" />
            ) : (
              warning.map((h) => (
                <HoldingCard key={h.symbol} holding={h} status="warning" onRemove={handleRemove} onSetAlert={setAlertOpen} onSell={handleSellClick} onHold={setHoldOpen} onAddMore={setAddMoreOpen} />
              ))
            )}
          </Box>

          {/* Healthy Holdings */}
          <Box sx={{ mb: 3 }}>
            <SectionTitle icon={Shield}>
              <Box component="span" sx={{ color: 'success.main' }}>Healthy — No Exit Signals</Box>
            </SectionTitle>
            {healthy.length === 0 ? (
              <EmptyState message="No healthy holdings" />
            ) : (
              healthy.map((h) => (
                <HoldingCard key={h.symbol} holding={h} status="healthy" onRemove={handleRemove} onSetAlert={setAlertOpen} onSell={handleSellClick} onHold={setHoldOpen} onAddMore={setAddMoreOpen} />
              ))
            )}
          </Box>

          {/* Sector Concentration + Market Leverage */}
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <SectionTitle icon={PieChart}>Sector Concentration</SectionTitle>
              <Card>
                <CardContent>
                  {data.sector_concentration && data.sector_concentration.length > 0 ? (
                    data.sector_concentration.map((s) => (
                      <Box key={s.sector} sx={{ mb: 1.5 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                          <Typography variant="body2">{s.sector}</Typography>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>{s.count} stocks ({s.pct}%)</Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={s.pct}
                          sx={{
                            height: 6, borderRadius: 3,
                            bgcolor: 'var(--surface-06)',
                            '& .MuiLinearProgress-bar': {
                              bgcolor: s.pct > 25 ? 'warning.main' : 'primary.main',
                              borderRadius: 3,
                            },
                          }}
                        />
                      </Box>
                    ))
                  ) : (
                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>--</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <SectionTitle icon={TrendingUp}>Market Leverage</SectionTitle>
              <Card>
                <CardContent>
                  {data.market_leverage ? (
                    <>
                      <Typography variant="subtitle2" sx={{ fontSize: '0.7rem', mb: 1 }}>Retail F&O Leverage (Client Long Contracts)</Typography>
                      <Typography variant="h5" sx={{ fontVariantNumeric: 'tabular-nums', mb: 0.5 }}>
                        {(data.market_leverage.client_long_contracts / 100000).toFixed(1)}L
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>
                        L/S Ratio: {data.market_leverage.long_short_ratio ?? '--'}
                      </Typography>
                      <Chip
                        label={data.market_leverage.trend_3m === 'ACCUMULATING'
                          ? `Collecting data (${data.market_leverage.data_points} day${data.market_leverage.data_points === 1 ? '' : 's'})`
                          : `3-month trend: ${data.market_leverage.trend_3m}`}
                        size="small"
                        sx={{
                          fontWeight: 600, fontSize: '0.7rem',
                          bgcolor: data.market_leverage.trend_3m === 'INCREASING' ? 'rgba(255,152,0,0.12)'
                            : data.market_leverage.trend_3m === 'ACCUMULATING' ? 'var(--surface-06)'
                            : 'rgba(76,175,80,0.12)',
                          color: data.market_leverage.trend_3m === 'INCREASING' ? 'warning.main'
                            : data.market_leverage.trend_3m === 'ACCUMULATING' ? 'text.secondary'
                            : 'success.main',
                        }}
                      />
                    </>
                  ) : (
                    <Box sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        Market leverage data not yet available
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}

      {/* Watchlist */}
      <Box sx={{ mt: 4 }}>
        <SectionTitle icon={Bookmark}>
          Watchlist
          {watchlist.length > 0 && (
            <Chip label={watchlist.length} size="small" sx={{ ml: 1, height: 20, fontSize: '0.65rem', bgcolor: 'rgba(79,195,247,0.12)', color: 'primary.main' }} />
          )}
        </SectionTitle>
        {watchlist.length === 0 ? (
          <Card>
            <CardContent sx={{ py: 4, textAlign: 'center' }}>
              <Visibility sx={{ fontSize: 36, color: 'text.disabled', mb: 1 }} />
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                No stocks in watchlist. Use "Add to Watchlist" on any stock's Deep Dive page.
              </Typography>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent sx={{ p: 0 }}>
              {watchlist.map((item, i) => (
                <WatchlistRow key={item.symbol} item={item} isLast={i === watchlist.length - 1} onRemove={handleWatchlistRemove} onAddToPortfolio={(sym) => { setPrefillSymbol(sym); setAddOpen(true); }} />
              ))}
            </CardContent>
          </Card>
        )}
      </Box>

      {/* Price Alerts */}
      <Box sx={{ mt: 4 }}>
        <SectionTitle icon={Notifications}>
          Price Alerts
          {alerts.length > 0 && (
            <Chip label={alerts.length} size="small" sx={{ ml: 1, height: 20, fontSize: '0.65rem', bgcolor: 'rgba(79,195,247,0.12)', color: 'primary.main' }} />
          )}
        </SectionTitle>
        {alerts.length === 0 ? (
          <Card>
            <CardContent sx={{ py: 3, textAlign: 'center' }}>
              <Notifications sx={{ fontSize: 36, color: 'text.disabled', mb: 1 }} />
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                No price alerts set. Use the bell icon on any holding to set one.
              </Typography>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent sx={{ p: 0 }}>
              {alerts.filter(a => a.triggered).length > 0 && (
                <Box sx={{ px: 2.5, py: 1, bgcolor: 'rgba(244,67,54,0.06)', borderBottom: '1px solid var(--surface-04)' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <NotificationsActive sx={{ fontSize: '0.9rem', color: 'error.main' }} />
                    <Typography variant="caption" sx={{ color: 'error.main', fontWeight: 600 }}>
                      {alerts.filter(a => a.triggered).length} alert(s) triggered
                    </Typography>
                  </Box>
                </Box>
              )}
              {alerts.map((alert, i) => (
                <AlertRow key={alert.id} alert={alert} isLast={i === alerts.length - 1} onDelete={handleDeleteAlert} />
              ))}
            </CardContent>
          </Card>
        )}
      </Box>

      {/* Trade History */}
      {tradeHistory.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <SectionTitle icon={History}>
            Decision Log
            <Chip label={tradeHistory.length} size="small" sx={{ ml: 1, height: 20, fontSize: '0.65rem', bgcolor: 'var(--surface-08)' }} />
          </SectionTitle>
          <Card>
            <CardContent sx={{ p: 0 }}>
              {tradeHistory.map((entry, i) => (
                <TradeHistoryRow key={entry.id} entry={entry} isLast={i === tradeHistory.length - 1} />
              ))}
            </CardContent>
          </Card>
        </Box>
      )}

      <SellDialog
        open={!!sellOpen}
        data={sellOpen}
        onClose={() => setSellOpen(null)}
        onSubmit={handleSell}
      />
      <SetAlertDialog
        open={!!alertOpen}
        symbol={alertOpen || ''}
        onClose={() => setAlertOpen(null)}
        onSubmit={handleCreateAlert}
      />
      <AddHoldingDialog open={addOpen} onClose={() => { setAddOpen(false); setPrefillSymbol(''); }} onAdd={handleAdd} prefillSymbol={prefillSymbol} />
      <AddMoreDialog
        open={!!addMoreOpen}
        data={addMoreOpen}
        onClose={() => setAddMoreOpen(null)}
        onSubmit={handleAddMore}
      />
      <HoldDialog
        open={!!holdOpen}
        symbol={holdOpen || ''}
        onClose={() => setHoldOpen(null)}
        onSubmit={handleHold}
      />
      <Dialog open={!!complianceWarn} onClose={() => setComplianceWarn(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Compliance Warning</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            <strong>{complianceWarn?.symbol}</strong> has been held for <strong>{complianceWarn?.daysHeld} days</strong> (less than 6 months).
            Are you sure you want to sell?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setComplianceWarn(null)}>No</Button>
          <Button variant="contained" color="error" onClick={() => {
            const { symbol, name, current_price } = complianceWarn;
            setComplianceWarn(null);
            setSellOpen({ symbol, name, current_price });
          }}>
            Yes, proceed to sell
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

const THESIS_OPTIONS = [
  { value: '', label: 'None (skip)' },
  { value: 'earnings_surprise', label: 'Earnings Surprise' },
  { value: 'debt_reduction', label: 'Debt Reduction' },
  { value: 'margin_expansion', label: 'Margin Expansion' },
  { value: 'sector_cycle', label: 'Sector Cycle' },
  { value: 'supply_disruption', label: 'Supply Disruption' },
  { value: 'forced_buying', label: 'Forced Buying' },
  { value: 'management_change', label: 'Management Change' },
  { value: 'balance_sheet_improvement', label: 'Balance Sheet Improvement' },
  { value: 'business_mix_change', label: 'Business Mix Change' },
];

function AddHoldingDialog({ open, onClose, onAdd, prefillSymbol = '' }) {
  const [universe, setUniverse] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);
  const [symbol, setSymbol] = useState(prefillSymbol);
  const [buyPrice, setBuyPrice] = useState('');
  const [buyDate, setBuyDate] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [notes, setNotes] = useState('');
  const [buyThesis, setBuyThesis] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open && universe.length === 0) {
      getStockUniverse().then(setUniverse).catch(() => {});
    }
  }, [open, universe.length]);

  useEffect(() => {
    if (prefillSymbol) {
      setSymbol(prefillSymbol);
      const match = universe.find(s => s.symbol === prefillSymbol);
      if (match) setSelectedStock(match);
    }
  }, [prefillSymbol, universe]);

  const handleSubmit = () => {
    if (!symbol.trim() || !buyPrice || !buyDate) return;
    setSubmitting(true);
    onAdd({
      symbol: symbol.trim().toUpperCase(),
      buy_price: parseFloat(buyPrice),
      buy_date: buyDate,
      quantity: parseInt(quantity) || 1,
      notes: notes.trim() || null,
      buy_thesis: buyThesis || null,
    });
    setSubmitting(false);
    setSelectedStock(null);
    setSymbol('');
    setBuyPrice('');
    setBuyDate('');
    setQuantity('1');
    setNotes('');
    setBuyThesis('');
  };

  const isValid = symbol.trim() && buyPrice && parseFloat(buyPrice) > 0 && buyDate;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Add Holding</DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '16px !important' }}>
        <Autocomplete
          options={universe}
          getOptionLabel={(opt) => typeof opt === 'string' ? opt : `${opt.name} (${opt.symbol})`}
          filterOptions={(options, { inputValue }) => {
            const q = inputValue.toLowerCase();
            return options.filter(o => o.symbol.toLowerCase().includes(q) || o.name.toLowerCase().includes(q)).slice(0, 50);
          }}
          value={selectedStock}
          onChange={(_, val) => {
            setSelectedStock(val);
            setSymbol(val ? val.symbol : '');
          }}
          isOptionEqualToValue={(opt, val) => opt.symbol === val.symbol}
          renderInput={(params) => <TextField {...params} label="Stock" placeholder="Type name or symbol..." size="small" autoFocus />}
          renderOption={(props, opt) => (
            <li {...props} key={opt.symbol}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                <Typography sx={{ fontSize: '0.85rem' }}>{opt.name}</Typography>
                <Typography sx={{ fontSize: '0.75rem', color: 'text.secondary', ml: 1 }}>{opt.symbol}</Typography>
              </Box>
            </li>
          )}
          disabled={!!prefillSymbol}
          noOptionsText="No matching stocks"
        />
        <TextField
          label="Buy Price (₹)"
          type="number"
          value={buyPrice}
          onChange={(e) => setBuyPrice(e.target.value)}
          size="small"
        />
        <TextField
          label="Buy Date"
          type="date"
          value={buyDate}
          onChange={(e) => setBuyDate(e.target.value)}
          size="small"
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          label="Quantity"
          type="number"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          size="small"
        />
        <FormControl size="small">
          <InputLabel sx={{ fontSize: '0.85rem' }}>Buy Thesis (why you bought)</InputLabel>
          <Select
            value={buyThesis}
            label="Buy Thesis (why you bought)"
            onChange={(e) => setBuyThesis(e.target.value)}
          >
            {THESIS_OPTIONS.map(t => <MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>)}
          </Select>
        </FormControl>
        <TextField
          label="Notes (optional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          size="small"
          multiline
          rows={2}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit} disabled={!isValid || submitting}>
          Add
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function HoldingCard({ holding, status, onRemove, onSetAlert, onSell, onHold, onAddMore }) {
  const [open, setOpen] = useState(status === 'alert');
  const navigate = useNavigate();

  const borderColor = status === 'alert' ? 'rgba(244,67,54,0.25)' : status === 'warning' ? 'rgba(255,152,0,0.2)' : undefined;

  return (
    <Card sx={{ mb: 1.5, borderColor }}>
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }} onClick={() => setOpen(!open)}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {status !== 'healthy' && <StatusBadge status={status} />}
            <Box>
              <Typography sx={{ fontWeight: 600, fontSize: '0.95rem' }}>{holding.name}</Typography>
              <Box sx={{ display: 'flex', gap: 1, mt: 0.3 }}>
                <Chip label={holding.symbol} size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'var(--surface-06)' }} />
                <Chip label={holding.sector} size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'var(--surface-06)' }} />
              </Box>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{ textAlign: 'right' }}>
              <Typography sx={{ fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>
                {holding.current_price != null ? `₹${holding.current_price.toLocaleString()}` : '--'}
              </Typography>
              {holding.pnl_pct != null ? (
                <ChangeIndicator value={holding.pnl_pct} fontSize="0.8rem" />
              ) : (
                <Typography variant="caption" sx={{ color: 'text.disabled' }}>--</Typography>
              )}
            </Box>
            <IconButton size="small">
              {open ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
            </IconButton>
          </Box>
        </Box>
        <Collapse in={open}>
          <Box sx={{ mt: 2, pl: 1 }}>
            <Box sx={{ display: 'flex', gap: 3, mb: 2, flexWrap: 'wrap' }}>
              <MiniStat label="Bought at" value={`₹${holding.buy_price}`} />
              <MiniStat label="Current" value={holding.current_price != null ? `₹${holding.current_price}` : '--'} />
              <MiniStat label="P&L" value={holding.pnl_pct != null ? `${holding.pnl_pct > 0 ? '+' : ''}${holding.pnl_pct}%` : '--'} color={holding.pnl_pct >= 0 ? 'success.main' : 'error.main'} />
              <MiniStat label="Held" value={getDaysHeld(holding.buy_date) != null ? `${getDaysHeld(holding.buy_date)} days` : '--'} />
            </Box>
            {getDaysHeld(holding.buy_date) >= 183 && (
              <Chip label="6-month holding period complete" size="small" sx={{ mb: 2, height: 22, fontSize: '0.65rem', fontWeight: 600, bgcolor: 'rgba(76,175,80,0.12)', color: 'success.main' }} />
            )}
            {holding.signals.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontSize: '0.7rem', mb: 1 }}>Exit Signals Detected</Typography>
                {holding.signals.map((sig, i) => (
                  <Box key={i} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 0.5 }}>
                    <ErrorOutline sx={{ fontSize: '0.85rem', color: status === 'alert' ? 'error.main' : 'warning.main', mt: 0.2 }} />
                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>{sig}</Typography>
                  </Box>
                ))}
              </Box>
            )}
            {holding.setup_review && (
              <Box sx={{
                mb: 2, p: 1.5, borderRadius: 1,
                bgcolor: holding.setup_review.still_valid ? 'rgba(76,175,80,0.06)' : 'rgba(244,67,54,0.06)',
                border: `1px solid ${holding.setup_review.still_valid ? 'rgba(76,175,80,0.2)' : 'rgba(244,67,54,0.2)'}`,
              }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                  <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>
                    Setup Review: {holding.buy_thesis?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  </Typography>
                  <Chip
                    label={holding.setup_review.still_valid ? 'INTACT' : 'WEAKENING'}
                    size="small"
                    sx={{
                      height: 18, fontSize: '0.55rem', fontWeight: 700,
                      bgcolor: holding.setup_review.still_valid ? 'rgba(76,175,80,0.15)' : 'rgba(244,67,54,0.15)',
                      color: holding.setup_review.still_valid ? 'success.main' : 'error.main',
                    }}
                  />
                </Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
                  {holding.setup_review.reason}
                </Typography>
                {holding.setup_review.detail && (
                  <Typography variant="caption" sx={{ color: 'text.disabled', display: 'block', mt: 0.5 }}>
                    {holding.setup_review.detail}
                  </Typography>
                )}
              </Box>
            )}
            {holding.buy_thesis && !holding.setup_review && (
              <Box sx={{ mb: 2, p: 1, borderRadius: 1, bgcolor: 'var(--surface-03)' }}>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  Buy thesis: {holding.buy_thesis.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                </Typography>
              </Box>
            )}
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Button size="small" variant="contained" color="error" startIcon={<Sell />}
                onClick={(e) => { e.stopPropagation(); onSell({ symbol: holding.symbol, name: holding.name, current_price: holding.current_price, buy_date: holding.buy_date }); }}>
                Sell
              </Button>
              <Button size="small" variant="outlined" color="success" startIcon={<PanTool />}
                onClick={(e) => { e.stopPropagation(); onHold(holding.symbol); }}
                sx={{ textTransform: 'none', fontSize: { xs: '0.7rem', sm: '0.85rem' } }}>
                Hold
              </Button>
              <Button size="small" variant="outlined" startIcon={<Add />}
                onClick={(e) => { e.stopPropagation(); onAddMore({ symbol: holding.symbol, name: holding.name }); }}
                sx={{ textTransform: 'none', fontSize: { xs: '0.7rem', sm: '0.85rem' } }}>
                Add More
              </Button>
              <Button size="small" variant="outlined" startIcon={<Notifications />}
                onClick={(e) => { e.stopPropagation(); onSetAlert(holding.symbol); }}>
                Set Alert
              </Button>
              <Button size="small" variant="text" onClick={() => navigate(`/stock/${holding.symbol}`)}>
                View Details
              </Button>
            </Box>
          </Box>
        </Collapse>
      </CardContent>
    </Card>
  );
}

function HoldingRow({ holding, isLast, onRemove }) {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 2.5, py: 1.5,
        borderBottom: isLast ? 'none' : '1px solid var(--surface-04)',
        cursor: 'pointer', transition: 'background-color 0.15s',
        '&:hover': { bgcolor: 'var(--surface-02)' },
      }}
      onClick={() => navigate(`/stock/${holding.symbol}`)}
    >
      <Box>
        <Typography sx={{ fontWeight: 500, fontSize: '0.9rem' }}>{holding.name}</Typography>
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>{holding.sector}</Typography>
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
        <Box sx={{ textAlign: 'right', display: { xs: 'none', sm: 'block' } }}>
          <Typography variant="caption">Bought</Typography>
          <Typography sx={{ fontVariantNumeric: 'tabular-nums', fontSize: '0.85rem' }}>₹{holding.buy_price}</Typography>
        </Box>
        <Box sx={{ textAlign: 'right' }}>
          <Typography variant="caption">Current</Typography>
          <Typography sx={{ fontVariantNumeric: 'tabular-nums', fontSize: '0.85rem' }}>
            {holding.current_price != null ? `₹${holding.current_price}` : '--'}
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'right', minWidth: 60 }}>
          {holding.pnl_pct != null ? (
            <ChangeIndicator value={holding.pnl_pct} />
          ) : (
            <Typography variant="caption" sx={{ color: 'text.disabled' }}>--</Typography>
          )}
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 40 }}>
          <Typography variant="caption" sx={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
            {getDaysHeld(holding.buy_date) != null ? `${getDaysHeld(holding.buy_date)}d` : '--'}
          </Typography>
          {getDaysHeld(holding.buy_date) >= 183 && (
            <Chip label="6mo+" size="small" sx={{ height: 18, fontSize: '0.55rem', fontWeight: 600, bgcolor: 'rgba(76,175,80,0.12)', color: 'success.main' }} />
          )}
        </Box>
        <IconButton size="small" onClick={(e) => { e.stopPropagation(); onRemove(holding.symbol); }}
          sx={{ color: 'text.secondary', '&:hover': { color: 'error.main' } }}>
          <Delete fontSize="small" />
        </IconButton>
      </Box>
    </Box>
  );
}

function MiniStat({ label, value, color }) {
  return (
    <Box>
      <Typography variant="caption">{label}</Typography>
      <Typography sx={{ fontWeight: 600, fontSize: '0.9rem', color: color || 'text.primary', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </Typography>
    </Box>
  );
}

function WatchlistRow({ item, isLast, onRemove, onAddToPortfolio }) {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 2.5, py: 1.5,
        borderBottom: isLast ? 'none' : '1px solid var(--surface-04)',
        cursor: 'pointer', transition: 'background-color 0.15s',
        '&:hover': { bgcolor: 'var(--surface-02)' },
      }}
      onClick={() => navigate(`/stock/${item.symbol}`)}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Bookmark sx={{ fontSize: '1rem', color: 'primary.main' }} />
        <Box>
          <Typography sx={{ fontWeight: 500, fontSize: '0.9rem' }}>{item.name}</Typography>
          <Box sx={{ display: 'flex', gap: 0.5, mt: 0.3 }}>
            <Chip label={item.symbol} size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'var(--surface-06)' }} />
            <Chip label={item.sector} size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'var(--surface-06)' }} />
            {item.market_cap_cr != null && (
              <Chip
                label={item.market_cap_cr >= 10000 ? `${(item.market_cap_cr / 1000).toFixed(0)}K Cr` : `${item.market_cap_cr.toLocaleString()} Cr`}
                size="small"
                sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'var(--surface-06)' }}
              />
            )}
          </Box>
        </Box>
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Button
          size="small"
          variant="outlined"
          startIcon={<Add />}
          onClick={(e) => { e.stopPropagation(); onAddToPortfolio(item.symbol); }}
          sx={{ textTransform: 'none', fontSize: '0.7rem', whiteSpace: 'nowrap' }}
        >
          Add to Portfolio
        </Button>
        <Box sx={{ textAlign: 'right' }}>
          <Typography variant="caption">Price</Typography>
          <Typography sx={{ fontVariantNumeric: 'tabular-nums', fontSize: '0.85rem' }}>
            {item.current_price != null ? `₹${item.current_price}` : '--'}
          </Typography>
        </Box>
        {item.notes && (
          <Typography variant="caption" sx={{ color: 'text.secondary', maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: { xs: 'none', md: 'block' } }}>
            {item.notes}
          </Typography>
        )}
        <IconButton size="small" onClick={(e) => { e.stopPropagation(); onRemove(item.symbol); }}
          sx={{ color: 'text.secondary', '&:hover': { color: 'error.main' } }}>
          <Delete fontSize="small" />
        </IconButton>
      </Box>
    </Box>
  );
}

function SetAlertDialog({ open, symbol, onClose, onSubmit }) {
  const [alertType, setAlertType] = useState('above');
  const [targetPrice, setTargetPrice] = useState('');
  const [notes, setNotes] = useState('');

  const handleSubmit = () => {
    if (!targetPrice || parseFloat(targetPrice) <= 0) return;
    onSubmit({
      symbol: symbol.toUpperCase(),
      alert_type: alertType,
      target_price: parseFloat(targetPrice),
      notes: notes.trim() || null,
    });
    setTargetPrice('');
    setNotes('');
    setAlertType('above');
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Set Price Alert — {symbol}</DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '16px !important' }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant={alertType === 'above' ? 'contained' : 'outlined'}
            size="small"
            onClick={() => setAlertType('above')}
            sx={{ flex: 1, textTransform: 'none' }}
          >
            Price goes above
          </Button>
          <Button
            variant={alertType === 'below' ? 'contained' : 'outlined'}
            size="small"
            color="error"
            onClick={() => setAlertType('below')}
            sx={{ flex: 1, textTransform: 'none' }}
          >
            Price drops below
          </Button>
        </Box>
        <TextField
          label="Target Price (₹)"
          type="number"
          value={targetPrice}
          onChange={(e) => setTargetPrice(e.target.value)}
          size="small"
          autoFocus
        />
        <TextField
          label="Notes (optional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          size="small"
          placeholder="e.g. Breakout confirmation level"
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit} disabled={!targetPrice || parseFloat(targetPrice) <= 0}>
          Set Alert
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function AlertRow({ alert, isLast, onDelete }) {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 2.5, py: 1.5,
        borderBottom: isLast ? 'none' : '1px solid var(--surface-04)',
        bgcolor: alert.triggered ? 'rgba(244,67,54,0.04)' : 'transparent',
        cursor: 'pointer', '&:hover': { bgcolor: 'var(--surface-02)' },
      }}
      onClick={() => navigate(`/stock/${alert.symbol}`)}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
        {alert.triggered ? (
          <NotificationsActive sx={{ fontSize: '1.1rem', color: 'error.main' }} />
        ) : (
          <Notifications sx={{ fontSize: '1.1rem', color: 'text.secondary' }} />
        )}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography sx={{ fontWeight: 500, fontSize: '0.9rem' }}>{alert.name}</Typography>
            {alert.triggered && (
              <Chip label="TRIGGERED" size="small" sx={{ height: 18, fontSize: '0.55rem', fontWeight: 700, bgcolor: 'rgba(244,67,54,0.15)', color: 'error.main' }} />
            )}
          </Box>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {alert.alert_type === 'above' ? 'Price above' : 'Price below'} ₹{alert.target_price}
            {alert.notes ? ` — ${alert.notes}` : ''}
          </Typography>
        </Box>
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box sx={{ textAlign: 'right' }}>
          <Typography variant="caption">Current</Typography>
          <Typography sx={{ fontVariantNumeric: 'tabular-nums', fontSize: '0.85rem' }}>
            {alert.current_price != null ? `₹${alert.current_price}` : '--'}
          </Typography>
        </Box>
        <IconButton size="small" onClick={(e) => { e.stopPropagation(); onDelete(alert.id); }}
          sx={{ color: 'text.secondary', '&:hover': { color: 'error.main' } }}>
          <Delete fontSize="small" />
        </IconButton>
      </Box>
    </Box>
  );
}

function SellDialog({ open, data, onClose, onSubmit }) {
  const [sellPrice, setSellPrice] = useState('');
  const [reason, setReason] = useState('');

  useEffect(() => {
    if (data?.current_price) setSellPrice(String(data.current_price));
  }, [data]);

  const handleSubmit = () => {
    if (!sellPrice || parseFloat(sellPrice) <= 0) return;
    onSubmit({
      symbol: data.symbol,
      sell_price: parseFloat(sellPrice),
      reason: reason.trim() || null,
    });
    setSellPrice('');
    setReason('');
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Sell {data?.symbol}</DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '16px !important' }}>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          Selling {data?.name}. This will remove it from your portfolio and log the trade.
        </Typography>
        <TextField
          label="Sell Price (₹)"
          type="number"
          value={sellPrice}
          onChange={(e) => setSellPrice(e.target.value)}
          size="small"
          autoFocus
        />
        <TextField
          label="Reason (optional)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          size="small"
          placeholder="e.g. Exit signals confirmed, thesis no longer valid"
          multiline
          rows={2}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" color="error" onClick={handleSubmit} disabled={!sellPrice || parseFloat(sellPrice) <= 0}>
          Confirm Sell
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function AddMoreDialog({ open, data, onClose, onSubmit }) {
  const [quantity, setQuantity] = useState('');
  const [buyPrice, setBuyPrice] = useState('');

  useEffect(() => {
    if (open) { setQuantity(''); setBuyPrice(''); }
  }, [open]);

  const handleSubmit = () => {
    if (!quantity || parseInt(quantity) <= 0 || !buyPrice || parseFloat(buyPrice) <= 0) return;
    onSubmit({
      symbol: data.symbol,
      quantity: parseInt(quantity),
      buy_price: parseFloat(buyPrice),
    });
  };

  const isValid = quantity && parseInt(quantity) > 0 && buyPrice && parseFloat(buyPrice) > 0;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Add More — {data?.symbol}</DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '16px !important' }}>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          Adding more shares to {data?.name}. The buy price will be averaged with your existing position.
        </Typography>
        <TextField
          label="Quantity"
          type="number"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          size="small"
          autoFocus
        />
        <TextField
          label="Buy Price (₹)"
          type="number"
          value={buyPrice}
          onChange={(e) => setBuyPrice(e.target.value)}
          size="small"
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit} disabled={!isValid}>
          Add Shares
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function HoldDialog({ open, symbol, onClose, onSubmit }) {
  const [reason, setReason] = useState('');

  useEffect(() => {
    if (open) setReason('');
  }, [open]);

  const handleSubmit = () => {
    onSubmit({ symbol, reason: reason.trim() || null });
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Hold — {symbol}</DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '16px !important' }}>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          Log a HOLD decision for {symbol}. This will be recorded in the Decision Log.
        </Typography>
        <TextField
          label="Why are you choosing to hold? (optional)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          size="small"
          autoFocus
          multiline
          rows={2}
          placeholder="e.g. Thesis still intact, waiting for breakout confirmation"
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" color="success" onClick={handleSubmit}>
          Confirm Hold
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function TradeHistoryRow({ entry, isLast }) {
  const isSell = entry.action === 'SELL';

  return (
    <Box
      sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 2.5, py: 1.5,
        borderBottom: isLast ? 'none' : '1px solid var(--surface-04)',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Chip
          label={entry.action}
          size="small"
          sx={{
            height: 22, fontSize: '0.6rem', fontWeight: 700,
            bgcolor: isSell ? 'rgba(244,67,54,0.15)' : 'rgba(76,175,80,0.15)',
            color: isSell ? 'error.main' : 'success.main',
          }}
        />
        <Box>
          <Typography sx={{ fontWeight: 500, fontSize: '0.9rem' }}>{entry.name}</Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {entry.decided_at?.split('T')[0] || entry.decided_at?.split(' ')[0]}
            {entry.reason ? ` — ${entry.reason}` : ''}
          </Typography>
        </Box>
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
        {isSell && (
          <>
            <Box sx={{ textAlign: 'right', display: { xs: 'none', sm: 'block' } }}>
              <Typography variant="caption">Buy → Sell</Typography>
              <Typography sx={{ fontVariantNumeric: 'tabular-nums', fontSize: '0.8rem' }}>
                ₹{entry.buy_price} → ₹{entry.sell_price}
              </Typography>
            </Box>
            <Box sx={{ textAlign: 'right', minWidth: 60 }}>
              {entry.pnl_pct != null && (
                <Typography sx={{
                  fontWeight: 600, fontSize: '0.85rem', fontVariantNumeric: 'tabular-nums',
                  color: entry.pnl_pct >= 0 ? 'success.main' : 'error.main',
                }}>
                  {entry.pnl_pct > 0 ? '+' : ''}{entry.pnl_pct}%
                </Typography>
              )}
            </Box>
          </>
        )}
        {!isSell && (
          <Box sx={{ textAlign: 'right' }}>
            <Typography variant="caption">Price at decision</Typography>
            <Typography sx={{ fontVariantNumeric: 'tabular-nums', fontSize: '0.8rem' }}>
              {entry.sell_price != null ? `₹${entry.sell_price}` : '--'}
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
}

function LegendItem({ color, label }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: color }} />
      <Typography variant="caption">{label}</Typography>
    </Box>
  );
}
