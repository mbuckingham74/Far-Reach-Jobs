import logging
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

# User-Agent for HTTP requests - avoids naive "Bot" string detection
USER_AGENT = "Mozilla/5.0 (compatible; FarReachJobs/1.0; +https://far-reach-jobs.tachyonfuture.com)"

# User-Agent for robots.txt parsing - must start with bot name for proper rule matching
ROBOTS_USER_AGENT = "FarReachJobs/1.0"


class RobotsChecker:
    """Check robots.txt compliance for a given domain."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.parser = RobotFileParser()
        self.crawl_delay: float | None = None
        self._loaded = False
        self._no_robots = False  # True if site has no robots.txt (all allowed)

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
                # Get crawl delay - check both UAs and use the most restrictive
                delay_bot = self.parser.crawl_delay(ROBOTS_USER_AGENT)
                delay_mozilla = self.parser.crawl_delay("Mozilla")
                delays = [d for d in [delay_bot, delay_mozilla] if d is not None]
                self.crawl_delay = max(delays) if delays else None
                logger.info(f"Loaded robots.txt from {robots_url}")
                return True
            elif response.status_code == 404:
                # No robots.txt = all allowed
                # Parse empty rules so can_fetch returns True
                self.parser.parse([])
                self._loaded = True
                self._no_robots = True
                logger.info(f"No robots.txt found at {robots_url}, all paths allowed")
                return True
            else:
                logger.warning(f"Unexpected status {response.status_code} for {robots_url}")
                return False
        except Exception as e:
            logger.error(f"Failed to fetch robots.txt from {robots_url}: {e}")
            return False

    def can_fetch(self, url: str) -> bool:
        """Check if the given URL can be fetched according to robots.txt.

        Checks both our bot name and Mozilla UA, honoring the most restrictive.
        """
        if not self._loaded:
            if not self.load():
                # If we can't load robots.txt, be conservative and allow
                logger.warning("Could not load robots.txt, allowing fetch by default")
                return True

        # No robots.txt = all allowed
        if self._no_robots:
            return True

        # Check both UAs - if either disallows, we don't fetch
        allowed_bot = self.parser.can_fetch(ROBOTS_USER_AGENT, url)
        allowed_mozilla = self.parser.can_fetch("Mozilla", url)
        return allowed_bot and allowed_mozilla

    def get_crawl_delay(self) -> float:
        """Get the crawl delay in seconds. Returns 1.0 if not specified."""
        if self.crawl_delay is not None:
            return self.crawl_delay
        return 1.0  # Default 1 second between requests
