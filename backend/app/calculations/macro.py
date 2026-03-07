"""
Global Pulse Calculation Engine (M3 + M5).

Produces macro dashboard data matching the macro.json dummy shape.
Real data from index_daily: Indian indices (4), sector heatmap (10), market phase.
Real data from fetchers: world indices, commodities, macro indicators, market depth.
"""
import pandas as pd
from app.db import get_connection
from app.fetchers.cache import cache_get

# ── Indian indices we report on ─────────────────────────
INDIAN_INDICES = [
    ("NIFTY 50", "Nifty 50"),
    ("NIFTY BANK", "Bank Nifty"),
    ("NIFTY MIDCAP 100", "Nifty Midcap"),
    ("NIFTY SMALLCAP 100", "Nifty Smallcap"),
]

# ── Sector indices for heatmap ──────────────────────────
SECTOR_INDICES = [
    ("NIFTY IT", "IT"),
    ("NIFTY PHARMA", "Pharma"),
    ("NIFTY AUTO", "Auto"),
    ("NIFTY FMCG", "FMCG"),
    ("NIFTY METAL", "Metal"),
    ("NIFTY REALTY", "Realty"),
    ("NIFTY ENERGY", "Energy"),
    ("NIFTY MEDIA", "Media"),
    ("NIFTY PSE", "PSU"),
    ("NIFTY INFRA", "Infra"),
]

# ── Market phase thresholds ─────────────────────────────
# Nifty close vs 200-day (52-week) MA
PHASE_BULLISH_PCT = 3.0    # above MA by > 3%
PHASE_BEARISH_PCT = -3.0   # below MA by > 3%


def get_global_pulse() -> dict:
    """Build the Global Pulse response with real + placeholder data."""
    conn = get_connection()
    try:
        # Load all index daily data
        df = pd.read_sql(
            "SELECT index_name, date, open, high, low, close FROM index_daily ORDER BY date",
            conn,
        )
    finally:
        conn.close()

    df["date"] = pd.to_datetime(df["date"])

    latest_date = df["date"].max().strftime("%Y-%m-%d")

    # Build each section
    indian_indices = _calc_indian_indices(df)
    sector_heatmap = _calc_sector_heatmap(df)
    market_phase = _calc_market_phase(df)

    # Trend data from daily accumulation (no backfill — builds over time)
    ad_trend = _get_accumulation_trend("ad")
    hl_trend = _get_accumulation_trend("52w_hl")
    fii_dii_trend = _get_accumulation_trend("fii_dii")

    return {
        "date": latest_date,
        "market_phase": market_phase,
        "world_indices": _get_cached_or_fallback("world_indices", _fallback_world_indices),
        "commodities": _get_cached_or_fallback("commodities", _fallback_commodities),
        "macro_indicators": _get_cached_or_fallback("macro_indicators", _fallback_macro_indicators),
        "indian_indices": indian_indices,
        "market_depth": _get_cached_or_fallback("market_depth", _fallback_market_depth),
        "sector_heatmap": sector_heatmap,
        "ad_trend": ad_trend,
        "hl_trend": hl_trend,
        "fii_dii_trend": fii_dii_trend,
    }


# ── Real calculations ───────────────────────────────────


def _calc_indian_indices(df: pd.DataFrame) -> list[dict]:
    """4 Indian indices with latest value, 1-day change %, and distance from 52W high."""
    results = []
    for db_name, display_name in INDIAN_INDICES:
        idx_df = df[df["index_name"] == db_name].sort_values("date")
        if idx_df.empty:
            continue

        latest = idx_df.iloc[-1]
        latest_close = round(float(latest["close"]), 2)

        # 1-day change %
        if len(idx_df) >= 2:
            prev_close = float(idx_df.iloc[-2]["close"])
            change_pct = round((latest_close - prev_close) / prev_close * 100, 1)
        else:
            change_pct = 0.0

        # 52-week (252 trading days) high
        lookback_252 = idx_df.tail(252)
        high_52w = float(lookback_252["high"].max())
        dist_from_52w_high = round((latest_close - high_52w) / high_52w * 100, 1)

        results.append({
            "name": display_name,
            "value": latest_close,
            "change_pct": change_pct,
            "dist_from_52w_high": dist_from_52w_high,
        })

    return results


