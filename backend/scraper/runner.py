import importlib
import logging
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Job, ScrapeSource
from scraper.base import BaseScraper, ScrapedJob, ScrapeResult

logger = logging.getLogger(__name__)

# Registry of available scrapers by class name
SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {}


def register_scraper(scraper_class: type[BaseScraper]) -> type[BaseScraper]:
    """Decorator to register a scraper class."""
    SCRAPER_REGISTRY[scraper_class.__name__] = scraper_class
    return scraper_class


def get_scraper_class(class_name: str) -> type[BaseScraper] | None:
    """Get a scraper class by name."""
    # First check registry
    if class_name in SCRAPER_REGISTRY:
        return SCRAPER_REGISTRY[class_name]

    # Try to import from scraper.sources module
    try:
        module = importlib.import_module("scraper.sources")
        if hasattr(module, class_name):
            scraper_class = getattr(module, class_name)
            SCRAPER_REGISTRY[class_name] = scraper_class
            return scraper_class
    except ImportError:
        pass

    return None


def upsert_job(db: Session, source_id: int, scraped_job: ScrapedJob) -> tuple[bool, bool]:
    """Insert or update a job in the database.

    Returns (is_new, is_updated) tuple.
    """
    now = datetime.now(timezone.utc)

    # Check if job already exists
    existing_job = db.query(Job).filter(Job.external_id == scraped_job.external_id).first()

    if existing_job:
        # Update last_seen_at and un-stale if necessary
        existing_job.last_seen_at = now
        if existing_job.is_stale:
            existing_job.is_stale = False
        return (False, True)
    else:
        # Create new job
        job = Job(
            source_id=source_id,
            external_id=scraped_job.external_id,
            title=scraped_job.title,
            organization=scraped_job.organization,
            location=scraped_job.location,
            state=scraped_job.state,
            description=scraped_job.description,
            job_type=scraped_job.job_type,
            salary_info=scraped_job.salary_info,
            url=scraped_job.url,
            first_seen_at=now,
            last_seen_at=now,
            is_stale=False,
        )
        db.add(job)
        return (True, False)


def run_scraper(db: Session, source: ScrapeSource) -> ScrapeResult:
    """Run a single scraper and upsert jobs to database."""
    start_time = time.time()

    # Get the scraper class
    scraper_class = get_scraper_class(source.scraper_class)
    if scraper_class is None:
        return ScrapeResult(
            source_name=source.name,
            jobs_found=0,
            jobs_new=0,
            jobs_updated=0,
            errors=[f"Unknown scraper class: {source.scraper_class}"],
            duration_seconds=0,
        )

    jobs_new = 0
    jobs_updated = 0
    all_errors: list[str] = []

    try:
        with scraper_class() as scraper:
            scraped_jobs, errors = scraper.run()
            all_errors.extend(errors)

            for scraped_job in scraped_jobs:
                try:
                    is_new, is_updated = upsert_job(db, source.id, scraped_job)
                    if is_new:
                        jobs_new += 1
                    elif is_updated:
                        jobs_updated += 1
                except Exception as e:
                    all_errors.append(f"Failed to upsert job {scraped_job.external_id}: {e}")

            # Update source's last_scraped_at
            source.last_scraped_at = datetime.now(timezone.utc)

    except Exception as e:
        all_errors.append(f"Scraper execution failed: {e}")

    duration = time.time() - start_time

    return ScrapeResult(
        source_name=source.name,
        jobs_found=jobs_new + jobs_updated,
        jobs_new=jobs_new,
        jobs_updated=jobs_updated,
        errors=all_errors,
        duration_seconds=duration,
    )


def run_all_scrapers(db: Session, sources: list[ScrapeSource]) -> list[ScrapeResult]:
    """Run all scrapers for the given sources."""
    results = []
    for source in sources:
        logger.info(f"Running scraper for {source.name}...")
        result = run_scraper(db, source)
        results.append(result)
    return results
