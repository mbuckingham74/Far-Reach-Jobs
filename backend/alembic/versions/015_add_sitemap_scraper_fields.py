"""Add SitemapScraper fields to scrape_sources

Revision ID: 015
Revises: 014
Create Date: 2025-11-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    # Add sitemap_url for SitemapScraper
    op.add_column('scrape_sources', sa.Column('sitemap_url', sa.String(1000), nullable=True))
    # Add sitemap_url_pattern for filtering URLs (e.g., "-ak/" for Alaska)
    op.add_column('scrape_sources', sa.Column('sitemap_url_pattern', sa.String(500), nullable=True))
    # Add organization field for sources where org can't be extracted from URL
    op.add_column('scrape_sources', sa.Column('organization', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('scrape_sources', 'organization')
    op.drop_column('scrape_sources', 'sitemap_url_pattern')
    op.drop_column('scrape_sources', 'sitemap_url')
