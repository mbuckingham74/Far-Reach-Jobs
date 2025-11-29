"""Add needs_configuration to scrape_sources

Revision ID: 014
Revises: 013
Create Date: 2025-11-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('scrape_sources', sa.Column('needs_configuration', sa.Boolean(), nullable=True, server_default='0'))


def downgrade():
    op.drop_column('scrape_sources', 'needs_configuration')
