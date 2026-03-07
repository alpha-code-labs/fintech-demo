import { Chip, Box, Typography } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat';

const phaseConfig = {
  BULLISH: { color: '#4caf50', bg: 'rgba(76,175,80,0.12)', icon: TrendingUpIcon },
  'CAUTIOUSLY BULLISH': { color: '#81c784', bg: 'rgba(129,199,132,0.12)', icon: TrendingUpIcon },
  SIDEWAYS: { color: '#ff9800', bg: 'rgba(255,152,0,0.12)', icon: TrendingFlatIcon },
  BEARISH: { color: '#f44336', bg: 'rgba(244,67,54,0.12)', icon: TrendingDownIcon },
};

export default function MarketPhaseBadge({ label, reason, size = 'large' }) {
  const config = phaseConfig[label] || phaseConfig.SIDEWAYS;
  const Icon = config.icon;

  if (size === 'small') {
    return (
      <Chip
        icon={<Icon sx={{ fontSize: '1rem', color: `${config.color} !important` }} />}
        label={label}
        size="small"
        sx={{
          backgroundColor: config.bg,
          color: config.color,
          fontWeight: 600,
          fontSize: '0.75rem',
          border: `1px solid ${config.color}30`,
        }}
      />
    );
  }

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        p: 2,
        borderRadius: 2,
        backgroundColor: config.bg,
        border: `1px solid ${config.color}30`,
      }}
    >
      <Icon sx={{ fontSize: { xs: '1.2rem', sm: '2rem' }, color: config.color, flexShrink: 0 }} />
      <Box sx={{ minWidth: 0 }}>
        <Typography sx={{ fontWeight: 700, fontSize: { xs: '0.75rem', sm: '1.1rem' }, color: config.color, letterSpacing: '0.04em' }}>
          <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>MARKET PHASE: </Box>{label}
        </Typography>
        {reason && (
          <Typography variant="body2" sx={{ mt: 0.3, color: 'text.secondary' }}>
            {reason}
          </Typography>
        )}
      </Box>
    </Box>
  );
}
