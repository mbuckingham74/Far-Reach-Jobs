import importlib
import json
import logging
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

from sqlalchemy.orm import Session
from bs4 import BeautifulSoup

from app.models import Job, ScrapeSource, ScrapeLog
from scraper.base import BaseScraper, ScrapedJob, ScrapeResult
from scraper.playwright_fetcher import get_playwright_fetcher

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


def create_dynamic_scraper(source: ScrapeSource) -> type[BaseScraper] | None:
    """Dynamically compile and return a scraper class from custom_scraper_code.

    Args:
        source: ScrapeSource with custom_scraper_code field populated

    Returns:
        A scraper class ready to instantiate, or None if compilation fails
    """
    if not source.custom_scraper_code:
        logger.error(f"No custom_scraper_code for source {source.name}")
        return None

    # Create a namespace with all the imports the generated code might need
    namespace = {
        "BaseScraper": BaseScraper,
        "ScrapedJob": ScrapedJob,
        "BeautifulSoup": BeautifulSoup,
        "urljoin": urljoin,
        # Common imports the AI might use
        "re": __import__("re"),
        "json": __import__("json"),
    }

    try:
        # Compile and execute the code in our namespace
        exec(source.custom_scraper_code, namespace)

        # Find the scraper class (should be the only class inheriting from BaseScraper)
        scraper_class = None
        for name, obj in namespace.items():
            if (isinstance(obj, type) and
                issubclass(obj, BaseScraper) and
                obj is not BaseScraper):
                scraper_class = obj
                break

        if scraper_class is None:
            logger.error(f"No BaseScraper subclass found in custom code for {source.name}")
            return None

        logger.info(f"Successfully compiled dynamic scraper {scraper_class.__name__} for {source.name}")
        return scraper_class

    except SyntaxError as e:
        logger.error(f"Syntax error in custom scraper code for {source.name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to compile custom scraper for {source.name}: {e}")
        return None


def upsert_job(db: Session, source_id: int, scraped_job: ScrapedJob) -> tuple[bool, bool]:
    """Insert or update a job in the database.

    Args:
        db: Database session
        source_id: ID of the scrape source
        scraped_job: Job data from scraper

    Returns:
        (is_new, is_updated) tuple. is_updated is True only if content changed.

    Note: Caller is responsible for deduplication via seen_ids before calling.
    """
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


def log_scrape_result(
    db: Session,
    source: ScrapeSource,
    result: ScrapeResult,
    trigger_type: str,
    started_at: datetime,
) -> ScrapeLog:
    """Log a scrape result to the database."""
    log = ScrapeLog(
        source_id=source.id,
        source_name=source.name,
        trigger_type=trigger_type,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        duration_seconds=int(result.duration_seconds),
        success=len(result.errors) == 0,
        jobs_found=result.jobs_found,
        jobs_added=result.jobs_new,
        jobs_updated=result.jobs_updated,
        jobs_removed=0,  # TODO: track when stale jobs are cleaned up
        errors=json.dumps(result.errors) if result.errors else None,
    )
    db.add(log)
    return log


def get_source_config(source: ScrapeSource) -> dict:
    """Extract configuration dictionary from a ScrapeSource model."""
    return {
        "name": source.name,
        "base_url": source.base_url,
        "listing_url": source.listing_url,
        "selector_job_container": source.selector_job_container,
        "selector_title": source.selector_title,
        "selector_url": source.selector_url,
        "selector_organization": source.selector_organization,
        "selector_location": source.selector_location,
        "selector_job_type": source.selector_job_type,
        "selector_salary": source.selector_salary,
        "selector_description": source.selector_description,
        "url_attribute": source.url_attribute,
        "selector_next_page": source.selector_next_page,
        "max_pages": source.max_pages,
        # Always use Playwright - overhead is minimal vs failing on JS sites
        "use_playwright": True,
        "default_location": source.default_location,
    }


