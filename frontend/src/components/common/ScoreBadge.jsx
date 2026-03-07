import { Box, Typography } from '@mui/material';

export default function ScoreBadge({ score, max = 8, size = 'medium' }) {
  const ratio = score / max;
  const color = ratio >= 0.75 ? '#4caf50' : ratio >= 0.5 ? '#ff9800' : '#f44336';
  const dim = size === 'small' ? 36 : size === 'large' ? 56 : 44;
  const fontSize = size === 'small' ? '0.75rem' : size === 'large' ? '1.1rem' : '0.9rem';

  return (
    <Box
      sx={{
        width: dim,
        height: dim,
        borderRadius: '50%',
        border: `2.5px solid ${color}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: `${color}15`,
        flexShrink: 0,
      }}
    >
      <Typography sx={{ fontWeight: 700, fontSize, color, fontVariantNumeric: 'tabular-nums' }}>
        {score}/{max}
      </Typography>
    </Box>
  );
}
