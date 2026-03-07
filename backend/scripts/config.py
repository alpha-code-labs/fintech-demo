"""
Pipeline configuration — all constants in one place.
"""
from pathlib import Path
from datetime import date, timedelta

# ── Paths ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # backend/
DB_PATH = PROJECT_ROOT / "data" / "investscan.db"

# ── Date ranges for backfill ───────────────────────────
TODAY = date.today()
STOCK_OHLC_START = TODAY - timedelta(days=730)   # 2 years
NIFTY50_START = TODAY - timedelta(days=730)      # 2 years
INDEX_START = TODAY - timedelta(days=365)        # 1 year
SECTOR_START = TODAY - timedelta(days=365)       # 1 year

# ── Rate limiting (seconds between API calls) ─────────
JUGAAD_DELAY = 1.0       # jugaad-data (NSE source)
YFINANCE_DELAY = 0.2     # yfinance (Yahoo source)
NSEPYTHON_DELAY = 2.0    # nsepython (NSE direct API)

# ── Market cap threshold ───────────────────────────────
UNIVERSE_MCAP_MIN = 500  # Crores

# ── NSE equity list CSV ────────────────────────────────
NSE_EQUITY_CSV_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"

# ── Index names ────────────────────────────────────────
NIFTY50_NAME = "NIFTY 50"

BROAD_INDICES = [
    "NIFTY BANK",
    "NIFTY MIDCAP 100",
    "NIFTY SMALLCAP 100",
]

SECTOR_INDICES = [
    "NIFTY IT",
    "NIFTY PHARMA",
    "NIFTY AUTO",
    "NIFTY FMCG",
    "NIFTY METAL",
    "NIFTY REALTY",
    "NIFTY ENERGY",
    "NIFTY MEDIA",
    "NIFTY PSE",
    "NIFTY INFRA",
]

# ── yfinance ticker mapping for indices (fallback when nselib fails) ──
YFINANCE_INDEX_TICKERS = {
    "NIFTY 50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "NIFTY MIDCAP 100": "NIFTY_MIDCAP_100.NS",
    "NIFTY SMALLCAP 100": "^CNXSC",
    "NIFTY IT": "^CNXIT",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY REALTY": "^CNXREALTY",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY MEDIA": "^CNXMEDIA",
    "NIFTY PSE": "^CNXPSE",
    "NIFTY INFRA": "^CNXINFRA",
}

# ── Retry settings ─────────────────────────────────────
MAX_RETRIES = 3
RETRY_BACKOFF = 5.0  # seconds, multiplied by retry_count
