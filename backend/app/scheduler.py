"""APScheduler integration — keeps data fresh automatically.

P0 item 4 from pending-list.md.

Schedule:
  Daily 4:30 PM IST (Mon-Fri):  Stock OHLC + delivery append
  Daily 4:45 PM IST (Mon-Fri):  Index append (14 indices)
  Daily 5:00 PM IST (Mon-Fri):  Macro data refresh (world indices, commodities, etc.)
  Daily 5:15 PM IST (Mon-Fri):  Bulk/block deals
  Daily 5:30 PM IST (Mon-Fri):  A/D + 52W + leverage accumulation (no backfill possible)
  Weekly Sunday 10:00 AM IST:   Universe refresh
  Quarterly 1st of Feb/May/Aug/Nov 6:00 AM IST: Financials refresh
  Quarterly 2nd of Feb/May/Aug/Nov 6:00 AM IST: Promoter holding refresh
  Quarterly 3rd of Feb/May/Aug/Nov 6:00 AM IST: Sector classification refresh

All jobs run in background threads — FastAPI stays responsive.
Jobs log to the standard logger. Check /api/scheduler/status for job info.
"""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")


# ── Job functions ─────────────────────────────────────


def _job_daily_ohlc():
    """Fetch daily stock OHLC + delivery for all stocks."""
    logger.info("Scheduler: starting daily OHLC append")
    try:
        from scripts.daily_ohlc import daily_ohlc_append
        daily_ohlc_append(delay=1.0)
        logger.info("Scheduler: daily OHLC append complete")
    except Exception as e:
        logger.error(f"Scheduler: daily OHLC failed: {e}")


def _job_daily_indices():
    """Fetch daily index data for all 14 indices."""
    logger.info("Scheduler: starting daily index append")
    try:
        from scripts.daily_indices import daily_index_append
        daily_index_append(delay=1.0)
        logger.info("Scheduler: daily index append complete")
    except Exception as e:
        logger.error(f"Scheduler: daily index failed: {e}")


def _job_macro_refresh():
    """Refresh all external macro data (world indices, commodities, etc.)."""
    logger.info("Scheduler: starting macro refresh")
    try:
        from app.fetchers.world_indices import fetch_world_indices
        from app.fetchers.commodities import fetch_commodities
        from app.fetchers.macro_indicators import fetch_macro_indicators
        from app.fetchers.market_depth import fetch_market_depth
        from app.fetchers.market_leverage import fetch_market_leverage

        for name, fn in [
            ("world_indices", fetch_world_indices),
            ("commodities", fetch_commodities),
            ("macro_indicators", fetch_macro_indicators),
            ("market_depth", fetch_market_depth),
            ("market_leverage", fetch_market_leverage),
        ]:
            try:
                fn(force=True)
            except Exception as e:
                logger.warning(f"Scheduler: {name} fetch failed: {e}")

        logger.info("Scheduler: macro refresh complete")
    except Exception as e:
        logger.error(f"Scheduler: macro refresh failed: {e}")


def _job_daily_deals():
    """Fetch daily bulk/block deals from NSE."""
    logger.info("Scheduler: starting daily deals fetch")
    try:
        from scripts.daily_deals import daily_deals_fetch
        daily_deals_fetch(delay=1.0)
        logger.info("Scheduler: daily deals fetch complete")
    except Exception as e:
        logger.error(f"Scheduler: daily deals failed: {e}")


def _job_daily_accumulation():
    """Store today's A/D counts and 52W highs/lows for trend tracking."""
    logger.info("Scheduler: starting daily accumulation")
    try:
        from scripts.daily_accumulation import daily_accumulation_store
        daily_accumulation_store()
        logger.info("Scheduler: daily accumulation complete")
    except Exception as e:
        logger.error(f"Scheduler: daily accumulation failed: {e}")


def _job_quarterly_financials():
    """Re-fetch quarterly financials for all stocks."""
    logger.info("Scheduler: starting quarterly financials refresh")
    try:
        from scripts.refresh_financials import refresh_financials
        refresh_financials(delay=0.2)
        logger.info("Scheduler: quarterly financials refresh complete")
    except Exception as e:
        logger.error(f"Scheduler: quarterly financials refresh failed: {e}")


def _job_quarterly_sectors():
    """Re-fetch sector/industry classification for all stocks."""
    logger.info("Scheduler: starting quarterly sector classification refresh")
    try:
        from scripts.refresh_sectors import refresh_sectors
        refresh_sectors(delay=0.2)
        logger.info("Scheduler: quarterly sector classification refresh complete")
    except Exception as e:
        logger.error(f"Scheduler: quarterly sector classification refresh failed: {e}")


