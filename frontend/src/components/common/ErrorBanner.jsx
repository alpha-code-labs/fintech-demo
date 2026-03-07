import { Alert, Button } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';

export default function ErrorBanner({ message = 'Something went wrong. Please try again.', onRetry }) {
  return (
    <Alert
      severity="error"
      sx={{
        borderRadius: 2,
        backgroundColor: 'rgba(244,67,54,0.08)',
        border: '1px solid rgba(244,67,54,0.2)',
        '& .MuiAlert-icon': { color: 'error.main' },
      }}
      action={
        onRetry && (
          <Button color="error" size="small" startIcon={<RefreshIcon />} onClick={onRetry}>
            Retry
          </Button>
        )
      }
    >
      {message}
    </Alert>
  );
}
