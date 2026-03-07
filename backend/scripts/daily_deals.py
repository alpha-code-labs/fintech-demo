"""Daily bulk/block deals fetch.

P1 item 7 from pending-list.md.

Fetches bulk and block deal data from nselib for dates after the
last date in the bulk_block_deals table.

Usage:
    python -m scripts.run_backfill --step daily_deals
"""

import time
import logging
from datetime import datetime, date, timedelta

import pandas as pd
from nselib import capital_market

from scripts.config import JUGAAD_DELAY
from scripts.db import get_connection, init_schema

logger = logging.getLogger(__name__)

DATE_FMT = "%d-%m-%Y"


def _get_last_deal_date() -> str | None:
    """Return the most recent date in bulk_block_deals, or None."""
    conn = get_connection()
    row = conn.execute("SELECT MAX(date) AS max_date FROM bulk_block_deals").fetchone()
    conn.close()
    return row["max_date"] if row and row["max_date"] else None


def _clean_qty(val) -> int | None:
    """Parse quantity like '7,13,195' to int."""
    if val is None:
        return None
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _clean_price(val) -> float | None:
    """Parse price to float."""
    if val is None:
        return None
    try:
        return round(float(str(val).replace(",", "").strip()), 2)
    except (ValueError, TypeError):
        return None


def _date_to_iso(nse_date: str) -> str:
    """Convert '02-MAR-2026' or '02-03-2026' to '2026-03-02'."""
    for fmt in ["%d-%b-%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(nse_date.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return nse_date


def _fetch_and_insert_deals(from_date: date, to_date: date) -> dict:
    """Fetch bulk and block deals for a date range and insert into DB."""
    from_str = from_date.strftime(DATE_FMT)
    to_str = to_date.strftime(DATE_FMT)

    results = {"bulk": 0, "block": 0}
    conn = get_connection()

    # Bulk deals
    try:
        df = capital_market.bulk_deal_data(from_date=from_str, to_date=to_str)
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                iso_date = _date_to_iso(str(row.get("Date", "")))
                symbol = str(row.get("Symbol", "")).strip()
                if not symbol:
                    continue
                conn.execute(
                    """INSERT OR IGNORE INTO bulk_block_deals
                       (date, symbol, deal_type, client_name, buy_sell, quantity, price, remarks)
                       VALUES (?, ?, 'BULK', ?, ?, ?, ?, ?)""",
                    (
                        iso_date,
                        symbol,
                        str(row.get("ClientName", "")).strip(),
                        str(row.get("Buy/Sell", "")).strip().upper(),
                        _clean_qty(row.get("QuantityTraded")),
                        _clean_price(row.get("TradePrice/Wght.Avg.Price")),
                        str(row.get("Remarks", "")).strip(),
                    ),
                )
                results["bulk"] += 1
    except Exception as e:
        logger.warning(f"Bulk deals fetch failed: {e}")

    # Block deals
    try:
        df = capital_market.block_deals_data(from_date=from_str, to_date=to_str)
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                iso_date = _date_to_iso(str(row.get("Date", "")))
                symbol = str(row.get("Symbol", "")).strip()
                if not symbol:
                    continue
                conn.execute(
                    """INSERT OR IGNORE INTO bulk_block_deals
                       (date, symbol, deal_type, client_name, buy_sell, quantity, price, remarks)
                       VALUES (?, ?, 'BLOCK', ?, ?, ?, ?, ?)""",
                    (
                        iso_date,
                        symbol,
                        str(row.get("ClientName", "")).strip(),
                        str(row.get("Buy/Sell", "")).strip().upper(),
                        _clean_qty(row.get("QuantityTraded")),
                        _clean_price(row.get("TradePrice/Wght.Avg.Price")),
                        str(row.get("Remarks", "")).strip(),
                    ),
                )
                results["block"] += 1
    except Exception as e:
        logger.warning(f"Block deals fetch failed: {e}")

    conn.commit()
    conn.close()
    return results


def daily_deals_fetch(delay: float = JUGAAD_DELAY, retry_errors: bool = False):
    """Fetch bulk/block deals for all trading days since last DB date."""
    init_schema()

    last_date_str = _get_last_deal_date()

    if last_date_str:
        from_date = datetime.strptime(last_date_str, "%Y-%m-%d").date() + timedelta(days=1)
    else:
        # First run: fetch last 30 days
        from_date = date.today() - timedelta(days=30)

    to_date = date.today()

    if from_date > to_date:
        print(f"Daily Deals: DB is up to date (last date: {last_date_str}). Nothing to fetch.")
        return

    # nselib requires from_date < to_date (no same-day queries)
    if from_date == to_date:
        print(f"Daily Deals: DB is up to date (last date: {last_date_str}). Nothing to fetch.")
        return

    print(f"Daily Deals: Fetching {from_date} → {to_date}")

    results = _fetch_and_insert_deals(from_date, to_date)

    print(f"  Bulk deals inserted: {results['bulk']}")
    print(f"  Block deals inserted: {results['block']}")
    print("Daily Deals: complete.")