def run_scraper(db: Session, source: ScrapeSource, trigger_type: str = "manual") -> ScrapeResult:
    """Run a single scraper and upsert jobs to database."""
    start_time = time.time()
    started_at = datetime.now(timezone.utc)

    # Handle DynamicScraper - compile from custom_scraper_code
    if source.scraper_class == "DynamicScraper":
        scraper_class = create_dynamic_scraper(source)
        if scraper_class is None:
            source.last_scraped_at = datetime.now(timezone.utc)
            source.last_scrape_success = False
            result = ScrapeResult(
                source_name=source.name,
                jobs_found=0,
                jobs_new=0,
                jobs_updated=0,
                errors=["Failed to compile custom scraper code. Check logs for details."],
                duration_seconds=0,
            )
            log_scrape_result(db, source, result, trigger_type, started_at)
            return result
    else:
        # Get the scraper class from registry
        scraper_class = get_scraper_class(source.scraper_class)

    if scraper_class is None:
        # Mark source as failed before returning
        source.last_scraped_at = datetime.now(timezone.utc)
        source.last_scrape_success = False
        result = ScrapeResult(
            source_name=source.name,
            jobs_found=0,
            jobs_new=0,
            jobs_updated=0,
            errors=[f"Unknown scraper class: {source.scraper_class}. "
                    "Ensure the scraper is decorated with @register_scraper and imported in scraper/sources/__init__.py"],
            duration_seconds=0,
        )
        log_scrape_result(db, source, result, trigger_type, started_at)
        return result

    jobs_new = 0
    jobs_updated = 0
    jobs_unchanged = 0
    all_errors: list[str] = []

    # Track seen external_ids to handle duplicates within same scrape
    seen_ids: set[str] = set()

    # Prepare scraper configuration for GenericScraper
    source_config = get_source_config(source)

    try:
        # GenericScraper needs configuration, others use default constructor
        if source.scraper_class == "GenericScraper":
            scraper_instance = scraper_class(source_config=source_config)
        else:
            scraper_instance = scraper_class()

        # DynamicScraper (custom AI-generated) always uses Playwright
        # These scrapers exist because the site needs JS rendering
        if source.scraper_class == "DynamicScraper":
            scraper_instance._use_playwright = True
            scraper_instance._playwright_fetcher = get_playwright_fetcher()

        with scraper_instance as scraper:
            scraped_jobs, errors = scraper.run()
            all_errors.extend(errors)

            for scraped_job in scraped_jobs:
                # Dedup check before savepoint - skip jobs we've already processed
                if scraped_job.external_id in seen_ids:
                    continue
                seen_ids.add(scraped_job.external_id)

                # Use savepoint so failures only roll back this job, not prior successful ones
                try:
                    with db.begin_nested():
                        is_new, is_updated = upsert_job(db, source.id, scraped_job)
                        # Savepoint auto-commits on successful exit
                    if is_new:
                        jobs_new += 1
                    elif is_updated:
                        jobs_updated += 1
                    else:
                        jobs_unchanged += 1
                except Exception as e:
                    # Savepoint was rolled back, main transaction intact
                    # Remove from seen_ids since the job wasn't actually persisted
                    seen_ids.discard(scraped_job.external_id)
                    logger.error(f"Failed to upsert job {scraped_job.external_id}: {e}")
                    all_errors.append(f"Failed to upsert job {scraped_job.external_id}")

            # Update source's last_scraped_at
            source.last_scraped_at = datetime.now(timezone.utc)

    except Exception as e:
        all_errors.append(f"Scraper execution failed: {e}")

    # Update source's last_scrape_success status
    source.last_scrape_success = len(all_errors) == 0

    duration = time.time() - start_time

    logger.info(
        f"[{source.name}] Scrape complete: {jobs_new} new, {jobs_updated} updated, "
        f"{jobs_unchanged} unchanged, {len(all_errors)} errors in {duration:.1f}s"
    )

    result = ScrapeResult(
        source_name=source.name,
        jobs_found=jobs_new + jobs_updated + jobs_unchanged,
        jobs_new=jobs_new,
        jobs_updated=jobs_updated,
        errors=all_errors,
        duration_seconds=duration,
    )

    # Log the result to the database
    log_scrape_result(db, source, result, trigger_type, started_at)

    return result


def run_all_scrapers(
    db: Session, sources: list[ScrapeSource], trigger_type: str = "manual"
) -> list[ScrapeResult]:
    """Run all scrapers for the given sources.

    Each source is committed independently so failures in one source
    don't roll back successful jobs from other sources.
    """
    results = []
    for source in sources:
        logger.info(f"Running scraper for {source.name}...")
        started_at = datetime.now(timezone.utc)
        try:
            result = run_scraper(db, source, trigger_type)
            # Commit after each source to isolate transactions
            db.commit()
        except Exception as e:
            # If something catastrophic happens, rollback this source and continue
            logger.error(f"Scraper for {source.name} failed catastrophically: {e}")
            db.rollback()
            result = ScrapeResult(
                source_name=source.name,
                jobs_found=0,
                jobs_new=0,
                jobs_updated=0,
                errors=[f"Scraper failed: {type(e).__name__}"],
                duration_seconds=0,
            )
            # Log the failure to scrape history (session is clean after rollback)
            try:
                # Mark source as failed
                source.last_scraped_at = datetime.now(timezone.utc)
                source.last_scrape_success = False
                log_scrape_result(db, source, result, trigger_type, started_at)
                db.commit()
            except Exception as log_error:
                logger.error(f"Failed to log scrape failure for {source.name}: {log_error}")
                db.rollback()
        results.append(result)
    return results
