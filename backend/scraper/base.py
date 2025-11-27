import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from scraper.robots import RobotsChecker, USER_AGENT

logger = logging.getLogger(__name__)


@dataclass
class ScrapedJob:
    """Represents a job scraped from a source."""
    external_id: str
    title: str
    url: str
    organization: str | None = None
    location: str | None = None
    state: str | None = None
    description: str | None = None
    job_type: str | None = None
    salary_info: str | None = None


@dataclass
class ScrapeResult:
    """Result of a scrape run."""
    source_name: str
    jobs_found: int
    jobs_new: int
    jobs_updated: int
    errors: list[str]
    duration_seconds: float


class BaseScraper(ABC):
    """Base class for all job scrapers.

    Subclasses must implement:
    - source_name: str property
    - base_url: str property
    - get_job_listings_urls(): list of URLs to scrape for job listings
    - parse_job_listing_page(soup, url): parse a listing page and yield ScrapedJob objects
    """

    def __init__(self):
        self.robots_checker: RobotsChecker | None = None
        # Use browser-like headers to avoid WAF blocks
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.client = httpx.Client(
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
        )

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name for this source."""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL of the website being scraped."""
        pass

    @abstractmethod
    def get_job_listing_urls(self) -> list[str]:
        """Return list of URLs that contain job listings to scrape."""
        pass

    @abstractmethod
    def parse_job_listing_page(self, soup: BeautifulSoup, url: str) -> list[ScrapedJob]:
        """Parse a job listing page and return list of ScrapedJob objects."""
        pass

    def generate_external_id(self, url: str) -> str:
        """Generate a unique external ID for a job based on its URL."""
        return hashlib.sha256(url.encode()).hexdigest()[:32]

    def check_robots(self) -> bool:
        """Initialize and check robots.txt compliance."""
        self.robots_checker = RobotsChecker(self.base_url)
        return self.robots_checker.load()

    def can_fetch(self, url: str) -> bool:
        """Check if a URL can be fetched according to robots.txt."""
        if self.robots_checker is None:
            self.check_robots()
        return self.robots_checker.can_fetch(url)

    def get_crawl_delay(self) -> float:
        """Get crawl delay from robots.txt or default."""
        if self.robots_checker is None:
            return 1.0
        return self.robots_checker.get_crawl_delay()

    def fetch_page(self, url: str) -> BeautifulSoup | None:
        """Fetch a page and return parsed BeautifulSoup, or None on error."""
        if not self.can_fetch(url):
            logger.warning(f"robots.txt disallows fetching: {url}")
            return None

        try:
            response = self.client.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def run(self) -> tuple[list[ScrapedJob], list[str]]:
        """Run the scraper and return (jobs, errors)."""
        jobs: list[ScrapedJob] = []
        errors: list[str] = []

        # Check robots.txt
        if not self.check_robots():
            errors.append(f"Failed to load robots.txt for {self.base_url}")
            # Continue anyway but log the warning

        crawl_delay = self.get_crawl_delay()
        listing_urls = self.get_job_listing_urls()

        logger.info(f"Starting scrape of {self.source_name} ({len(listing_urls)} listing URLs)")

        for i, url in enumerate(listing_urls):
            if i > 0:
                time.sleep(crawl_delay)

            soup = self.fetch_page(url)
            if soup is None:
                errors.append(f"Failed to fetch {url}")
                continue

            try:
                page_jobs = self.parse_job_listing_page(soup, url)
                jobs.extend(page_jobs)
                logger.info(f"Found {len(page_jobs)} jobs on {url}")
            except Exception as e:
                error_msg = f"Error parsing {url}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info(f"Scrape of {self.source_name} complete: {len(jobs)} jobs found")
        return jobs, errors

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
