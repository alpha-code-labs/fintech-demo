"""
Portfolio Monitor Calculation Engine (M6).

Loads user holdings from portfolio_holdings table, computes:
  - Current price + P&L per holding
  - Exit signals: upper wicks, MA break (30W/52W), support break, head & shoulders, bad news + breakdown
  - Health bucketing: healthy (0 signals) / warning (1-2) / alert (MA break or 3+)
  - Sector concentration
  - Portfolio-level totals

Response shape matches the dummy portfolio.json for frontend compatibility.
"""
import logging

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from app.db import get_connection

logger = logging.getLogger(__name__)


# ── Thresholds ────────────────────────────────────────────────
UPPER_WICK_RATIO = 0.6       # (high - close) / (high - low) > 0.6
UPPER_WICK_WEEKS = 3          # consecutive weeks needed
SUPPORT_LOOKBACK_WEEKS = 13   # ~3 months
LOOKBACK_WEEKS = 65           # ~15 months for 52W MA
HS_MIN_WEEKS = 10             # minimum pattern span in weeks
HS_MAX_WEEKS = 30             # maximum pattern span (~7 months)
HS_SWING_WINDOW = 3           # weeks on each side for swing high detection
HS_SHOULDER_TOLERANCE = 0.10  # shoulders must be within 10% of each other
HS_HEAD_MIN_ABOVE = 0.03     # head must be at least 3% above shoulders


# ── Table init ────────────────────────────────────────────────

def _ensure_table(conn):
    """Create portfolio_holdings and watchlist tables if they don't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            buy_price REAL NOT NULL,
            buy_date TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            buy_thesis TEXT,
            added_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    # Add buy_thesis column if table already exists without it
    try:
        conn.execute("SELECT buy_thesis FROM portfolio_holdings LIMIT 1")
    except Exception:
        try:
            conn.execute("ALTER TABLE portfolio_holdings ADD COLUMN buy_thesis TEXT")
        except Exception:
            pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            notes TEXT,
            added_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            target_price REAL NOT NULL,
            notes TEXT,
            triggered INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL,
            buy_price REAL,
            sell_price REAL,
            buy_date TEXT,
            sell_date TEXT,
            quantity INTEGER,
            pnl_pct REAL,
            reason TEXT,
            decided_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


# ── CRUD ──────────────────────────────────────────────────────

def add_holding(symbol: str, buy_price: float, buy_date: str,
                quantity: int = 1, notes: str = None,
                buy_thesis: str = None) -> dict:
    """Add a holding. Returns the created row."""
    conn = get_connection()
    try:
        _ensure_table(conn)
        conn.execute(
            """INSERT INTO portfolio_holdings (symbol, buy_price, buy_date, quantity, notes, buy_thesis)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (symbol.upper().strip(), buy_price, buy_date, quantity, notes, buy_thesis),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM portfolio_holdings WHERE symbol = ?",
            (symbol.upper().strip(),)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def remove_holding(symbol: str) -> bool:
    """Remove a holding by symbol. Returns True if deleted."""
    conn = get_connection()
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            "DELETE FROM portfolio_holdings WHERE symbol = ?",
            (symbol.upper().strip(),),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def sell_holding(symbol: str, sell_price: float, reason: str = None) -> dict | None:
    """Sell a holding: log to trade_history, then remove from portfolio."""
    symbol = symbol.upper().strip()
    conn = get_connection()
    try:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT * FROM portfolio_holdings WHERE symbol = ?", (symbol,)
        ).fetchone()
        if not row:
            return None

        buy_price = row["buy_price"]
        pnl_pct = round((sell_price - buy_price) / buy_price * 100, 1) if buy_price else 0

        conn.execute(
            """INSERT INTO trade_history
               (symbol, action, buy_price, sell_price, buy_date, sell_date, quantity, pnl_pct, reason)
               VALUES (?, 'SELL', ?, ?, ?, date('now'), ?, ?, ?)""",
            (symbol, buy_price, sell_price, row["buy_date"], row["quantity"], pnl_pct, reason),
        )
        conn.execute("DELETE FROM portfolio_holdings WHERE symbol = ?", (symbol,))
        conn.commit()

        return {
            "symbol": symbol,
            "action": "SELL",
            "buy_price": buy_price,
            "sell_price": sell_price,
            "pnl_pct": pnl_pct,
            "reason": reason,
        }
    finally:
        conn.close()


def hold_decision(symbol: str, reason: str = None) -> dict | None:
    """Log a HOLD decision — user reviewed exit signals and chose to keep."""
    symbol = symbol.upper().strip()
    conn = get_connection()
    try:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT buy_price, buy_date, quantity FROM portfolio_holdings WHERE symbol = ?",
            (symbol,),
        ).fetchone()
        if not row:
            return None

        # Get current price for the record
        price_row = conn.execute(
            "SELECT close FROM stock_ohlc WHERE symbol = ? ORDER BY date DESC LIMIT 1",
            (symbol,),
        ).fetchone()
        current_price = round(price_row["close"], 2) if price_row else None

        conn.execute(
            """INSERT INTO trade_history
               (symbol, action, buy_price, sell_price, buy_date, quantity, pnl_pct, reason)
               VALUES (?, 'HOLD', ?, ?, ?, ?, ?, ?)""",
            (symbol, row["buy_price"], current_price, row["buy_date"], row["quantity"],
             round((current_price - row["buy_price"]) / row["buy_price"] * 100, 1) if current_price and row["buy_price"] else None,
             reason),
        )
        conn.commit()

        return {
            "symbol": symbol,
            "action": "HOLD",
            "current_price": current_price,
            "reason": reason,
        }
    finally:
        conn.close()


