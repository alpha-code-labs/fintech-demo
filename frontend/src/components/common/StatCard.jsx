import { Card, CardContent, Typography, Box } from '@mui/material';
import ChangeIndicator from './ChangeIndicator';

export default function StatCard({ label, value, prefix = '', suffix = '', change, unit, sx = {} }) {
  return (
    <Card sx={{ height: '100%', ...sx }}>
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Typography variant="subtitle2" sx={{ mb: 1, fontSize: '0.7rem' }}>
          {label}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="h5" sx={{ fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
            {prefix}{typeof value === 'number' ? value.toLocaleString('en-IN') : value}
            {unit && <Typography component="span" sx={{ fontSize: '0.75rem', ml: 0.5, color: 'text.secondary' }}>{unit}</Typography>}
          </Typography>
          {change !== undefined && change !== null && (
            <ChangeIndicator value={change} />
          )}
        </Box>
        {suffix && (
          <Typography variant="caption" sx={{ mt: 0.5, display: 'block' }}>{suffix}</Typography>
        )}
      </CardContent>
    </Card>
  );
}
