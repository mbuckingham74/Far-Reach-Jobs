"""ADP WorkforceNow scraper using their JSON API.

ADP WorkforceNow is a heavy JavaScript SPA that loads job listings via API.
This scraper fetches jobs directly from the API endpoint rather than parsing HTML.
"""

import logging
import re
from urllib.parse import parse_qs, urlparse

import httpx

from scraper.base import BaseScraper, ScrapedJob
from scraper.robots import USER_AGENT

logger = logging.getLogger(__name__)


class ADPWorkforceScraper(BaseScraper):
    """Scraper for ADP WorkforceNow career portals.

    ADP WorkforceNow uses a JSON API to load job listings. The API endpoint is:
    /careercenter/public/events/staffing/v1/job-requisitions

    Required parameters extracted from the listing URL:
    - cid: Company ID (e.g., c3cf205d-9677-4dfd-ab98-87a0f91551f4)
    - ccId: Career Center ID (e.g., 19000101_000001)
    """

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
        self._listing_url = listing_url

        # Extract API parameters from the listing URL
        parsed = urlparse(listing_url)
        params = parse_qs(parsed.query)

        self._cid = params.get("cid", [None])[0]
        self._cc_id = params.get("ccId", [None])[0]

        if not self._cid or not self._cc_id:
            logger.warning(
                f"Could not extract cid/ccId from ADP URL: {listing_url}"
            )

    @property
    def source_name(self) -> str:
        return self._source_name

    @property
    def base_url(self) -> str:
        return self._base_url

    def _get_api_url(self) -> str:
        """Build the API URL for fetching job requisitions."""
        return (
            f"https://workforcenow.adp.com/mascsr/default/careercenter/public/"
            f"events/staffing/v1/job-requisitions"
            f"?cid={self._cid}&ccId={self._cc_id}&lang=en_US"
        )

    def _get_job_detail_url(self, item_id: str) -> str:
        """Build the URL for viewing a specific job posting."""
        return (
            f"https://workforcenow.adp.com/mascsr/default/mdf/recruitment/"
            f"recruitment.html?cid={self._cid}&ccId={self._cc_id}"
            f"&lang=en_US&selectedMenuKey=CareerCenter&jobId={item_id}"
        )

    def get_job_listing_urls(self) -> list[str]:
        """Not used for API-based scraping - return empty list."""
        return []

    def parse_job_listing_page(self, soup, url: str) -> list[ScrapedJob]:
        """Not used for API-based scraping."""
        return []

    def run(self) -> tuple[list[ScrapedJob], list[str]]:
        """Fetch jobs from the ADP API and return parsed results."""
        jobs: list[ScrapedJob] = []
        errors: list[str] = []

        if not self._cid or not self._cc_id:
            errors.append(
                f"Invalid ADP URL - missing cid or ccId parameters: {self._listing_url}"
            )
            return jobs, errors

        api_url = self._get_api_url()
        logger.info(f"Fetching ADP jobs from API: {api_url}")

        try:
            # Use JSON-specific headers for API request
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }

            response = httpx.get(
                api_url,
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
            )
            response.raise_for_status()

            data = response.json()
            requisitions = data.get("jobRequisitions", [])
            logger.info(f"Found {len(requisitions)} job requisitions from ADP API")

            for req in requisitions:
                try:
                    job = self._parse_requisition(req)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Error parsing requisition: {e}")
                    continue

        except httpx.HTTPStatusError as e:
            error_msg = f"ADP API returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Failed to fetch ADP API: {str(e)}"
            logger.exception(error_msg)
            errors.append(error_msg)

        return jobs, errors

    def _parse_requisition(self, req: dict) -> ScrapedJob | None:
        """Parse a single job requisition from the API response."""
        item_id = req.get("itemID")
        title = req.get("requisitionTitle")

        if not item_id or not title:
            return None

        # Build the job URL
        job_url = self._get_job_detail_url(item_id)

        # Extract location from requisitionLocations array
        location = None
        state = None
        locations = req.get("requisitionLocations", [])
        if locations:
            loc = locations[0]
            name_code = loc.get("nameCode", {})
            location = name_code.get("shortName", "").strip()

            # Extract state from address
            address = loc.get("address", {})
            subdivision = address.get("countrySubdivisionLevel1", {})
            state = subdivision.get("codeValue")

            # If location is empty, build from address components
            if not location:
                city = address.get("cityName", "")
                if city and state:
                    location = f"{city}, {state}"

        # Extract job type (Full-Time, Part-Time, etc.)
        job_type = None
        work_level = req.get("workLevelCode", {})
        if work_level:
            job_type = work_level.get("shortName")

        # Extract external job ID from custom fields if available
        external_id = item_id
        custom_fields = req.get("customFieldGroup", {})
        string_fields = custom_fields.get("stringFields", [])
        for field in string_fields:
            if field.get("nameCode", {}).get("codeValue") == "ExternalJobID":
                ext_id = field.get("stringValue")
                if ext_id:
                    external_id = ext_id
                break

        # Generate a stable external ID
        stable_id = self.generate_external_id(f"adp-{self._cid}-{external_id}")

        return ScrapedJob(
            external_id=stable_id,
            title=title,
            url=job_url,
            organization=self._source_name,
            location=location,
            state=state,
            description=None,  # Not available in listing API
            job_type=job_type,
            salary_info=None,  # Not typically exposed in API
        )
