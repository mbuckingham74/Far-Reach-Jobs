"""Add Arctic Slope Native Association (ASNA) source

ASNA uses EnterTimeOnline (UKG/Kronos) for their careers page.
The site has robots.txt with blanket Disallow: / but is a public job board,
so we enable skip_robots_check.

The page is JavaScript-rendered (SPA), so use_playwright is required.
Selectors will be configured via admin UI after deployment.

Revision ID: 017
Revises: 016
Create Date: 2025-11-29

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Insert ASNA source with skip_robots_check enabled
    # Source needs configuration via admin UI for CSS selectors
    conn = op.get_bind()

    # Check if source already exists (by name or listing_url containing tenant code)
    result = conn.execute(
        sa.text("""
            SELECT id FROM scrape_sources
            WHERE name LIKE '%Arctic Slope Native Association%'
               OR listing_url LIKE '%ACG00014%'
        """)
    ).fetchone()

    if result is None:
        conn.execute(
            sa.text("""
                INSERT INTO scrape_sources (
                    name,
                    base_url,
                    scraper_class,
                    is_active,
                    listing_url,
                    use_playwright,
                    skip_robots_check,
                    needs_configuration,
                    default_location,
                    default_state,
                    organization,
                    created_at
                ) VALUES (
                    :name,
                    :base_url,
                    :scraper_class,
                    :is_active,
                    :listing_url,
                    :use_playwright,
                    :skip_robots_check,
                    :needs_configuration,
                    :default_location,
                    :default_state,
                    :organization,
                    :created_at
                )
            """),
            {
                "name": "Arctic Slope Native Association (ASNA)",
                "base_url": "https://secure5.entertimeonline.com",
                "scraper_class": "GenericScraper",
                "is_active": False,
                "listing_url": "https://secure5.entertimeonline.com/ta/ACG00014.careers?CareersSearch=&lang=en-US",
                "use_playwright": True,
                "skip_robots_check": True,
                "needs_configuration": True,
                "default_location": "Utqiaġvik",
                "default_state": "AK",
                "organization": "Arctic Slope Native Association",
                "created_at": datetime.utcnow()
            }
        )


def downgrade() -> None:
    # Remove the ASNA source
    op.execute("""
        DELETE FROM scrape_sources
        WHERE name LIKE '%Arctic Slope Native Association%'
           OR listing_url LIKE '%ACG00014%'
    """)
