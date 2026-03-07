"""Daily accumulation of market breadth + flow + leverage data.

P2 items 13-16 from pending-list.md (A1-A4 from databuilder.md).

Stores daily A/D counts, 52W highs/lows, FII/DII flows, and market
leverage (F&O participant OI) in the daily_accumulation table.
These have no historical source — every day not collected is lost forever.
Reads from market_depth and macro_indicators fetcher caches (must run
after macro refresh).

Usage:
    python -m scripts.run_backfill --step daily_accumulation
"""

import logging
from datetime import date

from scripts.db import get_connection, init_schema

logger = logging.getLogger(__name__)


def daily_accumulation_store():
    """Read today's market depth from fetcher cache and store in daily_accumulation table."""
    init_schema()

    today = date.today().isoformat()

    conn = get_connection()

    # Check if we already have today's data
    existing = conn.execute(
        "SELECT COUNT(*) as cnt FROM daily_accumulation WHERE date = ?",
        (today,),
    ).fetchone()

    if existing and existing["cnt"] >= 4:
        print(f"Daily Accumulation: Already have data for {today}. Skipping.")
        conn.close()
        return

    inserted = 0

    # ── Market depth: A/D counts + 52W Highs/Lows ──
    try:
        from app.fetchers.market_depth import fetch_market_depth
        depth = fetch_market_depth(force=True)
    except Exception as e:
        logger.warning(f"Daily Accumulation: market_depth fetch failed: {e}")
        depth = None

    if depth:
        # Store A/D counts
        advancing = depth.get("advancing")
        declining = depth.get("declining")
        ad_ratio = depth.get("ad_ratio")
        if advancing is not None or declining is not None:
            conn.execute(
                """INSERT OR REPLACE INTO daily_accumulation
                   (date, metric, value1, value2, ratio)
                   VALUES (?, 'ad', ?, ?, ?)""",
                (today, advancing, declining, ad_ratio),
            )
            inserted += 1
            print(f"  A/D: {advancing} advancing, {declining} declining, ratio {ad_ratio}")

        # Store 52W Highs/Lows
        highs_52w = depth.get("highs_52w")
        lows_52w = depth.get("lows_52w")
        hl_ratio = depth.get("hl_ratio")
        if highs_52w is not None or lows_52w is not None:
            conn.execute(
                """INSERT OR REPLACE INTO daily_accumulation
                   (date, metric, value1, value2, ratio)
                   VALUES (?, '52w_hl', ?, ?, ?)""",
                (today, highs_52w, lows_52w, hl_ratio),
            )
            inserted += 1
            print(f"  52W: {highs_52w} highs, {lows_52w} lows, ratio {hl_ratio}")

    # ── FII/DII daily flows ──
    try:
        from app.fetchers.macro_indicators import _fetch_fii_dii
        fii_net, dii_net = _fetch_fii_dii()
        if fii_net is not None or dii_net is not None:
            conn.execute(
                """INSERT OR REPLACE INTO daily_accumulation
                   (date, metric, value1, value2, ratio)
                   VALUES (?, 'fii_dii', ?, ?, NULL)""",
                (today, fii_net, dii_net),
            )
            inserted += 1
            print(f"  FII/DII: FII net {fii_net} Cr, DII net {dii_net} Cr")
    except Exception as e:
        logger.warning(f"Daily Accumulation: FII/DII fetch failed: {e}")

    # Commit and close before leverage fetch — it writes to live_cache
    # which needs its own DB connection (avoids "database is locked").
    conn.commit()
    conn.close()

    # ── Market leverage (F&O participant OI) ──
    try:
        from app.fetchers.market_leverage import fetch_market_leverage
        leverage = fetch_market_leverage(force=True)
        if leverage and leverage.get("client_long_contracts") is not None:
            client_long = leverage["client_long_contracts"]
            client_short = leverage["client_short_contracts"]
            ls_ratio = leverage.get("client_long_short_ratio")
            conn2 = get_connection()
            conn2.execute(
                """INSERT OR REPLACE INTO daily_accumulation
                   (date, metric, value1, value2, ratio)
                   VALUES (?, 'market_leverage', ?, ?, ?)""",
                (today, client_long, client_short, ls_ratio),
            )
            conn2.commit()
            conn2.close()
            inserted += 1
            print(f"  Leverage: Client long {client_long:,}, short {client_short:,}, L/S ratio {ls_ratio}")
    except Exception as e:
        logger.warning(f"Daily Accumulation: market leverage fetch failed: {e}")

    print(f"Daily Accumulation: Stored {inserted} metric(s) for {today}.")


def get_accumulation_trend(metric: str, days: int = 30) -> list[dict]:
    """Get recent trend data for a metric ('ad' or '52w_hl').

    Returns list of dicts with date, value1, value2, ratio — oldest first.
    """
    conn = get_connection()
    rows = conn.execute(
        """SELECT date, value1, value2, ratio
           FROM daily_accumulation
           WHERE metric = ?
           ORDER BY date DESC
           LIMIT ?""",
        (metric, days),
    ).fetchall()
    conn.close()

    return [
        {"date": r["date"], "value1": r["value1"], "value2": r["value2"], "ratio": r["ratio"]}
        for r in reversed(rows)  # oldest first
    ]
