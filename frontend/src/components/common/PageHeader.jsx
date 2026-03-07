import { Box, Typography } from '@mui/material';

export default function PageHeader({ title, subtitle, right }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 1 }}>
      <Box>
        <Typography variant="h4">{title}</Typography>
        {subtitle && (
          <Typography variant="subtitle1" sx={{ mt: 0.5 }}>
            {subtitle}
          </Typography>
        )}
      </Box>
      {right && <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>{right}</Box>}
    </Box>
  );
}
