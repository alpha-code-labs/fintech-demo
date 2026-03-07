"""
Fetch market breadth data from nsetools and cache the result.

- Advancing / Declining stocks
- 52-week highs and lows counts
"""
from nsetools import Nse

from app.fetchers.cache import cache_set, cache_get

CACHE_KEY = "market_depth"


def fetch_market_depth(force: bool = False) -> dict:
    """Fetch market depth. Returns cached data if fresh (< 4 hours)."""
    if not force:
        cached = cache_get(CACHE_KEY, max_age_hours=4.0)
        if cached is not None:
            return cached

    nse = Nse()

    # Advance/Decline
    advancing = None
    declining = None
    ad_ratio = None
    try:
        ad = nse.get_advances_declines()
        if isinstance(ad, dict):
            advancing = ad.get("advances")
            declining = ad.get("declines")
            if advancing and declining and declining > 0:
                ad_ratio = round(advancing / declining, 2)
    except Exception:
        pass

    # 52-week highs and lows
    highs_52w = None
    lows_52w = None
    hl_ratio = None
    try:
        highs = nse.get_52_week_high()
        lows = nse.get_52_week_low()
        if isinstance(highs, list):
            highs_52w = len(highs)
        if isinstance(lows, list):
            lows_52w = len(lows)
        if highs_52w and lows_52w and lows_52w > 0:
            hl_ratio = round(highs_52w / lows_52w, 1)
    except Exception:
        pass

    result = {
        "advancing": advancing,
        "declining": declining,
        "ad_ratio": ad_ratio,
        "highs_52w": highs_52w,
        "lows_52w": lows_52w,
        "hl_ratio": hl_ratio,
    }

    cache_set(CACHE_KEY, result)
    return result
