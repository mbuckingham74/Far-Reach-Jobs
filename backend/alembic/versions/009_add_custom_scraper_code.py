"""Add custom_scraper_code field for AI-generated scrapers

Revision ID: 009
Revises: 008
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('scrape_sources', sa.Column('custom_scraper_code', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('scrape_sources', 'custom_scraper_code')
