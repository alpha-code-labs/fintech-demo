"""
Stock Deep Dive Calculation Engine (M2).

Produces per-stock analysis matching the ABCL.json dummy shape:
  - Technical signals (MAs, RS, consolidation, volume, delivery)
  - Fundamentals (quarterly financials in Crores + promoter holding)
  - Setup detection (earnings surprise, debt reduction, margin expansion, sector, news-based)
  - Sector context with peers from scanner cache
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.db import get_connection

logger = logging.getLogger(__name__)
from app.calculations.scanner import (
    run_scanner,
    LOOKBACK_WEEKS,
    CONSOLIDATION_BAND,
    VOLUME_GATE_X,
    PRICE_GATE_PCT,
    DELIVERY_SCORE_PCT,
    SECTOR_PEER_MIN,
)

# Crore = 10,000,000
CRORE = 1e7

# Map yfinance sectors to NSE sector indices
SECTOR_TO_INDEX = {
    "Technology": "NIFTY IT",
    "Healthcare": "NIFTY PHARMA",
    "Consumer Cyclical": "NIFTY AUTO",
    "Consumer Defensive": "NIFTY FMCG",
    "Basic Materials": "NIFTY METAL",
    "Real Estate": "NIFTY REALTY",
    "Energy": "NIFTY ENERGY",
    "Communication Services": "NIFTY MEDIA",
    "Industrials": "NIFTY INFRA",
    "Financial Services": "NIFTY BANK",
}


_universe_cache = None


def get_stock_universe() -> list[dict]:
    """Return symbol + company_name for all stocks in the universe. Cached after first call."""
    global _universe_cache
    if _universe_cache is not None:
        return _universe_cache
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT symbol, company_name FROM stock_universe ORDER BY company_name"
        ).fetchall()
        _universe_cache = [{"symbol": r["symbol"], "name": r["company_name"]} for r in rows]
        return _universe_cache
    finally:
        conn.close()


def get_stock_deep_dive(symbol: str, week_ending: str | None = None) -> dict | None:
    """
    Get full deep dive data for a single stock.
    Returns None if symbol not found in universe.
    If week_ending is provided, compute technicals as of that date.
    """
    symbol = symbol.upper()
    conn = get_connection()

    # 1. Basic info
    info = _get_stock_info(conn, symbol)
    if info is None:
        conn.close()
        return None

    # 2. Technical signals (single stock)
    technical = _calculate_technicals(conn, symbol, week_ending=week_ending)

    # 3. Sector context from scanner
    sector_context = _get_sector_context(symbol, info["sector"])

    # 4. Fundamentals (financials + promoter holding)
    fundamentals = _get_fundamentals(conn, symbol)

    # 5. Setup detection
    setups = _detect_setups(fundamentals, sector_context, symbol, stock_info=info)

    conn.close()

    # 6. Calculate score (same 8 signals as scanner)
    score = _calculate_score(technical, sector_context)

    result = {
        "symbol": symbol,
        "name": info["name"],
        "sector": info["sector"],
        "market_cap": info["market_cap"],
        "price": technical["price"],
        "price_date": technical.get("price_date"),
        "score": score,
        "technical": {
            "vol_vs_avg": technical["vol_vs_avg"],
            "delivery_pct": technical["delivery_pct"],
            "above_30w_ma": technical["above_30w_ma"],
            "ma_30w": technical["ma_30w"],
            "above_52w_ma": technical["above_52w_ma"],
            "ma_52w": technical["ma_52w"],
            "golden_cross": technical["golden_cross"],
            "rs_vs_nifty_4w": technical["rs_vs_nifty_4w"],
            "consolidation_months": technical["consolidation_months"],
            "consolidation_range": technical["consolidation_range"],
            "breakout_level": technical["breakout_level"],
            "detected_patterns": technical.get("detected_patterns", []),
        },
        "sector_context": sector_context,
        "fundamentals": fundamentals,
        "setups": setups,
        "ai_summary": None,
        "key_levels": {
            "breakout": technical["breakout_level"],
            "ma_30w": technical["ma_30w"],
            "ma_52w": technical["ma_52w"],
        },
    }

    # Generate AI summary (async-safe, returns None if no API key)
    result["ai_summary"] = _get_ai_summary(symbol, result)
    return result


# ── Basic Info ────────────────────────────────────────────────


def _get_stock_info(conn, symbol: str) -> dict | None:
    """Get stock universe info."""
    row = conn.execute(
        "SELECT company_name, sector, industry, market_cap_cr FROM stock_universe WHERE symbol = ?",
        (symbol,),
    ).fetchone()
    if row is None:
        return None
    return {
        "name": row["company_name"] or symbol,
        "sector": row["sector"] or "Unknown",
        "industry": row["industry"] or "Unknown",
        "market_cap": round(row["market_cap_cr"]) if row["market_cap_cr"] else None,
    }


# ── Technical Signals ─────────────────────────────────────────


def _calculate_technicals(conn, symbol: str, week_ending: str | None = None) -> dict:
    """Calculate all technical signals for a single stock.
    If week_ending is provided, truncate data to that date."""
    cutoff = (datetime.now() - timedelta(weeks=LOOKBACK_WEEKS)).strftime("%Y-%m-%d")

    # Load this stock's daily data
    stock_df = pd.read_sql_query(
        """SELECT date, open, high, low, close, volume, delivery_pct
           FROM stock_ohlc WHERE symbol = ? AND date >= ?
           ORDER BY date""",
        conn,
        params=[symbol, cutoff],
    )

    defaults = {
        "price": None, "price_date": None, "vol_vs_avg": None, "delivery_pct": None,
        "above_30w_ma": False, "ma_30w": None,
        "above_52w_ma": False, "ma_52w": None,
        "golden_cross": None, "rs_vs_nifty_4w": 0.0,
        "consolidation_months": 0, "consolidation_range": None, "breakout_level": None,
        "detected_patterns": [],
        "change_pct": 0.0,
    }

    if stock_df.empty or len(stock_df) < 10:
        return defaults

    stock_df["date"] = pd.to_datetime(stock_df["date"])

    # Resample to weekly
    indexed = stock_df.set_index("date")
    weekly = indexed.resample("W-FRI").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum", "delivery_pct": "mean",
    }).dropna(subset=["close"])

    if len(weekly) < 5:
        return defaults

    # Latest complete week (skip if last week has < 3 days)
    day_counts = indexed.resample("W-FRI")["close"].count()
    if day_counts.iloc[-1] < 3 and len(weekly) > 1:
        weekly = weekly.iloc[:-1]

    # If week_ending specified, truncate data to that week
    if week_ending:
        target = pd.Timestamp(week_ending)
        weekly = weekly[weekly.index <= target]

    if len(weekly) < 5:
        return defaults

    current = weekly.iloc[-1]
    prev = weekly.iloc[-2] if len(weekly) >= 2 else None

    price = round(float(current["close"]), 2)
    change_pct = round((current["close"] / prev["close"] - 1) * 100, 1) if prev is not None else 0.0

    # Volume vs 52W average
    avg_vol = weekly["volume"].rolling(52, min_periods=20).mean().iloc[-1]
    vol_vs_avg = round(float(current["volume"] / avg_vol), 1) if avg_vol and avg_vol > 0 else None

    # Delivery %
    delivery_pct = round(float(current["delivery_pct"]), 0) if pd.notna(current["delivery_pct"]) else None

    # Moving averages
    ma_10w = weekly["close"].rolling(10, min_periods=5).mean().iloc[-1]
    ma_30w = weekly["close"].rolling(30, min_periods=15).mean().iloc[-1]
    ma_52w = weekly["close"].rolling(52, min_periods=26).mean().iloc[-1]

    above_30w = bool(current["close"] > ma_30w) if pd.notna(ma_30w) else False
    above_52w = bool(current["close"] > ma_52w) if pd.notna(ma_52w) else False

    ma_30w_val = round(float(ma_30w), 2) if pd.notna(ma_30w) else None
    ma_52w_val = round(float(ma_52w), 2) if pd.notna(ma_52w) else None

    # Golden crossover
    golden_cross = None
    if len(weekly) >= 2:
        ma_10w_series = weekly["close"].rolling(10, min_periods=5).mean()
        ma_30w_series = weekly["close"].rolling(30, min_periods=15).mean()
        ma_52w_series = weekly["close"].rolling(52, min_periods=26).mean()

        if (len(ma_10w_series) >= 2 and pd.notna(ma_10w_series.iloc[-1])
                and pd.notna(ma_30w_series.iloc[-1]) and pd.notna(ma_30w_series.iloc[-2])):
            if ma_10w_series.iloc[-1] > ma_30w_series.iloc[-1] and ma_10w_series.iloc[-2] <= ma_30w_series.iloc[-2]:
                golden_cross = "10W crossed 30W this week"

        if golden_cross is None and (len(ma_10w_series) >= 2 and pd.notna(ma_10w_series.iloc[-1])
                and pd.notna(ma_52w_series.iloc[-1]) and pd.notna(ma_52w_series.iloc[-2])):
            if ma_10w_series.iloc[-1] > ma_52w_series.iloc[-1] and ma_10w_series.iloc[-2] <= ma_52w_series.iloc[-2]:
                golden_cross = "10W crossed 52W this week"

    # RS vs Nifty (4-week)
    rs_vs_nifty = _calc_single_stock_rs(conn, weekly)

    # Consolidation
    consol_months, consol_range, breakout_level = _detect_single_consolidation(weekly)

    # Breakout pattern classification within consolidation window
    detected_patterns = _detect_consolidation_patterns(weekly, consol_months)

    price_date = str(current.name.date()) if hasattr(current.name, 'date') else str(current.name)

    return {
        "price": price,
        "price_date": price_date,
        "change_pct": change_pct,
        "vol_vs_avg": vol_vs_avg,
        "delivery_pct": delivery_pct,
        "above_30w_ma": above_30w,
        "ma_30w": ma_30w_val,
        "above_52w_ma": above_52w,
        "ma_52w": ma_52w_val,
        "golden_cross": golden_cross,
        "rs_vs_nifty_4w": rs_vs_nifty,
        "consolidation_months": consol_months,
        "consolidation_range": consol_range,
        "breakout_level": breakout_level,
        "detected_patterns": detected_patterns,
    }


def _calc_single_stock_rs(conn, stock_weekly: pd.DataFrame) -> float:
    """Calculate 4-week RS vs Nifty for a single stock."""
    if len(stock_weekly) < 5:
        return 0.0

    cutoff = (datetime.now() - timedelta(weeks=LOOKBACK_WEEKS)).strftime("%Y-%m-%d")
    nifty_df = pd.read_sql_query(
        "SELECT date, close FROM index_daily WHERE index_name = 'NIFTY 50' AND date >= ? ORDER BY date",
        conn, params=[cutoff],
    )
    if nifty_df.empty:
        return 0.0

    nifty_df["date"] = pd.to_datetime(nifty_df["date"])
    nifty_weekly = nifty_df.set_index("date").resample("W-FRI").agg({"close": "last"}).dropna()

    if len(nifty_weekly) < 5:
        return 0.0

    stock_now = stock_weekly.iloc[-1]["close"]
    stock_4w = stock_weekly.iloc[-5]["close"]
    nifty_now = nifty_weekly.iloc[-1]["close"]
    nifty_4w = nifty_weekly.iloc[-5]["close"]

    stock_ret = (stock_now / stock_4w - 1) * 100
    nifty_ret = (nifty_now / nifty_4w - 1) * 100

    return round(float(stock_ret - nifty_ret), 1)


def _detect_single_consolidation(weekly: pd.DataFrame) -> tuple:
    """
    Detect consolidation for a single stock.
    Returns (months, [range_low, range_high], breakout_level) or (0, None, None).
    """
    if len(weekly) < 8:
        return 0, None, None

    prior = weekly.iloc[:-1]
    current = weekly.iloc[-1]

    best_weeks = 0
    range_high = None
    range_low = None

    for weeks in range(4, min(65, len(prior) + 1)):
        window = prior.iloc[-weeks:]
        max_h = window["high"].max()
        min_l = window["low"].min()
        if min_l <= 0:
            break
        range_pct = (max_h - min_l) / min_l * 100
        if range_pct <= CONSOLIDATION_BAND:
            best_weeks = weeks
            range_high = float(max_h)
            range_low = float(min_l)
        else:
            break

    months = round(best_weeks / 4.33)
    if months == 0:
        return 0, None, None

    consolidation_range = [round(range_low, 2), round(range_high, 2)]
    breakout_level = round(range_high, 2) if range_high else None

    return months, consolidation_range, breakout_level


def _detect_consolidation_patterns(weekly: pd.DataFrame, consol_months: int) -> list[str]:
    """
    Classify the shape of a consolidation into known breakout patterns.
    Runs on the consolidation window (consol_months * ~4.33 weeks).
    Returns list of detected pattern names.
    """
    if consol_months == 0 or len(weekly) < 8:
        return []

    consol_weeks = max(8, round(consol_months * 4.33))
    prior = weekly.iloc[:-1]  # exclude current (breakout) week
    window = prior.iloc[-min(consol_weeks, len(prior)):]

    if len(window) < 6:
        return []

    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)
    closes = window["close"].values.astype(float)

    detected = []

    # ── VCP (Volatility Contraction Pattern) ──
    # Successive price swings get tighter. Split window into thirds
    # and check if the range contracts.
    n = len(highs)
    if n >= 9:
        third = n // 3
        ranges = []
        for i in range(3):
            seg_h = highs[i * third:(i + 1) * third]
            seg_l = lows[i * third:(i + 1) * third]
            if len(seg_h) > 0 and seg_l.min() > 0:
                ranges.append((seg_h.max() - seg_l.min()) / seg_l.min() * 100)
        if len(ranges) == 3 and ranges[0] > ranges[1] > ranges[2] and ranges[0] > 3:
            detected.append("VCP")

    # ── Darvas Box ──
    # Price trades in a tight horizontal band. Check if the range
    # in the latter 2/3 of the window is very tight (< 8%).
    if n >= 6:
        box_start = n // 3
        box_highs = highs[box_start:]
        box_lows = lows[box_start:]
        if box_lows.min() > 0:
            box_range = (box_highs.max() - box_lows.min()) / box_lows.min() * 100
            # Also check that there was a run-up or move before the box
            pre_close = closes[:box_start]
            if len(pre_close) >= 2 and box_range <= 8:
                pre_range = (pre_close.max() - pre_close.min()) / pre_close.min() * 100 if pre_close.min() > 0 else 0
                if pre_range > box_range:
                    detected.append("Darvas Box")

    # ── Cup & Handle ──
    # U-shaped pattern: price drops then recovers. The lowest point
    # is roughly in the middle, and the ends are near the highs.
    if n >= 8:
        mid = n // 2
        left_high = closes[:max(2, mid // 2)].max()
        right_high = closes[-max(2, mid // 2):].max()
        cup_low = closes[mid // 2: mid + mid // 2].min()
        cup_low_idx = np.argmin(closes[mid // 2: mid + mid // 2]) + mid // 2

        if cup_low > 0 and left_high > 0:
            depth = (left_high - cup_low) / left_high * 100
            recovery = (right_high - cup_low) / cup_low * 100
            # Cup should dip at least 3% and recover most of it
            # Low should be roughly in the middle half
            mid_zone = n * 0.2 < cup_low_idx < n * 0.8
            if depth >= 3 and recovery >= depth * 0.6 and mid_zone:
                # Check for handle: small pullback in last ~25% of window
                handle_start = int(n * 0.75)
                if handle_start < n - 1:
                    handle = closes[handle_start:]
                    handle_dip = (handle.max() - handle.min()) / handle.max() * 100 if handle.max() > 0 else 0
                    if handle_dip < depth * 0.5:
                        detected.append("Cup & Handle")

    # ── Inverted Head & Shoulders ──
    # Three troughs where the middle (head) is the lowest.
    # Split into 3 segments, find each segment's low.
    if n >= 9:
        third = n // 3
        seg1_low = lows[:third].min()
        seg1_low_idx = np.argmin(lows[:third])
        seg2_low = lows[third:2 * third].min()
        seg3_low = lows[2 * third:].min()
        seg3_low_idx = np.argmin(lows[2 * third:]) + 2 * third

        if seg2_low > 0:
            # Head (middle) must be deepest
            head_deeper_than_left = seg2_low < seg1_low
            head_deeper_than_right = seg2_low < seg3_low
            # Shoulders should be roughly similar (within 5% of each other)
            shoulder_diff = abs(seg1_low - seg3_low) / max(seg1_low, seg3_low) * 100 if max(seg1_low, seg3_low) > 0 else 999
            # Head should be meaningfully lower than shoulders
            head_depth = (seg1_low - seg2_low) / seg1_low * 100 if seg1_low > 0 else 0

            if head_deeper_than_left and head_deeper_than_right and shoulder_diff < 5 and head_depth >= 2:
                detected.append("Inv H&S")

    return detected


# ── Sector Context ────────────────────────────────────────────


def _get_sector_context(symbol: str, sector: str) -> dict:
    """
    Get sector RS vs Nifty and triggered peers from scanner cache.
    """
    result = {
        "sector_rs_vs_nifty_4w": None,
        "peers_triggered": [],
    }

    # Sector RS from index data
    index_name = SECTOR_TO_INDEX.get(sector)
    if index_name:
        result["sector_rs_vs_nifty_4w"] = _calc_sector_rs(index_name)

    # Peers from scanner cache
    try:
        scanner_result = run_scanner()  # uses cache if available
        for sig in scanner_result.get("signals", []):
            if sig["sector"] == sector and sig["symbol"] != symbol:
                result["peers_triggered"].append({
                    "symbol": sig["symbol"],
                    "name": sig["name"],
                    "change_pct": sig["change_pct"],
                    "vol_vs_avg": sig["vol_vs_avg"],
                    "score": sig["score"],
                })
    except Exception:
        pass

    return result


def _calc_sector_rs(index_name: str) -> float | None:
    """Calculate 4-week sector index RS vs Nifty 50."""
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(weeks=10)).strftime("%Y-%m-%d")

    sector_df = pd.read_sql_query(
        "SELECT date, close FROM index_daily WHERE index_name = ? AND date >= ? ORDER BY date",
        conn, params=[index_name, cutoff],
    )
    nifty_df = pd.read_sql_query(
        "SELECT date, close FROM index_daily WHERE index_name = 'NIFTY 50' AND date >= ? ORDER BY date",
        conn, params=[cutoff],
    )
    conn.close()

    if sector_df.empty or nifty_df.empty:
        return None

    sector_df["date"] = pd.to_datetime(sector_df["date"])
    nifty_df["date"] = pd.to_datetime(nifty_df["date"])

    sw = sector_df.set_index("date").resample("W-FRI").agg({"close": "last"}).dropna()
    nw = nifty_df.set_index("date").resample("W-FRI").agg({"close": "last"}).dropna()

    if len(sw) < 5 or len(nw) < 5:
        return None

    sector_ret = (sw.iloc[-1]["close"] / sw.iloc[-5]["close"] - 1) * 100
    nifty_ret = (nw.iloc[-1]["close"] / nw.iloc[-5]["close"] - 1) * 100

    return round(float(sector_ret - nifty_ret), 1)


# ── Fundamentals ──────────────────────────────────────────────


def _get_fundamentals(conn, symbol: str) -> dict:
    """Load quarterly financials + promoter holding, format for display."""
    # Financials (last 6 quarters)
    fin_rows = conn.execute(
        """SELECT quarter_end, revenue, operating_income, net_income, eps,
                  operating_margin, total_debt, total_assets, total_equity,
                  cash_flow_operations
           FROM quarterly_financials
           WHERE symbol = ?
           ORDER BY quarter_end DESC LIMIT 6""",
        (symbol,),
    ).fetchall()

    # Promoter holding (last 4 quarters)
    promo_rows = conn.execute(
        """SELECT quarter_end, promoter_pct
           FROM promoter_holding
           WHERE symbol = ?
           ORDER BY quarter_end DESC LIMIT 4""",
        (symbol,),
    ).fetchall()

    # Build promoter lookup
    promo_map = {r["quarter_end"]: r["promoter_pct"] for r in promo_rows}

    quarters = []
    for row in fin_rows[:4]:  # Show 4 quarters
        qe = row["quarter_end"]
        label = _quarter_label(qe)

        revenue = _to_crores(row["revenue"])
        net_profit = _to_crores(row["net_income"])
        total_debt = _to_crores(row["total_debt"])
        opm = round(row["operating_margin"], 1) if row["operating_margin"] else None
        eps = round(row["eps"], 2) if row["eps"] else None

        # Basic ROCE approximation: operating_income / total_assets * 100
        roce = None
        if row["operating_income"] and row["total_assets"] and row["total_assets"] > 0:
            roce = round(row["operating_income"] / row["total_assets"] * 100, 1)

        # Asset turnover: revenue / total_assets (annualized from quarterly)
        asset_turnover = None
        if row["revenue"] and row["total_assets"] and row["total_assets"] > 0:
            asset_turnover = round(row["revenue"] / row["total_assets"], 3)

        # Cash flow from operations (in Crores)
        cfo = _to_crores(row["cash_flow_operations"]) if row["cash_flow_operations"] else None

        # Match promoter holding to nearest quarter
        promoter = promo_map.get(qe)
        if promoter is None:
            # Try matching to closest available quarter
            promoter = _find_nearest_promoter(qe, promo_map)

        quarters.append({
            "label": label,
            "revenue": revenue,
            "operating_margin": opm,
            "net_profit": net_profit,
            "eps": eps,
            "total_debt": total_debt,
            "roce": roce,
            "asset_turnover": asset_turnover,
            "cash_flow_operations": cfo,
            "promoter_holding": round(promoter, 1) if promoter else None,
        })

    pe, industry_pe = _fetch_pe(symbol)

    # Override latest quarter ROCE with accurate Screener.in value
    screener_roce = _fetch_screener_roce(symbol)
    if screener_roce is not None and quarters:
        quarters[0]["roce"] = screener_roce

    return {
        "quarters": quarters,
        "pe": pe,
        "industry_pe": industry_pe,
    }


def _to_crores(value) -> float | None:
    """Convert raw value (in rupees/currency) to Crores."""
    if value is None or pd.isna(value):
        return None
    cr = value / CRORE
    if abs(cr) >= 100:
        return round(cr)
    elif abs(cr) >= 1:
        return round(cr, 1)
    else:
        return round(cr, 2)


def _quarter_label(quarter_end: str) -> str:
    """Convert '2025-12-31' to 'Q3 FY26' (Indian financial year April-March)."""
    try:
        dt = datetime.strptime(quarter_end, "%Y-%m-%d")
    except ValueError:
        return quarter_end

    month = dt.month
    year = dt.year

    if month <= 3:
        q = 4
        fy = year % 100  # FY ends this year
    elif month <= 6:
        q = 1
        fy = (year + 1) % 100
    elif month <= 9:
        q = 2
        fy = (year + 1) % 100
    else:
        q = 3
        fy = (year + 1) % 100

    return f"Q{q} FY{fy}"


def _find_nearest_promoter(quarter_end: str, promo_map: dict) -> float | None:
    """Find promoter holding from nearest available quarter."""
    if not promo_map:
        return None
    try:
        target = datetime.strptime(quarter_end, "%Y-%m-%d")
        best = None
        best_diff = timedelta(days=999)
        for qe, pct in promo_map.items():
            dt = datetime.strptime(qe, "%Y-%m-%d")
            diff = abs(target - dt)
            if diff < best_diff:
                best_diff = diff
                best = pct
        return best if best_diff.days <= 120 else None  # within ~4 months
    except ValueError:
        return None


# ── P/E + ROCE Fetch ─────────────────────────────────────────

# In-memory cache: {symbol: (pe, industry_pe, timestamp)}
_pe_cache: dict[str, tuple] = {}
# Screener.in cache: {symbol: (industry_pe, roce, timestamp)}
_screener_cache: dict[str, tuple] = {}
_CACHE_TTL = timedelta(hours=24)

_SCREENER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def _fetch_pe(symbol: str) -> tuple[float | None, float | None]:
    """Fetch trailing P/E from yfinance + industry P/E from Screener.in, with 24h cache."""
    now = datetime.now()

    # Check cache
    if symbol in _pe_cache:
        pe, ind_pe, ts = _pe_cache[symbol]
        if now - ts < _CACHE_TTL:
            return pe, ind_pe

    pe = None

    # Stock P/E from yfinance
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.info
        pe = info.get("trailingPE")
        if pe is not None:
            pe = round(float(pe), 1)
    except Exception as e:
        logger.debug(f"P/E fetch failed for {symbol}: {e}")

    # Industry P/E from Screener.in (populates _screener_cache as side effect)
    ind_pe = None
    try:
        screener = _get_screener_data(symbol)
        ind_pe = screener.get("industry_pe")
    except Exception as e:
        logger.debug(f"Industry P/E fetch failed for {symbol}: {e}")

    _pe_cache[symbol] = (pe, ind_pe, now)
    return pe, ind_pe


def _fetch_screener_roce(symbol: str) -> float | None:
    """Get ROCE from Screener.in (uses shared cache with industry P/E)."""
    try:
        screener = _get_screener_data(symbol)
        return screener.get("roce")
    except Exception:
        return None


def _get_screener_data(symbol: str) -> dict:
    """Fetch ROCE and industry P/E from Screener.in in a single visit.

    Returns dict with 'roce' and 'industry_pe' keys. Uses 24h cache.
    """
    now = datetime.now()

    if symbol in _screener_cache:
        data, ts = _screener_cache[symbol]
        if now - ts < _CACHE_TTL:
            return data

    import requests
    from bs4 import BeautifulSoup
    import statistics

    result = {"roce": None, "industry_pe": None}

    for suffix in ["/consolidated/", "/"]:
        try:
            resp = requests.get(
                f"https://www.screener.in/company/{symbol}{suffix}",
                headers=_SCREENER_HEADERS,
                timeout=15,
            )
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract ROCE from top ratios section
            for li in soup.find_all("li"):
                name_span = li.find("span", class_="name")
                val_span = li.find("span", class_="number") or li.find("span", class_="value")
                if name_span and "ROCE" in name_span.get_text():
                    try:
                        val_text = val_span.get_text(strip=True).replace("%", "").replace(",", "")
                        result["roce"] = round(float(val_text), 2)
                    except (ValueError, TypeError, AttributeError):
                        pass
                    break

            # Extract industry P/E from peer section
            peer_section = soup.find("section", id="peers")
            if peer_section:
                industry_url = None
                for link in peer_section.find_all("a"):
                    href = link.get("href", "")
                    if href.startswith("/market/") and href.count("/") >= 5:
                        industry_url = href

                if industry_url:
                    try:
                        resp2 = requests.get(
                            f"https://www.screener.in{industry_url}",
                            headers=_SCREENER_HEADERS,
                            timeout=15,
                        )
                        if resp2.status_code == 200:
                            result["industry_pe"] = _extract_median_pe(resp2.text)
                    except requests.RequestException:
                        pass

            # If we got at least one value, use this page variant
            if result["roce"] is not None or result["industry_pe"] is not None:
                break

        except requests.RequestException:
            continue

    _screener_cache[symbol] = (result, now)
    return result


def _extract_median_pe(html: str) -> float | None:
    """Extract median P/E from a Screener.in industry page."""
    from bs4 import BeautifulSoup
    import statistics

    soup = BeautifulSoup(html, "html.parser")
    pe_values = []

    for table in soup.find_all("table"):
        header_row = table.find("tr")
        if not header_row:
            continue
        headers_list = [
            th.get_text(strip=True) for th in header_row.find_all(["th", "td"])
        ]
        pe_idx = None
        for i, h in enumerate(headers_list):
            if "P/E" in h:
                pe_idx = i
                break
        if pe_idx is None:
            continue
        for tr in table.find_all("tr")[1:]:
            cells = tr.find_all(["th", "td"])
            if len(cells) > pe_idx:
                pe_text = cells[pe_idx].get_text(strip=True)
                try:
                    pe_val = float(pe_text)
                    if 0 < pe_val < 500:
                        pe_values.append(pe_val)
                except ValueError:
                    pass

    if pe_values:
        return round(statistics.median(pe_values), 1)
    return None


# ── Setup Detection ───────────────────────────────────────────


def _detect_setups(fundamentals: dict, sector_context: dict, symbol: str = "",
                   stock_info: dict | None = None) -> dict:
    """
    Detect the 8 setups from Gordon's flowchart.
    5 are data-auto-detectable, 2 are news/LLM-driven, 1 is manual.
    """
    detected = []
    not_detected = []
    quarters = fundamentals.get("quarters", [])

    # Setup 1: Earnings Surprise
    _check_earnings_surprise(quarters, detected, not_detected)

    # Setup 2: Debt Reduction
    _check_debt_reduction(quarters, detected, not_detected)

    # Setup 3: Margin Expansion
    _check_margin_expansion(quarters, detected, not_detected)

    # Setup 3b: Balance Sheet Improvement (asset turnover, ROCE, cash flow)
    _check_balance_sheet_improvement(quarters, detected, not_detected)

    # Setup 4: Sector of the Cycle
    _check_sector_cycle(sector_context, detected, not_detected)

    # Setup 5: Forced Buying/Selling (from bulk/block deals)
    _check_forced_buying_selling(symbol, detected, not_detected)

    # Setups 6-7: News-based (LLM + Google News)
    _check_news_setups(symbol, stock_info or {}, detected, not_detected)

    # Setup 8: Business Mix Change (manual flag from DB)
    _check_business_mix_change(symbol, detected, not_detected)

    return {"detected": detected, "not_detected": not_detected}


def _check_earnings_surprise(quarters: list, detected: list, not_detected: list):
    """Net income YoY >= 50% AND revenue also grew."""
    if len(quarters) < 3:
        not_detected.append({
            "setup": "Earnings Surprise",
            "detail": "Not enough quarterly data for YoY comparison.",
            "source": "auto",
        })
        return

    # Compare latest quarter vs year-ago (3 quarters back in a 4-quarter list)
    latest = quarters[0]
    yoy_idx = min(3, len(quarters) - 1)  # Q3 FY26 vs Q3 FY25
    year_ago = quarters[yoy_idx]

    np_latest = latest.get("net_profit")
    np_yago = year_ago.get("net_profit")
    rev_latest = latest.get("revenue")
    rev_yago = year_ago.get("revenue")

    if np_latest and np_yago and np_yago > 0:
        np_change = (np_latest / np_yago - 1) * 100
        rev_grew = rev_latest and rev_yago and rev_latest > rev_yago

        if np_change >= 50 and rev_grew:
            rev_change = round((rev_latest / rev_yago - 1) * 100)
            detected.append({
                "setup": "Earnings Surprise",
                "detail": f"Net profit up {round(np_change)}% YoY. Revenue also grew {rev_change}% — not a one-time bump.",
                "source": "auto",
            })
            return

    not_detected.append({
        "setup": "Earnings Surprise",
        "detail": "No significant earnings surprise detected.",
        "source": "auto",
    })


def _check_debt_reduction(quarters: list, detected: list, not_detected: list):
    """Total debt declining over 3-4 consecutive quarters."""
    debts = [q.get("total_debt") for q in quarters if q.get("total_debt") is not None]

    if len(debts) < 3:
        not_detected.append({
            "setup": "Debt Reduction",
            "detail": "Not enough debt data across quarters.",
            "source": "auto",
        })
        return

    # Check if debt is declining (most recent first)
    declining_count = 0
    for i in range(len(debts) - 1):
        if debts[i] < debts[i + 1]:
            declining_count += 1
        else:
            break

    if declining_count >= 2:  # at least 3 consecutive quarters declining
        first_debt = debts[-1] if debts[-1] else debts[declining_count]
        latest_debt = debts[0]
        if first_debt and first_debt > 0:
            reduction_pct = round((1 - latest_debt / first_debt) * 100)
            detected.append({
                "setup": "Debt Reduction",
                "detail": f"Debt down {reduction_pct}% over {declining_count + 1} quarters.",
                "source": "auto",
            })
            return

    not_detected.append({
        "setup": "Debt Reduction",
        "detail": "No consistent debt reduction trend.",
        "source": "auto",
    })


def _check_margin_expansion(quarters: list, detected: list, not_detected: list):
    """Operating margin trending up over 3-4 quarters."""
    margins = [q.get("operating_margin") for q in quarters if q.get("operating_margin") is not None]

    if len(margins) < 3:
        not_detected.append({
            "setup": "Margin Expansion",
            "detail": "Not enough margin data across quarters.",
            "source": "auto",
        })
        return

    # Check if margin is expanding (most recent first, so reverse for trend)
    expanding_count = 0
    for i in range(len(margins) - 1):
        if margins[i] > margins[i + 1]:
            expanding_count += 1
        else:
            break

    if expanding_count >= 2:  # at least 3 consecutive quarters expanding
        oldest = margins[expanding_count]
        latest = margins[0]
        detected.append({
            "setup": "Margin Expansion",
            "detail": f"OPM up from {oldest}% to {latest}% over {expanding_count + 1} quarters.",
            "source": "auto",
        })
        return

    not_detected.append({
        "setup": "Margin Expansion",
        "detail": "No consistent margin expansion trend.",
        "source": "auto",
    })


def _check_balance_sheet_improvement(quarters: list, detected: list, not_detected: list):
    """Balance sheet improvement: asset turnover trending up, ROCE trending up,
    or cash flow from operations improving over 3+ quarters.

    Gordon [Para 58]: 'More efficient asset turns or better working capital
    management. Releases valuable cash and expands ROCE.'
    """
    if len(quarters) < 3:
        not_detected.append({
            "setup": "Balance Sheet Improvement",
            "detail": "Not enough quarterly data to assess trend.",
            "source": "auto",
        })
        return

    improvements = []

    # Check asset turnover trend (revenue / total_assets) — quarters are newest-first
    at_vals = [q.get("asset_turnover") for q in quarters if q.get("asset_turnover") is not None]
    if len(at_vals) >= 3:
        # Count consecutive improvements (newest first, so val[i] > val[i+1] = improving)
        at_improving = 0
        for i in range(len(at_vals) - 1):
            if at_vals[i] > at_vals[i + 1]:
                at_improving += 1
            else:
                break
        if at_improving >= 2:
            improvements.append(f"Asset turnover up from {at_vals[at_improving]:.3f} to {at_vals[0]:.3f} over {at_improving + 1} quarters")

    # Check ROCE trend
    roce_vals = [q.get("roce") for q in quarters if q.get("roce") is not None]
    if len(roce_vals) >= 3:
        roce_improving = 0
        for i in range(len(roce_vals) - 1):
            if roce_vals[i] > roce_vals[i + 1]:
                roce_improving += 1
            else:
                break
        if roce_improving >= 2:
            improvements.append(f"ROCE up from {roce_vals[roce_improving]}% to {roce_vals[0]}% over {roce_improving + 1} quarters")

    # Check cash flow from operations trend (if data available)
    cfo_vals = [q.get("cash_flow_operations") for q in quarters if q.get("cash_flow_operations") is not None]
    if len(cfo_vals) >= 3:
        cfo_improving = 0
        for i in range(len(cfo_vals) - 1):
            if cfo_vals[i] > cfo_vals[i + 1]:
                cfo_improving += 1
            else:
                break
        if cfo_improving >= 2:
            improvements.append(f"Operating cash flow improving over {cfo_improving + 1} quarters")

    if improvements:
        detected.append({
            "setup": "Balance Sheet Improvement",
            "detail": ". ".join(improvements) + ".",
            "source": "auto",
        })
    else:
        not_detected.append({
            "setup": "Balance Sheet Improvement",
            "detail": "No consistent improvement in asset turnover, ROCE, or cash flow.",
            "source": "auto",
        })


def _check_sector_cycle(sector_context: dict, detected: list, not_detected: list):
    """2+ peers triggered in same sector."""
    peers = sector_context.get("peers_triggered", [])
    sector_rs = sector_context.get("sector_rs_vs_nifty_4w")

    if len(peers) >= SECTOR_PEER_MIN:
        rs_note = f" Sector RS {'+' if sector_rs and sector_rs > 0 else ''}{sector_rs}% vs Nifty." if sector_rs is not None else ""
        detected.append({
            "setup": "Sector of the Cycle",
            "detail": f"{len(peers)} peers also triggered this week.{rs_note}",
            "source": "auto",
        })
    else:
        not_detected.append({
            "setup": "Sector of the Cycle",
            "detail": f"Only {len(peers)} peer(s) triggered. Not enough for sector confirmation.",
            "source": "auto",
        })


def _check_forced_buying_selling(symbol: str, detected: list, not_detected: list):
    """Check for recent bulk/block deals indicating forced buying or selling."""
    if not symbol:
        not_detected.append({
            "setup": "Forced Buying/Selling",
            "detail": "No bulk/block deal data available.",
            "source": "data",
        })
        return

    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    deals = conn.execute(
        """SELECT date, deal_type, client_name, buy_sell, quantity, price
           FROM bulk_block_deals
           WHERE symbol = ? AND date >= ?
           ORDER BY date DESC""",
        (symbol, cutoff),
    ).fetchall()
    conn.close()

    if not deals:
        not_detected.append({
            "setup": "Forced Buying/Selling",
            "detail": "No bulk/block deals in the last 30 days.",
            "source": "data",
        })
        return

    # Summarize deals
    total_buy_qty = 0
    total_sell_qty = 0
    block_count = 0
    deal_dates = set()

    for d in deals:
        qty = d["quantity"] or 0
        if d["buy_sell"] == "BUY":
            total_buy_qty += qty
        elif d["buy_sell"] == "SELL":
            total_sell_qty += qty
        if d["deal_type"] == "BLOCK":
            block_count += 1
        deal_dates.add(d["date"])

    total_deals = len(deals)
    latest_date = deals[0]["date"]

    # Determine if this is significant
    # Criteria: multiple deals or block deals present
    parts = []
    if block_count > 0:
        parts.append(f"{block_count} block deal(s)")
    bulk_count = total_deals - block_count
    if bulk_count > 0:
        parts.append(f"{bulk_count} bulk deal(s)")

    # Format quantities in lakhs for readability
    buy_str = f"{total_buy_qty / 100000:.1f}L" if total_buy_qty else "0"
    sell_str = f"{total_sell_qty / 100000:.1f}L" if total_sell_qty else "0"

    detail = (
        f"{' + '.join(parts)} in last 30 days across {len(deal_dates)} date(s). "
        f"Buy qty: {buy_str} shares, Sell qty: {sell_str} shares. "
        f"Latest: {latest_date}."
    )

    detected.append({
        "setup": "Forced Buying/Selling",
        "detail": detail,
        "source": "data",
    })


def _check_news_setups(symbol: str, stock_info: dict, detected: list, not_detected: list):
    """Check for management change and supply disruption via news + LLM."""
    company_name = stock_info.get("name", symbol)
    sector = stock_info.get("sector", "Unknown")

    try:
        from app.llm.news_setups import detect_news_setups
        news_result = detect_news_setups(symbol, company_name, sector)
    except Exception as e:
        logger.debug(f"News setup detection failed for {symbol}: {e}")
        news_result = {}

    # Management Change
    mc = news_result.get("management_change")
    if mc and mc.get("detail"):
        detected.append({
            "setup": "Management Change",
            "detail": mc["detail"],
            "source": "news",
        })
    else:
        not_detected.append({
            "setup": "Management Change",
            "detail": "No recent board changes found in news.",
            "source": "news",
        })

    # Supply Disruption
    sd = news_result.get("supply_disruption")
    if sd and sd.get("detail"):
        detected.append({
            "setup": "Supply Disruption",
            "detail": sd["detail"],
            "source": "news",
        })
    else:
        not_detected.append({
            "setup": "Supply Disruption",
            "detail": "No relevant disruption detected in news.",
            "source": "news",
        })

    # Forced Buying (from news/LLM — supplements the deals-based check above)
    fb = news_result.get("forced_buying")
    if fb and fb.get("detail"):
        already_detected = any(s["setup"] == "Forced Buying/Selling" for s in detected)
        if already_detected:
            # Enhance existing detail with news context
            for s in detected:
                if s["setup"] == "Forced Buying/Selling":
                    s["detail"] += f" News: {fb['detail']}"
                    break
        else:
            # Move from not_detected to detected with news detail
            not_detected[:] = [s for s in not_detected if s["setup"] != "Forced Buying/Selling"]
            detected.append({
                "setup": "Forced Buying/Selling",
                "detail": f"News: {fb['detail']}",
                "source": "news",
            })


def _check_business_mix_change(symbol: str, detected: list, not_detected: list):
    """Check if user has manually flagged a business mix change for this stock."""
    if not symbol:
        not_detected.append({
            "setup": "Business Mix Change",
            "detail": "Check segment revenue data on Screener.in.",
            "source": "manual",
        })
        return

    flag = get_stock_flag(symbol, "business_mix")
    if flag:
        detected.append({
            "setup": "Business Mix Change",
            "detail": flag.get("detail", "Flagged by user."),
            "source": "manual",
        })
    else:
        not_detected.append({
            "setup": "Business Mix Change",
            "detail": "Check segment revenue data on Screener.in.",
            "source": "manual",
        })


# ── Stock Flags (user-entered manual data) ───────────────────


def _ensure_flags_table(conn):
    """Create stock_flags table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_flags (
            symbol TEXT NOT NULL,
            flag_type TEXT NOT NULL,
            detail TEXT,
            flagged_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (symbol, flag_type)
        )
    """)
    conn.commit()


def get_stock_flag(symbol: str, flag_type: str) -> dict | None:
    """Get a specific flag for a stock. Returns None if not set."""
    conn = get_connection()
    try:
        _ensure_flags_table(conn)
        row = conn.execute(
            "SELECT detail, flagged_at FROM stock_flags WHERE symbol = ? AND flag_type = ?",
            (symbol.upper(), flag_type),
        ).fetchone()
        if row:
            return {"detail": row["detail"], "flagged_at": row["flagged_at"]}
        return None
    finally:
        conn.close()


def set_stock_flag(symbol: str, flag_type: str, detail: str = "") -> dict:
    """Set a flag for a stock. Returns the created/updated flag."""
    conn = get_connection()
    try:
        _ensure_flags_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO stock_flags (symbol, flag_type, detail)
               VALUES (?, ?, ?)""",
            (symbol.upper(), flag_type, detail),
        )
        conn.commit()
        return {"symbol": symbol.upper(), "flag_type": flag_type, "detail": detail}
    finally:
        conn.close()


