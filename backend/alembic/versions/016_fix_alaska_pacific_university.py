"""Fix Alaska Pacific University scraper - convert to GenericScraper with proper selectors

The APU careers page uses a Ninja Tables WordPress plugin with server-rendered HTML.
Jobs are in a simple table structure that GenericScraper can handle.

Previous setup used DynamicScraper with complex custom code that didn't match
the actual page structure, and the site blocks non-browser User-Agents (Cloudflare).

Fix:
- Convert from DynamicScraper to GenericScraper
- Set proper CSS selectors for the Ninja Tables structure
- Use #openings section ID (stable, author-controlled) instead of auto-generated footable ID
- Enable Playwright to bypass Cloudflare WAF
- Re-enable the source (is_active = 1)
- Store previous custom_scraper_code for reversible downgrade

Revision ID: 016
Revises: 015
Create Date: 2025-11-29
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None

# Store the previous custom scraper code for downgrade
# (retrieved from production database)
PREVIOUS_CUSTOM_SCRAPER_CODE = r'''class AlaskaPacificUniversityScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "Alaska Pacific University (APU)"

    @property
    def base_url(self) -> str:
        return "https://www.alaskapacific.edu"

    def get_job_listing_urls(self) -> list:
        return ["https://www.alaskapacific.edu/about/employment/#openings"]

    def parse_job_listing_page(self, soup, url):
        jobs = []
        openings_section = soup.find(id="openings")
        if not openings_section:
            job_links = soup.find_all("a", href=re.compile(r"job|career|position|employment", re.I))
            content_areas = soup.select(".entry-content, .page-content, .site-content, main")
            for content_area in content_areas:
                job_headings = content_area.find_all(["h2", "h3", "h4"],
                    string=re.compile(r"open|position|job|career|employment|hiring", re.I))
                for heading in job_headings:
                    next_elements = heading.find_next_siblings(limit=10)
                    for element in next_elements:
                        links = element.find_all("a") if element else []
                        for link in links:
                            href = link.get("href")
                            title = link.get_text(strip=True)
                            if href and title and len(title) > 5:
                                job_url = urljoin(self.base_url, href)
                                job = ScrapedJob(
                                    external_id=self.generate_external_id(job_url),
                                    title=title,
                                    url=job_url,
                                    organization="Alaska Pacific University",
                                    state="AK"
                                )
                                jobs.append(job)
        else:
            job_elements = openings_section.find_all(["div", "li", "article"])
            for element in job_elements:
                title_element = element.find(["h3", "h4", "h5", "strong", "b"])
                if not title_element:
                    continue
                title = title_element.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                description_parts = []
                for text_elem in element.find_all(text=True):
                    text = text_elem.strip()
                    if text and text != title:
                        description_parts.append(text)
                description = " ".join(description_parts) if description_parts else None
                job_url = url
                link = element.find("a", href=True)
                if link:
                    job_url = urljoin(self.base_url, link["href"])
                location = None
                location_text = element.get_text()
                if "anchorage" in location_text.lower():
                    location = "Anchorage, AK"
                elif "alaska" in location_text.lower():
                    location = "Alaska"
                job = ScrapedJob(
                    external_id=self.generate_external_id(job_url + "#" + title.replace(" ", "_")),
                    title=title,
                    url=job_url,
                    organization="Alaska Pacific University",
                    location=location,
                    state="AK",
                    description=description
                )
                jobs.append(job)
        if not jobs:
            text_content = soup.get_text()
            if re.search(r"no.{0,20}current.{0,20}opening|no.{0,20}position.{0,20}available", text_content, re.I):
                job = ScrapedJob(
                    external_id=self.generate_external_id(url + "#no_openings"),
                    title="No Current Openings",
                    url=url,
                    organization="Alaska Pacific University",
                    state="AK",
                    description="Please check back regularly for new employment opportunities."
                )
                jobs.append(job)
        return jobs'''


def upgrade() -> None:
    # Update Alaska Pacific University source to use GenericScraper
    # The page uses Ninja Tables with this structure:
    # <tr class="ninja_table_row_X">
    #   <td><a href="...">Job Title</a></td>
    #   <td>Department</td>
    #   <td>Full-Time</td>
    #   <td>Description...</td>
    # </tr>
    #
    # Using #openings section ID (stable, set by page author) instead of
    # auto-generated footable_XXXXX ID which can change on content updates
    op.execute("""
        UPDATE scrape_sources
        SET
            scraper_class = 'GenericScraper',
            listing_url = 'https://www.alaskapacific.edu/about/employment/',
            selector_job_container = '#openings table tbody tr',
            selector_title = 'td:first-child a',
            selector_url = 'td:first-child a',
            selector_organization = NULL,
            selector_location = NULL,
            selector_job_type = 'td:nth-child(3)',
            selector_salary = NULL,
            selector_description = 'td:nth-child(4)',
            url_attribute = 'href',
            use_playwright = 1,
            is_active = 1,
            default_location = 'Anchorage',
            default_state = 'AK',
            organization = 'Alaska Pacific University',
            custom_scraper_code = NULL,
            needs_configuration = 0
        WHERE name LIKE '%Alaska Pacific University%'
           OR base_url LIKE '%alaskapacific.edu%'
    """)


def downgrade() -> None:
    # Revert to DynamicScraper with original custom scraper code
    # Use parameterized query to safely handle the code string
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE scrape_sources
            SET
                scraper_class = 'DynamicScraper',
                listing_url = 'https://www.alaskapacific.edu/about/employment/#openings',
                selector_job_container = NULL,
                selector_title = NULL,
                selector_url = NULL,
                selector_organization = NULL,
                selector_location = NULL,
                selector_job_type = NULL,
                selector_salary = NULL,
                selector_description = NULL,
                url_attribute = NULL,
                use_playwright = 0,
                is_active = 0,
                default_location = NULL,
                default_state = NULL,
                organization = NULL,
                custom_scraper_code = :code,
                needs_configuration = 0
            WHERE name LIKE '%Alaska Pacific University%'
               OR base_url LIKE '%alaskapacific.edu%'
        """),
        {"code": PREVIOUS_CUSTOM_SCRAPER_CODE}
    )
