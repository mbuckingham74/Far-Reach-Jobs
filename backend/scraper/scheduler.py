import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler: BackgroundScheduler | None = None

# Job lifecycle constants
STALE_AFTER_HOURS = 24  # Mark as stale if not seen in 24 hours (2 missed scrapes)
DELETE_AFTER_DAYS = 7   # Delete if stale for 7 days


def run_scrapers():
    """Run all active scrapers and upsert jobs to database."""
    from app.database import SessionLocal
    from app.models import Job, ScrapeSource
    from scraper.runner import run_all_scrapers

    logger.info("Starting scheduled scrape run...")

    db = SessionLocal()
    try:
        # Get all active sources
        sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == True).all()
        if not sources:
            logger.warning("No active scrape sources configured")
            return

        # Run scrapers and get results (scheduled trigger type)
        results = run_all_scrapers(db, sources, trigger_type="scheduled")

        for result in results:
            logger.info(
                f"[{result.source_name}] Found: {result.jobs_found}, "
                f"New: {result.jobs_new}, Updated: {result.jobs_updated}, "
                f"Errors: {len(result.errors)}"
            )
            if result.errors:
                for error in result.errors:
                    logger.error(f"[{result.source_name}] {error}")

        db.commit()
        logger.info("Scrape run completed successfully")

    except Exception as e:
        logger.error(f"Scrape run failed: {e}")
        db.rollback()
    finally:
        db.close()


def cleanup_stale_jobs():
    """Mark jobs as stale if not seen in 24h, delete if stale for 7 days."""
    from app.database import SessionLocal
    from app.models import Job

    logger.info("Running stale job cleanup...")

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(hours=STALE_AFTER_HOURS)
        delete_threshold = now - timedelta(days=DELETE_AFTER_DAYS)

        # Mark jobs as stale if not seen recently
        stale_count = (
            db.query(Job)
            .filter(Job.is_stale == False)
            .filter(Job.last_seen_at < stale_threshold)
            .update({"is_stale": True})
        )
        logger.info(f"Marked {stale_count} jobs as stale")

        # Delete jobs that have been stale for too long
        delete_count = (
            db.query(Job)
            .filter(Job.is_stale == True)
            .filter(Job.last_seen_at < delete_threshold)
            .delete()
        )
        logger.info(f"Deleted {delete_count} stale jobs")

        db.commit()
        logger.info("Stale job cleanup completed")

    except Exception as e:
        logger.error(f"Stale job cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()


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
