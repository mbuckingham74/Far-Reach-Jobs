"""Add skip_robots_check to scrape_sources

Revision ID: 012
Revises: 011
Create Date: 2025-11-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('scrape_sources', sa.Column('skip_robots_check', sa.Boolean(), nullable=True, server_default='0'))


def downgrade():
    op.drop_column('scrape_sources', 'skip_robots_check')
