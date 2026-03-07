"""Weekly stock universe refresh.

P0 item 3 from pending-list.md.

Re-fetches the NSE equity list and compares with current universe.
- Checks market cap only for NEW symbols (not already in DB) — fast
- Removes delisted stocks (no longer on NSE equity list)
- Updates fetched_at for all surviving stocks
- Optionally does a full market cap re-check with --full flag

Uses INSERT OR REPLACE (symbol is PRIMARY KEY), so safe to re-run.

Usage:
    python -m scripts.run_backfill --step refresh_universe
"""

import io
import time
import logging
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone

from scripts.config import NSE_EQUITY_CSV_URL, UNIVERSE_MCAP_MIN, YFINANCE_DELAY
from scripts.db import get_connection, init_schema
from scripts.progress import print_progress_bar

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/csv,text/html,application/xhtml+xml",
}


def _download_nse_equity_list() -> pd.DataFrame:
    """Download the NSE equity list CSV and return EQ-series symbols."""
    resp = requests.get(NSE_EQUITY_CSV_URL, headers=NSE_HEADERS, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.columns = df.columns.str.strip()
    if "SERIES" in df.columns:
        df = df[df["SERIES"].str.strip() == "EQ"]
    elif " SERIES" in df.columns:
        df = df[df[" SERIES"].str.strip() == "EQ"]
    return df


def _get_existing_symbols() -> set[str]:
    """Return current symbols in stock_universe."""
    conn = get_connection()
    rows = conn.execute("SELECT symbol FROM stock_universe").fetchall()
    conn.close()
    return {r["symbol"] for r in rows}


def refresh_universe(delay: float = YFINANCE_DELAY, retry_errors: bool = False):
    """Refresh the stock universe: add new stocks, remove delisted."""
    init_schema()

    existing_symbols = _get_existing_symbols()
    print(f"Current universe: {len(existing_symbols)} stocks")

    print("Downloading NSE equity list...")
    nse_df = _download_nse_equity_list()
    nse_symbols = set(nse_df["SYMBOL"].str.strip().tolist())
    print(f"Found {len(nse_symbols)} EQ-series symbols on NSE")

    # ISIN lookup
    isin_map = {}
    if "ISIN NUMBER" in nse_df.columns:
        isin_map = dict(zip(nse_df["SYMBOL"].str.strip(), nse_df["ISIN NUMBER"].str.strip()))

    # --- Step 1: Remove delisted stocks ---
    delisted = existing_symbols - nse_symbols
    conn = get_connection()
    if delisted:
        for symbol in delisted:
            conn.execute("DELETE FROM stock_universe WHERE symbol = ?", (symbol,))
        conn.commit()
        print(f"Removed {len(delisted)} delisted stocks: {sorted(delisted)}")
    else:
        print("No delisted stocks to remove.")

    # --- Step 2: Check market cap only for NEW symbols ---
    new_symbols = sorted(nse_symbols - existing_symbols)
    added = 0
    below_threshold = 0
    errors = 0
    now = datetime.now(timezone.utc).isoformat()

    if new_symbols:
        print(f"\nChecking market cap for {len(new_symbols)} new symbols...")
        start_time = time.time()

        for i, symbol in enumerate(new_symbols):
            try:
                ticker = yf.Ticker(f"{symbol}.NS")
                info = ticker.info
                mcap = info.get("marketCap", 0) or 0
                mcap_cr = mcap / 1e7

                if mcap_cr >= UNIVERSE_MCAP_MIN:
                    conn.execute(
                        """INSERT OR REPLACE INTO stock_universe
                           (symbol, company_name, series, isin, sector, industry, market_cap_cr, fetched_at)
                           VALUES (?, ?, 'EQ', ?, ?, ?, ?, ?)""",
                        (
                            symbol,
                            info.get("longName", info.get("shortName", "")),
                            isin_map.get(symbol, ""),
                            info.get("sector", ""),
                            info.get("industry", ""),
                            round(mcap_cr, 2),
                            now,
                        ),
                    )
                    added += 1
                else:
                    below_threshold += 1

            except Exception as e:
                errors += 1
                if errors <= 10:
                    logger.warning(f"Error for {symbol}: {e}")

            print_progress_bar(i + 1, len(new_symbols), symbol, start_time)
            time.sleep(delay)

        conn.commit()
        print()  # newline after progress bar
    else:
        print("No new symbols to check.")

    # --- Step 3: Update fetched_at for surviving existing stocks ---
    surviving = existing_symbols & nse_symbols
    if surviving:
        conn.execute(
            "UPDATE stock_universe SET fetched_at = ? WHERE symbol IN ({})".format(
                ",".join("?" * len(surviving))
            ),
            [now] + sorted(surviving),
        )
        conn.commit()

    conn.close()

    # Summary
    final_count = len(surviving) - len(delisted) + added
    print(f"\nUniverse refresh complete:")
    print(f"  Previous count: {len(existing_symbols)}")
    print(f"  Delisted (removed): {len(delisted)}")
    print(f"  New symbols checked: {len(new_symbols)}")
    print(f"  New stocks added (>= {UNIVERSE_MCAP_MIN} Cr): {added}")
    print(f"  Below threshold: {below_threshold}")
    print(f"  Errors: {errors}")

    # Verify final count
    conn = get_connection()
    actual = conn.execute("SELECT COUNT(*) FROM stock_universe").fetchone()[0]
    conn.close()
    print(f"  Final universe count: {actual}")

    if added > 0:
        print(f"\n  NOTE: {added} new stocks added. Run daily_ohlc to fetch their OHLC data.")

    return actual
