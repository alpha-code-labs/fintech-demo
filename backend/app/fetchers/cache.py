"""
Live cache — stores fetcher results in SQLite so the macro route
reads from cache, not from external APIs per request.
"""
import json
import sqlite3
from datetime import datetime, timedelta

from app.db import get_connection


def _ensure_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS live_cache (
            key         TEXT PRIMARY KEY,
            data        TEXT NOT NULL,
            fetched_at  TEXT NOT NULL
        )
    """)
    conn.commit()


def cache_set(key: str, data: dict | list) -> None:
    conn = get_connection()
    try:
        _ensure_table(conn)
        conn.execute(
            "INSERT OR REPLACE INTO live_cache (key, data, fetched_at) VALUES (?, ?, ?)",
            (key, json.dumps(data), datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def cache_get(key: str, max_age_hours: float = 24.0) -> dict | list | None:
    """Return cached data if it exists and is fresher than max_age_hours."""
    conn = get_connection()
    try:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT data, fetched_at FROM live_cache WHERE key = ?", (key,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    fetched_at = datetime.fromisoformat(row["fetched_at"])
    if datetime.now() - fetched_at > timedelta(hours=max_age_hours):
        return None

    return json.loads(row["data"])
