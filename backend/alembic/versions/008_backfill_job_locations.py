"""Backfill job locations from source default_location

Revision ID: 008
Revises: 007
Create Date: 2025-11-27

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update jobs that have no location with their source's default_location
    # This is a one-time backfill for existing data
    op.execute("""
        UPDATE jobs j
        INNER JOIN scrape_sources s ON j.source_id = s.id
        SET j.location = s.default_location
        WHERE j.location IS NULL AND s.default_location IS NOT NULL
    """)


def downgrade() -> None:
    # Can't easily undo this - would need to know which jobs had NULL before
    # Safest is to not clear locations on downgrade
    pass
