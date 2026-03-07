"""Quarterly promoter holding refresh — re-fetch latest shareholding for all stocks.

P3 item 18 from pending-list.md (Step 17 from databuilder.md).

Re-runs NSE corporate-share-holdings-master API for every stock in the
universe. Uses INSERT OR REPLACE so new quarters get added and existing
quarters get updated.

Run after each quarterly shareholding pattern filing (~same schedule as
financials: Feb, May, Aug, Nov) or anytime.

Usage:
    python -m scripts.run_backfill --step refresh_promoter
"""
import time
import logging
import requests

from scripts.config import NSEPYTHON_DELAY
from scripts.db import get_connection, get_universe_symbols, init_schema
from scripts.backfill_promoter import _fetch_shareholding, _get_nse_session

logger = logging.getLogger(__name__)


def refresh_promoter(delay: float = NSEPYTHON_DELAY):
    """Re-fetch promoter holding for all stocks in universe."""
    init_schema()
    symbols = get_universe_symbols()

    if not symbols:
        print("No stocks in universe. Run --step universe first.")
        return

    total = len(symbols)
    print(f"Promoter Holding Refresh: {total} stocks")

    session = _get_nse_session()
    updated = 0
    errors = 0
    new_quarters = 0
    session_refreshes = 0
    start_time = time.time()

    for i, symbol in enumerate(symbols):
        try:
            records = _fetch_shareholding(symbol, session)

            if records:
                conn = get_connection()
                before_count = conn.execute(
                    "SELECT COUNT(*) as cnt FROM promoter_holding WHERE symbol = ?",
                    (symbol,),
                ).fetchone()["cnt"]

                for rec in records:
                    conn.execute(
                        """INSERT OR REPLACE INTO promoter_holding
                           (symbol, quarter_end, promoter_pct, public_pct, dii_pct, fii_pct,
                            source, fetched_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            rec["symbol"], rec["quarter_end"], rec["promoter_pct"],
                            rec["public_pct"], rec["dii_pct"], rec["fii_pct"],
                            rec["source"], rec["fetched_at"],
                        ),
                    )
                conn.commit()

                after_count = conn.execute(
                    "SELECT COUNT(*) as cnt FROM promoter_holding WHERE symbol = ?",
                    (symbol,),
                ).fetchone()["cnt"]
                conn.close()

                added = after_count - before_count
                if added > 0:
                    new_quarters += added
                updated += 1

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                logger.info("Session expired, refreshing cookies...")
                session = _get_nse_session()
                session_refreshes += 1
                time.sleep(5)
            errors += 1

        except Exception as e:
            errors += 1
            logger.warning(f"Promoter refresh failed for {symbol}: {e}")

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
    print(f"\n\nPromoter Holding Refresh complete.")
    print(f"  Stocks processed: {total}")
    print(f"  Successfully updated: {updated}")
    print(f"  New quarters added: {new_quarters}")
    print(f"  Errors: {errors}")
    print(f"  Session refreshes: {session_refreshes}")
    print(f"  Time: {int(elapsed//60)}m {int(elapsed%60)}s")
