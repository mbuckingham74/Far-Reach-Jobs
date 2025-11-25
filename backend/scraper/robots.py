import logging
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "FarReachJobsBot/1.0 (+https://far-reach-jobs.tachyonfuture.com)"


class RobotsChecker:
    """Check robots.txt compliance for a given domain."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.parser = RobotFileParser()
        self.crawl_delay: float | None = None
        self._loaded = False

    def load(self) -> bool:
        """Fetch and parse robots.txt. Returns True if successful."""
        robots_url = urljoin(self.base_url, "/robots.txt")
        try:
            response = httpx.get(
                robots_url,
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
                follow_redirects=True,
            )
            if response.status_code == 200:
                self.parser.parse(response.text.splitlines())
                self._loaded = True
                # Try to get crawl delay
                self.crawl_delay = self.parser.crawl_delay(USER_AGENT)
                logger.info(f"Loaded robots.txt from {robots_url}")
                return True
            elif response.status_code == 404:
                # No robots.txt = all allowed
                self._loaded = True
                logger.info(f"No robots.txt found at {robots_url}, all paths allowed")
                return True
            else:
                logger.warning(f"Unexpected status {response.status_code} for {robots_url}")
                return False
        except Exception as e:
            logger.error(f"Failed to fetch robots.txt from {robots_url}: {e}")
            return False

    def can_fetch(self, url: str) -> bool:
        """Check if the given URL can be fetched according to robots.txt."""
        if not self._loaded:
            if not self.load():
                # If we can't load robots.txt, be conservative and allow
                logger.warning("Could not load robots.txt, allowing fetch by default")
                return True

        return self.parser.can_fetch(USER_AGENT, url)

    def get_crawl_delay(self) -> float:
        """Get the crawl delay in seconds. Returns 1.0 if not specified."""
        if self.crawl_delay is not None:
            return self.crawl_delay
        return 1.0  # Default 1 second between requests
