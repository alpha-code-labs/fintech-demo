"""Daily stock OHLC + delivery % append.

P0 item 1 from pending-list.md.

Uses nselib bhav_copy_with_delivery() — one API call per trading date
returns ALL securities with OHLC, volume, and delivery data.
Appends to the existing stock_ohlc table. Only fetches dates after
the last date already in the database.

Usage:
    python -m scripts.run_backfill --step daily_ohlc
    python -m scripts.run_backfill --step daily_ohlc --retry-errors
"""

import time
import logging
from datetime import datetime, date, timedelta

import pandas as pd
from nselib import capital_market

from scripts.config import JUGAAD_DELAY
from scripts.db import get_connection, init_schema, get_universe_symbols
from scripts.progress import (
    get_remaining_items,
    get_error_items,
    mark_started,
    mark_done,
    mark_error,
    print_progress_bar,
)

logger = logging.getLogger(__name__)


# ── helpers ────────────────────────────────────────────


def _get_last_date_in_db() -> str | None:
    """Return the most recent date in stock_ohlc, or None if empty."""
    conn = get_connection()
    row = conn.execute("SELECT MAX(date) AS max_date FROM stock_ohlc").fetchone()
    conn.close()
    return row["max_date"] if row and row["max_date"] else None


def _get_trading_dates_to_fetch() -> list[str]:
    """Return list of ISO dates from last_db_date+1 to today (weekdays only)."""
    last_date = _get_last_date_in_db()
    if not last_date:
        return []

    start = datetime.strptime(last_date, "%Y-%m-%d").date() + timedelta(days=1)
    end = date.today()

    if start > end:
        return []

    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # skip Saturday (5) and Sunday (6)
            dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return dates


def _date_to_nselib(iso_date: str) -> str:
    """Convert YYYY-MM-DD → DD-MM-YYYY for nselib."""
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    return dt.strftime("%d-%m-%Y")


def _clean(val, as_int=False):
    """Convert NaN / None → None, else float (or int)."""
    if val is None:
        return None
    numeric = pd.to_numeric(val, errors="coerce")
    if pd.isna(numeric):
        return None
    return int(numeric) if as_int else float(numeric)


def _is_holiday(df, iso_date: str) -> bool:
    """Check if nselib returned stale data for a holiday.

    nselib returns the previous trading day's data when called with a
    holiday date instead of returning empty.  We detect this by comparing
    the DATE1 column (actual trade date) with the requested date.
    """
    if "DATE1" not in df.columns:
        return False
    # DATE1 format: '02-Mar-2026'
    actual_dates = df["DATE1"].dropna().unique()
    if len(actual_dates) == 0:
        return False
    # Convert requested ISO date to the same format as DATE1
    requested_dt = datetime.strptime(iso_date, "%Y-%m-%d")
    requested_str = requested_dt.strftime("%d-%b-%Y")  # e.g. '03-Mar-2026'
    # If none of the actual dates match our request, it's a holiday
    return all(str(d).strip() != requested_str for d in actual_dates)


# ── core ───────────────────────────────────────────────


def _process_bhavcopy_for_date(iso_date: str, universe_symbols: set) -> int:
    """Fetch bhavcopy for one date, insert into stock_ohlc. Return rows inserted."""
    nselib_date = _date_to_nselib(iso_date)
    df = capital_market.bhav_copy_with_delivery(nselib_date)

    if df is None or df.empty:
        return 0

    # nselib returns prev day's data for holidays — detect and skip
    if _is_holiday(df, iso_date):
        logger.info(f"{iso_date} is a market holiday (bhavcopy returned stale data)")
        return 0

    # Filter to EQ series
    if "SERIES" in df.columns:
        df = df[df["SERIES"].str.strip() == "EQ"]

    if df.empty:
        return 0

    conn = get_connection()
    inserted = 0

    for _, row in df.iterrows():
        symbol = str(row.get("SYMBOL", "")).strip()
        if not symbol or symbol not in universe_symbols:
            continue

        # Bhavcopy columns (verified from live API output):
        #   OPEN_PRICE, HIGH_PRICE, LOW_PRICE, CLOSE_PRICE, TTL_TRD_QNTY
        #   PREV_CLOSE, LAST_PRICE, AVG_PRICE, TURNOVER_LACS
        #   NO_OF_TRADES, DELIV_QTY, DELIV_PER

        open_p = _clean(row.get("OPEN_PRICE"))
        high_p = _clean(row.get("HIGH_PRICE"))
        low_p = _clean(row.get("LOW_PRICE"))
        close_p = _clean(row.get("CLOSE_PRICE"))
        volume = _clean(row.get("TTL_TRD_QNTY"), as_int=True)

        prev_close = _clean(row.get("PREV_CLOSE"))
        ltp = _clean(row.get("LAST_PRICE"))
        vwap = _clean(row.get("AVG_PRICE"))
        turnover_lacs = _clean(row.get("TURNOVER_LACS"))
        value = turnover_lacs * 100_000 if turnover_lacs is not None else None
        no_of_trades = _clean(row.get("NO_OF_TRADES"), as_int=True)
        deliverable_qty = _clean(row.get("DELIV_QTY"), as_int=True)
        delivery_pct = _clean(row.get("DELIV_PER"))

        conn.execute(
            """INSERT OR REPLACE INTO stock_ohlc
               (symbol, date, series, open, high, low, close, volume,
                prev_close, ltp, vwap, value, no_of_trades,
                deliverable_qty, delivery_pct)
               VALUES (?, ?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                symbol, iso_date,
                open_p, high_p, low_p, close_p, volume,
                prev_close, ltp, vwap, value,
                no_of_trades, deliverable_qty, delivery_pct,
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()
    return inserted


# ── entry point ────────────────────────────────────────


def daily_ohlc_append(delay: float = JUGAAD_DELAY, retry_errors: bool = False):
    """Fetch and insert OHLC + delivery for all trading days since last DB date."""
    init_schema()

    all_dates = _get_trading_dates_to_fetch()
    if not all_dates and not retry_errors:
        last = _get_last_date_in_db()
        print(f"Daily OHLC: DB is up to date (last date: {last}). Nothing to fetch.")
        return

    universe = set(get_universe_symbols())

    if retry_errors:
        remaining = get_error_items("daily_ohlc")
    else:
        remaining = get_remaining_items("daily_ohlc", all_dates)

    if not remaining:
        print("Daily OHLC: All dates already done.")
        return

    total = len(remaining)
    print(
        f"Daily OHLC: {total} trading day(s) to fetch "
        f"({remaining[0]} → {remaining[-1]}), {len(universe)} stocks in universe"
    )

    start_time = time.time()

    for i, iso_date in enumerate(remaining):
        mark_started("daily_ohlc", iso_date)
        try:
            rows = _process_bhavcopy_for_date(iso_date, universe)
            mark_done("daily_ohlc", iso_date, rows)
        except Exception as e:
            mark_error("daily_ohlc", iso_date, str(e)[:500])
            logger.warning(f"Failed for {iso_date}: {e}")

        print_progress_bar(i + 1, total, iso_date, start_time)
        time.sleep(delay)

    print()  # newline after progress bar
