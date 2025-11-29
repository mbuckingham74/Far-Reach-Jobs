"""Fix TCC location data - remove 'USVacancy Locations' suffix

Revision ID: 013
Revises: 012
Create Date: 2025-11-28
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None

# Updated custom scraper code with location cleaning
UPDATED_TCC_SCRAPER_CODE = '''class TananaChiefsScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "Tanana Chiefs Conference (TCC) - Interior villages"

    @property
    def base_url(self) -> str:
        return "https://careers.tananachiefs.org/OA_HTML/OA.jsp?OAFunc=TCC_IRC_ALL_JOBS"

    def get_job_listing_urls(self) -> list[str]:
        return [self.base_url]

    def _clean_location(self, location: str | None) -> str | None:
        """Clean location text by removing extraneous suffixes."""
        if not location:
            return None
        import re
        cleaned = location.strip()
        # Remove Oracle-specific suffixes
        patterns = [
            r",?\\s*USVacancy Locations\\s*$",
            r",?\\s*Vacancy Locations\\s*$",
            r",?\\s*US\\s*$",
        ]
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r",\\s*$", "", cleaned).strip()
        return cleaned if cleaned else None

    def parse_job_listing_page(self, soup, url):
        jobs = []

        # The main job table is identified by ID "JobSearchTable:Content"
        job_table = soup.find('table', id='JobSearchTable:Content')
        if not job_table:
            return jobs

        # Look for job rows
        job_rows = job_table.find_all('tr')

        for row in job_rows:
            cells = row.find_all('td')
            # Need at least 8 cells for a valid job row
            if len(cells) < 8:
                continue

            try:
                # Table structure (0-indexed):
                # 0: Checkbox (select)
                # 1: Name/ID with link to job details
                # 2: Job Title (text only)
                # 3: Organization Name
                # 4: Professional Area (Job Category)
                # 5: Location
                # 6: Date Posted
                # 7: Employment Type

                # Get job ID from cell 1 (Name column) - the anchor text is like "IRC47603"
                name_cell = cells[1]
                job_link = name_cell.find('a', class_='x5q')
                if not job_link:
                    continue

                # The job ID is in the anchor text (e.g., "IRC47603")
                job_id = job_link.get_text(strip=True)
                if not job_id:
                    continue

                # Get job title from cell 2
                title_cell = cells[2]
                title = title_cell.get_text(strip=True)
                if not title:
                    continue

                # Build a stable job URL using the vacancy ID from the hidden input
                hidden_input = name_cell.find('input', id=lambda x: x and 'hiddenUrlVACVWPP' in x)
                if hidden_input and hidden_input.get('value'):
                    job_url = 'https://careers.tananachiefs.org' + hidden_input.get('value')
                else:
                    job_url = f'https://careers.tananachiefs.org/OA_HTML/OA.jsp?OAFunc=IRC_VIS_VAC_DISPLAY&vacancyId={job_id}'

                # Organization name is in cell 3
                organization = cells[3].get_text(strip=True) or "Tanana Chiefs Conference"

                # Job category is in cell 4
                job_category = cells[4].get_text(strip=True) or None

                # Location is in cell 5 - clean it to remove Oracle suffixes
                raw_location = cells[5].get_text(strip=True) or None
                location = self._clean_location(raw_location)

                # Date posted is in cell 6
                date_posted = cells[6].get_text(strip=True) or None

                # Employment type is in cell 7
                employment_type = cells[7].get_text(strip=True) if len(cells) > 7 else None

                job = ScrapedJob(
                    external_id=f"tanana_{job_id}",
                    title=title,
                    url=job_url,
                    organization=organization,
                    location=location,
                    state="AK",
                    description=f"Posted: {date_posted}" if date_posted else None,
                    job_type=f"{job_category} - {employment_type}" if job_category and employment_type else job_category or employment_type,
                    salary_info=None
                )

                jobs.append(job)

            except Exception:
                continue

        return jobs

    def run(self):
        """Override run to select date filter and click Search button before scraping."""
        jobs = []
        errors = []

        soup = self.fetch_page(
            self.base_url,
            wait_for='table',
            select_actions=[
                {"selector": "select#DatePosted2", "value": {"label": "All Open Reqs"}}
            ],
            click_selector='button#Go',
            click_wait_for='table tr td a'
        )

        if soup is None:
            errors.append(f"Failed to fetch {self.base_url}")
            return jobs, errors

        try:
            page_jobs = self.parse_job_listing_page(soup, self.base_url)
            jobs.extend(page_jobs)
        except Exception as e:
            errors.append(f"Error parsing {self.base_url}: {e}")

        return jobs, errors
'''


def upgrade() -> None:
    # 1. Clean up existing job location data - match all patterns from clean_location helper

    # Handle "USVacancy Locations" suffix (with comma)
    op.execute("""
        UPDATE jobs
        SET location = TRIM(TRAILING ', USVacancy Locations' FROM location)
        WHERE location LIKE '%, USVacancy Locations'
    """)

    # Handle "USVacancy Locations" suffix (without comma)
    op.execute("""
        UPDATE jobs
        SET location = TRIM(LEADING ' ' FROM TRIM(TRAILING 'USVacancy Locations' FROM location))
        WHERE location LIKE '%USVacancy Locations'
    """)

    # Handle "Vacancy Locations" suffix (with comma)
    op.execute("""
        UPDATE jobs
        SET location = TRIM(TRAILING ', Vacancy Locations' FROM location)
        WHERE location LIKE '%, Vacancy Locations'
    """)

    # Handle "Vacancy Locations" suffix (without comma)
    op.execute("""
        UPDATE jobs
        SET location = TRIM(LEADING ' ' FROM TRIM(TRAILING 'Vacancy Locations' FROM location))
        WHERE location LIKE '%Vacancy Locations'
    """)

    # Handle trailing "US" (with comma) - but not state abbreviations like "AK, US"
    # Only match ", US" at the very end
    op.execute("""
        UPDATE jobs
        SET location = TRIM(TRAILING ', US' FROM location)
        WHERE location LIKE '%, US'
          AND location NOT LIKE '%, __, US'
    """)

    # Clean up any trailing commas or spaces left behind
    op.execute("""
        UPDATE jobs
        SET location = TRIM(TRAILING ',' FROM TRIM(location))
        WHERE location LIKE '%,'
    """)

    # 2. Update the TCC scraper code to include location cleaning
    # Use parameterized query to handle the code string safely
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE scrape_sources
            SET custom_scraper_code = :code
            WHERE name LIKE '%Tanana Chiefs%'
        """),
        {"code": UPDATED_TCC_SCRAPER_CODE}
    )


def downgrade() -> None:
    # Cannot restore original data - this is a one-way cleanup
    pass
