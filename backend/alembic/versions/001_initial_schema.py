"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('verification_token', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'])

    # Create scrape_sources table
    op.create_table(
        'scrape_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('base_url', sa.String(1000), nullable=False),
        sa.Column('scraper_class', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('last_scraped_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_scrape_sources_id', 'scrape_sources', ['id'])

    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('organization', sa.String(255), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('state', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('job_type', sa.String(100), nullable=True),
        sa.Column('salary_info', sa.String(255), nullable=True),
        sa.Column('url', sa.String(1000), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('is_stale', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['scrape_sources.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_jobs_id', 'jobs', ['id'])
    op.create_index('ix_jobs_external_id', 'jobs', ['external_id'], unique=True)
    op.create_index('ix_jobs_state', 'jobs', ['state'])
    op.create_index('ix_jobs_job_type', 'jobs', ['job_type'])
    op.create_index('ix_jobs_is_stale', 'jobs', ['is_stale'])
    op.create_index('ix_jobs_stale_last_seen', 'jobs', ['is_stale', 'last_seen_at'])
    op.create_index('ix_jobs_location', 'jobs', ['location'])

    # Create saved_jobs table
    op.create_table(
        'saved_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('saved_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'job_id', name='uq_user_job')
    )
    op.create_index('ix_saved_jobs_id', 'saved_jobs', ['id'])


def downgrade() -> None:
    op.drop_table('saved_jobs')
    op.drop_table('jobs')
    op.drop_table('scrape_sources')
    op.drop_table('users')
