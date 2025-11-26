"""Add GenericScraper configuration fields to scrape_sources

Revision ID: 005
Revises: 004
Create Date: 2025-11-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Add listing URL field
    op.add_column(
        'scrape_sources',
        sa.Column('listing_url', sa.String(1000), nullable=True)
    )

    # Add CSS selector fields for GenericScraper
    op.add_column(
        'scrape_sources',
        sa.Column('selector_job_container', sa.String(500), nullable=True)
    )
    op.add_column(
        'scrape_sources',
        sa.Column('selector_title', sa.String(500), nullable=True)
    )
    op.add_column(
        'scrape_sources',
        sa.Column('selector_url', sa.String(500), nullable=True)
    )
    op.add_column(
        'scrape_sources',
        sa.Column('selector_organization', sa.String(500), nullable=True)
    )
    op.add_column(
        'scrape_sources',
        sa.Column('selector_location', sa.String(500), nullable=True)
    )
    op.add_column(
        'scrape_sources',
        sa.Column('selector_job_type', sa.String(500), nullable=True)
    )
    op.add_column(
        'scrape_sources',
        sa.Column('selector_salary', sa.String(500), nullable=True)
    )
    op.add_column(
        'scrape_sources',
        sa.Column('selector_description', sa.String(500), nullable=True)
    )
    op.add_column(
        'scrape_sources',
        sa.Column('url_attribute', sa.String(100), nullable=True)
    )
    op.add_column(
        'scrape_sources',
        sa.Column('selector_next_page', sa.String(500), nullable=True)
    )
    op.add_column(
        'scrape_sources',
        sa.Column('max_pages', sa.Integer(), nullable=True)
    )

    # Update existing rows to use GenericScraper as default
    op.execute("UPDATE scrape_sources SET scraper_class = 'GenericScraper' WHERE scraper_class = 'GenericScraper' OR scraper_class IS NULL")
    op.execute("UPDATE scrape_sources SET url_attribute = 'href' WHERE url_attribute IS NULL")
    op.execute("UPDATE scrape_sources SET max_pages = 10 WHERE max_pages IS NULL")


def downgrade():
    op.drop_column('scrape_sources', 'max_pages')
    op.drop_column('scrape_sources', 'selector_next_page')
    op.drop_column('scrape_sources', 'url_attribute')
    op.drop_column('scrape_sources', 'selector_description')
    op.drop_column('scrape_sources', 'selector_salary')
    op.drop_column('scrape_sources', 'selector_job_type')
    op.drop_column('scrape_sources', 'selector_location')
    op.drop_column('scrape_sources', 'selector_organization')
    op.drop_column('scrape_sources', 'selector_url')
    op.drop_column('scrape_sources', 'selector_title')
    op.drop_column('scrape_sources', 'selector_job_container')
    op.drop_column('scrape_sources', 'listing_url')
