"""Tests for the /api/saved-jobs endpoints."""

from datetime import datetime

import pytest

from app.models import Job, SavedJob, ScrapeSource, User
from app.services.auth import hash_password, create_access_token


@pytest.fixture
def verified_user(db):
    """Create a verified user for authentication."""
    user = User(
        email="testuser@example.com",
        password_hash=hash_password("password123"),
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def second_user(db):
    """Create a second verified user for isolation testing."""
    user = User(
        email="seconduser@example.com",
        password_hash=hash_password("password123"),
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_token(verified_user):
    """Create an auth token for the verified user."""
    return create_access_token(
        data={"sub": str(verified_user.id), "email": verified_user.email}
    )


@pytest.fixture
def second_user_token(second_user):
    """Create an auth token for the second user."""
    return create_access_token(
        data={"sub": str(second_user.id), "email": second_user.email}
    )


@pytest.fixture
def test_source(db):
    """Create a test scrape source."""
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
def test_job(db, test_source):
    """Create a test job."""
    job = Job(
        source_id=test_source.id,
        external_id="test-job-1",
        title="Test Job",
        organization="Test Org",
        location="Anchorage, AK",
        state="AK",
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
def stale_test_job(db, test_source):
    """Create a stale test job."""
    job = Job(
        source_id=test_source.id,
        external_id="stale-test-job",
        title="Stale Test Job",
        url="https://example.com/jobs/stale",
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
        is_stale=True,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@pytest.fixture
def multiple_jobs(db, test_source):
    """Create multiple test jobs."""
    jobs = []
    for i in range(3):
        job = Job(
            source_id=test_source.id,
            external_id=f"multi-job-{i}",
            title=f"Job {i}",
            organization=f"Org {i}",
            url=f"https://example.com/jobs/{i}",
            first_seen_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
            is_stale=False,
        )
        db.add(job)
        jobs.append(job)
    db.commit()
    for job in jobs:
        db.refresh(job)
    return jobs


@pytest.fixture
def saved_job(db, verified_user, test_job):
    """Create a saved job for the verified user."""
    saved = SavedJob(user_id=verified_user.id, job_id=test_job.id)
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


class TestListSavedJobs:
    """Tests for GET /api/saved-jobs endpoint."""

    def test_list_saved_jobs_unauthenticated(self, client):
        """Should return 401 when not authenticated."""
        response = client.get("/api/saved-jobs")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_list_saved_jobs_empty(self, client, auth_token):
        """Should return empty list when user has no saved jobs."""
        response = client.get(
            "/api/saved-jobs",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["saved_jobs"] == []

    def test_list_saved_jobs_with_jobs(self, client, auth_token, saved_job, test_job):
        """Should return list of saved jobs with job details."""
        response = client.get(
            "/api/saved-jobs",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["saved_jobs"]) == 1
        assert data["saved_jobs"][0]["job_id"] == test_job.id
        assert data["saved_jobs"][0]["job"]["title"] == "Test Job"
        assert data["saved_jobs"][0]["job"]["organization"] == "Test Org"

    def test_list_saved_jobs_user_isolation(
        self, client, auth_token, second_user_token, saved_job, db, second_user, multiple_jobs
    ):
        """Users should only see their own saved jobs."""
        # Second user saves a different job
        saved2 = SavedJob(user_id=second_user.id, job_id=multiple_jobs[0].id)
        db.add(saved2)
        db.commit()

        # First user should only see their saved job
        response = client.get(
            "/api/saved-jobs",
            cookies={"access_token": auth_token},
        )
        assert len(response.json()["saved_jobs"]) == 1

        # Second user should only see their saved job
        response = client.get(
            "/api/saved-jobs",
            cookies={"access_token": second_user_token},
        )
        assert len(response.json()["saved_jobs"]) == 1
        assert response.json()["saved_jobs"][0]["job"]["title"] == "Job 0"

    def test_list_saved_jobs_ordered_by_saved_at(
        self, client, auth_token, verified_user, multiple_jobs, db
    ):
        """Saved jobs should be ordered by saved_at descending."""
        from datetime import timedelta

        # Save jobs with explicit timestamps to ensure ordering
        base_time = datetime.utcnow()
        for i, job in enumerate(multiple_jobs):
            saved = SavedJob(
                user_id=verified_user.id,
                job_id=job.id,
                saved_at=base_time + timedelta(minutes=i),
            )
            db.add(saved)
        db.commit()

        response = client.get(
            "/api/saved-jobs",
            cookies={"access_token": auth_token},
        )
        data = response.json()
        # Most recently saved (Job 2, saved last) should be first
        assert data["saved_jobs"][0]["job"]["title"] == "Job 2"
        assert data["saved_jobs"][2]["job"]["title"] == "Job 0"


class TestSaveJob:
    """Tests for POST /api/saved-jobs/{job_id} endpoint."""

    def test_save_job_unauthenticated(self, client, test_job):
        """Should return 401 when not authenticated."""
        response = client.post(f"/api/saved-jobs/{test_job.id}")
        assert response.status_code == 401

    def test_save_job_success(self, client, auth_token, test_job, db, verified_user):
        """Should save a job successfully."""
        response = client.post(
            f"/api/saved-jobs/{test_job.id}",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Job saved"
        assert data["job_id"] == test_job.id

        # Verify in database
        saved = db.query(SavedJob).filter(
            SavedJob.user_id == verified_user.id,
            SavedJob.job_id == test_job.id
        ).first()
        assert saved is not None

    def test_save_job_idempotent(self, client, auth_token, saved_job, test_job):
        """Saving an already-saved job should be idempotent."""
        response = client.post(
            f"/api/saved-jobs/{test_job.id}",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Job already saved"

    def test_save_nonexistent_job(self, client, auth_token):
        """Should return 404 for non-existent job."""
        response = client.post(
            "/api/saved-jobs/99999",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_save_stale_job(self, client, auth_token, stale_test_job):
        """Should return 404 for stale job."""
        response = client.post(
            f"/api/saved-jobs/{stale_test_job.id}",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 404


class TestUnsaveJob:
    """Tests for DELETE /api/saved-jobs/{job_id} endpoint."""

    def test_unsave_job_unauthenticated(self, client, test_job):
        """Should return 401 when not authenticated."""
        response = client.delete(f"/api/saved-jobs/{test_job.id}")
        assert response.status_code == 401

    def test_unsave_job_success(self, client, auth_token, saved_job, test_job, db, verified_user):
        """Should unsave a job successfully."""
        response = client.delete(
            f"/api/saved-jobs/{test_job.id}",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Job unsaved"

        # Verify removed from database
        saved = db.query(SavedJob).filter(
            SavedJob.user_id == verified_user.id,
            SavedJob.job_id == test_job.id
        ).first()
        assert saved is None

    def test_unsave_job_not_saved(self, client, auth_token, test_job):
        """Unsaving a job that wasn't saved should handle gracefully."""
        response = client.delete(
            f"/api/saved-jobs/{test_job.id}",
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Job was not saved"

    def test_unsave_other_users_job(
        self, client, second_user_token, saved_job, test_job
    ):
        """User should not be able to unsave another user's saved job."""
        # saved_job belongs to verified_user, try to unsave as second_user
        response = client.delete(
            f"/api/saved-jobs/{test_job.id}",
            cookies={"access_token": second_user_token},
        )
        assert response.status_code == 200
        # Should report not saved (because second_user didn't save it)
        assert response.json()["message"] == "Job was not saved"


class TestHTMXResponses:
    """Tests for HTMX partial responses."""

    def test_list_saved_jobs_htmx(self, client, auth_token, saved_job):
        """Should return HTML partial for HTMX request."""
        response = client.get(
            "/api/saved-jobs",
            headers={"HX-Request": "true"},
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_save_job_htmx(self, client, auth_token, test_job):
        """Should return HTML button partial for HTMX request."""
        response = client.post(
            f"/api/saved-jobs/{test_job.id}",
            headers={"HX-Request": "true"},
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_unsave_job_htmx_from_listing(self, client, auth_token, saved_job, test_job):
        """Should return save button HTML when unsaving from job listing."""
        response = client.delete(
            f"/api/saved-jobs/{test_job.id}",
            headers={"HX-Request": "true"},
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_unsave_job_htmx_from_saved_page(self, client, auth_token, saved_job, test_job):
        """Should return updated saved jobs list when unsaving from saved page."""
        response = client.delete(
            f"/api/saved-jobs/{test_job.id}?from=saved",
            headers={"HX-Request": "true"},
            cookies={"access_token": auth_token},
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
