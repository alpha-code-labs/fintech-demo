import { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, Chip, Button, Divider
} from '@mui/material';
import {
  Language, Flag, TrendingUp, NotificationsActive,
  ArrowForward, Email, WhatsApp
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { getBriefing } from '../services/api';
import {
  PageHeader, MarketPhaseBadge, ScoreBadge, StatusBadge,
  SectionTitle, ErrorBanner
} from '../components/common';
import { SkeletonPage } from '../components/common/LoadingSkeleton';

export default function WeeklyBriefing() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    getBriefing()
      .then(setData)
      .catch(() => setError('Failed to load briefing'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <SkeletonPage />;
  if (error) return <ErrorBanner message={error} onRetry={fetchData} />;
  if (!data) return null;

  return (
    <Box>
      <PageHeader
        title="Weekly Briefing"
        subtitle="Your weekend summary — auto-generated"
        right={
          <Chip label={`Week ending: ${data.week_ending}`} size="small" sx={{ fontWeight: 500 }} />
        }
      />

      {/* Market Phase */}
      <Box sx={{ mb: 3 }}>
        <MarketPhaseBadge label={data.market_phase} reason={`${data.market_phase_change} from last week`} />
      </Box>

      {/* World + India */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Language sx={{ fontSize: '1.2rem', color: 'primary.main' }} />
                <Typography variant="h6">World</Typography>
              </Box>
              <Typography variant="body1" sx={{ lineHeight: 1.8, color: 'text.secondary' }}>
                {data.world}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Flag sx={{ fontSize: '1.2rem', color: 'primary.main' }} />
                <Typography variant="h6">India</Typography>
              </Box>
              <Typography variant="body1" sx={{ lineHeight: 1.8, color: 'text.secondary' }}>
                {data.india}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Sectors */}
      <Box sx={{ mb: 3 }}>
        <SectionTitle icon={TrendingUp}>Sectors</SectionTitle>
        <Grid container spacing={1.5}>
          {data.sectors.map((s) => {
            const isStrong = s.note.toLowerCase().includes('strongest') || s.note.toLowerCase().includes('emerging');
            const isWeak = s.note.toLowerCase().includes('weakening') || s.note.toLowerCase().includes('broken');
            return (
              <Grid size={{ xs: 12, sm: 4 }} key={s.name}>
                <Card sx={{
                  borderColor: isStrong ? 'rgba(76,175,80,0.2)' : isWeak ? 'rgba(244,67,54,0.15)' : 'var(--surface-08)',
                }}>
                  <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                    <Typography sx={{ fontWeight: 600, mb: 0.5 }}>{s.name}</Typography>
                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>{s.note}</Typography>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      </Box>

      {/* New Signals */}
      <Box sx={{ mb: 3 }}>
        <SectionTitle
          icon={NotificationsActive}
          action={
            <Button size="small" endIcon={<ArrowForward />} onClick={() => navigate('/scanner')}>
              View All {data.new_signals_count}
            </Button>
          }
        >
          New Signals: {data.new_signals_count} stocks triggered
        </SectionTitle>
        <Grid container spacing={1.5}>
          {data.top_signals.map((s, i) => (
            <Grid size={{ xs: 12, sm: 4 }} key={s.symbol}>
              <Card
                sx={{
                  cursor: 'pointer', transition: 'all 0.2s',
                  '&:hover': { transform: 'translateY(-2px)', boxShadow: '0 4px 12px rgba(0,0,0,0.4)' },
                }}
                onClick={() => navigate(`/stock/${s.symbol}`)}
              >
                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Box>
                      <Typography sx={{ fontWeight: 500, fontSize: '0.7rem', color: 'text.secondary' }}>
                        #{i + 1}
                      </Typography>
                      <Typography sx={{ fontWeight: 600, fontSize: '0.95rem' }}>
                        {s.name}
                      </Typography>
                    </Box>
                    <ScoreBadge score={s.score} size="small" />
                  </Box>
                  <Chip label={s.sector} size="small" sx={{ height: 20, fontSize: '0.65rem', mr: 0.5, bgcolor: 'var(--surface-06)' }} />
                  <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
                    {s.note}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Portfolio Alerts */}
      {data.portfolio_alerts.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <SectionTitle
            icon={NotificationsActive}
            action={
              <Button size="small" endIcon={<ArrowForward />} onClick={() => navigate('/portfolio')}>
                Review Portfolio
              </Button>
            }
          >
            Portfolio Alerts
          </SectionTitle>
          {data.portfolio_alerts.map((a) => (
            <Card
              key={a.symbol}
              sx={{
                mb: 1, cursor: 'pointer', transition: 'all 0.2s',
                borderColor: a.level === 'alert' ? 'rgba(244,67,54,0.2)' : 'rgba(255,152,0,0.15)',
                '&:hover': { bgcolor: 'var(--surface-02)' },
              }}
              onClick={() => navigate('/portfolio')}
            >
              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <StatusBadge status={a.level} />
                  <Box>
                    <Typography sx={{ fontWeight: 600, fontSize: '0.9rem' }}>{a.name}</Typography>
                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>{a.note}</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {/* Quick Actions */}
      <Card sx={{ borderColor: 'rgba(79,195,247,0.1)' }}>
        <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Button variant="contained" size="small" onClick={() => navigate('/')}>Open Dashboard</Button>
              <Button variant="outlined" size="small" onClick={() => navigate('/scanner')}>View All Signals</Button>
              <Button variant="outlined" size="small" onClick={() => navigate('/portfolio')}>Review Portfolio</Button>
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Chip icon={<WhatsApp sx={{ fontSize: '0.9rem' }} />} label="WhatsApp" size="small" variant="outlined" sx={{ borderColor: 'var(--surface-10)' }} />
              <Chip icon={<Email sx={{ fontSize: '0.9rem' }} />} label="Email" size="small" variant="outlined" sx={{ borderColor: 'var(--surface-10)' }} />
            </Box>
          </Box>
          <Divider sx={{ my: 1.5, borderColor: 'var(--surface-06)' }} />
          <Typography variant="caption" sx={{ color: 'text.disabled' }}>
            Delivered via: In-app + WhatsApp (optional) + Email (optional). Generated by AI from the week's data.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}
