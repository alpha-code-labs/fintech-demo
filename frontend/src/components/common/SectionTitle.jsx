import { Typography, Box, Divider } from '@mui/material';

export default function SectionTitle({ children, icon: Icon, action }) {
  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {Icon && <Icon sx={{ fontSize: '1.2rem', color: 'primary.main' }} />}
          <Typography variant="h6">{children}</Typography>
        </Box>
        {action}
      </Box>
      <Divider sx={{ mt: 1, borderColor: 'var(--surface-06)' }} />
    </Box>
  );
}
