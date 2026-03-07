import { Box, Skeleton, Card, CardContent, Grid } from '@mui/material';

export function SkeletonCard({ height = 120 }) {
  return (
    <Card>
      <CardContent>
        <Skeleton variant="text" width="40%" sx={{ mb: 1 }} />
        <Skeleton variant="text" width="60%" height={32} />
        <Skeleton variant="text" width="30%" sx={{ mt: 1 }} />
      </CardContent>
    </Card>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }) {
  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          {Array.from({ length: cols }).map((_, i) => (
            <Skeleton key={i} variant="text" width={`${100 / cols}%`} height={20} />
          ))}
        </Box>
        {Array.from({ length: rows }).map((_, i) => (
          <Box key={i} sx={{ display: 'flex', gap: 2, mb: 1.5 }}>
            {Array.from({ length: cols }).map((_, j) => (
              <Skeleton key={j} variant="text" width={`${100 / cols}%`} height={24} />
            ))}
          </Box>
        ))}
      </CardContent>
    </Card>
  );
}

export function SkeletonPage() {
  return (
    <Box>
      <Skeleton variant="text" width={240} height={40} sx={{ mb: 1 }} />
      <Skeleton variant="text" width={180} height={24} sx={{ mb: 3 }} />
      <Skeleton variant="rounded" height={56} sx={{ mb: 3, borderRadius: 2 }} />
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[1, 2, 3, 4].map(i => (
          <Grid size={{ xs: 6, md: 3 }} key={i}>
            <SkeletonCard />
          </Grid>
        ))}
      </Grid>
      <SkeletonTable />
    </Box>
  );
}
