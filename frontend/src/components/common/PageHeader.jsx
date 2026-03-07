import { Box, Typography } from '@mui/material';

export default function PageHeader({ title, subtitle, right }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: { xs: 2, md: 3 }, flexWrap: 'wrap', gap: 1 }}>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="h4" sx={{ fontSize: { xs: '1.3rem', sm: '2.125rem' } }}>{title}</Typography>
        {subtitle && (
          <Typography variant="subtitle1" sx={{ mt: 0.5, fontSize: { xs: '0.8rem', sm: '1rem' } }}>
            {subtitle}
          </Typography>
        )}
      </Box>
      {right && <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>{right}</Box>}
    </Box>
  );
}
