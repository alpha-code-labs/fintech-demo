"""
Resume tracker — read/write job status, progress bar display.
"""
import sys
import time
from datetime import datetime, timezone
from scripts.db import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_remaining_items(step: str, all_items: list[str]) -> list[str]:
    """Return items not yet marked as 'done' in backfill_progress."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT item FROM backfill_progress WHERE step = ? AND status = 'done'",
        (step,),
    ).fetchall()
    conn.close()
    done = {r["item"] for r in rows}
    return [item for item in all_items if item not in done]


def mark_started(step: str, item: str):
    """Insert or update progress row with status='pending'."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO backfill_progress (step, item, status, started_at)
           VALUES (?, ?, 'pending', ?)
           ON CONFLICT(step, item) DO UPDATE SET
               status = 'pending',
               started_at = excluded.started_at""",
        (step, item, _now()),
    )
    conn.commit()
    conn.close()


def mark_done(step: str, item: str, rows_inserted: int):
    """Update progress row with status='done'."""
    conn = get_connection()
    conn.execute(
        """UPDATE backfill_progress
           SET status = 'done', rows_inserted = ?, completed_at = ?
           WHERE step = ? AND item = ?""",
        (rows_inserted, _now(), step, item),
    )
    conn.commit()
    conn.close()


def mark_error(step: str, item: str, error_message: str):
    """Update progress row with status='error', increment retry_count."""
    conn = get_connection()
    conn.execute(
        """UPDATE backfill_progress
           SET status = 'error',
               error_message = ?,
               retry_count = retry_count + 1,
               completed_at = ?
           WHERE step = ? AND item = ?""",
        (error_message, _now(), step, item),
    )
    conn.commit()
    conn.close()


def get_error_items(step: str) -> list[str]:
    """Return items with status='error' for retrying."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT item FROM backfill_progress WHERE step = ? AND status = 'error'",
        (step,),
    ).fetchall()
    conn.close()
    return [r["item"] for r in rows]


def get_progress_summary(step: str = None) -> dict:
    """Return counts of done/error/pending per step."""
    conn = get_connection()
    if step:
        rows = conn.execute(
            """SELECT step, status, COUNT(*) as cnt
               FROM backfill_progress WHERE step = ?
               GROUP BY step, status""",
            (step,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT step, status, COUNT(*) as cnt
               FROM backfill_progress
               GROUP BY step, status"""
        ).fetchall()
    conn.close()

    summary = {}
    for r in rows:
        s = r["step"]
        if s not in summary:
            summary[s] = {"done": 0, "error": 0, "pending": 0}
        summary[s][r["status"]] = r["cnt"]
    return summary


def print_progress_bar(done: int, total: int, item_name: str, start_time: float):
    """Print a progress bar to stderr."""
    if total == 0:
        return
    pct = done / total * 100
    bar_len = 30
    filled = int(bar_len * done / total)
    bar = "=" * filled + ">" + " " * (bar_len - filled - 1)

    elapsed = time.time() - start_time
    if done > 0:
        eta_sec = (elapsed / done) * (total - done)
        eta_m, eta_s = divmod(int(eta_sec), 60)
        eta_str = f"{eta_m}m {eta_s:02d}s"
    else:
        eta_str = "..."

    line = f"\r[{bar}] {done}/{total} ({pct:.1f}%) | ETA: {eta_str} | {item_name}"
    sys.stderr.write(line.ljust(100) + "\r")
    sys.stderr.flush()

    if done == total:
        sys.stderr.write("\n")


def print_status_report():
    """Print a human-readable progress report for all steps."""
    summary = get_progress_summary()
    if not summary:
        print("No backfill progress recorded yet.")
        return

    print("\n── Backfill Progress ──────────────────────────")
    for step in sorted(summary.keys()):
        counts = summary[step]
        total = counts["done"] + counts["error"] + counts["pending"]
        print(
            f"  {step:12s}  "
            f"done: {counts['done']:>5}  "
            f"error: {counts['error']:>4}  "
            f"pending: {counts['pending']:>4}  "
            f"total: {total:>5}"
        )

    # Show recent errors
    conn = get_connection()
    errors = conn.execute(
        """SELECT step, item, error_message, retry_count
           FROM backfill_progress
           WHERE status = 'error'
           ORDER BY completed_at DESC
           LIMIT 10"""
    ).fetchall()
    conn.close()

    if errors:
        print("\n── Recent Errors (last 10) ────────────────────")
        for e in errors:
            print(f"  [{e['step']}] {e['item']} (retries: {e['retry_count']})")
            print(f"         {e['error_message'][:120]}")
    print()
