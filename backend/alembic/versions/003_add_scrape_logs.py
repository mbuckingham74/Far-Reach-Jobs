"""Add scrape_logs table

Revision ID: 003
Revises: 002
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'scrape_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('source_name', sa.String(255), nullable=False),
        sa.Column('trigger_type', sa.String(50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('jobs_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('jobs_added', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('jobs_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('jobs_removed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('errors', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['scrape_sources.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_scrape_logs_id', 'scrape_logs', ['id'])
    op.create_index('ix_scrape_logs_source_id', 'scrape_logs', ['source_id'])
    op.create_index('ix_scrape_logs_started_at', 'scrape_logs', ['started_at'])
    op.create_index('ix_scrape_logs_trigger_type', 'scrape_logs', ['trigger_type'])


def downgrade() -> None:
    op.drop_table('scrape_logs')
