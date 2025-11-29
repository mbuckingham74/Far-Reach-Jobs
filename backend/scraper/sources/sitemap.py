"""SitemapScraper - Extracts jobs from XML sitemaps with URL-based filtering.

This scraper is ideal for sites where:
1. Job listings are JavaScript-rendered (hard to scrape directly)
2. A sitemap.xml contains individual job URLs
3. Job data can be extracted from URL structure (title, location)

Example: Alaska Airlines careers site has URLs like:
  /kotzebue-ak/customer-service-agent/873E0B7E718D43CE8180C9246164D91E/job/

From this URL we can extract:
  - Location: "Kotzebue, AK"
  - Title: "Customer Service Agent"
  - External ID: "873E0B7E718D43CE8180C9246164D91E"
"""
import logging
import re
from typing import Optional
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import httpx

from scraper.base import BaseScraper, ScrapedJob
from scraper.runner import register_scraper

logger = logging.getLogger(__name__)

# US state abbreviations for parsing
US_STATES = {
    'al': 'AL', 'ak': 'AK', 'az': 'AZ', 'ar': 'AR', 'ca': 'CA',
    'co': 'CO', 'ct': 'CT', 'de': 'DE', 'fl': 'FL', 'ga': 'GA',
    'hi': 'HI', 'id': 'ID', 'il': 'IL', 'in': 'IN', 'ia': 'IA',
    'ks': 'KS', 'ky': 'KY', 'la': 'LA', 'me': 'ME', 'md': 'MD',
    'ma': 'MA', 'mi': 'MI', 'mn': 'MN', 'ms': 'MS', 'mo': 'MO',
    'mt': 'MT', 'ne': 'NE', 'nv': 'NV', 'nh': 'NH', 'nj': 'NJ',
    'nm': 'NM', 'ny': 'NY', 'nc': 'NC', 'nd': 'ND', 'oh': 'OH',
    'ok': 'OK', 'or': 'OR', 'pa': 'PA', 'ri': 'RI', 'sc': 'SC',
    'sd': 'SD', 'tn': 'TN', 'tx': 'TX', 'ut': 'UT', 'vt': 'VT',
    'va': 'VA', 'wa': 'WA', 'wv': 'WV', 'wi': 'WI', 'wy': 'WY',
    'dc': 'DC',
}


