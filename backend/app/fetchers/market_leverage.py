"""
Market leverage fetcher — F&O participant-wise open interest as a proxy for
market-wide margin/leverage.

Uses nsepython.get_fao_participant_oi() which returns daily breakdown of
futures + options positions by Client (retail), FII, DII, and Pro.

Client (retail) total long contracts is the best available proxy for
margin leverage — when retail is heavily long, the market is overleveraged.

Stores in live_cache under key 'market_leverage'.
"""
import logging
from datetime import date, timedelta

from app.fetchers.cache import cache_get, cache_set

logger = logging.getLogger(__name__)


def fetch_market_leverage(force: bool = False) -> dict | None:
    """Fetch F&O participant OI data as a market leverage proxy.

    Returns dict with client_long, client_short, total_oi, etc.
    Tries today first, then yesterday (for after-hours / holidays).
    """
    if not force:
        cached = cache_get("market_leverage", max_age_hours=18.0)
        if cached is not None:
            return cached

    try:
        from nsepython import get_fao_participant_oi
    except ImportError:
        logger.warning("nsepython not installed — cannot fetch market leverage")
        return None

    # Try today, then up to 3 days back (weekends/holidays)
    for days_back in range(4):
        d = date.today() - timedelta(days=days_back)
        d_str = d.strftime("%d-%m-%Y")
        try:
            df = get_fao_participant_oi(d_str)
            if df is None or df.empty:
                continue

            result = _parse_participant_oi(df, d.isoformat())
            if result:
                cache_set("market_leverage", result)
                logger.info(f"Market leverage fetched for {d_str}: client_long={result['client_long_contracts']:,}")
                return result
        except Exception as e:
            logger.debug(f"Market leverage fetch for {d_str} failed: {e}")
            continue

    logger.warning("Market leverage: no data found for recent dates")
    return None


def _parse_participant_oi(df, date_str: str) -> dict | None:
    """Parse the messy DataFrame from nsepython into clean numbers."""
    try:
        # Row 0 is the real header, rows 1+ are data
        first_col = df.columns[0]

        client_row = None
        fii_row = None
        total_row = None

        for _, row in df.iterrows():
            label = str(row[first_col]).strip().upper()
            if label == "CLIENT":
                client_row = row
            elif label == "FII":
                fii_row = row
            elif label == "TOTAL":
                total_row = row

        if client_row is None:
            return None

        # Total Long/Short are in columns 13 and 14 (0-indexed)
        client_long = int(float(client_row.iloc[13]))
        client_short = int(float(client_row.iloc[14]))

        result = {
            "date": date_str,
            "client_long_contracts": client_long,
            "client_short_contracts": client_short,
            "client_long_short_ratio": round(client_long / client_short, 2) if client_short > 0 else None,
        }

        if fii_row is not None:
            result["fii_long_contracts"] = int(float(fii_row.iloc[13]))
            result["fii_short_contracts"] = int(float(fii_row.iloc[14]))

        if total_row is not None:
            result["total_oi_contracts"] = int(float(total_row.iloc[13]))

        return result
    except Exception as e:
        logger.warning(f"Failed to parse participant OI: {e}")
        return None
