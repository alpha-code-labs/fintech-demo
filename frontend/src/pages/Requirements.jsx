import { useState, useEffect, useCallback } from 'react';
import {
  Box, Card, CardContent, Typography, Button, TextField, CircularProgress,
} from '@mui/material';
import { Add, Close, Save } from '@mui/icons-material';
import { PageHeader } from '../components/common';

export default function Requirements() {
  const [requirements, setRequirements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchRequirements = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/requirements');
      if (!res.ok) throw new Error('Failed to load');
      const data = await res.json();
      setRequirements(data);
      setError(null);
    } catch {
      setError('Could not load requirements. Make sure the app is deployed to Azure.');
      setRequirements([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchRequirements(); }, [fetchRequirements]);

  const handleSave = async () => {
    if (!draft.trim()) return;
    setSaving(true);
    try {
      const res = await fetch('/api/requirements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: draft }),
      });
      if (!res.ok) throw new Error('Failed to save');
      const newReq = await res.json();
      setRequirements((prev) => [newReq, ...prev]);
      setDraft('');
      setIsEditing(false);
      setError(null);
    } catch {
      setError('Failed to save requirement. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleDiscard = () => {
    setDraft('');
    setIsEditing(false);
  };

  const formatDate = (iso) => {
    const d = new Date(iso);
    return d.toLocaleDateString('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  return (
    <Box>
      <PageHeader
        title="Requirement Changes"
        subtitle="Write your requirements and change requests here"
        right={
          !isEditing && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setIsEditing(true)}
              size="small"
            >
              Add Requirement
            </Button>
          )
        }
      />

      {isEditing && (
        <Card sx={{ mb: 3, border: '1px solid', borderColor: 'primary.main' }}>
          <CardContent sx={{ p: { xs: 2, md: 3 } }}>
            <Typography variant="subtitle2" sx={{ mb: 1.5, color: 'primary.main' }}>
              New Requirement
            </Typography>
            <TextField
              multiline
              minRows={4}
              maxRows={12}
              fullWidth
              placeholder="Write your requirement or change request here..."
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              autoFocus
              sx={{ mb: 2 }}
            />
            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
              <Button
                variant="outlined"
                startIcon={<Close />}
                onClick={handleDiscard}
                disabled={saving}
                size="small"
              >
                Discard
              </Button>
              <Button
                variant="contained"
                startIcon={saving ? <CircularProgress size={16} /> : <Save />}
                onClick={handleSave}
                disabled={saving || !draft.trim()}
                size="small"
              >
                {saving ? 'Saving...' : 'Save'}
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {error && (
        <Card sx={{ mb: 2, bgcolor: 'rgba(244,67,54,0.08)', border: '1px solid rgba(244,67,54,0.2)' }}>
          <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
            <Typography variant="body2" sx={{ color: 'error.main' }}>{error}</Typography>
          </CardContent>
        </Card>
      )}

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {!loading && requirements.length === 0 && !error && (
        <Card>
          <CardContent sx={{ py: 6, textAlign: 'center' }}>
            <Typography variant="body1" sx={{ color: 'text.secondary', mb: 1 }}>
              No requirements yet
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.disabled' }}>
              Click &quot;Add Requirement&quot; to write your first requirement or change request.
            </Typography>
          </CardContent>
        </Card>
      )}

      {requirements.map((req) => (
        <Card key={req.id} sx={{ mb: 2 }}>
          <CardContent sx={{ p: { xs: 2, md: 3 }, '&:last-child': { pb: { xs: 2, md: 3 } } }}>
            <Typography
              variant="body1"
              sx={{ whiteSpace: 'pre-wrap', mb: 1.5, lineHeight: 1.6 }}
            >
              {req.text}
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.disabled' }}>
              {formatDate(req.created_at)}
            </Typography>
          </CardContent>
        </Card>
      ))}
    </Box>
  );
}
