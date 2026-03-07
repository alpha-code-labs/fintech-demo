import { createTheme } from '@mui/material/styles';

export default function getTheme(mode) {
  const isDark = mode === 'dark';

  return createTheme({
    palette: {
      mode,
      primary: { main: isDark ? '#4fc3f7' : '#0288d1' },
      secondary: { main: '#81c784' },
      background: {
        default: isDark ? '#0a0e17' : '#f5f7fa',
        paper: isDark ? '#111827' : '#ffffff',
      },
      success: { main: '#4caf50' },
      warning: { main: '#ff9800' },
      error: { main: '#f44336' },
      text: isDark
        ? {
            primary: '#ffffff',
            secondary: 'rgba(255,255,255,0.7)',
            disabled: 'rgba(255,255,255,0.38)',
          }
        : {
            primary: 'rgba(0,0,0,0.87)',
            secondary: 'rgba(0,0,0,0.6)',
            disabled: 'rgba(0,0,0,0.38)',
          },
      divider: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.12)',
    },
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica", sans-serif',
      h4: { fontWeight: 700, fontSize: '1.75rem', letterSpacing: '-0.02em', '@media (max-width:600px)': { fontSize: '1.3rem' } },
      h5: { fontWeight: 600, fontSize: '1.25rem', letterSpacing: '-0.01em', '@media (max-width:600px)': { fontSize: '1.05rem' } },
      h6: { fontWeight: 600, fontSize: '1.1rem', '@media (max-width:600px)': { fontSize: '0.95rem' } },
      subtitle1: { fontWeight: 500, fontSize: '0.95rem', color: isDark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.6)' },
      subtitle2: { fontWeight: 500, fontSize: '0.8rem', color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)', textTransform: 'uppercase', letterSpacing: '0.08em' },
      body1: { fontSize: '0.9rem' },
      body2: { fontSize: '0.8rem', color: isDark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.6)' },
      caption: { fontSize: '0.75rem', color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' },
    },
    shape: {
      borderRadius: 12,
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            scrollbarWidth: 'thin',
            scrollbarColor: isDark ? 'rgba(255,255,255,0.15) transparent' : 'rgba(0,0,0,0.2) transparent',
            '--surface-02': isDark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)',
            '--surface-03': isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)',
            '--surface-04': isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)',
            '--surface-06': isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
            '--surface-08': isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.10)',
            '--surface-10': isDark ? 'rgba(255,255,255,0.10)' : 'rgba(0,0,0,0.12)',
            '--surface-12': isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.10)',
            '--surface-15': isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.15)',
            '--muted-20': isDark ? 'rgba(255,255,255,0.20)' : 'rgba(0,0,0,0.25)',
            '--muted-30': isDark ? 'rgba(255,255,255,0.30)' : 'rgba(0,0,0,0.35)',
            '--muted-40': isDark ? 'rgba(255,255,255,0.40)' : 'rgba(0,0,0,0.50)',
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 12,
            border: isDark ? '1px solid rgba(255,255,255,0.08)' : '1px solid rgba(0,0,0,0.10)',
            backgroundImage: 'none',
          },
        },
      },
      MuiCardContent: {
        styleOverrides: {
          root: {
            padding: 20,
            '&:last-child': { paddingBottom: 20 },
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 6,
            fontWeight: 500,
            fontSize: '0.75rem',
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            textTransform: 'none',
            fontWeight: 600,
            fontSize: '0.85rem',
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          root: {
            borderBottomColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)',
            fontSize: '0.85rem',
          },
          head: {
            fontWeight: 600,
            fontSize: '0.75rem',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)',
          },
        },
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: {
            backgroundColor: isDark ? '#1e293b' : '#ffffff',
            border: isDark ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(0,0,0,0.12)',
            fontSize: '0.8rem',
            color: isDark ? '#ffffff' : 'rgba(0,0,0,0.87)',
          },
        },
      },
    },
  });
}
