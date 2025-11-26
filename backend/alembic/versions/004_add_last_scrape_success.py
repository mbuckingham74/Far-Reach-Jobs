"""Add last_scrape_success column to scrape_sources

Revision ID: 004
Revises: 003
Create Date: 2025-11-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'scrape_sources',
        sa.Column('last_scrape_success', sa.Boolean(), nullable=True)
    )


def downgrade():
    op.drop_column('scrape_sources', 'last_scrape_success')
