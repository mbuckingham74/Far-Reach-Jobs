"""Playwright fetcher - calls the playwright-service to fetch pages with a real browser."""
import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings

logger = logging.getLogger(__name__)


class PlaywrightFetcher:
    """Fetches pages using the Playwright service (headless browser)."""

    def __init__(self, timeout: int = 30000):
        """Initialize the fetcher.

        Args:
            timeout: Page load timeout in milliseconds (default 30s)
        """
        self.timeout = timeout
        self.settings = get_settings()

    @property
    def is_available(self) -> bool:
        """Check if Playwright service is configured."""
        return bool(self.settings.playwright_service_url)

    def fetch(
        self,
        url: str,
        wait_for: Optional[str] = None,
        select_actions: Optional[list[dict]] = None,
        click_selector: Optional[str] = None,
        click_wait_for: Optional[str] = None,
    ) -> Optional[BeautifulSoup]:
        """Fetch a page using the Playwright service.

        Args:
            url: URL to fetch
            wait_for: Optional CSS selector to wait for before returning
            select_actions: Optional list of {selector, value} dicts for dropdown selection
            click_selector: Optional CSS selector to click after page loads
            click_wait_for: Optional CSS selector to wait for after clicking

        Returns:
            BeautifulSoup object or None on error
        """
        if not self.is_available:
            logger.warning("Playwright service not configured (PLAYWRIGHT_SERVICE_URL not set)")
            return None

        service_url = f"{self.settings.playwright_service_url}/fetch"

        try:
            logger.info(f"Fetching with Playwright: {url}")

            payload = {
                "url": url,
                "waitFor": wait_for,
                "timeout": self.timeout,
            }
            if select_actions:
                payload["selectActions"] = select_actions
            if click_selector:
                payload["clickSelector"] = click_selector
            if click_wait_for:
                payload["clickWaitFor"] = click_wait_for

            response = httpx.post(
                service_url,
                json=payload,
                timeout=60.0  # HTTP timeout for the service call
            )

            if response.status_code != 200:
                logger.error(f"Playwright service error: {response.status_code} - {response.text}")
                return None

            data = response.json()

            if not data.get("success"):
                logger.error(f"Playwright fetch failed: {data.get('error', 'Unknown error')}")
                return None

            html = data.get("html", "")
            if not html:
                logger.warning(f"Playwright returned empty HTML for {url}")
                return None

            logger.info(f"Playwright fetch successful: {url} ({len(html)} bytes)")
            return BeautifulSoup(html, "html.parser")

        except httpx.ConnectError:
            logger.error(f"Cannot connect to Playwright service at {service_url}")
            return None
        except httpx.TimeoutException:
            logger.error(f"Playwright service timeout for {url}")
            return None
        except Exception as e:
            logger.error(f"Playwright fetch error for {url}: {e}")
            return None


def get_playwright_fetcher() -> PlaywrightFetcher:
    """Get a PlaywrightFetcher instance."""
    return PlaywrightFetcher()


def fetch_all_pages(
    url: str,
    next_page_selector: str,
    wait_for: Optional[str] = None,
    max_pages: int = 10,
) -> list[BeautifulSoup]:
    """Fetch multiple pages by clicking through pagination in a single browser session.

    This is useful for SPAs where pagination requires clicking buttons rather than
    navigating to new URLs. The browser session is maintained across pages.

    Args:
        url: Initial URL to fetch
        next_page_selector: CSS selector for the "next page" button
        wait_for: Optional CSS selector to wait for on each page
        max_pages: Maximum number of pages to fetch (default 10)

    Returns:
        List of BeautifulSoup objects, one per page
    """
    settings = get_settings()
    if not settings.playwright_service_url:
        logger.warning("Playwright service not configured")
        return []

    service_url = f"{settings.playwright_service_url}/fetch-paginated"

    try:
        logger.info(f"Fetching paginated: {url} (max {max_pages} pages)")

        payload = {
            "url": url,
            "nextPageSelector": next_page_selector,
            "maxPages": max_pages,
            "timeout": 30000,
        }
        if wait_for:
            payload["waitFor"] = wait_for

        response = httpx.post(
            service_url,
            json=payload,
            timeout=120.0  # Longer timeout for multiple pages
        )

        if response.status_code != 200:
            logger.error(f"Playwright service error: {response.status_code} - {response.text}")
            return []

        data = response.json()

        if not data.get("success"):
            logger.error(f"Playwright paginated fetch failed: {data.get('error', 'Unknown error')}")
            return []

        pages = data.get("pages", [])
        logger.info(f"Playwright fetched {len(pages)} pages from {url}")

        # Convert HTML strings to BeautifulSoup objects
        soups = []
        for page_data in pages:
            html = page_data.get("html", "")
            if html:
                soups.append(BeautifulSoup(html, "html.parser"))

        return soups

    except httpx.ConnectError:
        logger.error(f"Cannot connect to Playwright service")
        return []
    except httpx.TimeoutException:
        logger.error(f"Playwright service timeout for paginated fetch")
        return []
    except Exception as e:
        logger.error(f"Playwright paginated fetch error: {e}")
        return []
