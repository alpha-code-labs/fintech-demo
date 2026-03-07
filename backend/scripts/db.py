"""
SQLite database layer — schema, connection, insert helpers.
"""
import sqlite3
import pandas as pd
from scripts.config import DB_PATH

SCHEMA_SQL = """
-- Stock universe: ~1,200 stocks above 500 Cr market cap
CREATE TABLE IF NOT EXISTS stock_universe (
    symbol          TEXT PRIMARY KEY,
    company_name    TEXT,
    series          TEXT DEFAULT 'EQ',
    isin            TEXT,
    sector          TEXT,
    industry        TEXT,
    market_cap_cr   REAL,
    fetched_at      TEXT NOT NULL
);

-- Step 0a: Daily OHLC + volume + delivery for every stock
CREATE TABLE IF NOT EXISTS stock_ohlc (
    symbol          TEXT NOT NULL,
    date            TEXT NOT NULL,
    series          TEXT DEFAULT 'EQ',
    open            REAL,
    high            REAL,
    low             REAL,
    close           REAL,
    prev_close      REAL,
    ltp             REAL,
    vwap            REAL,
    volume          INTEGER,
    value           REAL,
    no_of_trades    INTEGER,
    deliverable_qty INTEGER,
    delivery_pct    REAL,
    PRIMARY KEY (symbol, date)
);
CREATE INDEX IF NOT EXISTS idx_stock_ohlc_date ON stock_ohlc(date);
CREATE INDEX IF NOT EXISTS idx_stock_ohlc_symbol ON stock_ohlc(symbol);

-- Steps 0b/0c/0d: All indices in one table
CREATE TABLE IF NOT EXISTS index_daily (
    index_name      TEXT NOT NULL,
    date            TEXT NOT NULL,
    open            REAL,
    high            REAL,
    low             REAL,
    close           REAL,
    PRIMARY KEY (index_name, date)
);
CREATE INDEX IF NOT EXISTS idx_index_daily_name ON index_daily(index_name);
CREATE INDEX IF NOT EXISTS idx_index_daily_date ON index_daily(date);

-- Step 0e: Quarterly financials (income stmt + balance sheet)
CREATE TABLE IF NOT EXISTS quarterly_financials (
    symbol          TEXT NOT NULL,
    quarter_end     TEXT NOT NULL,
    revenue         REAL,
    operating_income REAL,
    net_income      REAL,
    eps             REAL,
    operating_margin REAL,
    total_debt      REAL,
    total_assets    REAL,
    total_equity    REAL,
    cash_flow_operations REAL,
    source          TEXT DEFAULT 'yfinance',
    fetched_at      TEXT NOT NULL,
    PRIMARY KEY (symbol, quarter_end)
);

-- Step 0f: Quarterly promoter holding
CREATE TABLE IF NOT EXISTS promoter_holding (
    symbol          TEXT NOT NULL,
    quarter_end     TEXT NOT NULL,
    promoter_pct    REAL,
    public_pct      REAL,
    dii_pct         REAL,
    fii_pct         REAL,
    source          TEXT DEFAULT 'nsepython',
    fetched_at      TEXT NOT NULL,
    PRIMARY KEY (symbol, quarter_end)
);

-- Bulk and block deals
CREATE TABLE IF NOT EXISTS bulk_block_deals (
    date            TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    deal_type       TEXT NOT NULL,  -- 'BULK' or 'BLOCK'
    client_name     TEXT,
    buy_sell        TEXT,           -- 'BUY' or 'SELL'
    quantity        INTEGER,
    price           REAL,
    remarks         TEXT,
    PRIMARY KEY (date, symbol, deal_type, client_name, buy_sell)
);
CREATE INDEX IF NOT EXISTS idx_deals_symbol ON bulk_block_deals(symbol);
CREATE INDEX IF NOT EXISTS idx_deals_date ON bulk_block_deals(date);

-- Daily accumulation: A/D ratio, 52W highs/lows, FII/DII, leverage (no backfill possible)
CREATE TABLE IF NOT EXISTS daily_accumulation (
    date            TEXT NOT NULL,
    metric          TEXT NOT NULL,  -- 'ad', '52w_hl', 'fii_dii', 'market_leverage'
    value1          INTEGER,       -- advancing / highs_52w / fii_net / client_long
    value2          INTEGER,       -- declining / lows_52w / dii_net / client_short
    ratio           REAL,          -- ad_ratio / hl_ratio / NULL / long_short_ratio
    PRIMARY KEY (date, metric)
);
CREATE INDEX IF NOT EXISTS idx_accum_date ON daily_accumulation(date);

-- Resume tracker
CREATE TABLE IF NOT EXISTS backfill_progress (
    step            TEXT NOT NULL,
    item            TEXT NOT NULL,
    status          TEXT NOT NULL,
    error_message   TEXT,
    rows_inserted   INTEGER DEFAULT 0,
    started_at      TEXT,
    completed_at    TEXT,
    retry_count     INTEGER DEFAULT 0,
    PRIMARY KEY (step, item)
);
"""


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode enabled."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema():
    """Create all tables and indices if they don't exist."""
    conn = get_connection()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()


def insert_dataframe(table: str, df: pd.DataFrame, conn: sqlite3.Connection) -> int:
    """Bulk insert a DataFrame into a table using INSERT OR REPLACE."""
    if df.empty:
        return 0
    cols = df.columns.tolist()
    placeholders = ",".join(["?"] * len(cols))
    col_names = ",".join(cols)
    sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"
    conn.executemany(sql, df.values.tolist())
    conn.commit()
    return len(df)


def get_universe_symbols() -> list[str]:
    """Return all symbols from the stock_universe table."""
    conn = get_connection()
    rows = conn.execute("SELECT symbol FROM stock_universe ORDER BY symbol").fetchall()
    conn.close()
    return [r["symbol"] for r in rows]
