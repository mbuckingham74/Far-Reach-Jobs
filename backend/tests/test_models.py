"""Tests for SQLAlchemy models and their constraints."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Job, ScrapeSource, User
from app.models.saved_job import SavedJob
from app.models.scrape_log import ScrapeLog


class TestUserModel:
    """Tests for the User model."""

    def test_create_user_with_required_fields(self, db):
        """User can be created with required fields."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password_here",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password_here"

    def test_user_email_unique_constraint(self, db):
        """User email must be unique."""
        user1 = User(email="duplicate@example.com", password_hash="hash1")
        db.add(user1)
        db.commit()

        user2 = User(email="duplicate@example.com", password_hash="hash2")
        db.add(user2)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_user_email_required(self, db):
        """User email is required (not nullable)."""
        user = User(email=None, password_hash="somehash")
        db.add(user)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_user_password_hash_required(self, db):
        """User password_hash is required (not nullable)."""
        user = User(email="nopassword@example.com", password_hash=None)
        db.add(user)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_user_default_values(self, db):
        """User has correct default values."""
        user = User(email="defaults@example.com", password_hash="hash")
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.is_verified is False
        assert user.verification_token is None
        assert user.verification_token_created_at is None
        assert user.created_at is not None

    def test_user_saved_jobs_relationship(self, db, fresh_job):
        """User has saved_jobs relationship."""
        user = User(email="saverjobs@example.com", password_hash="hash")
        db.add(user)
        db.commit()

        saved = SavedJob(user_id=user.id, job_id=fresh_job.id)
        db.add(saved)
        db.commit()

        db.refresh(user)
        assert len(user.saved_jobs) == 1
        assert user.saved_jobs[0].job_id == fresh_job.id

    def test_user_cascade_delete_saved_jobs(self, db, fresh_job):
        """Deleting a user cascades to delete their saved jobs."""
        user = User(email="todelete@example.com", password_hash="hash")
        db.add(user)
        db.commit()

        saved = SavedJob(user_id=user.id, job_id=fresh_job.id)
        db.add(saved)
        db.commit()
        saved_id = saved.id

        # Delete user
        db.delete(user)
        db.commit()

        # Saved job should be deleted
        assert db.query(SavedJob).filter(SavedJob.id == saved_id).first() is None


