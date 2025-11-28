"""Add robots_blocked fields to scrape_sources

Revision ID: 011
Revises: 010
Create Date: 2025-11-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('scrape_sources', sa.Column('robots_blocked', sa.Boolean(), nullable=True, server_default='0'))
    op.add_column('scrape_sources', sa.Column('robots_blocked_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('scrape_sources', 'robots_blocked_at')
    op.drop_column('scrape_sources', 'robots_blocked')
