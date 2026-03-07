"""Daily Indian + sector index append.

P0 item 2 from pending-list.md.

Fetches index data for all 14 indices (Nifty 50, 3 broad, 10 sector)
for dates after the last date in index_daily. Uses nselib with yfinance
fallback, same as backfill_indices.py.

Strategy: fetch the entire missing date range per index in one call
(nselib needs from_date < to_date; yfinance handles ranges well too).

Usage:
    python -m scripts.run_backfill --step daily_indices
    python -m scripts.run_backfill --step daily_indices --retry-errors
"""

import time
import logging
from datetime import datetime, date, timedelta

import pandas as pd
from nselib import capital_market
import yfinance as yf

from scripts.config import (
    NIFTY50_NAME, BROAD_INDICES, SECTOR_INDICES,
    JUGAAD_DELAY, YFINANCE_INDEX_TICKERS,
)
from scripts.db import get_connection, init_schema, insert_dataframe
from scripts.progress import (
    get_remaining_items,
    get_error_items,
    mark_started,
    mark_done,
    mark_error,
    print_progress_bar,
)

logger = logging.getLogger(__name__)

ALL_INDICES = [NIFTY50_NAME] + BROAD_INDICES + SECTOR_INDICES
DATE_FMT = "%d-%m-%Y"


# ── helpers ────────────────────────────────────────────


def _get_last_index_date() -> str | None:
    """Return the most recent date across all indices in index_daily."""
    conn = get_connection()
    row = conn.execute("SELECT MAX(date) AS max_date FROM index_daily").fetchone()
    conn.close()
    return row["max_date"] if row and row["max_date"] else None


def _map_nselib_df(df: pd.DataFrame, index_name: str) -> pd.DataFrame:
    """Map nselib index DataFrame to our schema."""
    return pd.DataFrame({
        "index_name": [index_name] * len(df),
        "date": pd.to_datetime(df["TIMESTAMP"].values, format="mixed").strftime("%Y-%m-%d"),
        "open": pd.to_numeric(df["OPEN_INDEX_VAL"], errors="coerce").values,
        "high": pd.to_numeric(df["HIGH_INDEX_VAL"], errors="coerce").values,
        "low": pd.to_numeric(df["LOW_INDEX_VAL"], errors="coerce").values,
        "close": pd.to_numeric(df["CLOSE_INDEX_VAL"], errors="coerce").values,
    })


def _map_yfinance_df(df: pd.DataFrame, index_name: str, ticker: str) -> pd.DataFrame:
    """Map yfinance DataFrame to our schema."""
    if df.empty:
        return pd.DataFrame()
    return pd.DataFrame({
        "index_name": [index_name] * len(df),
        "date": df.index.strftime("%Y-%m-%d"),
        "open": df[("Open", ticker)].values,
        "high": df[("High", ticker)].values,
        "low": df[("Low", ticker)].values,
        "close": df[("Close", ticker)].values,
    })


def _fetch_index_range(index_name: str, from_date: date, to_date: date) -> pd.DataFrame:
    """Fetch index data for a date range. nselib first, yfinance fallback.

    nselib requires from_date < to_date (no single-day queries).
    We always pass the full range (last_db_date+1 to today).
    """
    from_str = from_date.strftime(DATE_FMT)
    to_str = to_date.strftime(DATE_FMT)

    # Try nselib
    try:
        df = capital_market.index_data(index_name, from_str, to_str)
        if df is not None and not df.empty:
            mapped = _map_nselib_df(df, index_name)
            # Filter to only dates >= from_date (nselib sometimes returns earlier)
            mapped = mapped[mapped["date"] >= from_date.isoformat()]
            if not mapped.empty:
                return mapped
    except Exception as e:
        logger.debug(f"nselib failed for {index_name}: {e}")

    # Fallback to yfinance
    ticker = YFINANCE_INDEX_TICKERS.get(index_name)
    if not ticker:
        return pd.DataFrame()

    try:
        # yfinance end is exclusive, so add 1 day
        end_str = (to_date + timedelta(days=1)).isoformat()
        df = yf.download(ticker, start=from_date.isoformat(), end=end_str, progress=False)
        if not df.empty:
            return _map_yfinance_df(df, index_name, ticker)
    except Exception as e:
        logger.debug(f"yfinance failed for {index_name}: {e}")

    return pd.DataFrame()


# ── entry point ────────────────────────────────────────


def daily_index_append(delay: float = JUGAAD_DELAY, retry_errors: bool = False):
    """Fetch and insert index data for all trading days since last DB date."""
    init_schema()

    last_date_str = _get_last_index_date()
    if not last_date_str:
        print("Daily Indices: No existing index data. Run backfill first (steps 0b/0c/0d).")
        return

    from_date = datetime.strptime(last_date_str, "%Y-%m-%d").date() + timedelta(days=1)
    to_date = date.today()

    if from_date > to_date:
        print(f"Daily Indices: DB is up to date (last date: {last_date_str}). Nothing to fetch.")
        return

    # Use index names as items for progress tracking
    if retry_errors:
        remaining_names = get_error_items("daily_indices")
    else:
        remaining_names = get_remaining_items("daily_indices", ALL_INDICES)

    if not remaining_names:
        print("Daily Indices: All indices already done.")
        return

    remaining = [n for n in ALL_INDICES if n in set(remaining_names)]
    total = len(remaining)
    print(
        f"Daily Indices: {total} indices to update "
        f"({from_date.isoformat()} → {to_date.isoformat()})"
    )

    start_time = time.time()

    for i, index_name in enumerate(remaining):
        mark_started("daily_indices", index_name)
        try:
            mapped = _fetch_index_range(index_name, from_date, to_date)

            if mapped.empty:
                # Could be all holidays in the range
                mark_done("daily_indices", index_name, 0)
            else:
                mapped = mapped.drop_duplicates(subset=["index_name", "date"])
                conn = get_connection()
                rows = insert_dataframe("index_daily", mapped, conn)
                conn.close()
                mark_done("daily_indices", index_name, rows)
        except Exception as e:
            mark_error("daily_indices", index_name, str(e)[:500])
            logger.warning(f"Failed for {index_name}: {e}")

        print_progress_bar(i + 1, total, index_name, start_time)
        time.sleep(delay)

    print()  # newline after progress bar
