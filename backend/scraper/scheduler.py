from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)

scheduler: BackgroundScheduler | None = None


def run_scrapers():
    """Run all active scrapers - To be fully implemented in Phase 1C."""
    logger.info("Starting scheduled scrape run...")
    # Will be implemented to:
    # 1. Get all active scrape sources from DB
    # 2. Run each scraper
    # 3. Update last_scraped_at
    # 4. Run stale job cleanup
    logger.info("Scrape run completed.")


def cleanup_stale_jobs():
    """Mark jobs as stale if not seen in 24h, delete if stale for 7 days."""
    logger.info("Running stale job cleanup...")
    # Will be implemented in Phase 1C
    logger.info("Stale job cleanup completed.")


def start_scheduler():
    """Start the APScheduler with configured jobs.

    Uses America/Anchorage timezone for Alaska-centric scheduling.
    Noon and midnight in Alaska time (handles DST automatically).
    """
    global scheduler
    scheduler = BackgroundScheduler()

    # Use Alaska timezone directly - APScheduler handles DST
    alaska_tz = "America/Anchorage"

    scheduler.add_job(
        run_scrapers,
        CronTrigger(hour=0, minute=0, timezone=alaska_tz),  # Midnight Alaska
        id="scrape_midnight",
        replace_existing=True,
    )
    scheduler.add_job(
        run_scrapers,
        CronTrigger(hour=12, minute=0, timezone=alaska_tz),  # Noon Alaska
        id="scrape_noon",
        replace_existing=True,
    )

    # Run cleanup after each scrape (with 30 min delay to allow scraping to finish)
    scheduler.add_job(
        cleanup_stale_jobs,
        CronTrigger(hour=0, minute=30, timezone=alaska_tz),
        id="cleanup_midnight",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_stale_jobs,
        CronTrigger(hour=12, minute=30, timezone=alaska_tz),
        id="cleanup_noon",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with scrape jobs at noon and midnight Alaska time")


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
