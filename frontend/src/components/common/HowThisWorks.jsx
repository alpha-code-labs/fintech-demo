import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Collapse, IconButton, Chip
} from '@mui/material';
import { HelpOutline, ExpandMore, ExpandLess } from '@mui/icons-material';
import { Link } from 'react-router-dom';

export default function HowThisWorks({ title, sections }) {
  const [open, setOpen] = useState(false);

  return (
    <Card
      sx={{
        mb: 3,
        bgcolor: open ? 'var(--surface-02)' : 'transparent',
        border: '1px solid',
        borderColor: open ? 'rgba(79,195,247,0.2)' : 'var(--surface-06)',
        transition: 'all 0.2s',
      }}
    >
      <Box
        onClick={() => setOpen(!open)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          py: 1.5,
          cursor: 'pointer',
          '&:hover': { bgcolor: 'var(--surface-02)' },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <HelpOutline sx={{ fontSize: '1rem', color: 'primary.main' }} />
          <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: 'primary.main' }}>
            {title || 'How This Works'}
          </Typography>
        </Box>
        <IconButton size="small" sx={{ color: 'text.secondary' }}>
          {open ? <ExpandLess sx={{ fontSize: '1.1rem' }} /> : <ExpandMore sx={{ fontSize: '1.1rem' }} />}
        </IconButton>
      </Box>
      <Collapse in={open} timeout="auto" unmountOnExit>
        <CardContent sx={{ pt: 0, pb: 2, px: 2 }}>
          {sections.map((section, i) => (
            <Box key={i} sx={{ mb: i < sections.length - 1 ? 2.5 : 0 }}>
              {section.heading && (
                <Typography sx={{ fontSize: '0.75rem', fontWeight: 700, mb: 0.5, color: 'text.primary', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  {section.heading}
                </Typography>
              )}
              {section.body && (
                <Typography variant="body2" sx={{ color: 'text.secondary', lineHeight: 1.7, fontSize: '0.8rem' }}>
                  {section.body}
                </Typography>
              )}
              {section.bullets && (
                <Box component="ul" sx={{ m: 0, pl: 2.5, mt: 0.5 }}>
                  {section.bullets.map((b, j) => (
                    <Box component="li" key={j} sx={{ mb: 0.3 }}>
                      <Typography variant="body2" sx={{ color: 'text.secondary', lineHeight: 1.6, fontSize: '0.8rem' }}>
                        {b}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              )}
              {section.chips && (
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                  {section.chips.map((c, j) => (
                    <Chip key={j} label={c} size="small" sx={{ fontSize: '0.65rem', height: 22, bgcolor: 'var(--surface-06)' }} />
                  ))}
                </Box>
              )}
            </Box>
          ))}
          <Box sx={{ mt: 2, pt: 1.5, borderTop: '1px solid var(--surface-06)', display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="caption" sx={{ color: 'text.disabled', fontSize: '0.65rem' }}>
              For the full technical reference including APIs, data sources, and formulas, see the{' '}
              <Link to="/blueprint" style={{ color: 'inherit', textDecoration: 'underline' }}>Data Blueprint</Link>.
            </Typography>
          </Box>
        </CardContent>
      </Collapse>
    </Card>
  );
}