def _calc_sector_heatmap(df: pd.DataFrame) -> list[dict]:
    """10 sectors with 1-week change % and RS vs Nifty 4W."""
    # Get Nifty 50 for RS calculation
    nifty_df = df[df["index_name"] == "NIFTY 50"].sort_values("date")
    if nifty_df.empty:
        return []

    nifty_latest = float(nifty_df.iloc[-1]["close"])

    # Nifty 4-week (~20 trading days) return
    nifty_20d_ago = nifty_df.tail(21).iloc[0] if len(nifty_df) >= 21 else nifty_df.iloc[0]
    nifty_4w_return = (nifty_latest - float(nifty_20d_ago["close"])) / float(nifty_20d_ago["close"]) * 100

    # Nifty 1-week (~5 trading days) return
    nifty_5d_ago = nifty_df.tail(6).iloc[0] if len(nifty_df) >= 6 else nifty_df.iloc[0]
    nifty_1w_return = (nifty_latest - float(nifty_5d_ago["close"])) / float(nifty_5d_ago["close"]) * 100

    results = []
    for db_name, display_name in SECTOR_INDICES:
        idx_df = df[df["index_name"] == db_name].sort_values("date")
        if idx_df.empty:
            continue

        latest_close = float(idx_df.iloc[-1]["close"])

        # 1-week change %
        ref_5d = idx_df.tail(6).iloc[0] if len(idx_df) >= 6 else idx_df.iloc[0]
        change_pct = round((latest_close - float(ref_5d["close"])) / float(ref_5d["close"]) * 100, 1)

        # RS vs Nifty 4W = sector 4W return - Nifty 4W return
        ref_20d = idx_df.tail(21).iloc[0] if len(idx_df) >= 21 else idx_df.iloc[0]
        sector_4w_return = (latest_close - float(ref_20d["close"])) / float(ref_20d["close"]) * 100
        rs_vs_nifty_4w = round(sector_4w_return - nifty_4w_return, 1)

        results.append({
            "name": display_name,
            "change_pct": change_pct,
            "rs_vs_nifty_4w": rs_vs_nifty_4w,
        })

    # Sort by RS vs Nifty descending (strongest sectors first)
    results.sort(key=lambda x: x["rs_vs_nifty_4w"], reverse=True)
    return results


