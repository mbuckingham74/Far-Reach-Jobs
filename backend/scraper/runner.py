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
    """Decorator to register a scraper class.

    Usage:
        @register_scraper
        class MyOrgScraper(BaseScraper):
            ...

    The scraper will be available by its class name (e.g., "MyOrgScraper")
    when referenced in ScrapeSource.scraper_class.
    """
    SCRAPER_REGISTRY[scraper_class.__name__] = scraper_class
    logger.debug(f"Registered scraper: {scraper_class.__name__}")
    return scraper_class


def get_scraper_class(class_name: str) -> type[BaseScraper] | None:
    """Get a scraper class by name.

    Looks up in the registry first, then tries to import from scraper.sources.
    Returns None if the scraper class is not found.
    """
    # First check registry
    if class_name in SCRAPER_REGISTRY:
        return SCRAPER_REGISTRY[class_name]

    # Try to import from scraper.sources module
    # This handles cases where scrapers are defined but not yet imported
    try:
        module = importlib.import_module("scraper.sources")
        if hasattr(module, class_name):
            scraper_class = getattr(module, class_name)
            SCRAPER_REGISTRY[class_name] = scraper_class
            return scraper_class
    except ImportError:
        pass

    return None


def upsert_job(db: Session, source_id: int, scraped_job: ScrapedJob, seen_ids: set[str]) -> tuple[bool, bool]:
    """Insert or update a job in the database.

    Args:
        db: Database session
        source_id: ID of the scrape source
        scraped_job: Job data from scraper
        seen_ids: Set of external_ids already processed in this scrape (for deduplication)

    Returns:
        (is_new, is_updated) tuple. is_updated is True only if content changed.
    """
    # Skip if we've already seen this job in this scrape run (handles duplicates on same page)
    if scraped_job.external_id in seen_ids:
        return (False, False)
    seen_ids.add(scraped_job.external_id)

    now = datetime.now(timezone.utc)

    # Check if job already exists
    existing_job = db.query(Job).filter(Job.external_id == scraped_job.external_id).first()

    if existing_job:
        # Track if any content actually changed
        content_changed = False

        # Update mutable fields if they changed
        if scraped_job.title and existing_job.title != scraped_job.title:
            existing_job.title = scraped_job.title
            content_changed = True
        if scraped_job.organization and existing_job.organization != scraped_job.organization:
            existing_job.organization = scraped_job.organization
            content_changed = True
        if scraped_job.location and existing_job.location != scraped_job.location:
            existing_job.location = scraped_job.location
            content_changed = True
        if scraped_job.state and existing_job.state != scraped_job.state:
            existing_job.state = scraped_job.state
            content_changed = True
        if scraped_job.description and existing_job.description != scraped_job.description:
            existing_job.description = scraped_job.description
            content_changed = True
        if scraped_job.job_type and existing_job.job_type != scraped_job.job_type:
            existing_job.job_type = scraped_job.job_type
            content_changed = True
        if scraped_job.salary_info and existing_job.salary_info != scraped_job.salary_info:
            existing_job.salary_info = scraped_job.salary_info
            content_changed = True
        if scraped_job.url and existing_job.url != scraped_job.url:
            existing_job.url = scraped_job.url
            content_changed = True

        # Always update last_seen_at and un-stale
        existing_job.last_seen_at = now
        if existing_job.is_stale:
            existing_job.is_stale = False
            content_changed = True  # Count un-staling as a change

        return (False, content_changed)
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
        # Flush immediately to make the job visible to subsequent queries
        # and catch unique constraint violations early
        db.flush()
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
            errors=[f"Unknown scraper class: {source.scraper_class}. "
                    "Ensure the scraper is decorated with @register_scraper and imported in scraper/sources/__init__.py"],
            duration_seconds=0,
        )

    jobs_new = 0
    jobs_updated = 0
    jobs_unchanged = 0
    all_errors: list[str] = []

    # Track seen external_ids to handle duplicates within same scrape
    seen_ids: set[str] = set()

    try:
        with scraper_class() as scraper:
            scraped_jobs, errors = scraper.run()
            all_errors.extend(errors)

            for scraped_job in scraped_jobs:
                try:
                    is_new, is_updated = upsert_job(db, source.id, scraped_job, seen_ids)
                    if is_new:
                        jobs_new += 1
                    elif is_updated:
                        jobs_updated += 1
                    else:
                        jobs_unchanged += 1
                except Exception as e:
                    all_errors.append(f"Failed to upsert job {scraped_job.external_id}: {e}")

            # Update source's last_scraped_at
            source.last_scraped_at = datetime.now(timezone.utc)

    except Exception as e:
        all_errors.append(f"Scraper execution failed: {e}")

    duration = time.time() - start_time

    logger.info(
        f"[{source.name}] Scrape complete: {jobs_new} new, {jobs_updated} updated, "
        f"{jobs_unchanged} unchanged, {len(all_errors)} errors in {duration:.1f}s"
    )

    return ScrapeResult(
        source_name=source.name,
        jobs_found=jobs_new + jobs_updated + jobs_unchanged,
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
