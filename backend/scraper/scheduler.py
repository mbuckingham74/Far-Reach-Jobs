from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


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
    """Start the APScheduler with configured jobs."""
    # Run scrapers at noon and midnight PST (UTC-8)
    # Noon PST = 20:00 UTC, Midnight PST = 08:00 UTC
    scheduler.add_job(
        run_scrapers,
        CronTrigger(hour=8, minute=0, timezone="UTC"),  # Midnight PST
        id="scrape_midnight",
        replace_existing=True,
    )
    scheduler.add_job(
        run_scrapers,
        CronTrigger(hour=20, minute=0, timezone="UTC"),  # Noon PST
        id="scrape_noon",
        replace_existing=True,
    )

    # Run cleanup after each scrape (with 5 min delay to allow scraping to finish)
    scheduler.add_job(
        cleanup_stale_jobs,
        CronTrigger(hour=8, minute=30, timezone="UTC"),
        id="cleanup_midnight",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_stale_jobs,
        CronTrigger(hour=20, minute=30, timezone="UTC"),
        id="cleanup_noon",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with scrape jobs at noon and midnight PST")


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")