def clear_stock_flag(symbol: str, flag_type: str) -> bool:
    """Clear a flag for a stock. Returns True if deleted."""
    conn = get_connection()
    try:
        _ensure_flags_table(conn)
        cursor = conn.execute(
            "DELETE FROM stock_flags WHERE symbol = ? AND flag_type = ?",
            (symbol.upper(), flag_type),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ── Chart Judgment Journal ────────────────────────────────────


def _ensure_judgments_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chart_judgments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            pattern TEXT NOT NULL,
            conviction TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def get_chart_judgments(symbol: str) -> list[dict]:
    conn = get_connection()
    try:
        _ensure_judgments_table(conn)
        rows = conn.execute(
            "SELECT id, pattern, conviction, notes, created_at FROM chart_judgments WHERE symbol = ? ORDER BY created_at DESC",
            (symbol.upper(),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_chart_judgment(symbol: str, pattern: str, conviction: str, notes: str = "") -> dict:
    conn = get_connection()
    try:
        _ensure_judgments_table(conn)
        cursor = conn.execute(
            "INSERT INTO chart_judgments (symbol, pattern, conviction, notes) VALUES (?, ?, ?, ?)",
            (symbol.upper(), pattern, conviction, notes),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, pattern, conviction, notes, created_at FROM chart_judgments WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def delete_chart_judgment(judgment_id: int) -> bool:
    conn = get_connection()
    try:
        _ensure_judgments_table(conn)
        cursor = conn.execute("DELETE FROM chart_judgments WHERE id = ?", (judgment_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ── Score Calculation ─────────────────────────────────────────


def _calculate_score(technical: dict, sector_context: dict) -> int:
    """Calculate 8-point score (same signals as scanner)."""
    score = 0

    # 1. Volume >= 5x
    if technical.get("vol_vs_avg") and technical["vol_vs_avg"] >= VOLUME_GATE_X:
        score += 1

    # 2. Price change >= 5%
    if technical.get("change_pct") and technical["change_pct"] >= PRICE_GATE_PCT:
        score += 1

    # 3. Delivery >= 50%
    if technical.get("delivery_pct") and technical["delivery_pct"] >= DELIVERY_SCORE_PCT:
        score += 1

    # 4. Above 30W MA
    if technical.get("above_30w_ma"):
        score += 1

    # 5. Above 52W MA
    if technical.get("above_52w_ma"):
        score += 1

    # 6. Golden crossover
    if technical.get("golden_cross"):
        score += 1

    # 7. RS vs Nifty positive
    if technical.get("rs_vs_nifty_4w") and technical["rs_vs_nifty_4w"] > 0:
        score += 1

    # 8. Sector strong
    if len(sector_context.get("peers_triggered", [])) >= SECTOR_PEER_MIN:
        score += 1

    return score


# ── AI Summary with cache ────────────────────────────────────

_ai_cache: dict[str, tuple] = {}  # {symbol: (summary, timestamp)}
_AI_CACHE_TTL = timedelta(hours=24)


def _get_ai_summary(symbol: str, stock_data: dict) -> str | None:
    """Generate AI summary via LLM, with 24h in-memory cache."""
    now = datetime.now()
    if symbol in _ai_cache:
        cached_summary, cached_at = _ai_cache[symbol]
        if now - cached_at < _AI_CACHE_TTL:
            return cached_summary

    try:
        from app.llm.summaries import generate_stock_summary
        summary = generate_stock_summary(stock_data)
        if summary:
            _ai_cache[symbol] = (summary, now)
        return summary
    except Exception as e:
        logger.warning(f"AI summary generation failed for {symbol}: {e}")
        return None
