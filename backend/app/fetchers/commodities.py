"""
Fetch commodity prices from yfinance and cache the result.
"""
import yfinance as yf

from app.fetchers.cache import cache_set, cache_get

CACHE_KEY = "commodities"

COMMODITIES = [
    ("GC=F", "Gold", "$"),
    ("CL=F", "Crude Oil", "$"),
    ("SI=F", "Silver", "$"),
    ("HG=F", "Copper", "$"),
    ("NG=F", "Natural Gas", "$"),
]


def fetch_commodities(force: bool = False) -> list[dict]:
    """Fetch commodity prices. Returns cached data if fresh (< 4 hours)."""
    if not force:
        cached = cache_get(CACHE_KEY, max_age_hours=4.0)
        if cached is not None:
            return cached

    tickers = [t for t, _, _ in COMMODITIES]
    data = yf.download(tickers, period="5d", group_by="ticker", progress=False)

    results = []
    for ticker, name, unit in COMMODITIES:
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
                results.append({"name": name, "value": None, "unit": unit, "change_pct": None})
                continue
            results.append({"name": name, "value": latest, "unit": unit, "change_pct": change_pct})
        except Exception:
            results.append({"name": name, "value": None, "unit": unit, "change_pct": None})

    cache_set(CACHE_KEY, results)
    return results
