"""Add use_playwright field to scrape_sources

Revision ID: 006
Revises: 005
Create Date: 2025-11-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'scrape_sources',
        sa.Column('use_playwright', sa.Boolean(), nullable=True, default=False)
    )
    # Set existing rows to False
    op.execute("UPDATE scrape_sources SET use_playwright = FALSE WHERE use_playwright IS NULL")


def downgrade() -> None:
    op.drop_column('scrape_sources', 'use_playwright')
