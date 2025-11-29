"""Pytest configuration and fixtures for Far Reach Jobs tests."""

import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app modules
os.environ["ENVIRONMENT"] = "development"
os.environ["MYSQL_PASSWORD"] = "test"

from app.database import Base, get_db
from app.main import app
from app.models import Job, ScrapeSource, User


# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Enable foreign key support for SQLite (required for ON DELETE CASCADE/SET NULL)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def active_source(db):
    """Create an active scrape source."""
    source = ScrapeSource(
        name="Test Source",
        base_url="https://example.com",
        is_active=True,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@pytest.fixture
def inactive_source(db):
    """Create an inactive scrape source."""
    source = ScrapeSource(
        name="Inactive Source",
        base_url="https://inactive.com",
        is_active=False,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@pytest.fixture
def fresh_job(db, active_source):
    """Create a non-stale job first seen today."""
    job = Job(
        source_id=active_source.id,
        external_id="fresh-job-1",
        title="Fresh Job",
        url="https://example.com/jobs/1",
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
        is_stale=False,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@pytest.fixture
def old_job(db, active_source):
    """Create a non-stale job first seen 10 days ago."""
    ten_days_ago = datetime.utcnow() - timedelta(days=10)
    job = Job(
        source_id=active_source.id,
        external_id="old-job-1",
        title="Old Job",
        url="https://example.com/jobs/2",
        first_seen_at=ten_days_ago,
        last_seen_at=datetime.utcnow(),
        is_stale=False,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@pytest.fixture
def stale_job(db, active_source):
    """Create a stale job."""
    job = Job(
        source_id=active_source.id,
        external_id="stale-job-1",
        title="Stale Job",
        url="https://example.com/jobs/3",
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow() - timedelta(days=3),
        is_stale=True,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@pytest.fixture
def robots_blocked_source(db):
    """Create a source blocked by robots.txt."""
    source = ScrapeSource(
        name="Robots Blocked Source",
        base_url="https://blocked.com",
        is_active=True,
        robots_blocked=True,
        robots_blocked_at=datetime.utcnow(),
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source
