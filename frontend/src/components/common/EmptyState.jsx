import { Box, Typography } from '@mui/material';
import InboxIcon from '@mui/icons-material/Inbox';

export default function EmptyState({ message = 'No data available', icon: Icon = InboxIcon }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 8, opacity: 0.5 }}>
      <Icon sx={{ fontSize: 48, mb: 2, color: 'text.secondary' }} />
      <Typography variant="body1" color="text.secondary">{message}</Typography>
    </Box>
  );
}
