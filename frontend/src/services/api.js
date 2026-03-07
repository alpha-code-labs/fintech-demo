import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001';

const client = axios.create({ baseURL: API_BASE, timeout: 30000 });

// Unwrap response.data so components receive the data object directly
const unwrap = (req) => req.then((res) => res.data);

export const getMacro = () => unwrap(client.get('/api/macro'));
export const getScanner = (weekEnding) => unwrap(client.get('/api/scanner', { params: weekEnding ? { week_ending: weekEnding } : {} }));
export const getStockUniverse = () => unwrap(client.get('/api/stock/universe'));
export const getStock = (symbol, weekEnding) => unwrap(client.get(`/api/stock/${symbol}`, { params: weekEnding ? { week_ending: weekEnding } : {} }));
export const getPortfolio = () => unwrap(client.get('/api/portfolio'));
export const addHolding = (data) => unwrap(client.post('/api/portfolio/holdings', data));
export const removeHolding = (symbol) => unwrap(client.delete(`/api/portfolio/holdings/${symbol}`));
export const getBriefing = () => unwrap(client.get('/api/briefing'));
export const flagBusinessMix = (symbol, detail = '') => unwrap(client.post(`/api/stock/${symbol}/flag/business_mix`, { detail }));
export const unflagBusinessMix = (symbol) => unwrap(client.delete(`/api/stock/${symbol}/flag/business_mix`));
export const getJudgments = (symbol) => unwrap(client.get(`/api/stock/${symbol}/judgments`));
export const addJudgment = (symbol, data) => unwrap(client.post(`/api/stock/${symbol}/judgments`, data));
export const deleteJudgment = (symbol, id) => unwrap(client.delete(`/api/stock/${symbol}/judgments/${id}`));
export const sellHolding = (data) => unwrap(client.post('/api/portfolio/sell', data));
export const holdDecision = (data) => unwrap(client.post('/api/portfolio/hold', data));
export const addMoreShares = (data) => unwrap(client.post('/api/portfolio/add-more', data));
export const getTradeHistory = () => unwrap(client.get('/api/portfolio/history'));
export const getWatchlist = () => unwrap(client.get('/api/watchlist'));
export const addToWatchlist = (data) => unwrap(client.post('/api/watchlist', data));
export const removeFromWatchlist = (symbol) => unwrap(client.delete(`/api/watchlist/${symbol}`));
export const getAlerts = () => unwrap(client.get('/api/alerts'));
export const createAlert = (data) => unwrap(client.post('/api/alerts', data));
export const deleteAlert = (id) => unwrap(client.delete(`/api/alerts/${id}`));
