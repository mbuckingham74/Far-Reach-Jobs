"""GenericScraper - A configurable scraper that uses CSS selectors.

This scraper can be configured via the admin panel to scrape any job listing
page by specifying CSS selectors for job containers and fields.
"""
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.base import BaseScraper, ScrapedJob
from scraper.runner import register_scraper
from scraper.playwright_fetcher import get_playwright_fetcher

logger = logging.getLogger(__name__)


@register_scraper
class GenericScraper(BaseScraper):
    """A configurable scraper that extracts jobs using CSS selectors.

    Unlike other scrapers that have hardcoded parsing logic, GenericScraper
    reads its configuration from the ScrapeSource database record. This allows
    new job sources to be added via the admin panel without writing code.

    Required configuration (set on ScrapeSource):
    - listing_url: URL of the page containing job listings
    - selector_job_container: CSS selector for each job's container element
    - selector_title: CSS selector for job title (within container)
    - selector_url: CSS selector for job link (within container)

    Optional configuration:
    - selector_organization: CSS selector for organization name
    - selector_location: CSS selector for job location
    - selector_job_type: CSS selector for job type
    - selector_salary: CSS selector for salary info
    - selector_description: CSS selector for job description
    - url_attribute: Attribute to extract URL from (default: "href")
    - selector_next_page: CSS selector for pagination next link
    - max_pages: Maximum pages to scrape (default: 10)
    - use_playwright: Use headless browser instead of httpx (for bot-protected sites)
    """

    def __init__(self, source_config: dict | None = None):
        """Initialize with optional source configuration.

        Args:
            source_config: Dictionary of configuration from ScrapeSource model.
                          If None, scraper won't work (requires config).
        """
        super().__init__()
        self.config = source_config or {}
        self._source_name = self.config.get("name", "Generic Source")
        self._base_url = self.config.get("base_url", "")
        self._listing_url = self.config.get("listing_url") or self._base_url
        self._use_playwright = self.config.get("use_playwright", False)
        self._playwright_fetcher = get_playwright_fetcher() if self._use_playwright else None

    @property
    def source_name(self) -> str:
        return self._source_name

    @property
    def base_url(self) -> str:
        return self._base_url

    def get_job_listing_urls(self) -> list[str]:
        """Return the configured listing URL."""
        if not self._listing_url:
            return []
        return [self._listing_url]

    def _fetch_page(self, url: str, wait_for: str | None = None) -> BeautifulSoup | None:
        """Fetch a page using either Playwright or httpx.

        Args:
            url: URL to fetch
            wait_for: CSS selector to wait for (Playwright only)

        Returns:
            BeautifulSoup object or None on error
        """
        # Always check robots.txt compliance first
        if not self.can_fetch(url):
            logger.warning(f"robots.txt disallows fetching: {url}")
            return None

        if self._use_playwright and self._playwright_fetcher:
            if self._playwright_fetcher.is_available:
                logger.info(f"Using Playwright to fetch: {url}")
                result = self._playwright_fetcher.fetch(url, wait_for=wait_for)
                if result is not None:
                    return result
                # Playwright failed, fall back to httpx
                logger.warning(f"Playwright fetch failed for {url}, falling back to httpx")

        # Use standard httpx fetch (skip robots check since we already did it)
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def _extract_text(self, container: BeautifulSoup, selector: str | None) -> str | None:
        """Extract text content using a CSS selector."""
        if not selector:
            return None
        element = container.select_one(selector)
        if element:
            return element.get_text(strip=True)
        return None

    def _extract_url(self, container: BeautifulSoup, selector: str | None, page_url: str) -> str | None:
        """Extract URL from an element's attribute.

        Args:
            container: BeautifulSoup element containing the job
            selector: CSS selector for the URL element
            page_url: Current page URL for resolving relative links
        """
        if not selector:
            return None
        element = container.select_one(selector)
        if element:
            attr = self.config.get("url_attribute", "href") or "href"
            url = element.get(attr)
            if url:
                # Make URL absolute relative to the current page URL
                # This correctly handles ./job/123 and ../job/123 paths
                return urljoin(page_url, url)
        return None

    def parse_job_listing_page(self, soup: BeautifulSoup, url: str) -> list[ScrapedJob]:
        """Parse jobs from a listing page using configured CSS selectors."""
        jobs = []

        container_selector = self.config.get("selector_job_container")
        if not container_selector:
            logger.error(f"No job container selector configured for {self.source_name}")
            return jobs

        containers = soup.select(container_selector)
        logger.info(f"Found {len(containers)} job containers on {url}")

        for container in containers:
            # Extract required fields
            title = self._extract_text(container, self.config.get("selector_title"))
            job_url = self._extract_url(container, self.config.get("selector_url"), url)

            if not title:
                logger.debug("Skipping container - no title found")
                continue

            # Generate external ID from URL or title
            if job_url:
                external_id = self.generate_external_id(job_url)
            else:
                external_id = self.generate_external_id(f"{self.source_name}:{title}")

            # Extract optional fields
            # Use scraped location, falling back to source's default_location if not found
            location = self._extract_text(container, self.config.get("selector_location"))
            if not location:
                location = self.config.get("default_location")

            job = ScrapedJob(
                external_id=external_id,
                title=title,
                url=job_url or url,  # Fallback to listing page URL
                organization=self._extract_text(container, self.config.get("selector_organization")),
                location=location,
                job_type=self._extract_text(container, self.config.get("selector_job_type")),
                salary_info=self._extract_text(container, self.config.get("selector_salary")),
                description=self._extract_text(container, self.config.get("selector_description")),
            )
            jobs.append(job)

        return jobs

    def run(self) -> tuple[list[ScrapedJob], list[str]]:
        """Run the scraper with pagination support."""
        if not self.config:
            return [], ["GenericScraper requires configuration. Set CSS selectors in the admin panel."]

        if not self._listing_url:
            return [], [f"No listing URL configured for {self.source_name}"]

        container_selector = self.config.get("selector_job_container")
        if not container_selector:
            return [], [f"No job container selector configured for {self.source_name}"]

        all_jobs: list[ScrapedJob] = []
        errors: list[str] = []

        # Check robots.txt
        if not self.check_robots():
            errors.append(f"Failed to load robots.txt for {self.base_url}")
            # Continue anyway but log the warning

        crawl_delay = self.get_crawl_delay()
        max_pages = self.config.get("max_pages", 10) or 10
        next_page_selector = self.config.get("selector_next_page")

        current_url = self._listing_url
        pages_scraped = 0

        while current_url and pages_scraped < max_pages:
            if pages_scraped > 0:
                import time
                time.sleep(crawl_delay)

            logger.info(f"Scraping page {pages_scraped + 1}: {current_url}")

            # Wait for job container selector when using Playwright
            wait_for = container_selector if self._use_playwright else None
            soup = self._fetch_page(current_url, wait_for=wait_for)
            if soup is None:
                errors.append(f"Failed to fetch {current_url}")
                break

            try:
                page_jobs = self.parse_job_listing_page(soup, current_url)
                all_jobs.extend(page_jobs)
                logger.info(f"Found {len(page_jobs)} jobs on page {pages_scraped + 1}")
            except Exception as e:
                error_msg = f"Error parsing {current_url}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                break

            pages_scraped += 1

            # Check for next page
            if next_page_selector and pages_scraped < max_pages:
                next_link = soup.select_one(next_page_selector)
                if next_link:
                    next_url = next_link.get("href")
                    if next_url:
                        current_url = urljoin(current_url, next_url)
                    else:
                        break
                else:
                    break
            else:
                break

        logger.info(f"Scrape of {self.source_name} complete: {len(all_jobs)} jobs found across {pages_scraped} pages")
        return all_jobs, errors
