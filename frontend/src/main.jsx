import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { useMediaQuery, useTheme } from '@mui/material';
import { BrowserRouter } from 'react-router-dom';
import { SnackbarProvider } from 'notistack';
import { ThemeModeProvider } from './context/ThemeContext';
import App from './App';
import './index.css';

function Root() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  return (
    <SnackbarProvider
      maxSnack={3}
      anchorOrigin={isMobile ? { vertical: 'top', horizontal: 'center' } : { vertical: 'bottom', horizontal: 'right' }}
      autoHideDuration={3000}
    >
      <App />
    </SnackbarProvider>
  );
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeModeProvider>
        <Root />
      </ThemeModeProvider>
    </BrowserRouter>
  </StrictMode>
);
