"""Enable Playwright by default for all sources

This migration:
1. Sets use_playwright=True for all existing sources that have it False or NULL
2. Changes the column default to True for new sources

Playwright is required for most modern job sites that use JavaScript rendering.
Without it, the scraper only gets the initial HTML before JS executes, missing
dynamically loaded job listings.

Revision ID: 019
Revises: 018
Create Date: 2025-12-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable Playwright for all existing sources
    op.execute(
        "UPDATE scrape_sources SET use_playwright = TRUE WHERE use_playwright = FALSE OR use_playwright IS NULL"
    )

    # Change the column default to True for new sources
    op.alter_column(
        'scrape_sources',
        'use_playwright',
        server_default=sa.text('1'),  # MySQL uses 1 for True
        existing_type=sa.Boolean(),
        existing_nullable=True
    )


def downgrade() -> None:
    # Revert column default to False
    op.alter_column(
        'scrape_sources',
        'use_playwright',
        server_default=sa.text('0'),
        existing_type=sa.Boolean(),
        existing_nullable=True
    )
    # Note: We don't revert existing data as that could break working scrapers