@register_scraper
class SitemapScraper(BaseScraper):
    """Scraper that extracts jobs from XML sitemaps.

    Configuration (set on ScrapeSource):
    - sitemap_url: URL of the sitemap XML file
    - sitemap_url_pattern: Regex pattern to filter job URLs (e.g., "-ak/" for Alaska)
    - organization: Organization name to use for all jobs
    - default_location: Fallback location if not extractable from URL
    - default_state: Fallback state if not extractable from URL

    URL Parsing:
    The scraper attempts to extract job data from URL structure:
    - Location: Looks for city-state patterns like "kotzebue-ak" or "seattle-wa"
    - Title: Extracts from URL slug and converts to title case
    - External ID: Uses unique portion of URL path
    """

    def __init__(self, source_config: dict | None = None):
        """Initialize with source configuration.

        Args:
            source_config: Dictionary of configuration from ScrapeSource model.
        """
        super().__init__()
        self.config = source_config or {}
        self._source_name = self.config.get("name", "Sitemap Source")
        self._base_url = self.config.get("base_url", "")
        self._sitemap_url = self.config.get("sitemap_url", "")
        self._url_pattern = self.config.get("sitemap_url_pattern", "")
        self._organization = self.config.get("organization") or self._source_name
        self._default_location = self.config.get("default_location")
        self._default_state = self.config.get("default_state")

    @property
    def source_name(self) -> str:
        return self._source_name

    @property
    def base_url(self) -> str:
        return self._base_url

    def get_job_listing_urls(self) -> list[str]:
        """Return the sitemap URL."""
        if self._sitemap_url:
            return [self._sitemap_url]
        return []

    def _fetch_sitemap(self, url: str) -> Optional[str]:
        """Fetch sitemap XML content.

        Args:
            url: Sitemap URL

        Returns:
            XML content as string, or None on error
        """
        try:
            response = self.client.get(url, follow_redirects=True)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch sitemap {url}: {e}")
            return None

    def _parse_sitemap_urls(self, xml_content: str, depth: int = 0) -> tuple[list[str], list[str]]:
        """Parse URLs from sitemap XML.

        Handles both regular sitemaps and sitemap indexes (recursively).

        Args:
            xml_content: Raw XML string
            depth: Current recursion depth (to prevent infinite loops)

        Returns:
            Tuple of (job URLs, errors)
        """
        urls = []
        errors = []
        max_depth = 3  # Prevent infinite recursion

        try:
            # Remove namespace for easier parsing
            xml_content = re.sub(r'\sxmlns="[^"]+"', '', xml_content, count=1)
            root = ET.fromstring(xml_content)

            # Check if this is a sitemap index
            if root.tag == 'sitemapindex':
                if depth >= max_depth:
                    errors.append(f"Sitemap index recursion limit reached (depth {depth})")
                    return urls, errors

                logger.info(f"Sitemap index detected, fetching child sitemaps (depth {depth})")
                child_sitemap_urls = []
                for sitemap in root.findall('.//sitemap/loc'):
                    if sitemap.text:
                        child_sitemap_urls.append(sitemap.text.strip())

                logger.info(f"Found {len(child_sitemap_urls)} child sitemaps")

                # Fetch each child sitemap (with robots.txt check)
                for child_url in child_sitemap_urls:
                    # Check robots.txt before fetching child sitemaps (may be cross-domain)
                    if not self.can_fetch(child_url):
                        logger.warning(f"robots.txt disallows child sitemap: {child_url}")
                        errors.append(f"robots.txt disallows child sitemap: {child_url}")
                        continue

                    logger.info(f"Fetching child sitemap: {child_url}")
                    child_content = self._fetch_sitemap(child_url)
                    if child_content:
                        child_urls, child_errors = self._parse_sitemap_urls(child_content, depth + 1)
                        urls.extend(child_urls)
                        errors.extend(child_errors)
                    else:
                        errors.append(f"Failed to fetch child sitemap: {child_url}")

                return urls, errors

            # Regular sitemap - extract URLs
            for url_elem in root.findall('.//url/loc'):
                if url_elem.text:
                    urls.append(url_elem.text.strip())

        except ET.ParseError as e:
            errors.append(f"Failed to parse sitemap XML: {e}")
            logger.error(f"Failed to parse sitemap XML: {e}")
        except Exception as e:
            errors.append(f"Error processing sitemap: {e}")
            logger.error(f"Error processing sitemap: {e}")

        return urls, errors

    def _filter_urls(self, urls: list[str]) -> list[str]:
        """Filter URLs by configured pattern.

        Args:
            urls: List of URLs to filter

        Returns:
            Filtered list matching the pattern
        """
        if not self._url_pattern:
            return urls

        try:
            pattern = re.compile(self._url_pattern, re.IGNORECASE)
            filtered = [url for url in urls if pattern.search(url)]
            logger.info(f"Filtered {len(urls)} URLs to {len(filtered)} matching pattern '{self._url_pattern}'")
            return filtered
        except re.error as e:
            logger.error(f"Invalid URL filter pattern '{self._url_pattern}': {e}")
            return urls

    def _parse_location_from_url(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """Extract location and state from URL path.

        Looks for patterns like:
        - /kotzebue-ak/... -> ("Kotzebue", "AK")
        - /seattle-wa/... -> ("Seattle", "WA")
        - /new-york-ny/... -> ("New York", "NY")

        Args:
            url: Job URL

        Returns:
            Tuple of (city, state) or (None, None) if not found
        """
        path = urlparse(url).path
        segments = [s for s in path.split('/') if s]

        if not segments:
            return None, None

        # First segment usually contains location
        first_segment = segments[0].lower()

        # Look for state abbreviation at end (e.g., "kotzebue-ak", "new-york-ny")
        for state_abbr in US_STATES:
            if first_segment.endswith(f'-{state_abbr}'):
                city_part = first_segment[:-len(state_abbr)-1]  # Remove "-ak" etc.
                city = city_part.replace('-', ' ').title()
                state = US_STATES[state_abbr]
                return city, state

        return None, None

    def _parse_title_from_url(self, url: str) -> Optional[str]:
        """Extract job title from URL path.

        Looks for title slug in URL path, typically second segment:
        - /kotzebue-ak/customer-service-agent/... -> "Customer Service Agent"

        Args:
            url: Job URL

        Returns:
            Job title or None if not found
        """
        path = urlparse(url).path
        segments = [s for s in path.split('/') if s]

        if len(segments) < 2:
            return None

        # Second segment is typically the title slug
        title_slug = segments[1]

        # Skip if it looks like an ID (all hex or numeric)
        if re.match(r'^[0-9a-fA-F-]+$', title_slug):
            return None

        # Convert slug to title
        title = title_slug.replace('-', ' ').title()
        return title

    def _generate_external_id(self, url: str) -> str:
        """Generate external ID from URL.

        Looks for unique identifier in URL path:
        - /kotzebue-ak/customer-service-agent/873E0B7E.../job/ -> "873E0B7E..."

        Falls back to hashing the URL if no ID found.

        Args:
            url: Job URL

        Returns:
            External ID string
        """
        path = urlparse(url).path
        segments = [s for s in path.split('/') if s and s != 'job']

        # Look for UUID-like segment (common in job portals)
        for segment in segments:
            # Check for UUID or hex ID pattern
            if re.match(r'^[0-9a-fA-F]{20,}$', segment):
                return segment
            if re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', segment):
                return segment

        # Fallback to URL hash
        return self.generate_external_id(url)

    def _parse_job_from_url(self, url: str) -> Optional[ScrapedJob]:
        """Create a ScrapedJob from URL structure.

        Args:
            url: Job URL

        Returns:
            ScrapedJob or None if insufficient data
        """
        title = self._parse_title_from_url(url)
        if not title:
            logger.debug(f"Could not extract title from URL: {url}")
            return None

        city, state = self._parse_location_from_url(url)

        # Build location string
        location = None
        if city and state:
            location = f"{city}, {state}"
        elif city:
            location = city
        elif self._default_location:
            location = self._default_location

        # Use extracted state or default
        final_state = state or self._default_state

        external_id = self._generate_external_id(url)

        return ScrapedJob(
            external_id=external_id,
            title=title,
            url=url,
            organization=self._organization,
            location=location,
            state=final_state,
            job_type=None,  # Not available from URL
            salary_info=None,  # Not available from URL
            description=None,  # Not available from URL
        )

    def parse_job_listing_page(self, soup, url: str) -> list[ScrapedJob]:
        """Not used - SitemapScraper parses URLs directly."""
        return []

    def run(self) -> tuple[list[ScrapedJob], list[str]]:
        """Run the sitemap scraper.

        Returns:
            Tuple of (jobs list, errors list)
        """
        if not self.config:
            return [], ["SitemapScraper requires configuration."]

        if not self._sitemap_url:
            return [], [f"No sitemap URL configured for {self.source_name}"]

        errors: list[str] = []
        jobs: list[ScrapedJob] = []

        # Check robots.txt for sitemap URL
        if not self.check_robots():
            errors.append(f"Failed to load robots.txt for {self.base_url}")

        if not self.can_fetch(self._sitemap_url):
            return [], [f"robots.txt disallows fetching sitemap: {self._sitemap_url}"]

        # Fetch sitemap
        logger.info(f"Fetching sitemap: {self._sitemap_url}")
        xml_content = self._fetch_sitemap(self._sitemap_url)
        if not xml_content:
            return [], [f"Failed to fetch sitemap from {self._sitemap_url}"]

        # Parse URLs from sitemap (handles sitemap indexes recursively)
        all_urls, parse_errors = self._parse_sitemap_urls(xml_content)
        errors.extend(parse_errors)
        logger.info(f"Found {len(all_urls)} URLs in sitemap")

        if not all_urls:
            errors.append(f"No URLs found in sitemap {self._sitemap_url}")
            return [], errors

        # Filter by pattern
        filtered_urls = self._filter_urls(all_urls)

        if not filtered_urls:
            errors.append(f"No URLs matched pattern '{self._url_pattern}' (out of {len(all_urls)} total URLs)")
            return [], errors

        # Parse jobs from URLs
        unparseable_urls = []
        for url in filtered_urls:
            job = self._parse_job_from_url(url)
            if job:
                jobs.append(job)
            else:
                unparseable_urls.append(url)
                logger.debug(f"Could not parse job from URL: {url}")

        # Surface visibility when many URLs fail to parse
        if unparseable_urls:
            parse_rate = len(jobs) / len(filtered_urls) * 100 if filtered_urls else 0
            if len(jobs) == 0:
                # Complete failure - surface first few URLs as examples
                sample_urls = unparseable_urls[:3]
                errors.append(
                    f"Could not parse any jobs from {len(unparseable_urls)} URLs. "
                    f"URL structure may not match expected pattern. "
                    f"Sample URLs: {', '.join(sample_urls)}"
                )
            elif parse_rate < 50:
                # Less than half succeeded - warn
                errors.append(
                    f"Only parsed {len(jobs)}/{len(filtered_urls)} URLs ({parse_rate:.0f}%). "
                    f"Some URLs may have unexpected structure."
                )

        logger.info(f"Parsed {len(jobs)} jobs from {len(filtered_urls)} URLs")
        return jobs, errors
