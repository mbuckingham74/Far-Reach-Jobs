"""Fix Alaska Pacific University scraper - convert to GenericScraper with proper selectors

The APU careers page uses a Ninja Tables WordPress plugin with server-rendered HTML.
Jobs are in a simple table structure that GenericScraper can handle.

Previous setup used DynamicScraper with complex custom code that didn't match
the actual page structure, and the site blocks non-browser User-Agents (Cloudflare).

Fix:
- Convert from DynamicScraper to GenericScraper
- Set proper CSS selectors for the Ninja Tables structure
- Enable Playwright to bypass Cloudflare WAF
- Re-enable the source (is_active = 1)
- Clear custom_scraper_code (no longer needed)

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


def upgrade() -> None:
    # Update Alaska Pacific University source to use GenericScraper
    # The page uses Ninja Tables with this structure:
    # <tr class="ninja_table_row_X">
    #   <td><a href="...">Job Title</a></td>
    #   <td>Department</td>
    #   <td>Full-Time</td>
    #   <td>Description...</td>
    # </tr>
    op.execute("""
        UPDATE scrape_sources
        SET
            scraper_class = 'GenericScraper',
            listing_url = 'https://www.alaskapacific.edu/about/employment/',
            selector_job_container = '#footable_70083 tbody tr',
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
    # Revert to DynamicScraper (but don't restore the custom code - too complex)
    op.execute("""
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
            needs_configuration = 0
        WHERE name LIKE '%Alaska Pacific University%'
           OR base_url LIKE '%alaskapacific.edu%'
    """)
