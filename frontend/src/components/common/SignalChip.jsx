import { Chip } from '@mui/material';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import CancelOutlinedIcon from '@mui/icons-material/CancelOutlined';

export default function SignalChip({ label, value, showLabel = true }) {
  const isYes = value === true || value === 'YES';

  return (
    <Chip
      icon={isYes
        ? <CheckCircleOutlineIcon sx={{ fontSize: '0.9rem', color: '#4caf50 !important' }} />
        : <CancelOutlinedIcon sx={{ fontSize: '0.9rem', color: 'var(--muted-30) !important' }} />
      }
      label={showLabel ? label : (isYes ? 'YES' : 'NO')}
      size="small"
      variant="outlined"
      sx={{
        borderColor: isYes ? 'rgba(76,175,80,0.3)' : 'var(--surface-10)',
        color: isYes ? '#4caf50' : 'var(--muted-40)',
        fontSize: '0.75rem',
        '& .MuiChip-icon': { ml: '6px' },
      }}
    />
  );
}
