"""
Step 0 prerequisite: Fetch stock universe (all NSE stocks above 500 Cr market cap).
Downloads NSE equity list CSV, then checks market cap via yfinance.
"""
import io
import time
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone

from scripts.config import NSE_EQUITY_CSV_URL, UNIVERSE_MCAP_MIN, YFINANCE_DELAY
from scripts.db import get_connection, init_schema
from scripts.progress import print_progress_bar


NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/csv,text/html,application/xhtml+xml",
}


def download_nse_equity_list() -> pd.DataFrame:
    """Download the NSE equity list CSV and return EQ-series symbols."""
    resp = requests.get(NSE_EQUITY_CSV_URL, headers=NSE_HEADERS, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    # Clean column names (sometimes have extra spaces)
    df.columns = df.columns.str.strip()
    # Filter to EQ series only
    if "SERIES" in df.columns:
        df = df[df["SERIES"].str.strip() == "EQ"]
    elif " SERIES" in df.columns:
        df = df[df[" SERIES"].str.strip() == "EQ"]
    return df


def fetch_universe(delay: float = YFINANCE_DELAY):
    """
    Build the stock universe:
    1. Download NSE equity CSV
    2. Get market cap for each symbol via yfinance
    3. Keep only stocks >= 500 Cr
    4. Insert into stock_universe table
    """
    init_schema()

    # Check if universe already has data — skip if so
    conn_check = get_connection()
    existing = conn_check.execute("SELECT COUNT(*) FROM stock_universe").fetchone()[0]
    conn_check.close()
    if existing > 0:
        print(f"Universe already has {existing} stocks. Skipping. (Delete table to re-fetch.)")
        return existing

    print("Downloading NSE equity list...")
    nse_df = download_nse_equity_list()
    symbols = nse_df["SYMBOL"].str.strip().tolist()
    print(f"Found {len(symbols)} EQ-series symbols on NSE")

    # Build ISIN lookup if available
    isin_map = {}
    if "ISIN NUMBER" in nse_df.columns:
        isin_map = dict(zip(nse_df["SYMBOL"].str.strip(), nse_df["ISIN NUMBER"].str.strip()))

    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    skipped = 0
    errors = 0
    start_time = time.time()

    for i, symbol in enumerate(symbols):
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            info = ticker.info
            mcap = info.get("marketCap", 0) or 0
            mcap_cr = mcap / 1e7  # Convert INR to Crores

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
                inserted += 1
            else:
                skipped += 1

        except Exception as e:
            errors += 1
            print(f"\n  Error for {symbol}: {e}")

        print_progress_bar(i + 1, len(symbols), symbol, start_time)
        time.sleep(delay)

    conn.commit()
    conn.close()

    print(f"\nUniverse complete: {inserted} stocks >= {UNIVERSE_MCAP_MIN} Cr")
    print(f"  Skipped (below threshold): {skipped}")
    print(f"  Errors: {errors}")
    return inserted


if __name__ == "__main__":
    fetch_universe()
