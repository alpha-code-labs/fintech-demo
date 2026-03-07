"""
Step 'delivery': Backfill delivery % and related columns into stock_ohlc.
Uses nselib bhav_copy_with_delivery(trade_date) — one API call per trading date
returns ALL stocks for that day. Updates the 7 NULL columns left by yfinance.
"""
import time
import pandas as pd
from datetime import datetime
from nselib import capital_market

from scripts.config import JUGAAD_DELAY
from scripts.db import get_connection, init_schema
from scripts.progress import (
    get_remaining_items, get_error_items,
    mark_started, mark_done, mark_error,
    print_progress_bar,
)


def _get_all_trading_dates() -> list[str]:
    """Get all distinct dates from stock_ohlc, ordered ascending."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT date FROM stock_ohlc ORDER BY date"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def _convert_date_for_nselib(iso_date: str) -> str:
    """Convert 'YYYY-MM-DD' to 'DD-MM-YYYY' for nselib API."""
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    return dt.strftime("%d-%m-%Y")


def _convert_nse_date(nse_date: str) -> str:
    """Convert '02-Mar-2026' to '2026-03-02'."""
    dt = datetime.strptime(nse_date, "%d-%b-%Y")
    return dt.strftime("%Y-%m-%d")


def _update_delivery_for_date(iso_date: str) -> int:
    """
    Fetch bhav copy with delivery for a single date,
    update stock_ohlc rows with delivery data.
    Returns count of rows updated.
    """
    nselib_date = _convert_date_for_nselib(iso_date)
    df = capital_market.bhav_copy_with_delivery(nselib_date)

    if df is None or df.empty:
        return 0

    # Filter to EQ series only
    if "SERIES" in df.columns:
        df = df[df["SERIES"].str.strip() == "EQ"]

    if df.empty:
        return 0

    conn = get_connection()
    updated = 0

    for _, row in df.iterrows():
        symbol = str(row.get("SYMBOL", "")).strip()
        if not symbol:
            continue

        prev_close = pd.to_numeric(row.get("PREV_CLOSE"), errors="coerce")
        ltp = pd.to_numeric(row.get("LAST_PRICE"), errors="coerce")
        vwap = pd.to_numeric(row.get("AVG_PRICE"), errors="coerce")
        turnover_lacs = pd.to_numeric(row.get("TURNOVER_LACS"), errors="coerce")
        value = turnover_lacs * 100000 if pd.notna(turnover_lacs) else None
        no_of_trades = pd.to_numeric(row.get("NO_OF_TRADES"), errors="coerce")
        deliverable_qty = pd.to_numeric(row.get("DELIV_QTY"), errors="coerce")
        delivery_pct = pd.to_numeric(row.get("DELIV_PER"), errors="coerce")

        # Convert NaN to None for SQLite
        prev_close = None if pd.isna(prev_close) else float(prev_close)
        ltp = None if pd.isna(ltp) else float(ltp)
        vwap = None if pd.isna(vwap) else float(vwap)
        value = None if value is not None and pd.isna(value) else value
        no_of_trades = None if pd.isna(no_of_trades) else int(no_of_trades)
        deliverable_qty = None if pd.isna(deliverable_qty) else int(deliverable_qty)
        delivery_pct = None if pd.isna(delivery_pct) else float(delivery_pct)

        cursor = conn.execute(
            """UPDATE stock_ohlc SET
                prev_close = ?, ltp = ?, vwap = ?, value = ?,
                no_of_trades = ?, deliverable_qty = ?, delivery_pct = ?
            WHERE symbol = ? AND date = ?""",
            (prev_close, ltp, vwap, value,
             no_of_trades, deliverable_qty, delivery_pct,
             symbol, iso_date),
        )
        updated += cursor.rowcount

    conn.commit()
    conn.close()
    return updated


def backfill_delivery(delay: float = JUGAAD_DELAY, retry_errors: bool = False):
    """Backfill delivery data for all trading dates in stock_ohlc."""
    init_schema()

    all_dates = _get_all_trading_dates()
    if not all_dates:
        print("No dates in stock_ohlc. Run --step 0a first.")
        return

    if retry_errors:
        remaining = get_error_items("delivery")
        print(f"Retrying {len(remaining)} errored dates...")
    else:
        remaining = get_remaining_items("delivery", all_dates)

    if not remaining:
        print("Step delivery: All dates already done.")
        return

    total = len(remaining)
    print(f"Step delivery: Backfilling delivery data for {total} trading dates")
    print(f"  Date range: {remaining[0]} to {remaining[-1]}")
    print(f"  Using nselib bhav_copy_with_delivery — 1 API call per date, {delay}s delay")

    start_time = time.time()

    for i, iso_date in enumerate(remaining):
        mark_started("delivery", iso_date)
        try:
            updated = _update_delivery_for_date(iso_date)
            mark_done("delivery", iso_date, updated)
        except Exception as e:
            mark_error("delivery", iso_date, str(e)[:500])

        print_progress_bar(i + 1, total, iso_date, start_time)
        time.sleep(delay)

    print(f"\nStep delivery complete.")


if __name__ == "__main__":
    backfill_delivery()