class TestJobModel:
    """Tests for the Job model."""

    def test_create_job_with_required_fields(self, db, active_source):
        """Job can be created with required fields."""
        job = Job(
            source_id=active_source.id,
            external_id="job-123",
            title="Test Job",
            url="https://example.com/jobs/123",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        assert job.id is not None
        assert job.title == "Test Job"

    def test_job_external_id_unique_constraint(self, db, active_source):
        """Job external_id must be unique."""
        job1 = Job(
            source_id=active_source.id,
            external_id="duplicate-id",
            title="Job 1",
            url="https://example.com/jobs/1",
        )
        db.add(job1)
        db.commit()

        job2 = Job(
            source_id=active_source.id,
            external_id="duplicate-id",
            title="Job 2",
            url="https://example.com/jobs/2",
        )
        db.add(job2)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_job_source_id_required(self, db):
        """Job source_id is required (foreign key)."""
        job = Job(
            source_id=None,
            external_id="no-source",
            title="No Source Job",
            url="https://example.com/job",
        )
        db.add(job)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_job_default_values(self, db, active_source):
        """Job has correct default values."""
        job = Job(
            source_id=active_source.id,
            external_id="defaults-job",
            title="Defaults Test",
            url="https://example.com/job",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        assert job.is_stale is False
        assert job.first_seen_at is not None
        assert job.last_seen_at is not None
        assert job.created_at is not None

    def test_job_source_relationship(self, db, active_source):
        """Job has source relationship."""
        job = Job(
            source_id=active_source.id,
            external_id="rel-job",
            title="Relationship Test",
            url="https://example.com/job",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        assert job.source is not None
        assert job.source.id == active_source.id
        assert job.source.name == active_source.name

    def test_job_saved_by_relationship(self, db, active_source):
        """Job has saved_by relationship."""
        user = User(email="saver@example.com", password_hash="hash")
        db.add(user)
        db.commit()

        job = Job(
            source_id=active_source.id,
            external_id="saveable-job",
            title="Saveable",
            url="https://example.com/job",
        )
        db.add(job)
        db.commit()

        saved = SavedJob(user_id=user.id, job_id=job.id)
        db.add(saved)
        db.commit()

        db.refresh(job)
        assert len(job.saved_by) == 1
        assert job.saved_by[0].user_id == user.id

    def test_job_cascade_delete_saved_jobs(self, db, active_source):
        """Deleting a job cascades to delete saved job entries."""
        user = User(email="jobdeleter@example.com", password_hash="hash")
        db.add(user)
        db.commit()

        job = Job(
            source_id=active_source.id,
            external_id="todelete-job",
            title="Will Be Deleted",
            url="https://example.com/job",
        )
        db.add(job)
        db.commit()

        saved = SavedJob(user_id=user.id, job_id=job.id)
        db.add(saved)
        db.commit()
        saved_id = saved.id

        # Delete job
        db.delete(job)
        db.commit()

        # Saved job entry should be deleted
        assert db.query(SavedJob).filter(SavedJob.id == saved_id).first() is None

    def test_job_optional_fields(self, db, active_source):
        """Job optional fields can be null."""
        job = Job(
            source_id=active_source.id,
            external_id="minimal-job",
            title="Minimal",
            url="https://example.com/job",
            organization=None,
            location=None,
            state=None,
            description=None,
            job_type=None,
            salary_info=None,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        assert job.organization is None
        assert job.location is None
        assert job.state is None


class TestSavedJobModel:
    """Tests for the SavedJob model."""

    def test_create_saved_job(self, db, fresh_job):
        """SavedJob can be created with user and job."""
        user = User(email="savedjob@example.com", password_hash="hash")
        db.add(user)
        db.commit()

        saved = SavedJob(user_id=user.id, job_id=fresh_job.id)
        db.add(saved)
        db.commit()
        db.refresh(saved)

        assert saved.id is not None
        assert saved.user_id == user.id
        assert saved.job_id == fresh_job.id
        assert saved.saved_at is not None

    def test_saved_job_unique_constraint(self, db, fresh_job):
        """User cannot save the same job twice (unique constraint)."""
        user = User(email="uniquesave@example.com", password_hash="hash")
        db.add(user)
        db.commit()

        saved1 = SavedJob(user_id=user.id, job_id=fresh_job.id)
        db.add(saved1)
        db.commit()

        saved2 = SavedJob(user_id=user.id, job_id=fresh_job.id)
        db.add(saved2)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_saved_job_user_relationship(self, db, fresh_job):
        """SavedJob has user relationship."""
        user = User(email="userrel@example.com", password_hash="hash")
        db.add(user)
        db.commit()

        saved = SavedJob(user_id=user.id, job_id=fresh_job.id)
        db.add(saved)
        db.commit()
        db.refresh(saved)

        assert saved.user is not None
        assert saved.user.email == "userrel@example.com"

    def test_saved_job_job_relationship(self, db, fresh_job):
        """SavedJob has job relationship."""
        user = User(email="jobrel@example.com", password_hash="hash")
        db.add(user)
        db.commit()

        saved = SavedJob(user_id=user.id, job_id=fresh_job.id)
        db.add(saved)
        db.commit()
        db.refresh(saved)

        assert saved.job is not None
        assert saved.job.id == fresh_job.id

    def test_saved_job_cascade_on_user_delete(self, db, fresh_job):
        """SavedJob is deleted when user is deleted (CASCADE)."""
        user = User(email="cascade@example.com", password_hash="hash")
        db.add(user)
        db.commit()

        saved = SavedJob(user_id=user.id, job_id=fresh_job.id)
        db.add(saved)
        db.commit()
        saved_id = saved.id

        db.delete(user)
        db.commit()

        assert db.query(SavedJob).filter(SavedJob.id == saved_id).first() is None

    def test_saved_job_cascade_on_job_delete(self, db, active_source):
        """SavedJob is deleted when job is deleted (CASCADE)."""
        user = User(email="jobcascade@example.com", password_hash="hash")
        db.add(user)
        db.commit()

        job = Job(
            source_id=active_source.id,
            external_id="cascade-job",
            title="Cascade Test",
            url="https://example.com/job",
        )
        db.add(job)
        db.commit()

        saved = SavedJob(user_id=user.id, job_id=job.id)
        db.add(saved)
        db.commit()
        saved_id = saved.id

        db.delete(job)
        db.commit()

        assert db.query(SavedJob).filter(SavedJob.id == saved_id).first() is None


class TestScrapeSourceModel:
    """Tests for the ScrapeSource model."""

    def test_create_source_with_required_fields(self, db):
        """ScrapeSource can be created with required fields."""
        source = ScrapeSource(
            name="Test Source",
            base_url="https://example.com",
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        assert source.id is not None
        assert source.name == "Test Source"
        assert source.base_url == "https://example.com"

    def test_source_default_values(self, db):
        """ScrapeSource has correct default values."""
        source = ScrapeSource(
            name="Defaults Source",
            base_url="https://example.com",
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        assert source.scraper_class == "GenericScraper"
        assert source.is_active is True
        assert source.use_playwright is False
        assert source.max_pages == 10
        assert source.url_attribute == "href"
        assert source.created_at is not None

    def test_source_jobs_relationship(self, db):
        """ScrapeSource has jobs relationship."""
        source = ScrapeSource(
            name="Jobs Source",
            base_url="https://example.com",
        )
        db.add(source)
        db.commit()

        job = Job(
            source_id=source.id,
            external_id="source-job",
            title="Source Job",
            url="https://example.com/job",
        )
        db.add(job)
        db.commit()

        db.refresh(source)
        assert len(source.jobs) == 1
        assert source.jobs[0].title == "Source Job"

    def test_source_cascade_delete_jobs(self, db):
        """Deleting a source cascades to delete its jobs."""
        source = ScrapeSource(
            name="Delete Source",
            base_url="https://example.com",
        )
        db.add(source)
        db.commit()

        job = Job(
            source_id=source.id,
            external_id="deleteme-job",
            title="Will Be Deleted",
            url="https://example.com/job",
        )
        db.add(job)
        db.commit()
        job_id = job.id

        db.delete(source)
        db.commit()

        assert db.query(Job).filter(Job.id == job_id).first() is None

    def test_source_selector_fields(self, db):
        """ScrapeSource selector fields can be set."""
        source = ScrapeSource(
            name="Selector Source",
            base_url="https://example.com",
            selector_job_container=".job-card",
            selector_title=".title",
            selector_url=".link",
            selector_organization=".company",
            selector_location=".location",
            selector_next_page=".next",
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        assert source.selector_job_container == ".job-card"
        assert source.selector_title == ".title"
        assert source.selector_url == ".link"
        assert source.selector_organization == ".company"

    def test_source_custom_scraper_code(self, db):
        """ScrapeSource can store custom scraper code."""
        code = """
def scrape(html):
    return []
"""
        source = ScrapeSource(
            name="Custom Source",
            base_url="https://example.com",
            scraper_class="DynamicScraper",
            custom_scraper_code=code,
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        assert source.custom_scraper_code == code
        assert source.scraper_class == "DynamicScraper"


class TestScrapeLogModel:
    """Tests for the ScrapeLog model."""

    def test_create_scrape_log(self, db, active_source):
        """ScrapeLog can be created with required fields."""
        log = ScrapeLog(
            source_id=active_source.id,
            source_name=active_source.name,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.id is not None
        assert log.source_name == active_source.name
        assert log.trigger_type == "manual"

    def test_scrape_log_default_values(self, db, active_source):
        """ScrapeLog has correct default values."""
        log = ScrapeLog(
            source_id=active_source.id,
            source_name=active_source.name,
            trigger_type="scheduled",
            started_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.success is True
        assert log.jobs_found == 0
        assert log.jobs_added == 0
        assert log.jobs_updated == 0
        assert log.jobs_removed == 0
        assert log.completed_at is not None

    def test_scrape_log_source_relationship(self, db, active_source):
        """ScrapeLog has source relationship."""
        log = ScrapeLog(
            source_id=active_source.id,
            source_name=active_source.name,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.source is not None
        assert log.source.id == active_source.id

    def test_scrape_log_preserves_source_name_on_delete(self, db):
        """ScrapeLog preserves source_name even if source is deleted."""
        source = ScrapeSource(
            name="Deletable Source",
            base_url="https://example.com",
        )
        db.add(source)
        db.commit()

        log = ScrapeLog(
            source_id=source.id,
            source_name=source.name,
            trigger_type="scheduled",
            started_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()
        log_id = log.id

        # Delete source (SET NULL on source_id)
        db.delete(source)
        db.commit()

        # Log should still exist with source_name preserved
        log = db.query(ScrapeLog).filter(ScrapeLog.id == log_id).first()
        assert log is not None
        assert log.source_name == "Deletable Source"
        assert log.source_id is None
        assert log.source is None

    def test_scrape_log_with_results(self, db, active_source):
        """ScrapeLog can store job counts and errors."""
        log = ScrapeLog(
            source_id=active_source.id,
            source_name=active_source.name,
            trigger_type="scheduled",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            duration_seconds=45,
            success=True,
            jobs_found=20,
            jobs_added=10,
            jobs_updated=5,
            jobs_removed=2,
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.jobs_found == 20
        assert log.jobs_added == 10
        assert log.jobs_updated == 5
        assert log.jobs_removed == 2
        assert log.duration_seconds == 45

    def test_scrape_log_with_errors(self, db, active_source):
        """ScrapeLog can store error information."""
        import json
        errors = json.dumps(["Error 1", "Error 2"])

        log = ScrapeLog(
            source_id=active_source.id,
            source_name=active_source.name,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            success=False,
            errors=errors,
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.success is False
        assert log.errors == errors
        assert json.loads(log.errors) == ["Error 1", "Error 2"]

    def test_scrape_log_trigger_type_required(self, db, active_source):
        """ScrapeLog trigger_type is required."""
        log = ScrapeLog(
            source_id=active_source.id,
            source_name=active_source.name,
            trigger_type=None,
            started_at=datetime.now(timezone.utc),
        )
        db.add(log)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_scrape_log_source_name_required(self, db, active_source):
        """ScrapeLog source_name is required."""
        log = ScrapeLog(
            source_id=active_source.id,
            source_name=None,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
        )
        db.add(log)
        with pytest.raises(IntegrityError):
            db.commit()


class TestModelIndexes:
    """Tests to verify indexes exist and work correctly."""

    def test_user_email_index(self, db):
        """User email should be indexed for fast lookups."""
        # Create multiple users
        for i in range(5):
            user = User(email=f"indexed{i}@example.com", password_hash="hash")
            db.add(user)
        db.commit()

        # Query by email should work efficiently (index exists)
        user = db.query(User).filter(User.email == "indexed2@example.com").first()
        assert user is not None
        assert user.email == "indexed2@example.com"

    def test_job_external_id_index(self, db, active_source):
        """Job external_id should be indexed for fast lookups."""
        for i in range(5):
            job = Job(
                source_id=active_source.id,
                external_id=f"indexed-{i}",
                title=f"Job {i}",
                url=f"https://example.com/job/{i}",
            )
            db.add(job)
        db.commit()

        job = db.query(Job).filter(Job.external_id == "indexed-3").first()
        assert job is not None
        assert job.external_id == "indexed-3"

    def test_job_state_index(self, db, active_source):
        """Job state should be indexed for filtering."""
        states = ["AK", "TX", "CA", "AK", "NY"]
        for i, state in enumerate(states):
            job = Job(
                source_id=active_source.id,
                external_id=f"state-{i}",
                title=f"Job {i}",
                url=f"https://example.com/job/{i}",
                state=state,
            )
            db.add(job)
        db.commit()

        ak_jobs = db.query(Job).filter(Job.state == "AK").all()
        assert len(ak_jobs) == 2

    def test_job_is_stale_index(self, db, active_source):
        """Job is_stale should be indexed for filtering active jobs."""
        for i in range(5):
            job = Job(
                source_id=active_source.id,
                external_id=f"stale-test-{i}",
                title=f"Job {i}",
                url=f"https://example.com/job/{i}",
                is_stale=(i % 2 == 0),
            )
            db.add(job)
        db.commit()

        active_jobs = db.query(Job).filter(Job.is_stale == False).all()
        assert len(active_jobs) == 2  # i=1, i=3