def _calc_market_phase(df: pd.DataFrame) -> dict:
    """Market phase based on 4 criteria from Gordon's process:
    1. Nifty vs 200-day MA (primary)
    2. Advance/Decline ratio (breadth)
    3. 52W highs vs lows ratio (breadth)
    4. FII + DII combined flow (liquidity)

    Each criterion votes bullish (+1), bearish (-1), or neutral (0).
    Final label derived from the sum of votes.
    """
    nifty_df = df[df["index_name"] == "NIFTY 50"].sort_values("date")
    if len(nifty_df) < 200:
        return {"label": "INSUFFICIENT DATA", "reason": "Need 200+ trading days for Nifty 50"}

    latest_close = float(nifty_df.iloc[-1]["close"])
    ma_200 = float(nifty_df.tail(200)["close"].mean())
    pct_from_ma = (latest_close - ma_200) / ma_200 * 100

    # Scoring: each criterion contributes +1 (bullish), -1 (bearish), or 0 (neutral)
    score = 0
    reasons = []

    # ── Criterion 1: Nifty vs 200-day MA ──
    if pct_from_ma > PHASE_BULLISH_PCT:
        score += 1
        reasons.append(f"Nifty {pct_from_ma:+.1f}% above 200-day MA ({ma_200:,.0f})")
    elif pct_from_ma < PHASE_BEARISH_PCT:
        score -= 1
        reasons.append(f"Nifty {pct_from_ma:+.1f}% below 200-day MA ({ma_200:,.0f})")
    else:
        reasons.append(f"Nifty {pct_from_ma:+.1f}% from 200-day MA ({ma_200:,.0f})")

    # ── Criterion 2: Advance/Decline ratio ──
    depth = cache_get("market_depth", max_age_hours=24.0)
    if depth and depth.get("ad_ratio") is not None:
        ad_ratio = depth["ad_ratio"]
        if ad_ratio > 1.5:
            score += 1
            reasons.append(f"A/D healthy ({ad_ratio})")
        elif ad_ratio < 0.7:
            score -= 1
            reasons.append(f"A/D weak ({ad_ratio})")
        else:
            reasons.append(f"A/D neutral ({ad_ratio})")

    # ── Criterion 3: 52W highs vs lows ──
    if depth and depth.get("hl_ratio") is not None:
        hl_ratio = depth["hl_ratio"]
        if hl_ratio > 2.0:
            score += 1
            reasons.append(f"52W highs dominating (H/L {hl_ratio})")
        elif hl_ratio < 0.5:
            score -= 1
            reasons.append(f"52W lows dominating (H/L {hl_ratio})")
        else:
            reasons.append(f"52W H/L mixed ({hl_ratio})")

    # ── Criterion 4: FII + DII combined flow ──
    macro = cache_get("macro_indicators", max_age_hours=24.0)
    if macro:
        fii = macro.get("fii_flow_mtd")
        dii = macro.get("dii_flow_mtd")
        if fii is not None and dii is not None:
            combined = fii + dii
            if combined > 0:
                score += 1
                reasons.append(f"FII+DII net positive (₹{combined:+,.0f} Cr)")
            elif combined < -2000:
                score -= 1
                reasons.append(f"FII+DII net negative (₹{combined:+,.0f} Cr)")
            else:
                reasons.append(f"FII+DII near flat (₹{combined:+,.0f} Cr)")

    # ── Derive label from composite score ──
    if score >= 3:
        label = "BULLISH"
    elif score == 2:
        label = "CAUTIOUSLY BULLISH"
    elif score <= -3:
        label = "BEARISH"
    elif score <= -2:
        label = "CAUTIOUSLY BEARISH"
    else:
        label = "SIDEWAYS"

    return {"label": label, "reason": ". ".join(reasons)}


# ── Accumulated trend data ─────────────────────────────


def _get_accumulation_trend(metric: str) -> list[dict]:
    """Get trend data from daily_accumulation table (last 30 days)."""
    try:
        from scripts.daily_accumulation import get_accumulation_trend
        return get_accumulation_trend(metric, days=30)
    except Exception:
        return []


# ── Cached fetcher data (populated by refresh endpoint) ─


def _get_cached_or_fallback(key: str, fallback_fn):
    """Return cached fetcher data, or fallback (nulls) if cache is empty/stale."""
    cached = cache_get(key, max_age_hours=24.0)
    if cached is not None:
        return cached
    return fallback_fn()


def _fallback_world_indices() -> list[dict]:
    return [
        {"name": "S&P 500", "value": None, "change_pct": None},
        {"name": "Nasdaq", "value": None, "change_pct": None},
        {"name": "FTSE 100", "value": None, "change_pct": None},
        {"name": "Nikkei 225", "value": None, "change_pct": None},
        {"name": "Shanghai", "value": None, "change_pct": None},
    ]


def _fallback_commodities() -> list[dict]:
    return [
        {"name": "Gold", "value": None, "unit": "$", "change_pct": None},
        {"name": "Crude Oil", "value": None, "unit": "$", "change_pct": None},
        {"name": "Silver", "value": None, "unit": "$", "change_pct": None},
        {"name": "Copper", "value": None, "unit": "$", "change_pct": None},
        {"name": "Natural Gas", "value": None, "unit": "$", "change_pct": None},
    ]


def _fallback_macro_indicators() -> dict:
    return {
        "dxy": {"value": None, "change_pct": None},
        "us_10y": {"value": None},
        "india_10y": {"value": None},
        "inr_usd": {"value": None},
        "fii_flow_mtd": None,
        "dii_flow_mtd": None,
    }


def _fallback_market_depth() -> dict:
    return {
        "advancing": None,
        "declining": None,
        "ad_ratio": None,
        "highs_52w": None,
        "lows_52w": None,
        "hl_ratio": None,
    }
