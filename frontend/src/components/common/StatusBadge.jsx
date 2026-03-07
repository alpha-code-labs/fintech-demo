import { Chip } from '@mui/material';

const statusConfig = {
  healthy: { label: 'HEALTHY', color: '#4caf50', bg: 'rgba(76,175,80,0.12)' },
  ok: { label: 'OK', color: '#4caf50', bg: 'rgba(76,175,80,0.12)' },
  warning: { label: 'WATCH', color: '#ff9800', bg: 'rgba(255,152,0,0.12)' },
  watch: { label: 'WATCH', color: '#ff9800', bg: 'rgba(255,152,0,0.12)' },
  alert: { label: 'REVIEW', color: '#f44336', bg: 'rgba(244,67,54,0.12)' },
  review: { label: 'REVIEW', color: '#f44336', bg: 'rgba(244,67,54,0.12)' },
};

export default function StatusBadge({ status }) {
  const config = statusConfig[status?.toLowerCase()] || statusConfig.healthy;

  return (
    <Chip
      label={config.label}
      size="small"
      sx={{
        backgroundColor: config.bg,
        color: config.color,
        fontWeight: 700,
        fontSize: '0.7rem',
        letterSpacing: '0.06em',
        border: `1px solid ${config.color}30`,
        height: 24,
      }}
    />
  );
}
