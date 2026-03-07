"""
Fetch macro indicators from yfinance + nsepython + CCIL and cache the result.

- DXY (Dollar Index): yfinance DX-Y.NYB
- US 10Y yield: yfinance ^TNX
- India 10Y yield: CCIL tenorwise indicative yields page (scrape)
- INR/USD: yfinance USDINR=X
- FII/DII flows: nsepython nse_fiidii() — latest day's net value in Crores
"""
import logging
import re
import requests
import yfinance as yf

from app.fetchers.cache import cache_set, cache_get

logger = logging.getLogger(__name__)

CACHE_KEY = "macro_indicators"


def fetch_macro_indicators(force: bool = False) -> dict:
    """Fetch macro indicators. Returns cached data if fresh (< 4 hours)."""
    if not force:
        cached = cache_get(CACHE_KEY, max_age_hours=4.0)
        if cached is not None:
            return cached

    # ── yfinance: DXY, US 10Y, INR/USD ──
    tickers = ["DX-Y.NYB", "^TNX", "USDINR=X"]
    data = yf.download(tickers, period="5d", group_by="ticker", progress=False)

    def _get_latest(ticker):
        try:
            close = data[ticker]["Close"].dropna()
            if len(close) >= 2:
                latest = round(float(close.iloc[-1]), 2)
                prev = float(close.iloc[-2])
                change_pct = round((latest - prev) / prev * 100, 2)
                return latest, change_pct
            elif len(close) == 1:
                return round(float(close.iloc[0]), 2), 0.0
        except Exception:
            pass
        return None, None

    dxy_val, dxy_chg = _get_latest("DX-Y.NYB")
    us10y_val, _ = _get_latest("^TNX")
    inr_val, _ = _get_latest("USDINR=X")

    # ── nsepython: FII/DII flows ──
    fii_net, dii_net = _fetch_fii_dii()

    # ── CCIL: India 10Y yield ──
    india_10y = _fetch_india_10y()

    result = {
        "dxy": {"value": dxy_val, "change_pct": dxy_chg},
        "us_10y": {"value": us10y_val},
        "india_10y": {"value": india_10y},
        "inr_usd": {"value": inr_val},
        "fii_flow_mtd": fii_net,
        "dii_flow_mtd": dii_net,
    }

    cache_set(CACHE_KEY, result)
    return result


def _fetch_india_10y() -> float | None:
    """Scrape India 10Y government bond yield from CCIL tenorwise indicative yields."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }
        resp = requests.get(
            "https://www.ccilindia.com/tenorwise-indicative-yields",
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            return None

        # Pattern: 10Y</td> ... <td>6.48% GS 2035</td> ... <td>6.6876</td>
        match = re.search(
            r"10Y</td>\s*<td[^>]*>[^<]+</td>\s*<td[^>]*>(\d+\.\d+)</td>",
            resp.text,
        )
        if match:
            return round(float(match.group(1)), 2)
        return None
    except Exception as e:
        logger.warning(f"India 10Y yield fetch failed: {e}")
        return None


def _fetch_fii_dii() -> tuple[float | None, float | None]:
    """Fetch latest FII and DII net values from NSE via nsepython.
    Returns (fii_net_cr, dii_net_cr) — net values in Crores."""
    try:
        from nsepython import nse_fiidii
        df = nse_fiidii()

        fii_net = None
        dii_net = None

        for _, row in df.iterrows():
            cat = row.get("category", "")
            net = row.get("netValue")
            if net is not None:
                net = round(float(net), 2)
            if "FII" in cat or "FPI" in cat:
                fii_net = net
            elif "DII" in cat:
                dii_net = net

        return fii_net, dii_net
    except Exception as e:
        logger.warning(f"FII/DII fetch failed: {e}")
        return None, None
