"""
Fetch world indices from yfinance and cache the result.
"""
import yfinance as yf

from app.fetchers.cache import cache_set, cache_get

CACHE_KEY = "world_indices"

INDICES = [
    ("^GSPC", "S&P 500"),
    ("^IXIC", "Nasdaq"),
    ("^FTSE", "FTSE 100"),
    ("^N225", "Nikkei 225"),
    ("000001.SS", "Shanghai"),
]


def fetch_world_indices(force: bool = False) -> list[dict]:
    """Fetch world indices. Returns cached data if fresh (< 4 hours)."""
    if not force:
        cached = cache_get(CACHE_KEY, max_age_hours=4.0)
        if cached is not None:
            return cached

    tickers = [t for t, _ in INDICES]
    data = yf.download(tickers, period="5d", group_by="ticker", progress=False)

    results = []
    for ticker, name in INDICES:
        try:
            close = data[ticker]["Close"].dropna()
            if len(close) >= 2:
                latest = round(float(close.iloc[-1]), 2)
                prev = float(close.iloc[-2])
                change_pct = round((latest - prev) / prev * 100, 1)
            elif len(close) == 1:
                latest = round(float(close.iloc[0]), 2)
                change_pct = 0.0
            else:
                results.append({"name": name, "value": None, "change_pct": None})
                continue
            results.append({"name": name, "value": latest, "change_pct": change_pct})
        except Exception:
            results.append({"name": name, "value": None, "change_pct": None})

    cache_set(CACHE_KEY, results)
    return results
