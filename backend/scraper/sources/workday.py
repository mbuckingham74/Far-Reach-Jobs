"""Workday scraper using their JSON API.

Workday is a JavaScript SPA that loads job listings via API.
This scraper fetches jobs directly from the API endpoint rather than parsing HTML.
"""

import logging
import re
from urllib.parse import urlparse

import httpx

from scraper.base import BaseScraper, ScrapedJob
from scraper.robots import USER_AGENT

logger = logging.getLogger(__name__)


class WorkdayScraper(BaseScraper):
    """Scraper for Workday career portals.

    Workday uses a JSON API to load job listings. The API endpoint is:
    POST /wday/cxs/{tenant}/{site}/jobs

    URL patterns:
    - https://{tenant}.wd1.myworkdayjobs.com/{site}
    - https://{tenant}.wd1.myworkdayjobs.com/{site}?hiringCompany=...

    Examples:
    - https://calistacorp.wd1.myworkdayjobs.com/Calista
    - https://calistacorp.wd1.myworkdayjobs.com/CalistaBrice
    - https://calistacorp.wd1.myworkdayjobs.com/Yulista
    """

    # Number of jobs to fetch per request (Workday max is typically 20)
    PAGE_SIZE = 20

    def __init__(
        self,
        source_name: str,
        base_url: str,
        listing_url: str,
    ):
        super().__init__(use_playwright=False)
        self._source_name = source_name
        self._base_url = base_url

        # Extract tenant and site from the listing URL
        # Pattern: https://{tenant}.wd1.myworkdayjobs.com/{site}?...
        parsed = urlparse(listing_url)
        self._host = parsed.netloc
        self._scheme = parsed.scheme or "https"

        # Extract tenant from host (e.g., "calistacorp" from "calistacorp.wd1.myworkdayjobs.com")
        host_parts = self._host.split(".")
        self._tenant = host_parts[0] if host_parts else None

        # Extract site from path (e.g., "Calista" from "/Calista" or "/Calista?...")
        path_parts = [p for p in parsed.path.split("/") if p]
        self._site = path_parts[0] if path_parts else None

        # Store any query params (like hiringCompany filter)
        self._query = parsed.query

        if self._tenant and self._site:
            self._api_url = (
                f"{self._scheme}://{self._host}/wday/cxs/{self._tenant}/{self._site}/jobs"
            )
            self._job_base_url = f"{self._scheme}://{self._host}/en-US/{self._site}/job"
        else:
            self._api_url = None
            self._job_base_url = None
            logger.warning(
                f"Could not extract tenant/site from Workday URL: {listing_url}"
            )

    @property
    def source_name(self) -> str:
        return self._source_name

    @property
    def base_url(self) -> str:
        return self._base_url

    def get_job_listing_urls(self) -> list[str]:
        """Not used for API-based scraping - return empty list."""
        return []

    def parse_job_listing_page(self, soup, url: str) -> list[ScrapedJob]:
        """Not used for API-based scraping."""
        return []

    def run(self) -> tuple[list[ScrapedJob], list[str]]:
        """Fetch jobs from the Workday API and return parsed results."""
        jobs: list[ScrapedJob] = []
        errors: list[str] = []

        if not self._api_url:
            errors.append(
                f"Invalid Workday URL - could not extract tenant/site. "
                f"Expected pattern: https://{{tenant}}.wd1.myworkdayjobs.com/{{site}}"
            )
            return jobs, errors

        logger.info(f"Fetching Workday jobs from API: {self._api_url}")

        try:
            # Headers for API request
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }

            # Fetch all jobs with pagination
            offset = 0
            total_jobs = None

            while True:
                # Request body for search
                request_body = {
                    "limit": self.PAGE_SIZE,
                    "offset": offset,
                    "searchText": "",
                }

                response = httpx.post(
                    self._api_url,
                    headers=headers,
                    json=request_body,
                    timeout=30.0,
                    follow_redirects=True,
                )
                response.raise_for_status()

                data = response.json()
                total_jobs = data.get("total", 0)
                job_postings = data.get("jobPostings", [])

                if not job_postings:
                    break

                logger.info(
                    f"Fetched {len(job_postings)} jobs from Workday API "
                    f"(offset={offset}, total={total_jobs})"
                )

                for posting in job_postings:
                    try:
                        job = self._parse_job_posting(posting)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.warning(f"Error parsing job posting: {e}")
                        continue

                offset += len(job_postings)

                # Check if we've fetched all jobs
                if offset >= total_jobs:
                    break

                # Safety limit to prevent infinite loops
                if offset > 1000:
                    logger.warning("Hit safety limit of 1000 jobs, stopping pagination")
                    break

            logger.info(f"Total jobs fetched from Workday: {len(jobs)}")

        except httpx.HTTPStatusError as e:
            error_msg = f"Workday API returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Failed to fetch Workday API: {str(e)}"
            logger.exception(error_msg)
            errors.append(error_msg)

        return jobs, errors

    def _parse_job_posting(self, posting: dict) -> ScrapedJob | None:
        """Parse a single job posting from the API response."""
        title = posting.get("title")
        external_path = posting.get("externalPath")

        if not title or not external_path:
            return None

        # Build the full job URL
        # externalPath is like "/job/Anchorage-AK/Billing-Specialist_JR107856"
        job_url = f"{self._scheme}://{self._host}/en-US/{self._site}{external_path}"

        # Extract job ID from the path (e.g., "JR107856" from "Billing-Specialist_JR107856")
        job_id_match = re.search(r"_([A-Z0-9]+(?:-\d+)?)$", external_path)
        job_id = job_id_match.group(1) if job_id_match else external_path

        # Generate stable external ID
        stable_id = self.generate_external_id(f"workday-{self._tenant}-{self._site}-{job_id}")

        # Extract location from locationsText
        # Examples: "Anchorage, AK", "2 Locations", "ALAS - Alaska State Wide"
        location_text = posting.get("locationsText", "")
        location = None
        state = None

        if location_text and not re.match(r"^\d+ Locations?$", location_text):
            location = location_text
            # Try to extract state from "City, ST" pattern
            state_match = re.search(r",\s*([A-Z]{2})$", location)
            if state_match:
                state = state_match.group(1)

        # Extract organization from bulletFields if available
        # bulletFields is typically ["Company Name", "Job ID"]
        organization = None
        bullet_fields = posting.get("bulletFields", [])
        if bullet_fields:
            organization = bullet_fields[0]

        return ScrapedJob(
            external_id=stable_id,
            title=title,
            url=job_url,
            organization=organization,
            location=location,
            state=state,
            description=None,  # Brief description not in list API
            job_type=None,  # Not typically in list API
            salary_info=None,
        )
