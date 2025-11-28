"""Add default_state field to scrape_sources

Revision ID: 010
Revises: 009
Create Date: 2025-11-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'scrape_sources',
        sa.Column('default_state', sa.String(50), nullable=True)
    )

    # Set default_state to 'AK' for all Alaska-based sources
    # This provides state data for sources that don't include it in job listings
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE scrape_sources SET default_state = 'AK' WHERE default_state IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_column('scrape_sources', 'default_state')