def _job_quarterly_promoter():
    """Re-fetch promoter holding for all stocks."""
    logger.info("Scheduler: starting quarterly promoter holding refresh")
    try:
        from scripts.refresh_promoter import refresh_promoter
        refresh_promoter(delay=2.0)
        logger.info("Scheduler: quarterly promoter holding refresh complete")
    except Exception as e:
        logger.error(f"Scheduler: quarterly promoter holding refresh failed: {e}")


def _job_weekly_universe():
    """Refresh stock universe — add new stocks, remove delisted."""
    logger.info("Scheduler: starting weekly universe refresh")
    try:
        from scripts.refresh_universe import refresh_universe
        refresh_universe(delay=0.2)
        logger.info("Scheduler: weekly universe refresh complete")
    except Exception as e:
        logger.error(f"Scheduler: universe refresh failed: {e}")


# ── Setup ─────────────────────────────────────────────


def start_scheduler():
    """Register all jobs and start the scheduler."""
    if scheduler.running:
        return

    # Daily OHLC — 4:30 PM IST, Mon-Fri
    scheduler.add_job(
        _job_daily_ohlc,
        CronTrigger(hour=16, minute=30, day_of_week="mon-fri", timezone="Asia/Kolkata"),
        id="daily_ohlc",
        name="Daily Stock OHLC + Delivery",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Daily indices — 4:45 PM IST, Mon-Fri
    scheduler.add_job(
        _job_daily_indices,
        CronTrigger(hour=16, minute=45, day_of_week="mon-fri", timezone="Asia/Kolkata"),
        id="daily_indices",
        name="Daily Index Append (14 indices)",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Macro refresh — 5:00 PM IST, Mon-Fri
    scheduler.add_job(
        _job_macro_refresh,
        CronTrigger(hour=17, minute=0, day_of_week="mon-fri", timezone="Asia/Kolkata"),
        id="macro_refresh",
        name="Macro Data Refresh",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Daily deals — 5:15 PM IST, Mon-Fri
    scheduler.add_job(
        _job_daily_deals,
        CronTrigger(hour=17, minute=15, day_of_week="mon-fri", timezone="Asia/Kolkata"),
        id="daily_deals",
        name="Daily Bulk/Block Deals",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Daily accumulation (A/D + 52W) — 5:30 PM IST, Mon-Fri
    scheduler.add_job(
        _job_daily_accumulation,
        CronTrigger(hour=17, minute=30, day_of_week="mon-fri", timezone="Asia/Kolkata"),
        id="daily_accumulation",
        name="Daily A/D + 52W Accumulation",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Quarterly financials refresh — 1st of Feb, May, Aug, Nov at 6:00 AM IST
    scheduler.add_job(
        _job_quarterly_financials,
        CronTrigger(hour=6, minute=0, day=1, month="2,5,8,11", timezone="Asia/Kolkata"),
        id="quarterly_financials",
        name="Quarterly Financials Refresh",
        replace_existing=True,
        misfire_grace_time=86400,  # 24h grace — can run anytime that day
    )

    # Quarterly sector classification refresh — 3rd of Feb, May, Aug, Nov at 6:00 AM IST
    scheduler.add_job(
        _job_quarterly_sectors,
        CronTrigger(hour=6, minute=0, day=3, month="2,5,8,11", timezone="Asia/Kolkata"),
        id="quarterly_sectors",
        name="Quarterly Sector Classification Refresh",
        replace_existing=True,
        misfire_grace_time=86400,
    )

    # Quarterly promoter holding refresh — 2nd of Feb, May, Aug, Nov at 6:00 AM IST
    # (day after financials to spread the load)
    scheduler.add_job(
        _job_quarterly_promoter,
        CronTrigger(hour=6, minute=0, day=2, month="2,5,8,11", timezone="Asia/Kolkata"),
        id="quarterly_promoter",
        name="Quarterly Promoter Holding Refresh",
        replace_existing=True,
        misfire_grace_time=86400,
    )

    # Weekly universe refresh — Sunday 10:00 AM IST
    scheduler.add_job(
        _job_weekly_universe,
        CronTrigger(hour=10, minute=0, day_of_week="sun", timezone="Asia/Kolkata"),
        id="weekly_universe",
        name="Weekly Universe Refresh",
        replace_existing=True,
        misfire_grace_time=7200,
    )

    scheduler.start()
    logger.info("Scheduler started with 9 jobs")


def stop_scheduler():
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def get_scheduler_status() -> dict:
    """Return status of all scheduled jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return {
        "running": scheduler.running,
        "jobs": jobs,
    }
