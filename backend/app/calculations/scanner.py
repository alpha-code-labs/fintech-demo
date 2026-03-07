"""
Scanner Calculation Engine (M1).

Implements Gordon's investment scanning process:
  Gate 1: Weekly volume >= 5x 52-week average
  Gate 2: Weekly price change >= 5%
  Gate 3: Delivery % data exists and >= DELIVERY_GATE_PCT

  Score (0-8): delivery_high + above_30w + above_52w + golden_cross +
               rs_positive + consolidation_breakout + sector_index_outperforming + peers_triggered
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.db import get_connection

# ── Thresholds ────────────────────────────────────────────────
VOLUME_GATE_X = 5.0          # weekly volume >= 5x 52-week average
PRICE_GATE_PCT = 5.0         # weekly price change >= 5%
DELIVERY_GATE_PCT = 35.0     # minimum delivery % to pass gate 3
DELIVERY_SCORE_PCT = 35.0    # delivery % threshold for score point (matches gate)
CONSOLIDATION_BAND = 15.0    # max range % for consolidation
CONSOLIDATION_MIN_WEEKS = 26 # ~6 months
SECTOR_PEER_MIN = 2          # min peers for "sector strong"
LOOKBACK_WEEKS = 65          # ~15 months of weekly data needed

# Map yfinance sector names → NSE sector index names
SECTOR_TO_INDEX = {
    "Technology": "NIFTY IT",
    "Healthcare": "NIFTY PHARMA",
    "Consumer Cyclical": "NIFTY AUTO",
    "Consumer Defensive": "NIFTY FMCG",
    "Basic Materials": "NIFTY METAL",
    "Real Estate": "NIFTY REALTY",
    "Energy": "NIFTY ENERGY",
    "Communication Services": "NIFTY MEDIA",
    "Utilities": "NIFTY PSE",
    "Industrials": "NIFTY INFRA",
    "Financial Services": "NIFTY BANK",
}

# Simple in-memory cache: {week_ending: result}
_cache: dict[str, dict] = {}
_latest_week_key: str | None = None  # cache the "latest" week resolution


def run_scanner(week_ending: str | None = None) -> dict:
    """
    Run the full scanner pipeline for a given week.
    Returns response matching the dummy scanner.json shape.
    """
    global _latest_week_key

    # Check cache early
    if week_ending is not None and week_ending in _cache:
        return _cache[week_ending]
    if week_ending is None and _latest_week_key and _latest_week_key in _cache:
        return _cache[_latest_week_key]

    conn = get_connection()

    # Load raw data
    stock_daily = _load_stock_data(conn)
    nifty_daily = _load_nifty_data(conn)
    sector_daily = _load_sector_index_data(conn)
    universe = _load_universe(conn)
    conn.close()

    if stock_daily.empty:
        return {
            "week_ending": week_ending or "",
            "stocks_scanned": len(universe),
            "stocks_triggered": 0,
            "signals": [],
        }

    # Resample daily → weekly
    stock_weekly = _resample_to_weekly(stock_daily)
    nifty_weekly = _resample_to_weekly_index(nifty_daily)

    if stock_weekly.empty or nifty_weekly.empty:
        return {
            "week_ending": week_ending or "",
            "stocks_scanned": len(universe),
            "stocks_triggered": 0,
            "signals": [],
        }

    # Determine target week — use most recent COMPLETE week (>= 3 trading days)
    all_week_ends = stock_weekly.index.get_level_values("week_end").unique().sort_values()

    if week_ending is not None:
        target_week = pd.Timestamp(week_ending)
        if target_week not in all_week_ends:
            diffs = abs(all_week_ends - target_week)
            target_week = all_week_ends[diffs.argmin()]
    else:
        # Find the latest week with >= 3 trading days (skip incomplete current week)
        for candidate in reversed(all_week_ends):
            week_data = stock_weekly.xs(candidate, level="week_end", drop_level=True)
            median_days = week_data["trading_days"].median()
            if median_days >= 3:
                target_week = candidate
                break
        else:
            target_week = all_week_ends[-1]

    target_week_str = target_week.strftime("%Y-%m-%d")

    # Check cache (also catches default week_ending=None resolved to a date)
    if target_week_str in _cache:
        return _cache[target_week_str]

    # Calculate all metrics
    metrics = _calculate_metrics(stock_weekly, nifty_weekly, target_week, universe)

    # Apply 3 gates
    triggered = metrics[
        (metrics["vol_vs_avg"] >= VOLUME_GATE_X)
        & (metrics["change_pct"] >= PRICE_GATE_PCT)
        & (metrics["delivery_pct"].notna())
        & (metrics["delivery_pct"] >= DELIVERY_GATE_PCT)
    ].copy()

    # Count sector peers (among triggered stocks)
    sector_counts = triggered.groupby("sector").size().to_dict()
    triggered["peers_triggered"] = triggered["sector"].map(
        lambda s: max(0, sector_counts.get(s, 0) - 1)
    )

    # Sector index RS vs Nifty (4-week return of sector index minus Nifty 4W return)
    sector_index_weekly = _resample_to_weekly_index_multi(sector_daily)
    sector_rs = _calc_sector_index_rs(sector_index_weekly, nifty_weekly, target_week)
    triggered["sector_index_rs"] = triggered["sector"].map(
        lambda s: sector_rs.get(SECTOR_TO_INDEX.get(s, ""), None)
    )
    triggered["sector_index_outperforming"] = triggered["sector_index_rs"].fillna(0) > 0

    # Calculate 8-point score (matches product vision criteria exactly)
    rs_positive = triggered["rs_vs_nifty_4w"].fillna(0) > 0
    consolidation_breakout = (triggered["consolidation_months"] >= 6).astype(int)
    triggered["score"] = (
        (triggered["delivery_pct"] >= DELIVERY_SCORE_PCT).astype(int)  # 1. Delivery high
        + triggered["above_30w"].astype(int)                           # 2. Above 30W MA
        + triggered["above_52w"].astype(int)                           # 3. Above 52W MA
        + triggered["golden_cross_flag"].astype(int)                   # 4. Golden crossover
        + rs_positive.astype(int)                                      # 5. RS vs Nifty positive
        + consolidation_breakout                                       # 6. 6+ month consolidation breakout
        + triggered["sector_index_outperforming"].astype(int)          # 7. Sector index outperforming Nifty
        + (triggered["peers_triggered"] >= SECTOR_PEER_MIN).astype(int)  # 8. Multiple peers triggered
    )

    # Sort by score descending, then by vol_vs_avg descending
    triggered = triggered.sort_values(
        ["score", "vol_vs_avg"], ascending=[False, False]
    )

    # Format response
    signals = []
    for _, row in triggered.iterrows():
        golden_cross_text = None
        if row["gc_30w"]:
            golden_cross_text = "10W crossed 30W this week"
        elif row["gc_52w"]:
            golden_cross_text = "10W crossed 52W this week"

        rs_val = row["rs_vs_nifty_4w"]
        rs_val = round(float(rs_val), 1) if pd.notna(rs_val) else 0.0

        market_cap = universe.get(row["symbol"], {}).get("market_cap_cr")
        signals.append({
            "symbol": row["symbol"],
            "name": universe.get(row["symbol"], {}).get("name", row["symbol"]),
            "sector": row["sector"],
            "market_cap_cr": round(market_cap) if market_cap else None,
            "price": round(float(row["close"]), 2),
            "change_pct": round(float(row["change_pct"]), 1),
            "vol_vs_avg": round(float(row["vol_vs_avg"]), 1),
            "delivery_pct": round(float(row["delivery_pct"]), 0),
            "score": int(row["score"]),
            "signals": {
                "above_30w_ma": bool(row["above_30w"]),
                "above_52w_ma": bool(row["above_52w"]),
                "golden_cross": golden_cross_text,
                "rs_vs_nifty_4w": rs_val,
                "consolidation_months": int(row["consolidation_months"]),
                "sector_index_rs": round(float(row["sector_index_rs"]), 1) if pd.notna(row.get("sector_index_rs")) else None,
                "sector_index_outperforming": bool(row["sector_index_outperforming"]),
                "peers_triggered": int(row["peers_triggered"]),
            },
        })

    # Distribution watchlist: high volume but price DOWN (potential breakdown)
    distribution = metrics[
        (metrics["vol_vs_avg"] >= VOLUME_GATE_X)
        & (metrics["change_pct"] < 0)
    ].copy()
    distribution = distribution.sort_values("vol_vs_avg", ascending=False).head(20)

    distribution_list = []
    for _, row in distribution.iterrows():
        market_cap_d = universe.get(row["symbol"], {}).get("market_cap_cr")
        del_pct = round(float(row["delivery_pct"]), 0) if pd.notna(row.get("delivery_pct")) else None
        distribution_list.append({
            "symbol": row["symbol"],
            "name": universe.get(row["symbol"], {}).get("name", row["symbol"]),
            "sector": row["sector"],
            "market_cap_cr": round(market_cap_d) if market_cap_d else None,
            "price": round(float(row["close"]), 2),
            "change_pct": round(float(row["change_pct"]), 1),
            "vol_vs_avg": round(float(row["vol_vs_avg"]), 1),
            "delivery_pct": del_pct,
            "below_30w_ma": not bool(row["above_30w"]) if pd.notna(row.get("above_30w")) else None,
            "below_52w_ma": not bool(row["above_52w"]) if pd.notna(row.get("above_52w")) else None,
        })

    result = {
        "week_ending": target_week_str,
        "stocks_scanned": len(universe),
        "stocks_triggered": len(signals),
        "signals": signals,
        "distribution_watchlist": distribution_list,
    }

    _cache[target_week_str] = result
    if week_ending is None:
        _latest_week_key = target_week_str
    return result


# ── Data Loading ──────────────────────────────────────────────


def _load_stock_data(conn) -> pd.DataFrame:
    """Load ~15 months of daily OHLC (enough for 52W + buffer)."""
    cutoff = (datetime.now() - timedelta(weeks=LOOKBACK_WEEKS)).strftime("%Y-%m-%d")
    df = pd.read_sql_query(
        """SELECT symbol, date, open, high, low, close, volume,
                  delivery_pct, deliverable_qty
           FROM stock_ohlc
           WHERE date >= ?
           ORDER BY symbol, date""",
        conn,
        params=[cutoff],
    )
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df


def _load_nifty_data(conn) -> pd.DataFrame:
    """Load Nifty 50 daily data for the same period."""
    cutoff = (datetime.now() - timedelta(weeks=LOOKBACK_WEEKS)).strftime("%Y-%m-%d")
    df = pd.read_sql_query(
        """SELECT date, close
           FROM index_daily
           WHERE index_name = 'NIFTY 50' AND date >= ?
           ORDER BY date""",
        conn,
        params=[cutoff],
    )
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df


def _load_sector_index_data(conn) -> pd.DataFrame:
    """Load all sector index daily data for sector RS calculation."""
    cutoff = (datetime.now() - timedelta(weeks=LOOKBACK_WEEKS)).strftime("%Y-%m-%d")
    index_names = list(SECTOR_TO_INDEX.values())
    placeholders = ",".join(["?"] * len(index_names))
    df = pd.read_sql_query(
        f"""SELECT index_name, date, close
            FROM index_daily
            WHERE index_name IN ({placeholders}) AND date >= ?
            ORDER BY index_name, date""",
        conn,
        params=index_names + [cutoff],
    )
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df


def _load_universe(conn) -> dict:
    """Load stock universe as {symbol: {name, sector, industry, market_cap_cr}}."""
    rows = conn.execute(
        "SELECT symbol, company_name, sector, industry, market_cap_cr FROM stock_universe"
    ).fetchall()
    return {
        r["symbol"]: {
            "name": r["company_name"] or r["symbol"],
            "sector": r["sector"] or "Unknown",
            "industry": r["industry"] or "Unknown",
            "market_cap_cr": r["market_cap_cr"],
        }
        for r in rows
    }


# ── Weekly Resampling ─────────────────────────────────────────


def _resample_to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """
    Convert daily OHLC to weekly candles (Mon-Fri ending Friday).
    Returns DataFrame with MultiIndex (symbol, week_end).
    """
    indexed = daily.set_index("date")
    weekly = (
        indexed.groupby("symbol")
        .resample("W-FRI")
        .agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "delivery_pct": "mean",
        })
    )
    # Track trading days per week (for filtering incomplete weeks)
    day_counts = (
        indexed.groupby("symbol")
        .resample("W-FRI")["close"]
        .count()
        .rename("trading_days")
    )
    weekly = weekly.join(day_counts)
    # Drop weeks with no trading data
    weekly = weekly.dropna(subset=["close"])
    weekly.index.names = ["symbol", "week_end"]
    return weekly


def _resample_to_weekly_index(daily: pd.DataFrame) -> pd.DataFrame:
    """Resample Nifty daily to weekly (Friday close)."""
    weekly = (
        daily.set_index("date")
        .resample("W-FRI")
        .agg({"close": "last"})
        .dropna()
    )
    weekly.index.name = "week_end"
    return weekly


def _resample_to_weekly_index_multi(daily: pd.DataFrame) -> pd.DataFrame:
    """Resample multiple sector indices daily → weekly (Friday close).
    Returns DataFrame with MultiIndex (index_name, week_end)."""
    if daily.empty:
        return pd.DataFrame()
    indexed = daily.set_index("date")
    weekly = (
        indexed.groupby("index_name")
        .resample("W-FRI")
        .agg({"close": "last"})
        .dropna()
    )
    weekly.index.names = ["index_name", "week_end"]
    return weekly


def _calc_sector_index_rs(
    sector_weekly: pd.DataFrame,
    nifty_weekly: pd.DataFrame,
    target_week: pd.Timestamp,
) -> dict[str, float]:
    """Calculate 4-week RS vs Nifty for each sector index.
    Returns {index_name: rs_value}."""
    if sector_weekly.empty:
        return {}

    # Nifty 4-week return
    nifty_at_target = nifty_weekly.loc[:target_week]
    if len(nifty_at_target) < 5:
        return {}
    nifty_now = nifty_at_target.iloc[-1]["close"]
    nifty_4w_ago = nifty_at_target.iloc[-5]["close"]
    nifty_return = (nifty_now / nifty_4w_ago - 1) * 100

    result = {}
    for idx_name in sector_weekly.index.get_level_values("index_name").unique():
        try:
            idx_data = sector_weekly.loc[idx_name]
            idx_at_target = idx_data.loc[:target_week]
            if len(idx_at_target) < 5:
                continue
            idx_now = idx_at_target.iloc[-1]["close"]
            idx_4w_ago = idx_at_target.iloc[-5]["close"]
            idx_return = (idx_now / idx_4w_ago - 1) * 100
            result[idx_name] = round(idx_return - nifty_return, 1)
        except (KeyError, IndexError):
            continue
    return result


# ── Metric Calculations ──────────────────────────────────────


def _calculate_metrics(
    stock_weekly: pd.DataFrame,
    nifty_weekly: pd.DataFrame,
    target_week: pd.Timestamp,
    universe: dict,
) -> pd.DataFrame:
    """
    Calculate all scanner metrics for every stock for the target week.
    Returns a flat DataFrame with one row per stock.
    """
    # Rolling calculations (vectorized across all stocks)
    stock_weekly = stock_weekly.copy()
    g = stock_weekly.groupby(level="symbol")
    stock_weekly["avg_vol_52w"] = g["volume"].transform(
        lambda x: x.rolling(52, min_periods=20).mean()
    )
    stock_weekly["ma_10w"] = g["close"].transform(
        lambda x: x.rolling(10, min_periods=5).mean()
    )
    stock_weekly["ma_30w"] = g["close"].transform(
        lambda x: x.rolling(30, min_periods=15).mean()
    )
    stock_weekly["ma_52w"] = g["close"].transform(
        lambda x: x.rolling(52, min_periods=26).mean()
    )
    stock_weekly["prev_close"] = g["close"].shift(1)

    # Re-group after adding columns for shift operations
    g2 = stock_weekly.groupby(level="symbol")
    stock_weekly["prev_ma_10w"] = g2["ma_10w"].shift(1)
    stock_weekly["prev_ma_30w"] = g2["ma_30w"].shift(1)
    stock_weekly["prev_ma_52w"] = g2["ma_52w"].shift(1)

    # Filter to target week only
    target_data = stock_weekly.xs(target_week, level="week_end", drop_level=True)
    if target_data.empty:
        return pd.DataFrame()

    target_data = target_data.reset_index()  # symbol becomes a column

    # Weekly price change %
    target_data["change_pct"] = (
        (target_data["close"] - target_data["prev_close"])
        / target_data["prev_close"]
        * 100
    )

    # Volume vs 52W average
    target_data["vol_vs_avg"] = target_data["volume"] / target_data["avg_vol_52w"]

    # MA signals
    target_data["above_30w"] = target_data["close"] > target_data["ma_30w"]
    target_data["above_52w"] = target_data["close"] > target_data["ma_52w"]

    # Golden crossover: 10W crossed above 30W or 52W THIS week
    target_data["gc_30w"] = (
        (target_data["ma_10w"] > target_data["ma_30w"])
        & (target_data["prev_ma_10w"] <= target_data["prev_ma_30w"])
    )
    target_data["gc_52w"] = (
        (target_data["ma_10w"] > target_data["ma_52w"])
        & (target_data["prev_ma_10w"] <= target_data["prev_ma_52w"])
    )
    target_data["golden_cross_flag"] = target_data["gc_30w"] | target_data["gc_52w"]

    # Relative strength vs Nifty (4-week return)
    rs_series = _calc_rs_vs_nifty(stock_weekly, nifty_weekly, target_week)
    target_data["rs_vs_nifty_4w"] = target_data["symbol"].map(rs_series)

    # Consolidation detection
    consol_data = _detect_consolidation_all(stock_weekly, target_week)
    target_data = target_data.merge(
        consol_data, left_on="symbol", right_index=True, how="left", suffixes=("", "_consol")
    )
    target_data["consolidation_months"] = target_data["consolidation_months"].fillna(0)

    # Sector from universe
    target_data["sector"] = target_data["symbol"].map(
        lambda s: universe.get(s, {}).get("sector", "Unknown")
    )

    # Clean up NaN in gates
    target_data = target_data.replace([np.inf, -np.inf], np.nan)
    target_data = target_data.dropna(subset=["vol_vs_avg", "change_pct", "close"])

    return target_data


def _calc_rs_vs_nifty(
    stock_weekly: pd.DataFrame,
    nifty_weekly: pd.DataFrame,
    target_week: pd.Timestamp,
) -> pd.Series:
    """
    Calculate 4-week relative strength vs Nifty 50 for each stock.
    RS = (stock 4W return) - (Nifty 4W return)
    """
    # Nifty 4-week return
    nifty_at_target = nifty_weekly.loc[:target_week]
    if len(nifty_at_target) < 5:
        return pd.Series(dtype=float)

    nifty_now = nifty_at_target.iloc[-1]["close"]
    nifty_4w_ago = nifty_at_target.iloc[-5]["close"]
    nifty_return = (nifty_now / nifty_4w_ago - 1) * 100

    # Stock 4-week returns
    rs_values = {}
    for symbol in stock_weekly.index.get_level_values("symbol").unique():
        try:
            sym_data = stock_weekly.loc[symbol]
            sym_at_target = sym_data.loc[:target_week]
            if len(sym_at_target) < 5:
                continue
            stock_now = sym_at_target.iloc[-1]["close"]
            stock_4w_ago = sym_at_target.iloc[-5]["close"]
            stock_return = (stock_now / stock_4w_ago - 1) * 100
            rs_values[symbol] = round(stock_return - nifty_return, 1)
        except (KeyError, IndexError):
            continue

    return pd.Series(rs_values, name="rs_vs_nifty_4w")


def _detect_consolidation_all(
    stock_weekly: pd.DataFrame,
    target_week: pd.Timestamp,
) -> pd.DataFrame:
    """
    Detect consolidation for all stocks.
    Returns DataFrame with index=symbol, columns=[consolidation_months].
    """
    results = {}

    for symbol in stock_weekly.index.get_level_values("symbol").unique():
        try:
            sym_data = stock_weekly.loc[symbol]
            sym_prior = sym_data.loc[:target_week]

            if len(sym_prior) < 8:
                results[symbol] = 0
                continue

            # Exclude current week — look at the weeks BEFORE it
            prior = sym_prior.iloc[:-1]
            if len(prior) < 4:
                results[symbol] = 0
                continue

            # Find longest consolidation ending at the most recent prior week
            best_weeks = 0
            for weeks in range(4, min(65, len(prior) + 1)):
                window = prior.iloc[-weeks:]
                max_h = window["high"].max()
                min_l = window["low"].min()
                if min_l <= 0:
                    break
                range_pct = (max_h - min_l) / min_l * 100
                if range_pct <= CONSOLIDATION_BAND:
                    best_weeks = weeks
                else:
                    break

            results[symbol] = round(best_weeks / 4.33)
        except (KeyError, IndexError):
            results[symbol] = 0

    return pd.DataFrame.from_dict(
        results, orient="index", columns=["consolidation_months"]
    )
