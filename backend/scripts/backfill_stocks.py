"""
Step 0a: Backfill stock OHLC + volume for all stocks in universe.
Uses yfinance (1 API call per stock for 2 years) — fast.
Delivery data not available from yfinance; can be backfilled from bhavcopy later.
"""
import time
import pandas as pd
import yfinance as yf
from datetime import date

from scripts.config import STOCK_OHLC_START, TODAY, YFINANCE_DELAY
from scripts.db import get_connection, get_universe_symbols, init_schema, insert_dataframe
from scripts.progress import (
    get_remaining_items, get_error_items,
    mark_started, mark_done, mark_error,
    print_progress_bar,
)


def _fetch_stock_yfinance(symbol: str, start: date, end: date) -> pd.DataFrame:
    """Fetch 2 years of OHLC + volume from yfinance in a single call."""
    ticker = f"{symbol}.NS"
    df = yf.download(ticker, start=start.isoformat(), end=end.isoformat(), progress=False)

    if df.empty:
        return pd.DataFrame()

    # yfinance returns multi-index columns: (metric, ticker)
    # For single ticker download, flatten them
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    return pd.DataFrame({
        "symbol": symbol,
        "series": "EQ",
        "date": df.index.strftime("%Y-%m-%d"),
        "open": df["Open"].values,
        "high": df["High"].values,
        "low": df["Low"].values,
        "close": df["Close"].values,
        "volume": df["Volume"].values,
    })


def backfill_step_0a(delay: float = YFINANCE_DELAY, retry_errors: bool = False):
    """Backfill stock OHLC data for all stocks in universe."""
    init_schema()
    all_symbols = get_universe_symbols()

    if not all_symbols:
        print("No stocks in universe. Run --step universe first.")
        return

    if retry_errors:
        remaining = get_error_items("0a")
        print(f"Retrying {len(remaining)} errored stocks...")
    else:
        remaining = get_remaining_items("0a", all_symbols)

    if not remaining:
        print("Step 0a: All stocks already done.")
        return

    total = len(remaining)
    print(f"Step 0a: Fetching OHLC for {total} stocks ({STOCK_OHLC_START} to {TODAY})")
    print(f"  Using yfinance — 1 API call per stock, {delay}s delay")

    start_time = time.time()

    for i, symbol in enumerate(remaining):
        mark_started("0a", symbol)
        try:
            mapped = _fetch_stock_yfinance(symbol, STOCK_OHLC_START, TODAY)

            if mapped.empty:
                mark_error("0a", symbol, "No data from yfinance")
                continue

            mapped = mapped.drop_duplicates(subset=["symbol", "date"])
            conn = get_connection()
            rows = insert_dataframe("stock_ohlc", mapped, conn)
            conn.close()
            mark_done("0a", symbol, rows)

        except Exception as e:
            mark_error("0a", symbol, str(e)[:500])

        print_progress_bar(i + 1, total, symbol, start_time)
        time.sleep(delay)

    print(f"\nStep 0a complete.")


if __name__ == "__main__":
    backfill_step_0a()
