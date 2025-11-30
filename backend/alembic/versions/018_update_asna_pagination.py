"""Update ASNA scraper to use paginated fetch

ASNA's EnterTimeOnline careers page uses JavaScript-based pagination
(clicking buttons instead of URL navigation). This update uses the
new fetch_all_pages function to get all pages in a single browser session.

Revision ID: 018
Revises: 017
Create Date: 2025-11-29

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None

ASNA_SCRAPER_CODE = '''class ASNAScraper(BaseScraper):
    """Scraper for Arctic Slope Native Association (ASNA) careers.

    ASNA uses EnterTimeOnline (UKG/Kronos) which is a JavaScript SPA.
    Jobs are listed with pagination that requires clicking buttons.
    """

    @property
    def source_name(self) -> str:
        return "Arctic Slope Native Association (ASNA)"

    @property
    def base_url(self) -> str:
        return "https://secure5.entertimeonline.com"

    def get_job_listing_urls(self) -> list:
        return ["https://secure5.entertimeonline.com/ta/ACG00014.careers?CareersSearch=&lang=en-US"]

    def parse_job_listing_page(self, soup, url):
        """Parse jobs from a single page of results."""
        jobs = []
        containers = soup.select(".c-jobs-list__item")

        for container in containers:
            title_elem = container.select_one(".c-job-header__name .c-link")
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            if not title:
                continue

            # Extract location
            loc_elem = container.select_one(".c-job-details__filters-location")
            location = loc_elem.get_text(strip=True) if loc_elem else "Utqiagvik, AK"

            # Extract job type
            type_elem = container.select_one(".c-job-details__salary-expectation-type")
            job_type = type_elem.get_text(strip=True) if type_elem else None

            # Extract salary
            salary_elem = container.select_one(".c-job-details__salary-expectation")
            salary = salary_elem.get_text(strip=True) if salary_elem else None

            # Extract description
            desc_elem = container.select_one(".c-jobs-list__item-desc")
            description = desc_elem.get_text(strip=True) if desc_elem else None

            # Generate unique ID from title (no unique URLs on this site)
            external_id = self.generate_external_id(f"ASNA:{title}")

            job = ScrapedJob(
                external_id=external_id,
                title=title,
                url=url,  # Link to listing page
                organization="Arctic Slope Native Association",
                location=location,
                state="AK",
                job_type=job_type,
                salary_info=salary,
                description=description,
            )
            jobs.append(job)

        return jobs

    def run(self):
        """Run scraper with paginated fetch for all pages."""
        from scraper.playwright_fetcher import fetch_all_pages

        all_jobs = []
        errors = []

        if not self.check_robots():
            errors.append("Failed to load robots.txt")

        listing_url = self.get_job_listing_urls()[0]

        # Fetch all pages in a single browser session
        # The Next Page button selector - must not be disabled
        next_page_selector = "button[aria-label=\\"Next Page\\"]:not([disabled])"

        pages = fetch_all_pages(
            url=listing_url,
            next_page_selector=next_page_selector,
            wait_for=".c-jobs-list__item",
            max_pages=10
        )

        if not pages:
            errors.append("Failed to fetch any pages")
            return all_jobs, errors

        # Parse jobs from each page
        for i, soup in enumerate(pages):
            page_jobs = self.parse_job_listing_page(soup, listing_url)
            all_jobs.extend(page_jobs)

        return all_jobs, errors
'''


def upgrade() -> None:
    # Update ASNA source to use paginated DynamicScraper
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE scrape_sources
            SET
                scraper_class = 'DynamicScraper',
                custom_scraper_code = :code,
                use_playwright = 1,
                skip_robots_check = 1,
                is_active = 0,
                needs_configuration = 1
            WHERE name LIKE '%Arctic Slope Native Association%'
               OR listing_url LIKE '%ACG00014%'
        """),
        {"code": ASNA_SCRAPER_CODE}
    )


def downgrade() -> None:
    # Revert to GenericScraper without custom code
    op.execute("""
        UPDATE scrape_sources
        SET
            scraper_class = 'GenericScraper',
            custom_scraper_code = NULL
        WHERE name LIKE '%Arctic Slope Native Association%'
           OR listing_url LIKE '%ACG00014%'
    """)
