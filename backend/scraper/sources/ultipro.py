"""UltiPro scraper using their JSON API.

UltiPro (now UKG Pro Recruiting) is a JavaScript SPA that loads job listings via API.
This scraper fetches jobs directly from the API endpoint rather than parsing HTML.
"""

import logging
import re
from urllib.parse import urlparse

import httpx

from scraper.base import BaseScraper, ScrapedJob
from scraper.robots import USER_AGENT

logger = logging.getLogger(__name__)


class UltiProScraper(BaseScraper):
    """Scraper for UltiPro career portals.

    UltiPro uses a JSON API to load job listings. The API endpoint is:
    POST /JobBoardView/LoadSearchResults

    URL pattern: https://recruiting2.ultipro.com/{tenant}/JobBoard/{board-id}/
    Example: https://recruiting2.ultipro.com/SOU1048SOFO/JobBoard/c9cedf85-000e-4f7b-b325-fdda3f04c5be/
    """

    # Number of jobs to fetch per request
    PAGE_SIZE = 50

    def __init__(
        self,
        source_name: str,
        base_url: str,
        listing_url: str,
        use_playwright: bool = False,
    ):
        super().__init__(use_playwright=use_playwright)
        self._source_name = source_name
        self._base_url = base_url

        # Extract tenant, board ID, and host from the listing URL
        # Pattern: https://recruiting2.ultipro.com/{tenant}/JobBoard/{board-id}/...
        # User might paste a job detail URL or the board URL - we need to normalize
        parsed = urlparse(listing_url)
        path_parts = [p for p in parsed.path.split("/") if p]

        self._host = parsed.netloc
        self._scheme = parsed.scheme or "https"
        self._tenant = None
        self._board_id = None

        # Find JobBoard in the path and extract tenant (before) and board-id (after)
        for i, part in enumerate(path_parts):
            if part.lower() == "jobboard" and i > 0 and i + 1 < len(path_parts):
                self._tenant = path_parts[i - 1]
                self._board_id = path_parts[i + 1]
                break

        # Build normalized board URL from extracted parts
        if self._tenant and self._board_id:
            self._board_url = (
                f"{self._scheme}://{self._host}/{self._tenant}/JobBoard/{self._board_id}"
            )
        else:
            self._board_url = None
            logger.warning(
                f"Could not extract tenant/board-id from UltiPro URL: {listing_url}"
            )

    @property
    def source_name(self) -> str:
        return self._source_name

    @property
    def base_url(self) -> str:
        return self._base_url

    def _get_api_url(self) -> str:
        """Build the API URL for fetching job listings."""
        return f"{self._board_url}/JobBoardView/LoadSearchResults"

    def _get_job_detail_url(self, job_id: str) -> str:
        """Build the URL for viewing a specific job posting."""
        return f"{self._board_url}/OpportunityDetail?opportunityId={job_id}"

    def get_job_listing_urls(self) -> list[str]:
        """Not used for API-based scraping - return empty list."""
        return []

    def parse_job_listing_page(self, soup, url: str) -> list[ScrapedJob]:
        """Not used for API-based scraping."""
        return []

    def run(self) -> tuple[list[ScrapedJob], list[str]]:
        """Fetch jobs from the UltiPro API and return parsed results."""
        jobs: list[ScrapedJob] = []
        errors: list[str] = []

        if not self._board_url:
            errors.append(
                f"Invalid UltiPro URL - could not extract tenant/board-id. "
                f"Expected pattern: https://recruiting2.ultipro.com/{{tenant}}/JobBoard/{{board-id}}/"
            )
            return jobs, errors

        api_url = self._get_api_url()
        logger.info(f"Fetching UltiPro jobs from API: {api_url}")

        try:
            # Headers for API request
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }

            # Fetch all jobs with pagination
            skip = 0
            total_fetched = 0

            while True:
                # Request body for search
                request_body = {
                    "opportunitySearch": {
                        "Top": self.PAGE_SIZE,
                        "Skip": skip,
                        "QueryString": "",
                        "OrderBy": [
                            {"Value": "postedDateDesc", "PropertyName": "PostedDate"}
                        ],
                    }
                }

                response = httpx.post(
                    api_url,
                    headers=headers,
                    json=request_body,
                    timeout=30.0,
                    follow_redirects=True,
                )
                response.raise_for_status()

                data = response.json()
                opportunities = data.get("opportunities", [])

                if not opportunities:
                    break

                logger.info(
                    f"Fetched {len(opportunities)} jobs from UltiPro API (skip={skip})"
                )

                for opp in opportunities:
                    try:
                        job = self._parse_opportunity(opp)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.warning(f"Error parsing opportunity: {e}")
                        continue

                total_fetched += len(opportunities)

                # Check if we've fetched all jobs
                if len(opportunities) < self.PAGE_SIZE:
                    break

                skip += self.PAGE_SIZE

                # Safety limit to prevent infinite loops
                if skip > 1000:
                    logger.warning("Hit safety limit of 1000 jobs, stopping pagination")
                    break

            logger.info(f"Total jobs fetched from UltiPro: {len(jobs)}")

        except httpx.HTTPStatusError as e:
            error_msg = f"UltiPro API returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Failed to fetch UltiPro API: {str(e)}"
            logger.exception(error_msg)
            errors.append(error_msg)

        return jobs, errors

    def _parse_opportunity(self, opp: dict) -> ScrapedJob | None:
        """Parse a single job opportunity from the API response."""
        job_id = opp.get("Id")
        title = opp.get("Title")

        if not job_id or not title:
            return None

        # Build the job URL
        job_url = self._get_job_detail_url(job_id)

        # Extract location from Locations array
        location = None
        state = None
        locations = opp.get("Locations") or []
        if locations:
            loc = locations[0]
            address = loc.get("Address") or {}
            city = address.get("City", "")

            # State can be a string or an object like {'Code': 'AK', 'Name': 'Alaska'}
            state_value = address.get("State")
            if isinstance(state_value, dict):
                state = state_value.get("Code") or state_value.get("Name", "")
            elif isinstance(state_value, str):
                state = state_value
            else:
                state = ""

            if city and state:
                location = f"{city}, {state}"
            elif city:
                location = city
            elif state:
                location = state

        # Extract job type (Full-Time, Part-Time)
        job_type = None
        if opp.get("FullTime") is True:
            job_type = "Full-Time"
        elif opp.get("FullTime") is False:
            job_type = "Part-Time"

        # Use RequisitionNumber or Id as external identifier
        external_id = opp.get("RequisitionNumber") or job_id

        # Generate a stable external ID
        stable_id = self.generate_external_id(f"ultipro-{self._board_id}-{external_id}")

        # Get description (brief description from listing)
        description = opp.get("BriefDescription")

        return ScrapedJob(
            external_id=stable_id,
            title=title,
            url=job_url,
            organization=self._source_name,
            location=location,
            state=state,
            description=description,
            job_type=job_type,
            salary_info=None,  # Not typically exposed in API
        )
