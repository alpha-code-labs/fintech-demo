"""
Step 0e: Backfill quarterly financials (income statement + balance sheet)
for all stocks in universe via yfinance.
"""
import time
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone

from scripts.config import YFINANCE_DELAY
from scripts.db import get_connection, get_universe_symbols, init_schema
from scripts.progress import (
    get_remaining_items, get_error_items,
    mark_started, mark_done, mark_error,
    print_progress_bar,
)


def _safe_get(df: pd.DataFrame, row_name: str, col) -> float | None:
    """Safely get a value from a yfinance financial DataFrame."""
    if df is None or df.empty:
        return None
    # yfinance row names can vary slightly
    for name in [row_name, row_name.replace(" ", "")]:
        if name in df.index:
            val = df.loc[name, col]
            if pd.notna(val):
                return float(val)
    return None


def _extract_financials(symbol: str) -> list[dict]:
    """
    Extract quarterly financial data for a symbol.
    Returns list of dicts, one per quarter.
    """
    ticker = yf.Ticker(f"{symbol}.NS")

    income = ticker.quarterly_income_stmt
    balance = ticker.quarterly_balance_sheet
    cashflow = ticker.quarterly_cashflow

    if income is None or income.empty:
        return []

    # Columns are quarter-end dates, take last 6
    quarters = income.columns[:6]
    now = datetime.now(timezone.utc).isoformat()
    records = []

    for q in quarters:
        quarter_end = q.strftime("%Y-%m-%d")

        revenue = _safe_get(income, "Total Revenue", q)
        op_income = _safe_get(income, "Operating Income", q)
        net_income = _safe_get(income, "Net Income", q)
        eps = _safe_get(income, "Basic EPS", q)

        # Calculate operating margin
        op_margin = None
        if revenue and op_income and revenue != 0:
            op_margin = round(op_income / revenue * 100, 2)

        # Balance sheet items
        total_debt = None
        total_assets = None
        total_equity = None
        if balance is not None and not balance.empty and q in balance.columns:
            total_debt = _safe_get(balance, "Total Debt", q)
            total_assets = _safe_get(balance, "Total Assets", q)
            total_equity = _safe_get(balance, "Stockholders Equity", q)
            # Try alternate names
            if total_equity is None:
                total_equity = _safe_get(balance, "Total Equity Gross Minority Interest", q)

        # Cash flow from operations
        cfo = None
        if cashflow is not None and not cashflow.empty and q in cashflow.columns:
            cfo = _safe_get(cashflow, "Operating Cash Flow", q)
            if cfo is None:
                cfo = _safe_get(cashflow, "Cash Flow From Continuing Operating Activities", q)

        records.append({
            "symbol": symbol,
            "quarter_end": quarter_end,
            "revenue": revenue,
            "operating_income": op_income,
            "net_income": net_income,
            "eps": eps,
            "operating_margin": op_margin,
            "total_debt": total_debt,
            "total_assets": total_assets,
            "total_equity": total_equity,
            "cash_flow_operations": cfo,
            "source": "yfinance",
            "fetched_at": now,
        })

    return records


def backfill_step_0e(delay: float = YFINANCE_DELAY, retry_errors: bool = False):
    """Backfill quarterly financials for all stocks in universe."""
    init_schema()
    all_symbols = get_universe_symbols()

    if not all_symbols:
        print("No stocks in universe. Run --step universe first.")
        return

    if retry_errors:
        remaining = get_error_items("0e")
        print(f"Retrying {len(remaining)} errored stocks...")
    else:
        remaining = get_remaining_items("0e", all_symbols)

    if not remaining:
        print("Step 0e: All stocks already done.")
        return

    total = len(remaining)
    print(f"Step 0e: Fetching financials for {total} stocks")

    start_time = time.time()

    for i, symbol in enumerate(remaining):
        mark_started("0e", symbol)
        try:
            records = _extract_financials(symbol)

            if not records:
                mark_done("0e", symbol, 0)
                continue

            conn = get_connection()
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
            conn.close()
            mark_done("0e", symbol, len(records))

        except Exception as e:
            mark_error("0e", symbol, str(e)[:500])

        print_progress_bar(i + 1, total, symbol, start_time)
        time.sleep(delay)

    print(f"\nStep 0e complete.")


if __name__ == "__main__":
    backfill_step_0e()
