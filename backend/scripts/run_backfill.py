"""
Master CLI orchestrator for Phase 0 backfill.

Usage:
    python -m scripts.run_backfill --all
    python -m scripts.run_backfill --step universe
    python -m scripts.run_backfill --step 0a
    python -m scripts.run_backfill --step 0a --retry-errors
    python -m scripts.run_backfill --step 0a --delay 2.0
    python -m scripts.run_backfill --status
"""
import argparse
import signal
import sys

from scripts.db import init_schema
from scripts.progress import print_status_report
from scripts.universe import fetch_universe
from scripts.backfill_stocks import backfill_step_0a
from scripts.backfill_indices import backfill_step_0b, backfill_step_0c, backfill_step_0d
from scripts.backfill_financials import backfill_step_0e
from scripts.backfill_promoter import backfill_step_0f
from scripts.backfill_delivery import backfill_delivery
from scripts.daily_ohlc import daily_ohlc_append
from scripts.daily_indices import daily_index_append
from scripts.refresh_universe import refresh_universe
from scripts.daily_deals import daily_deals_fetch
from scripts.daily_accumulation import daily_accumulation_store
from scripts.refresh_financials import refresh_financials
from scripts.refresh_promoter import refresh_promoter
from scripts.refresh_sectors import refresh_sectors


# Graceful shutdown on Ctrl+C
_shutdown = False

def _signal_handler(sig, frame):
    global _shutdown
    if _shutdown:
        print("\nForce quit.")
        sys.exit(1)
    _shutdown = True
    print("\nShutting down after current item... (press Ctrl+C again to force)")

signal.signal(signal.SIGINT, _signal_handler)


STEPS = {
    "universe": ("Stock Universe", lambda d, r: fetch_universe(delay=d)),
    "0a": ("Stock OHLC", lambda d, r: backfill_step_0a(delay=d, retry_errors=r)),
    "0b": ("Nifty 50", lambda d, r: backfill_step_0b(delay=d, retry_errors=r)),
    "0c": ("Broad Indices", lambda d, r: backfill_step_0c(delay=d, retry_errors=r)),
    "0d": ("Sector Indices", lambda d, r: backfill_step_0d(delay=d, retry_errors=r)),
    "0e": ("Financials", lambda d, r: backfill_step_0e(delay=d, retry_errors=r)),
    "0f": ("Promoter Holding", lambda d, r: backfill_step_0f(delay=d, retry_errors=r)),
    "delivery": ("Delivery % Backfill", lambda d, r: backfill_delivery(delay=d, retry_errors=r)),
    "daily_ohlc": ("Daily OHLC + Delivery Append", lambda d, r: daily_ohlc_append(delay=d, retry_errors=r)),
    "daily_indices": ("Daily Index Append", lambda d, r: daily_index_append(delay=d, retry_errors=r)),
    "refresh_universe": ("Weekly Universe Refresh", lambda d, r: refresh_universe(delay=d)),
    "daily_deals": ("Daily Bulk/Block Deals", lambda d, r: daily_deals_fetch(delay=d)),
    "daily_accumulation": ("Daily A/D + 52W Accumulation", lambda d, r: daily_accumulation_store()),
    "refresh_financials": ("Quarterly Financials Refresh", lambda d, r: refresh_financials(delay=d)),
    "refresh_promoter": ("Quarterly Promoter Holding Refresh", lambda d, r: refresh_promoter(delay=d)),
    "refresh_sectors": ("Quarterly Sector Classification Refresh", lambda d, r: refresh_sectors(delay=d)),
}

ALL_ORDER = ["universe", "0b", "0c", "0d", "0a", "0e", "0f"]


def main():
    parser = argparse.ArgumentParser(
        description="InvestScan Phase 0 Backfill Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Steps:
  universe   Fetch stock universe (~1,200 stocks above 500 Cr)
  0a         Stock OHLC + volume + delivery (2 years, ~20 min)
  0b         Nifty 50 index (2 years, ~2 sec)
  0c         Broad indices: Bank Nifty, Midcap, Smallcap (1 year)
  0d         Sector indices: IT, Pharma, Auto, etc. (1 year)
  0e         Quarterly financials via yfinance (~6 min)
  0f         Promoter holding via NSE API (~40 min)
  delivery   Backfill delivery % from NSE bhavcopy (~8 min)
  daily_ohlc    Daily OHLC + delivery append (run after market close)
  daily_indices    Daily index append — 14 indices (run after market close)
  refresh_universe Weekly universe refresh (add/remove/update stocks)
  daily_deals    Daily bulk/block deals fetch from NSE
  daily_accumulation  Store today's A/D + 52W highs/lows (no backfill)
  refresh_financials  Quarterly financials refresh for all stocks (~5 min)
  refresh_promoter  Quarterly promoter holding refresh (~50 min)
  refresh_sectors  Quarterly sector classification refresh (~5 min)
        """,
    )
    parser.add_argument(
        "--step",
        choices=list(STEPS.keys()),
        help="Run a specific step",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all steps in order",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show progress report and exit",
    )
    parser.add_argument(
        "--retry-errors",
        action="store_true",
        help="Retry only failed items from a specific step",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Override delay between API calls (seconds)",
    )

    args = parser.parse_args()

    # Initialize schema first
    init_schema()

    if args.status:
        print_status_report()
        return

    if not args.step and not args.all:
        parser.print_help()
        return

    if args.step:
        name, fn = STEPS[args.step]
        delay = args.delay if args.delay is not None else _default_delay(args.step)
        print(f"\n{'='*50}")
        print(f"  Running: {name}")
        print(f"  Delay: {delay}s")
        print(f"{'='*50}\n")
        fn(delay, args.retry_errors)

    elif args.all:
        for step_key in ALL_ORDER:
            if _shutdown:
                print("Shutdown requested. Stopping.")
                break
            name, fn = STEPS[step_key]
            delay = args.delay if args.delay is not None else _default_delay(step_key)
            print(f"\n{'='*50}")
            print(f"  Running: {name} (step {step_key})")
            print(f"  Delay: {delay}s")
            print(f"{'='*50}\n")
            fn(delay, args.retry_errors)

        print("\n── All steps complete ──")
        print_status_report()


def _default_delay(step: str) -> float:
    """Return the default delay for a given step."""
    from scripts.config import JUGAAD_DELAY, YFINANCE_DELAY, NSEPYTHON_DELAY
    defaults = {
        "universe": YFINANCE_DELAY,
        "0a": YFINANCE_DELAY,
        "0b": JUGAAD_DELAY,
        "0c": JUGAAD_DELAY,
        "0d": JUGAAD_DELAY,
        "0e": YFINANCE_DELAY,
        "0f": NSEPYTHON_DELAY,
        "delivery": JUGAAD_DELAY,
        "daily_ohlc": JUGAAD_DELAY,
        "daily_indices": JUGAAD_DELAY,
        "refresh_universe": YFINANCE_DELAY,
        "daily_deals": JUGAAD_DELAY,
    }
    return defaults.get(step, 1.0)


if __name__ == "__main__":
    main()
