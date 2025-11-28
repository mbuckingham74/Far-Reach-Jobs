"""Tests for the /api/jobs endpoints."""

from datetime import datetime, timedelta

import pytest

from app.models import Job, ScrapeSource


# Additional fixtures for jobs tests
@pytest.fixture
def second_source(db):
    """Create a second active scrape source."""
    source = ScrapeSource(
        name="Second Source",
        base_url="https://second.com",
        is_active=True,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@pytest.fixture
def job_with_details(db, active_source):
    """Create a job with full details for testing filters."""
    job = Job(
        source_id=active_source.id,
        external_id="detailed-job-1",
        title="Software Engineer",
        organization="Acme Corp",
        location="Anchorage, AK",
        state="AK",
        description="Build amazing software for Alaska communities",
        job_type="Full-time",
        salary_info="$80,000 - $120,000",
        url="https://example.com/jobs/detailed",
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
        is_stale=False,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@pytest.fixture
def multiple_jobs(db, active_source, second_source):
    """Create multiple jobs with varying attributes for filter testing."""
    jobs_data = [
        {
            "source_id": active_source.id,
            "external_id": "multi-1",
            "title": "Nurse Practitioner",
            "organization": "Rural Health Clinic",
            "location": "Bethel, AK",
            "state": "AK",
            "job_type": "Full-time",
            "first_seen_at": datetime.utcnow(),
        },
        {
            "source_id": active_source.id,
            "external_id": "multi-2",
            "title": "Teacher",
            "organization": "Bethel School District",
            "location": "Bethel, AK",
            "state": "AK",
            "job_type": "Full-time",
            "first_seen_at": datetime.utcnow() - timedelta(days=3),
        },
        {
            "source_id": second_source.id,
            "external_id": "multi-3",
            "title": "Pilot",
            "organization": "Bush Air",
            "location": "Fairbanks, AK",
            "state": "AK",
            "job_type": "Part-time",
            "first_seen_at": datetime.utcnow() - timedelta(days=10),
        },
        {
            "source_id": second_source.id,
            "external_id": "multi-4",
            "title": "Park Ranger",
            "organization": "National Park Service",
            "location": "Denali, AK",
            "state": "AK",
            "job_type": "Seasonal",
            "first_seen_at": datetime.utcnow() - timedelta(days=20),
        },
        {
            "source_id": active_source.id,
            "external_id": "multi-5",
            "title": "Fish Processor",
            "organization": "Kodiak Seafood",
            "location": "Kodiak, AK",
            "state": "AK",
            "job_type": "Seasonal",
            "first_seen_at": datetime.utcnow() - timedelta(days=5),
        },
    ]

    created_jobs = []
    for data in jobs_data:
        job = Job(
            url=f"https://example.com/jobs/{data['external_id']}",
            last_seen_at=datetime.utcnow(),
            is_stale=False,
            **data,
        )
        db.add(job)
        created_jobs.append(job)

    db.commit()
    for job in created_jobs:
        db.refresh(job)

    return created_jobs


class TestListJobs:
    """Tests for GET /api/jobs endpoint."""

    def test_list_jobs_empty(self, client):
        """Should return empty list when no jobs exist."""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["total_pages"] == 0

    def test_list_jobs_returns_non_stale_only(self, client, fresh_job, stale_job):
        """Should only return non-stale jobs."""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["id"] == fresh_job.id

    def test_list_jobs_pagination(self, client, multiple_jobs):
        """Should paginate results correctly."""
        # Get first page with 2 items
        response = client.get("/api/jobs?per_page=2&page=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["per_page"] == 2
        assert data["total_pages"] == 3

        # Get second page
        response = client.get("/api/jobs?per_page=2&page=2")
        data = response.json()
        assert len(data["jobs"]) == 2
        assert data["page"] == 2

        # Get last page (should have 1 item)
        response = client.get("/api/jobs?per_page=2&page=3")
        data = response.json()
        assert len(data["jobs"]) == 1
        assert data["page"] == 3

    def test_list_jobs_pagination_limits(self, client, fresh_job):
        """Should enforce pagination limits."""
        # per_page max is 100
        response = client.get("/api/jobs?per_page=200")
        assert response.status_code == 422  # Validation error

        # page min is 1
        response = client.get("/api/jobs?page=0")
        assert response.status_code == 422

    def test_list_jobs_ordered_by_last_seen(self, client, db, active_source):
        """Jobs should be ordered by last_seen_at descending."""
        # Create jobs with different last_seen times
        old_seen = Job(
            source_id=active_source.id,
            external_id="old-seen",
            title="Old Seen",
            url="https://example.com/old",
            first_seen_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow() - timedelta(hours=2),
            is_stale=False,
        )
        new_seen = Job(
            source_id=active_source.id,
            external_id="new-seen",
            title="New Seen",
            url="https://example.com/new",
            first_seen_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
            is_stale=False,
        )
        db.add_all([old_seen, new_seen])
        db.commit()

        response = client.get("/api/jobs")
        data = response.json()
        assert data["jobs"][0]["title"] == "New Seen"
        assert data["jobs"][1]["title"] == "Old Seen"


class TestSearchJobs:
    """Tests for job search functionality."""

    def test_search_by_title(self, client, job_with_details, multiple_jobs):
        """Should find jobs matching title."""
        response = client.get("/api/jobs?q=Software")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "Software" in data["jobs"][0]["title"]

    def test_search_by_organization(self, client, multiple_jobs):
        """Should find jobs matching organization."""
        response = client.get("/api/jobs?q=Rural Health")
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["organization"] == "Rural Health Clinic"

    def test_search_by_description(self, client, job_with_details):
        """Should find jobs matching description."""
        response = client.get("/api/jobs?q=Alaska communities")
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["id"] == job_with_details.id

    def test_search_by_location(self, client, multiple_jobs):
        """Should find jobs matching location."""
        response = client.get("/api/jobs?q=Bethel")
        data = response.json()
        assert data["total"] == 2  # Both Bethel jobs

    def test_search_case_insensitive(self, client, job_with_details):
        """Search should be case insensitive."""
        response = client.get("/api/jobs?q=SOFTWARE")
        data = response.json()
        assert data["total"] == 1

    def test_search_no_results(self, client, multiple_jobs):
        """Should return empty when no matches."""
        response = client.get("/api/jobs?q=nonexistentterm12345")
        data = response.json()
        assert data["total"] == 0
        assert data["jobs"] == []


class TestFilterJobs:
    """Tests for job filtering."""

    def test_filter_by_state(self, client, db, active_source, multiple_jobs):
        """Should filter jobs by state."""
        # Add a job in a different state
        mt_job = Job(
            source_id=active_source.id,
            external_id="mt-job",
            title="Montana Job",
            state="MT",
            url="https://example.com/mt",
            first_seen_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
            is_stale=False,
        )
        db.add(mt_job)
        db.commit()

        # Filter by AK
        response = client.get("/api/jobs?state=AK")
        data = response.json()
        assert data["total"] == 5
        for job in data["jobs"]:
            assert job["state"] == "AK"

        # Filter by MT
        response = client.get("/api/jobs?state=MT")
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["state"] == "MT"

    def test_filter_by_location(self, client, multiple_jobs):
        """Should filter jobs by location (partial match)."""
        response = client.get("/api/jobs?location=Bethel")
        data = response.json()
        assert data["total"] == 2
        for job in data["jobs"]:
            assert "Bethel" in job["location"]

    def test_filter_by_job_type(self, client, multiple_jobs):
        """Should filter jobs by job type."""
        response = client.get("/api/jobs?job_type=Seasonal")
        data = response.json()
        assert data["total"] == 2
        for job in data["jobs"]:
            assert job["job_type"] == "Seasonal"

    def test_filter_by_organization(self, client, multiple_jobs):
        """Should filter jobs by organization (exact match)."""
        response = client.get("/api/jobs?organization=Bush Air")
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["organization"] == "Bush Air"

    def test_filter_by_source_id(self, client, multiple_jobs, active_source, second_source):
        """Should filter jobs by source ID."""
        response = client.get(f"/api/jobs?source_id={active_source.id}")
        data = response.json()
        # 3 jobs from active_source in multiple_jobs
        assert data["total"] == 3

        response = client.get(f"/api/jobs?source_id={second_source.id}")
        data = response.json()
        # 2 jobs from second_source in multiple_jobs
        assert data["total"] == 2

    def test_filter_by_date_posted_1_day(self, client, multiple_jobs):
        """Should filter jobs posted in the last 1 day."""
        response = client.get("/api/jobs?date_posted=1")
        data = response.json()
        # Only jobs from today (first_seen_at within 1 day)
        assert data["total"] == 1  # Only "Nurse Practitioner" was posted today

    def test_filter_by_date_posted_7_days(self, client, multiple_jobs):
        """Should filter jobs posted in the last 7 days."""
        response = client.get("/api/jobs?date_posted=7")
        data = response.json()
        # Jobs posted within 7 days: today, 3 days ago, 5 days ago
        assert data["total"] == 3

    def test_filter_by_date_posted_30_days(self, client, multiple_jobs):
        """Should filter jobs posted in the last 30 days."""
        response = client.get("/api/jobs?date_posted=30")
        data = response.json()
        # All 5 jobs are within 30 days
        assert data["total"] == 5

    def test_combined_filters(self, client, multiple_jobs):
        """Should apply multiple filters together."""
        # Seasonal jobs in AK
        response = client.get("/api/jobs?state=AK&job_type=Seasonal")
        data = response.json()
        assert data["total"] == 2

        # Full-time jobs in Bethel
        response = client.get("/api/jobs?job_type=Full-time&location=Bethel")
        data = response.json()
        assert data["total"] == 2

    def test_invalid_source_id_ignored(self, client, multiple_jobs):
        """Non-numeric source_id should be ignored."""
        response = client.get("/api/jobs?source_id=invalid")
        data = response.json()
        assert data["total"] == 5  # All jobs returned

    def test_invalid_date_posted_ignored(self, client, multiple_jobs):
        """Non-numeric date_posted should be ignored."""
        response = client.get("/api/jobs?date_posted=invalid")
        data = response.json()
        assert data["total"] == 5  # All jobs returned


class TestGetSingleJob:
    """Tests for GET /api/jobs/{job_id} endpoint."""

    def test_get_job_success(self, client, job_with_details):
        """Should return job details for valid ID."""
        response = client.get(f"/api/jobs/{job_with_details.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_with_details.id
        assert data["title"] == "Software Engineer"
        assert data["organization"] == "Acme Corp"
        assert data["location"] == "Anchorage, AK"
        assert data["state"] == "AK"
        assert data["job_type"] == "Full-time"
        assert data["salary_info"] == "$80,000 - $120,000"

    def test_get_job_not_found(self, client):
        """Should return 404 for non-existent job."""
        response = client.get("/api/jobs/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_stale_job_returns_404(self, client, stale_job):
        """Should return 404 for stale job."""
        response = client.get(f"/api/jobs/{stale_job.id}")
        assert response.status_code == 404


class TestGetStates:
    """Tests for GET /api/jobs/states endpoint."""

    def test_get_states_empty(self, client):
        """Should return empty list when no jobs."""
        response = client.get("/api/jobs/states")
        assert response.status_code == 200
        assert response.json()["states"] == []

    def test_get_states_returns_unique(self, client, db, active_source):
        """Should return unique states from non-stale jobs."""
        jobs = [
            Job(source_id=active_source.id, external_id="j1", title="J1", state="AK",
                url="https://a.com/1", first_seen_at=datetime.utcnow(),
                last_seen_at=datetime.utcnow(), is_stale=False),
            Job(source_id=active_source.id, external_id="j2", title="J2", state="AK",
                url="https://a.com/2", first_seen_at=datetime.utcnow(),
                last_seen_at=datetime.utcnow(), is_stale=False),
            Job(source_id=active_source.id, external_id="j3", title="J3", state="MT",
                url="https://a.com/3", first_seen_at=datetime.utcnow(),
                last_seen_at=datetime.utcnow(), is_stale=False),
        ]
        db.add_all(jobs)
        db.commit()

        response = client.get("/api/jobs/states")
        data = response.json()
        assert sorted(data["states"]) == ["AK", "MT"]

    def test_get_states_excludes_stale(self, client, db, active_source):
        """Should exclude states from stale jobs."""
        active_job = Job(
            source_id=active_source.id, external_id="active", title="Active",
            state="AK", url="https://a.com/active",
            first_seen_at=datetime.utcnow(), last_seen_at=datetime.utcnow(),
            is_stale=False
        )
        stale_job = Job(
            source_id=active_source.id, external_id="stale", title="Stale",
            state="MT", url="https://a.com/stale",
            first_seen_at=datetime.utcnow(), last_seen_at=datetime.utcnow(),
            is_stale=True
        )
        db.add_all([active_job, stale_job])
        db.commit()

        response = client.get("/api/jobs/states")
        data = response.json()
        assert data["states"] == ["AK"]  # MT excluded (stale)


class TestGetLocations:
    """Tests for GET /api/jobs/locations endpoint."""

    def test_get_locations_empty(self, client):
        """Should return empty list when no jobs."""
        response = client.get("/api/jobs/locations")
        assert response.status_code == 200
        assert response.json()["locations"] == []

    def test_get_locations_returns_unique(self, client, multiple_jobs):
        """Should return unique locations."""
        response = client.get("/api/jobs/locations")
        data = response.json()
        # Bethel, Fairbanks, Denali, Kodiak
        assert len(data["locations"]) == 4
        assert "Bethel, AK" in data["locations"]

    def test_get_locations_htmx_returns_html(self, client, multiple_jobs):
        """Should return HTML options for HTMX request."""
        response = client.get("/api/jobs/locations", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert '<option value="">All Locations</option>' in response.text
        assert "Bethel, AK" in response.text


class TestGetJobTypes:
    """Tests for GET /api/jobs/job-types endpoint."""

    def test_get_job_types_empty(self, client):
        """Should return empty list when no jobs."""
        response = client.get("/api/jobs/job-types")
        assert response.status_code == 200
        assert response.json()["job_types"] == []

    def test_get_job_types_returns_unique(self, client, multiple_jobs):
        """Should return unique job types."""
        response = client.get("/api/jobs/job-types")
        data = response.json()
        assert sorted(data["job_types"]) == ["Full-time", "Part-time", "Seasonal"]


class TestHTMXResponses:
    """Tests for HTMX partial responses."""

    def test_list_jobs_htmx_returns_html(self, client, fresh_job):
        """Should return HTML partial for HTMX request."""
        response = client.get("/api/jobs", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Should contain job card HTML
        assert fresh_job.title in response.text
