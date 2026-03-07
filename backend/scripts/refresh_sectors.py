"""Quarterly sector classification refresh — update sector/industry for all stocks.

P3 item 19 from pending-list.md (Step 2 from databuilder.md).

Re-fetches sector and industry from yfinance for every stock in the universe.
Updates the stock_universe table in-place. Sectors rarely change, but
companies occasionally get reclassified, and new stocks added via
refresh_universe may have stale or missing sector data.

Run once a quarter or after a major index rebalancing.

Usage:
    python -m scripts.run_backfill --step refresh_sectors
"""
import time
import logging

import yfinance as yf

from scripts.config import YFINANCE_DELAY
from scripts.db import get_connection, get_universe_symbols, init_schema

logger = logging.getLogger(__name__)


def refresh_sectors(delay: float = YFINANCE_DELAY):
    """Re-fetch sector/industry classification for all stocks in universe."""
    init_schema()
    symbols = get_universe_symbols()

    if not symbols:
        print("No stocks in universe. Run --step universe first.")
        return

    total = len(symbols)
    print(f"Sector Classification Refresh: {total} stocks")

    updated = 0
    changed = 0
    errors = 0
    start_time = time.time()

    for i, symbol in enumerate(symbols):
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            info = ticker.info

            new_sector = info.get("sector", "") or ""
            new_industry = info.get("industry", "") or ""

            if not new_sector:
                # yfinance returned no sector — skip to avoid blanking data
                pass
            else:
                # Check if it changed
                conn = get_connection()
                row = conn.execute(
                    "SELECT sector, industry FROM stock_universe WHERE symbol = ?",
                    (symbol,),
                ).fetchone()

                old_sector = row["sector"] if row else ""
                old_industry = row["industry"] if row else ""

                conn.execute(
                    "UPDATE stock_universe SET sector = ?, industry = ? WHERE symbol = ?",
                    (new_sector, new_industry, symbol),
                )
                conn.commit()
                conn.close()
                updated += 1

                if old_sector != new_sector or old_industry != new_industry:
                    changed += 1
                    print(f"\n    {symbol}: {old_sector}/{old_industry} -> {new_sector}/{new_industry}")

        except Exception as e:
            errors += 1
            logger.warning(f"Sector refresh failed for {symbol}: {e}")

        # Progress
        elapsed = time.time() - start_time
        rate = (i + 1) / elapsed if elapsed > 0 else 0
        eta = (total - i - 1) / rate if rate > 0 else 0
        print(
            f"\r  [{i+1}/{total}] {symbol:<15} "
            f"updated={updated} changed={changed} errors={errors} "
            f"ETA {int(eta//60)}m{int(eta%60)}s",
            end="", flush=True,
        )

        time.sleep(delay)

    elapsed = time.time() - start_time
    print(f"\n\nSector Classification Refresh complete.")
    print(f"  Stocks processed: {total}")
    print(f"  Successfully updated: {updated}")
    print(f"  Classifications changed: {changed}")
    print(f"  Errors: {errors}")
    print(f"  Time: {int(elapsed//60)}m {int(elapsed%60)}s")
