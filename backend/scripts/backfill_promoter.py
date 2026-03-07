"""
Step 0f: Backfill promoter holding data for all stocks in universe.
Uses NSE corporate-share-holdings-master API.
"""
import time
import requests
from datetime import datetime, timezone

from scripts.config import NSEPYTHON_DELAY
from scripts.db import get_connection, get_universe_symbols, init_schema
from scripts.progress import (
    get_remaining_items, get_error_items,
    mark_started, mark_done, mark_error,
    print_progress_bar,
)


NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def _get_nse_session() -> requests.Session:
    """Create a session with NSE cookies. Retries up to 3 times."""
    session = requests.Session()
    session.headers.update(NSE_HEADERS)
    for attempt in range(3):
        try:
            session.get("https://www.nseindia.com/", timeout=20)
            return session
        except requests.exceptions.RequestException:
            if attempt < 2:
                time.sleep(5)
    # Last attempt — let it raise
    session.get("https://www.nseindia.com/", timeout=30)
    return session


def _fetch_shareholding(symbol: str, session: requests.Session) -> list[dict]:
    """
    Fetch quarterly shareholding pattern from NSE API.
    Returns list of dicts with promoter/public percentages per quarter.
    """
    url = f"https://www.nseindia.com/api/corporate-share-holdings-master?symbol={symbol}&index=equities"
    resp = session.get(url, timeout=15)
    resp.raise_for_status()

    # API returns "missing index" string for unknown symbols
    text = resp.text.strip()
    if text == "missing index" or not text.startswith("["):
        return []

    data = resp.json()
    now = datetime.now(timezone.utc).isoformat()
    records = []

    if isinstance(data, list):
        for entry in data[:4]:  # Last 4 quarters
            quarter_end_raw = entry.get("date", "")
            if not quarter_end_raw:
                continue

            # Convert "31-DEC-2025" to "2025-12-31"
            try:
                quarter_end = datetime.strptime(quarter_end_raw, "%d-%b-%Y").strftime("%Y-%m-%d")
            except ValueError:
                quarter_end = quarter_end_raw

            promoter_pct = _safe_float(entry.get("pr_and_prgrp"))
            public_pct = _safe_float(entry.get("public_val"))

            records.append({
                "symbol": symbol,
                "quarter_end": quarter_end,
                "promoter_pct": promoter_pct,
                "public_pct": public_pct,
                "dii_pct": None,  # Not available from this endpoint
                "fii_pct": None,  # Not available from this endpoint
                "source": "nse_api",
                "fetched_at": now,
            })

    return records


def _safe_float(val) -> float | None:
    """Convert a string or number to float, or return None."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def backfill_step_0f(delay: float = NSEPYTHON_DELAY, retry_errors: bool = False):
    """Backfill promoter holding for all stocks in universe."""
    init_schema()
    all_symbols = get_universe_symbols()

    if not all_symbols:
        print("No stocks in universe. Run --step universe first.")
        return

    if retry_errors:
        remaining = get_error_items("0f")
        print(f"Retrying {len(remaining)} errored stocks...")
    else:
        remaining = get_remaining_items("0f", all_symbols)

    if not remaining:
        print("Step 0f: All stocks already done.")
        return

    total = len(remaining)
    print(f"Step 0f: Fetching promoter holding for {total} stocks")

    session = _get_nse_session()
    start_time = time.time()
    session_refresh_count = 0

    for i, symbol in enumerate(remaining):
        mark_started("0f", symbol)
        try:
            records = _fetch_shareholding(symbol, session)

            if not records:
                mark_done("0f", symbol, 0)
                continue

            conn = get_connection()
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
            conn.close()
            mark_done("0f", symbol, len(records))

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                print(f"\n  Session expired, refreshing cookies...")
                session = _get_nse_session()
                session_refresh_count += 1
                time.sleep(5)
                mark_error("0f", symbol, "403 — session expired, will retry")
            else:
                mark_error("0f", symbol, str(e)[:500])

        except Exception as e:
            mark_error("0f", symbol, str(e)[:500])

        print_progress_bar(i + 1, total, symbol, start_time)
        time.sleep(delay)

    print(f"\nStep 0f complete. (Session refreshed {session_refresh_count} times)")


if __name__ == "__main__":
    backfill_step_0f()
