"""
Steps 0b/0c/0d: Backfill index data.
  0b — NIFTY 50 (2 years)
  0c — NIFTY BANK, NIFTY MIDCAP 100, NIFTY SMLCAP 100 (1 year)
  0d — 10 sector indices (1 year)
Primary source: nselib index_data() with date chunking.
Fallback: yfinance (for indices where nselib has bugs).
"""
import time
import pandas as pd
import yfinance as yf
from datetime import date, timedelta
from nselib import capital_market

from scripts.config import (
    NIFTY50_NAME, NIFTY50_START, TODAY,
    BROAD_INDICES, INDEX_START,
    SECTOR_INDICES, SECTOR_START,
    JUGAAD_DELAY, YFINANCE_INDEX_TICKERS,
)
from scripts.db import get_connection, init_schema, insert_dataframe
from scripts.progress import (
    get_remaining_items, get_error_items,
    mark_started, mark_done, mark_error,
    print_progress_bar,
)

DATE_FMT = "%d-%m-%Y"
CHUNK_DAYS = 80


def _date_chunks(start: date, end: date) -> list[tuple[str, str]]:
    """Split a date range into chunks for the nselib API."""
    chunks = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), end)
        chunks.append((cursor.strftime(DATE_FMT), chunk_end.strftime(DATE_FMT)))
        cursor = chunk_end + timedelta(days=1)
    return chunks


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
    # yfinance multi-index columns: (metric, ticker)
    return pd.DataFrame({
        "index_name": [index_name] * len(df),
        "date": df.index.strftime("%Y-%m-%d"),
        "open": df[("Open", ticker)].values,
        "high": df[("High", ticker)].values,
        "low": df[("Low", ticker)].values,
        "close": df[("Close", ticker)].values,
    })


def _fetch_nselib_chunked(index_name: str, start: date, end: date, delay: float) -> pd.DataFrame:
    """Fetch index data from nselib in chunks."""
    chunks = _date_chunks(start, end)
    all_dfs = []
    for from_str, to_str in chunks:
        try:
            df = capital_market.index_data(index_name, from_str, to_str)
            if df is not None and not df.empty:
                all_dfs.append(df)
        except Exception:
            raise  # Let caller handle and try fallback
        time.sleep(delay)
    if not all_dfs:
        return pd.DataFrame()
    return pd.concat(all_dfs, ignore_index=True)


def _fetch_yfinance(index_name: str, start: date, end: date) -> pd.DataFrame:
    """Fetch index data from yfinance as fallback."""
    ticker = YFINANCE_INDEX_TICKERS.get(index_name)
    if not ticker:
        return pd.DataFrame()
    df = yf.download(ticker, start=start.isoformat(), end=end.isoformat(), progress=False)
    if df.empty:
        return pd.DataFrame()
    return _map_yfinance_df(df, index_name, ticker)


def _fetch_index(index_name: str, start: date, end: date, delay: float) -> pd.DataFrame:
    """Try nselib first, fall back to yfinance."""
    try:
        raw = _fetch_nselib_chunked(index_name, start, end, delay)
        if not raw.empty:
            return _map_nselib_df(raw, index_name)
    except Exception as e:
        print(f"\n  nselib failed for {index_name}: {e}")
        print(f"  Trying yfinance fallback...")

    # Fallback to yfinance
    return _fetch_yfinance(index_name, start, end)


def _backfill_index_list(step: str, indices: list[tuple[str, date, date]],
                         delay: float, retry_errors: bool):
    """Generic function to backfill a list of indices."""
    all_names = [name for name, _, _ in indices]

    if retry_errors:
        remaining_names = set(get_error_items(step))
    else:
        remaining_names = set(get_remaining_items(step, all_names))

    remaining = [(n, f, t) for n, f, t in indices if n in remaining_names]

    if not remaining:
        print(f"Step {step}: All indices already done.")
        return

    total = len(remaining)
    print(f"Step {step}: Fetching {total} indices")

    start_time = time.time()

    for i, (index_name, from_date, to_date) in enumerate(remaining):
        mark_started(step, index_name)
        try:
            mapped = _fetch_index(index_name, from_date, to_date, delay)

            if mapped.empty:
                mark_error(step, index_name, "No data from nselib or yfinance")
                continue

            mapped = mapped.drop_duplicates(subset=["index_name", "date"])
            conn = get_connection()
            rows = insert_dataframe("index_daily", mapped, conn)
            conn.close()
            mark_done(step, index_name, rows)

        except Exception as e:
            mark_error(step, index_name, str(e)[:500])

        print_progress_bar(i + 1, total, index_name, start_time)
    print(f"\nStep {step} complete.")


def backfill_step_0b(delay: float = JUGAAD_DELAY, retry_errors: bool = False):
    """Step 0b: NIFTY 50 — 2 years."""
    init_schema()
    indices = [(NIFTY50_NAME, NIFTY50_START, TODAY)]
    _backfill_index_list("0b", indices, delay, retry_errors)


def backfill_step_0c(delay: float = JUGAAD_DELAY, retry_errors: bool = False):
    """Step 0c: Bank Nifty, Midcap 100, Smallcap 100 — 1 year."""
    init_schema()
    indices = [(name, INDEX_START, TODAY) for name in BROAD_INDICES]
    _backfill_index_list("0c", indices, delay, retry_errors)


def backfill_step_0d(delay: float = JUGAAD_DELAY, retry_errors: bool = False):
    """Step 0d: 10 sector indices — 1 year."""
    init_schema()
    indices = [(name, SECTOR_START, TODAY) for name in SECTOR_INDICES]
    _backfill_index_list("0d", indices, delay, retry_errors)


if __name__ == "__main__":
    backfill_step_0b()
    backfill_step_0c()
    backfill_step_0d()
