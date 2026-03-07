"""Quarterly financials refresh — re-fetch latest financials for all stocks.

P3 item 17 from pending-list.md (Steps 15-16 from databuilder.md).

Re-runs yfinance quarterly_income_stmt + quarterly_balance_sheet for every
stock in the universe. Uses INSERT OR REPLACE so new quarters get added
and existing quarters get updated.

Run after each quarterly results season (May, Aug, Nov, Feb) or anytime
you want to pick up newly declared results.

Usage:
    python -m scripts.run_backfill --step refresh_financials
"""
import time
import logging

from scripts.config import YFINANCE_DELAY
from scripts.db import get_connection, get_universe_symbols, init_schema
from scripts.backfill_financials import _extract_financials

logger = logging.getLogger(__name__)


def refresh_financials(delay: float = YFINANCE_DELAY):
    """Re-fetch quarterly financials for all stocks in universe."""
    init_schema()
    symbols = get_universe_symbols()

    if not symbols:
        print("No stocks in universe. Run --step universe first.")
        return

    total = len(symbols)
    print(f"Quarterly Financials Refresh: {total} stocks")

    updated = 0
    errors = 0
    new_quarters = 0
    start_time = time.time()

    # Get existing quarter counts per symbol for comparison
    conn = get_connection()
    existing_counts = {}
    rows = conn.execute(
        "SELECT symbol, COUNT(*) as cnt FROM quarterly_financials GROUP BY symbol"
    ).fetchall()
    for r in rows:
        existing_counts[r["symbol"]] = r["cnt"]
    conn.close()

    for i, symbol in enumerate(symbols):
        try:
            records = _extract_financials(symbol)

            if records:
                conn = get_connection()
                before_count = conn.execute(
                    "SELECT COUNT(*) as cnt FROM quarterly_financials WHERE symbol = ?",
                    (symbol,),
                ).fetchone()["cnt"]

                for rec in records:
                    conn.execute(
                        """INSERT OR REPLACE INTO quarterly_financials
                           (symbol, quarter_end, revenue, operating_income, net_income,
                            eps, operating_margin, total_debt, total_assets, total_equity,
                            cash_flow_operations, source, fetched_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            rec["symbol"], rec["quarter_end"], rec["revenue"],
                            rec["operating_income"], rec["net_income"], rec["eps"],
                            rec["operating_margin"], rec["total_debt"], rec["total_assets"],
                            rec["total_equity"], rec.get("cash_flow_operations"),
                            rec["source"], rec["fetched_at"],
                        ),
                    )
                conn.commit()

                after_count = conn.execute(
                    "SELECT COUNT(*) as cnt FROM quarterly_financials WHERE symbol = ?",
                    (symbol,),
                ).fetchone()["cnt"]
                conn.close()

                added = after_count - before_count
                if added > 0:
                    new_quarters += added
                updated += 1

        except Exception as e:
            errors += 1
            logger.warning(f"Financials refresh failed for {symbol}: {e}")

        # Progress
        elapsed = time.time() - start_time
        rate = (i + 1) / elapsed if elapsed > 0 else 0
        eta = (total - i - 1) / rate if rate > 0 else 0
        print(
            f"\r  [{i+1}/{total}] {symbol:<15} "
            f"updated={updated} new_qtrs={new_quarters} errors={errors} "
            f"ETA {int(eta//60)}m{int(eta%60)}s",
            end="", flush=True,
        )

        time.sleep(delay)

    elapsed = time.time() - start_time
    print(f"\n\nQuarterly Financials Refresh complete.")
    print(f"  Stocks processed: {total}")
    print(f"  Successfully updated: {updated}")
    print(f"  New quarters added: {new_quarters}")
    print(f"  Errors: {errors}")
    print(f"  Time: {int(elapsed//60)}m {int(elapsed%60)}s")