def add_more_shares(symbol: str, quantity: int, buy_price: float) -> dict | None:
    """Add more shares to an existing holding with weighted average price."""
    symbol = symbol.upper().strip()
    conn = get_connection()
    try:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT * FROM portfolio_holdings WHERE symbol = ?", (symbol,)
        ).fetchone()
        if not row:
            return None

        old_qty = row["quantity"]
        old_price = row["buy_price"]
        new_qty = old_qty + quantity
        new_avg = round((old_qty * old_price + quantity * buy_price) / new_qty, 2)

        conn.execute(
            "UPDATE portfolio_holdings SET quantity = ?, buy_price = ? WHERE symbol = ?",
            (new_qty, new_avg, symbol),
        )

        conn.execute(
            """INSERT INTO trade_history
               (symbol, action, buy_price, sell_price, buy_date, quantity, reason)
               VALUES (?, 'ADD', ?, NULL, date('now'), ?, ?)""",
            (symbol, buy_price, quantity,
             f"Added {quantity} shares at ₹{buy_price}. Avg: ₹{old_price} -> ₹{new_avg}, Qty: {old_qty} -> {new_qty}"),
        )
        conn.commit()

        return {
            "symbol": symbol,
            "action": "ADD",
            "old_qty": old_qty,
            "old_price": old_price,
            "new_qty": new_qty,
            "new_avg": new_avg,
        }
    finally:
        conn.close()


def get_trade_history() -> list[dict]:
    """Return all trade history entries, newest first."""
    conn = get_connection()
    try:
        _ensure_table(conn)
        rows = conn.execute(
            """SELECT h.*, u.company_name
               FROM trade_history h
               LEFT JOIN stock_universe u ON h.symbol = u.symbol
               ORDER BY h.decided_at DESC"""
        ).fetchall()
        return [
            {
                "id": r["id"],
                "symbol": r["symbol"],
                "name": r["company_name"] or r["symbol"],
                "action": r["action"],
                "buy_price": r["buy_price"],
                "sell_price": r["sell_price"],
                "buy_date": r["buy_date"],
                "sell_date": r["sell_date"],
                "quantity": r["quantity"],
                "pnl_pct": r["pnl_pct"],
                "reason": r["reason"],
                "decided_at": r["decided_at"],
            }
            for r in rows
        ]
    finally:
        conn.close()


# ── Watchlist CRUD ────────────────────────────────────────────

