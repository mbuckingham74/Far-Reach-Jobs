"""Add default_location field to scrape_sources

Revision ID: 007
Revises: 006
Create Date: 2025-11-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'scrape_sources',
        sa.Column('default_location', sa.String(255), nullable=True)
    )

    # Set default locations for known Alaska sources based on their names
    # This provides initial location data for the location filter
    location_mappings = [
        ("City of Bethel", "Bethel"),
        ("City of Nome", "Nome"),
        ("City of Kotzebue", "Kotzebue"),
        ("City of Dillingham", "Dillingham"),
        # Regional organizations - use their headquarters/main office location
        ("Yukon-Kuskokwim Health Corporation (YKHC)", "Bethel"),
        ("Norton Sound Health Corporation (NSHC)", "Nome"),
        ("Maniilaq Association", "Kotzebue"),
        ("Bristol Bay Native Association (BBNA)", "Dillingham"),
        ("Bristol Bay Area Health Corporation (BBAHC)", "Dillingham"),
        ("Arctic Slope Native Association (ASNA)", "Utqiaġvik"),
        ("Tanana Chiefs Conference (TCC)", "Fairbanks"),
        ("Southcentral Foundation (SCF)", "Anchorage"),
        ("Cook Inlet Tribal Council (CITC)", "Anchorage"),
        ("Alaska Native Tribal Health Consortium (ANTHC)", "Anchorage"),
        ("SEARHC (SE Alaska Regional Health Consortium)", "Juneau"),
        ("Sealaska", "Juneau"),
        ("Association of Village Council Presidents (AVCP)", "Bethel"),
        # School districts
        ("Lower Kuskokwim School District (LKSD)", "Bethel"),
        ("Lower Yukon School District (LYSD)", "Mountain Village"),
        ("Bering Strait School District (BSSD)", "Unalakleet"),
        ("Northwest Arctic Borough School District (NWABSD)", "Kotzebue"),
    ]

    # Use SQLAlchemy text() with bound parameters for safe SQL execution
    conn = op.get_bind()
    for source_name, location in location_mappings:
        # Use bound parameters to prevent SQL injection
        conn.execute(
            sa.text(
                "UPDATE scrape_sources SET default_location = :location "
                "WHERE name LIKE :pattern AND default_location IS NULL"
            ),
            {"location": location, "pattern": f"%{source_name}%"}
        )


def downgrade() -> None:
    op.drop_column('scrape_sources', 'default_location')
