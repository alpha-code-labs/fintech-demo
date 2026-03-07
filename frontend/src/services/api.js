// Demo mode — all data from local JSON, no backend needed
import macroData from '../data/macro.json';
import scannerData from '../data/scanner.json';
import portfolioData from '../data/portfolio.json';
import briefingData from '../data/briefing.json';

// Stock deep dive files
const stockFiles = import.meta.glob('../data/stocks/*.json', { eager: true });
const stocks = {};
for (const [path, mod] of Object.entries(stockFiles)) {
  const symbol = path.split('/').pop().replace('.json', '');
  stocks[symbol] = mod.default;
}

// Simulate async (components expect promises)
const resolve = (data) => Promise.resolve(data);
const noop = () => Promise.resolve({ status: 'ok' });

// Read APIs
export const getMacro = () => resolve(macroData);
export const getScanner = () => resolve(scannerData);
export const getStock = (symbol) => {
  const data = stocks[symbol.toUpperCase()];
  return data ? resolve(data) : Promise.reject(new Error(`Stock ${symbol} not found`));
};
export const getPortfolio = () => resolve(portfolioData);
export const getBriefing = () => resolve(briefingData);
export const getStockUniverse = () => resolve(
  Object.values(stocks).map((s) => ({ symbol: s.symbol, name: s.name, sector: s.sector }))
);

// Write APIs — no-ops in demo mode, return mock success
export const addHolding = () => noop();
export const removeHolding = () => noop();
export const sellHolding = () => noop();
export const holdDecision = () => noop();
export const addMoreShares = () => Promise.resolve({ status: 'ok', result: { new_avg: 0 } });
export const flagBusinessMix = () => noop();
export const unflagBusinessMix = () => noop();
export const addJudgment = () => noop();
export const deleteJudgment = () => noop();
export const getJudgments = () => resolve([]);
export const getTradeHistory = () => resolve([]);
export const getWatchlist = () => resolve([]);
export const addToWatchlist = () => noop();
export const removeFromWatchlist = () => noop();
export const getAlerts = () => resolve([]);
export const createAlert = () => noop();
export const deleteAlert = () => noop();