def add_to_watchlist(symbol: str, notes: str = None) -> dict:
    """Add a stock to the watchlist. Returns the created row."""
    conn = get_connection()
    try:
        _ensure_table(conn)
        conn.execute(
            "INSERT INTO watchlist (symbol, notes) VALUES (?, ?)",
            (symbol.upper().strip(), notes),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM watchlist WHERE symbol = ?",
            (symbol.upper().strip(),),
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def remove_from_watchlist(symbol: str) -> bool:
    """Remove a stock from the watchlist. Returns True if deleted."""
    conn = get_connection()
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            "DELETE FROM watchlist WHERE symbol = ?",
            (symbol.upper().strip(),),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_watchlist() -> list[dict]:
    """Return all watchlist items with current price and name."""
    conn = get_connection()
    try:
        _ensure_table(conn)
        rows = conn.execute(
            """SELECT w.symbol, w.notes, w.added_at,
                      u.company_name, u.sector, u.market_cap_cr
               FROM watchlist w
               LEFT JOIN stock_universe u ON w.symbol = u.symbol
               ORDER BY w.added_at DESC"""
        ).fetchall()

        items = []
        for row in rows:
            symbol = row["symbol"]
            # Get latest price
            price_row = conn.execute(
                "SELECT close FROM stock_ohlc WHERE symbol = ? ORDER BY date DESC LIMIT 1",
                (symbol,),
            ).fetchone()
            current_price = round(price_row["close"], 2) if price_row else None

            items.append({
                "symbol": symbol,
                "name": row["company_name"] or symbol,
                "sector": row["sector"] or "Unknown",
                "market_cap_cr": round(row["market_cap_cr"]) if row["market_cap_cr"] else None,
                "current_price": current_price,
                "notes": row["notes"],
                "added_at": row["added_at"],
            })

        return items
    finally:
        conn.close()


# ── Price Alerts CRUD ─────────────────────────────────────────

def create_alert(symbol: str, alert_type: str, target_price: float,
                 notes: str = None) -> dict:
    """Create a price alert. alert_type is 'above' or 'below'."""
    conn = get_connection()
    try:
        _ensure_table(conn)
        conn.execute(
            """INSERT INTO price_alerts (symbol, alert_type, target_price, notes)
               VALUES (?, ?, ?, ?)""",
            (symbol.upper().strip(), alert_type, target_price, notes),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM price_alerts WHERE id = last_insert_rowid()"
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def delete_alert(alert_id: int) -> bool:
    """Delete a price alert by ID."""
    conn = get_connection()
    try:
        _ensure_table(conn)
        cursor = conn.execute("DELETE FROM price_alerts WHERE id = ?", (alert_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_alerts() -> list[dict]:
    """Return all alerts with triggered status checked against current prices."""
    conn = get_connection()
    try:
        _ensure_table(conn)
        rows = conn.execute(
            """SELECT a.*, u.company_name
               FROM price_alerts a
               LEFT JOIN stock_universe u ON a.symbol = u.symbol
               ORDER BY a.triggered DESC, a.created_at DESC"""
        ).fetchall()

        alerts = []
        for row in rows:
            symbol = row["symbol"]
            price_row = conn.execute(
                "SELECT close FROM stock_ohlc WHERE symbol = ? ORDER BY date DESC LIMIT 1",
                (symbol,),
            ).fetchone()
            current_price = round(price_row["close"], 2) if price_row else None

            # Check if alert should be triggered
            triggered = False
            if current_price is not None:
                if row["alert_type"] == "above" and current_price >= row["target_price"]:
                    triggered = True
                elif row["alert_type"] == "below" and current_price <= row["target_price"]:
                    triggered = True

            # Update triggered status in DB if changed
            if triggered and not row["triggered"]:
                conn.execute(
                    "UPDATE price_alerts SET triggered = 1 WHERE id = ?",
                    (row["id"],),
                )
                conn.commit()

            alerts.append({
                "id": row["id"],
                "symbol": symbol,
                "name": row["company_name"] or symbol,
                "alert_type": row["alert_type"],
                "target_price": row["target_price"],
                "current_price": current_price,
                "notes": row["notes"],
                "triggered": bool(triggered or row["triggered"]),
                "created_at": row["created_at"],
            })

        return alerts
    finally:
        conn.close()


# ── Main calculation ──────────────────────────────────────────

def get_portfolio() -> dict:
    """Build the full portfolio response with real exit signals."""
    conn = get_connection()
    try:
        _ensure_table(conn)
        holdings_rows = conn.execute(
            "SELECT symbol, buy_price, buy_date, quantity, notes, buy_thesis FROM portfolio_holdings"
        ).fetchall()

        if not holdings_rows:
            return _empty_response()

        holdings = [dict(r) for r in holdings_rows]
        symbols = [h["symbol"] for h in holdings]

        # Load universe for names/sectors
        universe = _load_universe(conn)

        # Load stock OHLC for held symbols
        stock_daily = _load_stock_data(conn, symbols)

        # Load Nifty for RS calculation (optional, used in signals)
        nifty_daily = _load_nifty_data(conn)
    finally:
        conn.close()

    if stock_daily.empty:
        return _build_response_no_data(holdings, universe)

    # Resample to weekly
    stock_weekly = _resample_to_weekly(stock_daily)

    if stock_weekly.empty:
        return _build_response_no_data(holdings, universe)

    # Calculate MAs
    stock_weekly = _calculate_mas(stock_weekly)

    # Pre-compute market leverage for exit signal #7
    market_leverage = _get_market_leverage()
    leverage_elevated = (
        market_leverage is not None
        and market_leverage.get("trend_3m") == "INCREASING"
    )

    # Build each holding's data
    healthy, warning, alert = [], [], []
    total_value = 0.0
    total_cost = 0.0

    for h in holdings:
        symbol = h["symbol"]
        info = universe.get(symbol, {"name": symbol, "sector": "Unknown"})

        # Get current price
        current_price = _get_current_price(stock_weekly, symbol)
        if current_price is None:
            # Stock not found in data — show with no signals
            entry = _make_holding_entry(h, info, None, [])
            healthy.append(entry)
            continue

        # P&L
        buy_price = h["buy_price"]
        pnl_pct = round((current_price - buy_price) / buy_price * 100, 1)

        # Held months
        try:
            buy_dt = datetime.strptime(h["buy_date"], "%Y-%m-%d")
            held_months = max(1, (datetime.now() - buy_dt).days // 30)
        except ValueError:
            held_months = 0

        # Portfolio value tracking
        qty = h["quantity"]
        total_value += current_price * qty
        total_cost += buy_price * qty

        # Exit signal detection
        signals = _detect_exit_signals(stock_weekly, symbol, info["name"], info["sector"])

        # Exit signal #7: Market-wide margin leverage elevated
        if leverage_elevated:
            signals.append("Market-wide margin leverage elevated and rising")

        # Setup review (exit signal #8)
        buy_thesis = h.get("buy_thesis")
        setup_review = _check_setup_still_valid(symbol, buy_thesis) if buy_thesis else None
        if setup_review and not setup_review["still_valid"]:
            signals.append(f"Original setup may have ended: {setup_review['reason']}")

        # Health bucketing
        has_ma_break = any("below 30W MA" in s or "below 52W MA" in s for s in signals)
        has_bad_news = any("Bad news" in s for s in signals)
        entry = {
            "symbol": symbol,
            "name": info["name"],
            "sector": info["sector"],
            "buy_price": buy_price,
            "buy_date": h["buy_date"],
            "quantity": qty,
            "current_price": round(current_price, 2),
            "pnl_pct": pnl_pct,
            "held_months": held_months,
            "signals": signals,
            "buy_thesis": buy_thesis,
            "setup_review": setup_review,
        }

        if len(signals) == 0:
            healthy.append(entry)
        elif has_ma_break or has_bad_news or len(signals) >= 3:
            alert.append(entry)
        else:
            warning.append(entry)

    # Portfolio totals
    total_pnl = total_value - total_cost
    total_pnl_pct = round(total_pnl / total_cost * 100, 1) if total_cost > 0 else 0.0
    total_holdings = len(holdings)

    # Sector concentration
    sector_concentration = _calc_sector_concentration(holdings, universe)

    return {
        "total_holdings": total_holdings,
        "portfolio_value": round(total_value, 0),
        "total_pnl": round(total_pnl, 0),
        "total_pnl_pct": total_pnl_pct,
        "holdings": {
            "healthy": healthy,
            "warning": warning,
            "alert": alert,
        },
        "sector_concentration": sector_concentration,
        "market_leverage": market_leverage,
    }


# ── Exit signal detection ─────────────────────────────────────

def _detect_exit_signals(stock_weekly: pd.DataFrame, symbol: str,
                         company_name: str = "", sector: str = "") -> list[str]:
    """Detect all exit signals for a single stock."""
    signals = []

    try:
        sym_data = stock_weekly.loc[symbol].sort_index()
    except KeyError:
        return signals

    if len(sym_data) < 4:
        return signals

    latest = sym_data.iloc[-1]
    close = float(latest["close"])

    # 1. Upper wick detection
    wick_signal = _check_upper_wicks(sym_data)
    if wick_signal:
        signals.append(wick_signal)

    # 2. Below 30W MA
    ma_30w = latest.get("ma_30w")
    if pd.notna(ma_30w) and close < float(ma_30w):
        signals.append(f"Price below 30W MA ({float(ma_30w):,.0f})")

    # 3. Below 52W MA
    ma_52w = latest.get("ma_52w")
    if pd.notna(ma_52w) and close < float(ma_52w):
        signals.append(f"Price below 52W MA ({float(ma_52w):,.0f})")

    # 4. Support break
    support_signal = _check_support_break(sym_data)
    if support_signal:
        signals.append(support_signal)

    # 5. Head & Shoulders pattern
    hs_signal = _check_head_and_shoulders(sym_data)
    if hs_signal:
        signals.append(hs_signal)

    # 6. Bad news + technical breakdown (only if at least one technical signal fired)
    if signals:
        bad_news_signal = _check_bad_news_breakdown(symbol, company_name or symbol, sector)
        if bad_news_signal:
            signals.append(bad_news_signal)

    return signals


def _check_upper_wicks(sym_data: pd.DataFrame) -> str | None:
    """Check for consecutive upper wicks in recent weeks."""
    recent = sym_data.tail(UPPER_WICK_WEEKS + 1)  # +1 for context
    if len(recent) < UPPER_WICK_WEEKS:
        return None

    consecutive = 0
    for i in range(len(recent) - 1, -1, -1):
        row = recent.iloc[i]
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])

        if high == low:  # no range
            break

        wick_ratio = (high - close) / (high - low)
        if wick_ratio > UPPER_WICK_RATIO:
            consecutive += 1
        else:
            break

    if consecutive >= UPPER_WICK_WEEKS:
        return f"Upper wicks: {consecutive} consecutive weeks"
    return None


def _check_support_break(sym_data: pd.DataFrame) -> str | None:
    """Check if current price broke below 3-month support."""
    if len(sym_data) < SUPPORT_LOOKBACK_WEEKS + 1:
        return None

    current_close = float(sym_data.iloc[-1]["close"])
    # Support = lowest weekly close in past 3 months (excluding current week)
    lookback = sym_data.iloc[-(SUPPORT_LOOKBACK_WEEKS + 1):-1]
    support_level = float(lookback["close"].min())

    if current_close < support_level:
        return f"Support at {support_level:,.0f} broken"
    return None


def _check_head_and_shoulders(sym_data: pd.DataFrame) -> str | None:
    """Detect Head & Shoulders pattern from weekly highs.

    Looks for three swing highs where the middle (head) is highest and
    the two shoulders are roughly equal.  Flags for human review if
    current price is near or below the neckline.
    """
    if len(sym_data) < HS_MIN_WEEKS:
        return None

    # Use the last HS_MAX_WEEKS of data
    window = sym_data.tail(HS_MAX_WEEKS)
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)
    closes = window["close"].values.astype(float)

    if len(highs) < HS_MIN_WEEKS:
        return None

    # Find swing highs: week i is a swing high if high[i] >= all highs
    # within HS_SWING_WINDOW on each side
    swing_indices = []
    for i in range(HS_SWING_WINDOW, len(highs) - HS_SWING_WINDOW):
        left = highs[max(0, i - HS_SWING_WINDOW):i]
        right = highs[i + 1:i + HS_SWING_WINDOW + 1]
        if highs[i] >= max(left) and highs[i] >= max(right):
            swing_indices.append(i)

    # Merge nearby swing highs (within 2 weeks, keep highest)
    merged = []
    for idx in swing_indices:
        if merged and idx - merged[-1] <= 2:
            if highs[idx] > highs[merged[-1]]:
                merged[-1] = idx
        else:
            merged.append(idx)

    if len(merged) < 3:
        return None

    # Try all combinations of 3 consecutive swing highs
    current_close = closes[-1]
    best_pattern = None

    for i in range(len(merged) - 2):
        ls_idx, h_idx, rs_idx = merged[i], merged[i + 1], merged[i + 2]
        ls_high = highs[ls_idx]
        head_high = highs[h_idx]
        rs_high = highs[rs_idx]

        # Head must be the highest
        if head_high <= ls_high or head_high <= rs_high:
            continue

        # Head must be meaningfully above shoulders
        avg_shoulder = (ls_high + rs_high) / 2
        if (head_high - avg_shoulder) / avg_shoulder < HS_HEAD_MIN_ABOVE:
            continue

        # Shoulders must be roughly equal
        if abs(ls_high - rs_high) / max(ls_high, rs_high) > HS_SHOULDER_TOLERANCE:
            continue

        # Pattern must span at least HS_MIN_WEEKS
        if rs_idx - ls_idx < HS_MIN_WEEKS // 2:
            continue

        # Find neckline: lowest low between left shoulder and head,
        # and between head and right shoulder
        trough1 = float(lows[ls_idx:h_idx + 1].min())
        trough2 = float(lows[h_idx:rs_idx + 1].min())
        neckline = min(trough1, trough2)

        # Right shoulder must be complete (we need some decline after it)
        # Check if price has declined from right shoulder
        if rs_idx >= len(highs) - 1:
            # Right shoulder is the very last bar — pattern not yet complete
            continue

        # Flag if current price is within 5% above neckline or below it
        neckline_dist = (current_close - neckline) / neckline * 100
        if neckline_dist <= 5.0:
            best_pattern = (ls_high, head_high, rs_high, neckline, neckline_dist)
            break  # take the first valid pattern found

    if best_pattern is None:
        return None

    ls_high, head_high, rs_high, neckline, neckline_dist = best_pattern

    if neckline_dist <= 0:
        return (
            f"H&S pattern: neckline {neckline:,.0f} broken "
            f"(head {head_high:,.0f}) — review chart"
        )
    else:
        return (
            f"H&S pattern forming: neckline at {neckline:,.0f}, "
            f"price {neckline_dist:.0f}% above — review chart"
        )


# ── Bad news cache ───────────────────────────────────────────
_bad_news_cache: dict[str, tuple] = {}  # {symbol: (result, timestamp)}
_BAD_NEWS_CACHE_TTL = timedelta(hours=24)


def _check_bad_news_breakdown(symbol: str, company_name: str, sector: str) -> str | None:
    """Check for bad news that coincides with technical breakdown.

    Only called when at least one technical exit signal is already firing.
    Fetches recent news headlines and asks LLM to identify negative news.
    """
    now = datetime.now()
    if symbol in _bad_news_cache:
        cached, ts = _bad_news_cache[symbol]
        if now - ts < _BAD_NEWS_CACHE_TTL:
            return cached

    result = _scan_bad_news(symbol, company_name, sector)
    _bad_news_cache[symbol] = (result, now)
    return result


def _scan_bad_news(symbol: str, company_name: str, sector: str) -> str | None:
    """Fetch news and use LLM to detect bad news for a stock."""
    try:
        from app.llm.news_setups import _fetch_news_headlines
        headlines = _fetch_news_headlines(company_name, symbol)
    except Exception as e:
        logger.debug(f"Bad news fetch failed for {symbol}: {e}")
        return None

    if not headlines:
        return None

    try:
        from app.llm.client import generate
    except Exception:
        return None

    headlines_text = "\n".join(f"- {h}" for h in headlines[:10])

    prompt = f"""You are a stock market risk analyst. Given recent news headlines for {company_name} ({symbol}), identify any NEGATIVE news that could cause a stock decline.

Headlines:
{headlines_text}

Look for: earnings miss, profit warning, regulatory action, fraud/scandal, management exodus, downgrade, contract loss, plant shutdown, debt default, credit downgrade, legal judgment, or any other materially negative development.

If you find clearly negative news, respond with a single concise sentence describing the bad news (max 15 words).
If there is no clearly negative news, respond with exactly: NONE

Your response (one line only):"""

    raw = generate(prompt, max_tokens=60)
    if not raw:
        return None

    text = raw.strip()
    if text.upper() == "NONE" or "none" in text.lower() and len(text) < 10:
        return None

    return f"Bad news + breakdown: {text}"


# ── Data loading ──────────────────────────────────────────────

def _load_stock_data(conn, symbols: list[str]) -> pd.DataFrame:
    """Load daily OHLC for specific symbols."""
    if not symbols:
        return pd.DataFrame()

    cutoff = (datetime.now() - timedelta(weeks=LOOKBACK_WEEKS)).strftime("%Y-%m-%d")
    placeholders = ",".join(["?"] * len(symbols))
    df = pd.read_sql_query(
        f"""SELECT symbol, date, open, high, low, close, volume, delivery_pct
            FROM stock_ohlc
            WHERE symbol IN ({placeholders}) AND date >= ?
            ORDER BY symbol, date""",
        conn,
        params=symbols + [cutoff],
    )
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df


def _load_nifty_data(conn) -> pd.DataFrame:
    """Load Nifty 50 daily data."""
    cutoff = (datetime.now() - timedelta(weeks=LOOKBACK_WEEKS)).strftime("%Y-%m-%d")
    df = pd.read_sql_query(
        """SELECT date, close FROM index_daily
           WHERE index_name = 'NIFTY 50' AND date >= ?
           ORDER BY date""",
        conn,
        params=[cutoff],
    )
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df


# ── Setup review (exit signal #8) ─────────────────────────────

# Valid thesis values
THESIS_OPTIONS = [
    "earnings_surprise",
    "debt_reduction",
    "margin_expansion",
    "sector_cycle",
    "supply_disruption",
    "forced_buying",
    "management_change",
    "other",
]


def _check_setup_still_valid(symbol: str, thesis: str) -> dict | None:
    """
    Check if the original buy thesis still holds by re-running the relevant
    setup check against current data.

    Returns: {still_valid: bool, thesis: str, reason: str, detail: str}
    """
    if not thesis or thesis not in THESIS_OPTIONS:
        return None

    conn = get_connection()
    try:
        if thesis == "earnings_surprise":
            return _review_earnings(conn, symbol)
        elif thesis == "debt_reduction":
            return _review_debt(conn, symbol)
        elif thesis == "margin_expansion":
            return _review_margins(conn, symbol)
        elif thesis == "sector_cycle":
            return _review_sector(conn, symbol)
        elif thesis in ("supply_disruption", "management_change", "forced_buying"):
            # These are event-driven — can't auto-check, prompt user to review
            return {
                "still_valid": True,
                "thesis": thesis,
                "reason": "Review manually",
                "detail": f"'{thesis.replace('_', ' ').title()}' is event-driven — check if the catalyst is still in play.",
            }
        else:
            return None
    except Exception as e:
        logger.debug(f"Setup review failed for {symbol}/{thesis}: {e}")
        return None
    finally:
        conn.close()


def _review_earnings(conn, symbol: str) -> dict:
    """Check if earnings surprise is sustaining or was one-time."""
    rows = conn.execute(
        """SELECT quarter_end, net_income, revenue
           FROM quarterly_financials
           WHERE symbol = ?
           ORDER BY quarter_end DESC
           LIMIT 5""",
        (symbol,),
    ).fetchall()

    if len(rows) < 3:
        return {"still_valid": True, "thesis": "earnings_surprise",
                "reason": "Insufficient data", "detail": "Need 3+ quarters to assess."}

    # Compare latest quarter to 2 quarters ago (YoY-ish)
    latest_ni = rows[0]["net_income"]
    prev_ni = rows[2]["net_income"]
    latest_rev = rows[0]["revenue"]
    prev_rev = rows[2]["revenue"]

    if latest_ni is None or prev_ni is None or prev_ni == 0:
        return {"still_valid": True, "thesis": "earnings_surprise",
                "reason": "Data incomplete", "detail": "Missing net income data."}

    ni_growth = (latest_ni - prev_ni) / abs(prev_ni) * 100
    rev_growth = ((latest_rev - prev_rev) / abs(prev_rev) * 100) if prev_rev and latest_rev else 0

    if ni_growth < -10:
        return {"still_valid": False, "thesis": "earnings_surprise",
                "reason": f"Earnings declined {ni_growth:.0f}% — may have been one-time",
                "detail": f"Net income: ₹{latest_ni/10000000:.0f} Cr vs ₹{prev_ni/10000000:.0f} Cr (2Q ago). Revenue growth: {rev_growth:.0f}%."}
    elif ni_growth < 10:
        return {"still_valid": True, "thesis": "earnings_surprise",
                "reason": f"Earnings flat ({ni_growth:+.0f}%) — monitor closely",
                "detail": f"Growth has slowed. Check if next quarter confirms the trend."}
    else:
        return {"still_valid": True, "thesis": "earnings_surprise",
                "reason": f"Earnings still growing ({ni_growth:+.0f}%)",
                "detail": f"Thesis intact. Net income and revenue both trending up."}


def _review_debt(conn, symbol: str) -> dict:
    """Check if debt reduction is continuing or has stalled."""
    rows = conn.execute(
        """SELECT quarter_end, total_debt
           FROM quarterly_financials
           WHERE symbol = ? AND total_debt IS NOT NULL
           ORDER BY quarter_end DESC
           LIMIT 4""",
        (symbol,),
    ).fetchall()

    if len(rows) < 2:
        return {"still_valid": True, "thesis": "debt_reduction",
                "reason": "Insufficient data", "detail": "Need 2+ quarters with debt data."}

    debts = [r["total_debt"] for r in rows]
    latest = debts[0]
    oldest = debts[-1]

    if oldest == 0:
        return {"still_valid": True, "thesis": "debt_reduction",
                "reason": "Near zero debt", "detail": "Debt already near zero."}

    change_pct = (latest - oldest) / abs(oldest) * 100

    if change_pct > 5:
        return {"still_valid": False, "thesis": "debt_reduction",
                "reason": f"Debt increased {change_pct:+.0f}% — reduction has stalled",
                "detail": f"Debt: ₹{latest/10000000:.0f} Cr (latest) vs ₹{oldest/10000000:.0f} Cr ({len(rows)-1}Q ago)."}
    elif change_pct > -5:
        return {"still_valid": True, "thesis": "debt_reduction",
                "reason": f"Debt flat ({change_pct:+.0f}%) — monitor",
                "detail": "Reduction has slowed but not reversed."}
    else:
        return {"still_valid": True, "thesis": "debt_reduction",
                "reason": f"Debt still declining ({change_pct:+.0f}%)",
                "detail": "Thesis intact. Debt reduction continues."}


def _review_margins(conn, symbol: str) -> dict:
    """Check if margin expansion is continuing."""
    rows = conn.execute(
        """SELECT quarter_end, operating_income, revenue
           FROM quarterly_financials
           WHERE symbol = ? AND operating_income IS NOT NULL AND revenue IS NOT NULL AND revenue > 0
           ORDER BY quarter_end DESC
           LIMIT 4""",
        (symbol,),
    ).fetchall()

    if len(rows) < 2:
        return {"still_valid": True, "thesis": "margin_expansion",
                "reason": "Insufficient data", "detail": "Need 2+ quarters with margin data."}

    margins = [(r["operating_income"] / r["revenue"] * 100) for r in rows]
    latest_m = margins[0]
    oldest_m = margins[-1]
    diff = latest_m - oldest_m

    if diff < -3:
        return {"still_valid": False, "thesis": "margin_expansion",
                "reason": f"Margins contracting ({diff:+.1f}pp) — expansion may have ended",
                "detail": f"Operating margin: {latest_m:.1f}% (latest) vs {oldest_m:.1f}% ({len(rows)-1}Q ago)."}
    elif diff < 1:
        return {"still_valid": True, "thesis": "margin_expansion",
                "reason": f"Margins flat ({diff:+.1f}pp) — monitor",
                "detail": "Expansion has plateaued but not reversed."}
    else:
        return {"still_valid": True, "thesis": "margin_expansion",
                "reason": f"Margins still expanding ({diff:+.1f}pp)",
                "detail": "Thesis intact. Operating margins continue to improve."}


def _review_sector(conn, symbol: str) -> dict:
    """Check if the sector cycle thesis is still active."""
    # Check sector RS from index data
    row = conn.execute(
        "SELECT sector FROM stock_universe WHERE symbol = ?", (symbol,)
    ).fetchone()

    if not row or not row["sector"]:
        return {"still_valid": True, "thesis": "sector_cycle",
                "reason": "Sector unknown", "detail": "Cannot determine sector."}

    # Use scanner cache to check if sector peers are still triggering
    try:
        from app.calculations.scanner import run_scanner
        scanner = run_scanner()
        sector = row["sector"]
        peers_in_sector = [s for s in scanner.get("signals", []) if s.get("sector") == sector]
        if len(peers_in_sector) >= 2:
            return {"still_valid": True, "thesis": "sector_cycle",
                    "reason": f"Sector active — {len(peers_in_sector)} peers triggered this week",
                    "detail": f"Peers: {', '.join(p['symbol'] for p in peers_in_sector[:5])}"}
        elif len(peers_in_sector) == 1:
            return {"still_valid": True, "thesis": "sector_cycle",
                    "reason": "Sector cooling — only 1 peer triggered",
                    "detail": "Monitor closely. Fewer sector signals than when you bought."}
        else:
            return {"still_valid": False, "thesis": "sector_cycle",
                    "reason": "No sector peers triggered — cycle may be exhausting",
                    "detail": f"Zero stocks in {sector} passed the scanner this week. The sector rotation may have moved on."}
    except Exception:
        return {"still_valid": True, "thesis": "sector_cycle",
                "reason": "Unable to check", "detail": "Scanner data unavailable."}


def _load_universe(conn) -> dict:
    """Load stock universe as {symbol: {name, sector}}."""
    rows = conn.execute(
        "SELECT symbol, company_name, sector FROM stock_universe"
    ).fetchall()
    return {
        r["symbol"]: {
            "name": r["company_name"] or r["symbol"],
            "sector": r["sector"] or "Unknown",
        }
        for r in rows
    }


# ── Weekly resampling + MAs ───────────────────────────────────

def _resample_to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Convert daily OHLC to weekly candles (Mon-Fri ending Friday)."""
    indexed = daily.set_index("date")
    weekly = (
        indexed.groupby("symbol")
        .resample("W-FRI")
        .agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "delivery_pct": "mean",
        })
    )
    weekly = weekly.dropna(subset=["close"])
    weekly.index.names = ["symbol", "week_end"]
    return weekly


def _calculate_mas(stock_weekly: pd.DataFrame) -> pd.DataFrame:
    """Calculate 10W, 30W, 52W moving averages."""
    stock_weekly = stock_weekly.copy()
    g = stock_weekly.groupby(level="symbol")
    stock_weekly["ma_10w"] = g["close"].transform(
        lambda x: x.rolling(10, min_periods=5).mean()
    )
    stock_weekly["ma_30w"] = g["close"].transform(
        lambda x: x.rolling(30, min_periods=15).mean()
    )
    stock_weekly["ma_52w"] = g["close"].transform(
        lambda x: x.rolling(52, min_periods=26).mean()
    )
    return stock_weekly


# ── Helpers ───────────────────────────────────────────────────

def _get_current_price(stock_weekly: pd.DataFrame, symbol: str) -> float | None:
    """Get the latest weekly close for a symbol."""
    try:
        sym_data = stock_weekly.loc[symbol]
        return float(sym_data.iloc[-1]["close"])
    except (KeyError, IndexError):
        return None


def _make_holding_entry(h: dict, info: dict, current_price, signals: list) -> dict:
    """Build a holding entry when we have no price data."""
    return {
        "symbol": h["symbol"],
        "name": info["name"],
        "sector": info["sector"],
        "buy_price": h["buy_price"],
        "buy_date": h.get("buy_date"),
        "quantity": h.get("quantity", 1),
        "current_price": current_price,
        "pnl_pct": None,
        "held_months": 0,
        "signals": signals,
    }


def _calc_sector_concentration(holdings: list[dict], universe: dict) -> list[dict]:
    """Calculate sector distribution of holdings."""
    sector_counts: dict[str, int] = {}
    for h in holdings:
        sector = universe.get(h["symbol"], {}).get("sector", "Others")
        sector_counts[sector] = sector_counts.get(sector, 0) + 1

    total = len(holdings)
    result = []
    for sector, count in sorted(sector_counts.items(), key=lambda x: -x[1]):
        result.append({
            "sector": sector,
            "count": count,
            "pct": round(count / total * 100) if total > 0 else 0,
        })
    return result


def _get_market_leverage() -> dict | None:
    """Build market leverage data from daily_accumulation trend.

    Uses F&O participant OI (Client long/short) as a proxy for market-wide
    margin leverage. Returns shape expected by frontend:
    {margin_borrowing_cr, trend_3m} or None if insufficient data.
    """
    try:
        from scripts.daily_accumulation import get_accumulation_trend
        trend = get_accumulation_trend("market_leverage", days=90)
    except Exception:
        return None

    if not trend:
        return None

    latest = trend[-1]
    client_long = latest.get("value1")
    client_short = latest.get("value2")
    ls_ratio = latest.get("ratio")

    if client_long is None:
        return None

    # Approximate margin borrowing in Cr from contracts
    # Each Nifty lot ~= 25 contracts × ~₹22,000 = ~₹5.5L notional
    # This is a rough market-wide estimate; the actual number is the
    # client long contract count which the frontend displays
    # We express it as the raw long contracts (in lakhs) for now
    margin_borrowing_cr = round(client_long / 100000, 1)  # contracts in lakhs

    # 3-month trend: compare latest vs oldest available
    if len(trend) >= 7:
        oldest = trend[0]
        oldest_long = oldest.get("value1", 0) or 0
        if oldest_long > 0 and client_long > 0:
            change_pct = (client_long - oldest_long) / oldest_long * 100
            if change_pct > 5:
                trend_3m = "INCREASING"
            elif change_pct < -5:
                trend_3m = "DECREASING"
            else:
                trend_3m = "STABLE"
        else:
            trend_3m = "STABLE"
    else:
        trend_3m = "ACCUMULATING"  # not enough data yet

    return {
        "margin_borrowing_cr": margin_borrowing_cr,
        "trend_3m": trend_3m,
        "client_long_contracts": client_long,
        "client_short_contracts": client_short,
        "long_short_ratio": ls_ratio,
        "data_points": len(trend),
    }


def _empty_response() -> dict:
    """Response when no holdings exist."""
    return {
        "total_holdings": 0,
        "portfolio_value": 0,
        "total_pnl": 0,
        "total_pnl_pct": 0.0,
        "holdings": {"healthy": [], "warning": [], "alert": []},
        "sector_concentration": [],
        "market_leverage": _get_market_leverage(),
    }


def _build_response_no_data(holdings: list[dict], universe: dict) -> dict:
    """Response when we have holdings but no OHLC data."""
    items = []
    for h in holdings:
        info = universe.get(h["symbol"], {"name": h["symbol"], "sector": "Unknown"})
        items.append(_make_holding_entry(h, info, None, []))

    return {
        "total_holdings": len(holdings),
        "portfolio_value": 0,
        "total_pnl": 0,
        "total_pnl_pct": 0.0,
        "holdings": {"healthy": items, "warning": [], "alert": []},
        "sector_concentration": _calc_sector_concentration(holdings, universe),
        "market_leverage": _get_market_leverage(),
    }
