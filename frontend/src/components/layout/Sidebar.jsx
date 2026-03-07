import {
  Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  Box, Typography, useMediaQuery, useTheme, IconButton,
  BottomNavigation, BottomNavigationAction, Paper
} from '@mui/material';
import {
  Public, Scanner, AccountBalance, Assessment, Summarize,
  DarkMode, LightMode, Architecture
} from '@mui/icons-material';
import { useLocation, useNavigate } from 'react-router-dom';
import { useThemeMode } from '../../context/ThemeContext';

const DRAWER_WIDTH = 260;

const navItems = [
  { label: 'Global Pulse', short: 'Pulse', path: '/', icon: Public, description: 'Market overview' },
  { label: 'Signal Scanner', short: 'Scanner', path: '/scanner', icon: Scanner, description: 'Weekly stock scan' },
  { label: 'Portfolio', short: 'Portfolio', path: '/portfolio', icon: AccountBalance, description: 'Your holdings' },
  { label: 'Reporting', short: 'Report', path: '/reporting', icon: Assessment, description: 'Portfolio report' },
  { label: 'Briefing', short: 'Briefing', path: '/briefing', icon: Summarize, description: 'Weekly summary' },
  { label: 'Data Blueprint', short: 'Blueprint', path: '/blueprint', icon: Architecture, description: 'Technical reference' },
];

function isActive(item, pathname) {
  if (item.matchPrefix) return pathname.startsWith(item.matchPrefix);
  return pathname === item.path;
}

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { mode, toggleMode } = useThemeMode();

  if (isMobile) {
    const activeIdx = navItems.findIndex(item => isActive(item, location.pathname));
    return (
      <Paper
        sx={{
          position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 1200,
          borderTop: '1px solid var(--surface-08)',
          bgcolor: 'background.paper',
        }}
        elevation={8}
      >
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <BottomNavigation
            value={activeIdx}
            onChange={(_, idx) => navigate(navItems[idx].path)}
            sx={{ bgcolor: 'transparent', height: 64, flex: 1 }}
          >
            {navItems.map((item) => (
              <BottomNavigationAction
                key={item.path}
                label={item.short}
                icon={<item.icon />}
                sx={{
                  color: 'text.secondary',
                  '&.Mui-selected': { color: 'primary.main' },
                  minWidth: 0,
                  '& .MuiBottomNavigationAction-label': { fontSize: '0.65rem', mt: 0.3 },
                }}
              />
            ))}
          </BottomNavigation>
          <IconButton size="small" onClick={toggleMode} sx={{ mr: 1, color: 'text.secondary' }}>
            {mode === 'dark' ? <LightMode sx={{ fontSize: '1.1rem' }} /> : <DarkMode sx={{ fontSize: '1.1rem' }} />}
          </IconButton>
        </Box>
      </Paper>
    );
  }

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          bgcolor: 'background.paper',
          borderRight: '1px solid var(--surface-06)',
          display: 'flex',
          flexDirection: 'column',
        },
      }}
    >
      <Box sx={{ px: 2.5, py: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 36, height: 36, borderRadius: '10px',
              background: 'linear-gradient(135deg, #4fc3f7 0%, #29b6f6 100%)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            <Typography sx={{ fontWeight: 800, fontSize: '1rem', color: '#0a0e17' }}>IS</Typography>
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography sx={{ fontWeight: 700, fontSize: '1.1rem', color: 'text.primary', lineHeight: 1.2 }}>
              InvestScan
            </Typography>
            <Typography sx={{ fontSize: '0.65rem', color: 'text.secondary', letterSpacing: '0.04em' }}>
              Investment Scanner
            </Typography>
          </Box>
          <IconButton size="small" onClick={toggleMode} sx={{ color: 'text.secondary' }}>
            {mode === 'dark' ? <LightMode sx={{ fontSize: '1.1rem' }} /> : <DarkMode sx={{ fontSize: '1.1rem' }} />}
          </IconButton>
        </Box>
      </Box>

      <Box sx={{ px: 1, flex: 1 }}>
        <Typography
          sx={{ px: 2, mb: 1, fontSize: '0.65rem', fontWeight: 600, color: 'text.disabled', textTransform: 'uppercase', letterSpacing: '0.1em' }}
        >
          Navigation
        </Typography>
        <List disablePadding>
          {navItems.map((item) => {
            const active = isActive(item, location.pathname);
            return (
              <ListItemButton
                key={item.path}
                selected={active}
                onClick={() => navigate(item.path)}
                sx={{
                  mx: 1, mb: 0.5, borderRadius: 2, py: 1.2,
                  transition: 'all 0.2s',
                  '&.Mui-selected': {
                    bgcolor: 'rgba(79, 195, 247, 0.1)',
                    '&:hover': { bgcolor: 'rgba(79, 195, 247, 0.15)' },
                  },
                  '&:hover': { bgcolor: 'var(--surface-04)' },
                }}
              >
                <ListItemIcon sx={{ minWidth: 36, color: active ? 'primary.main' : 'text.secondary' }}>
                  <item.icon sx={{ fontSize: '1.25rem' }} />
                </ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{
                    fontSize: '0.85rem',
                    fontWeight: active ? 600 : 400,
                    color: active ? 'primary.main' : 'text.primary',
                  }}
                />
              </ListItemButton>
            );
          })}
        </List>
      </Box>

    </Drawer>
  );
}

export { DRAWER_WIDTH };
