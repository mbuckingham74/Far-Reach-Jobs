"""Tests for the /api/jobs/stats endpoint."""


def test_stats_empty_database(client):
    """Stats should return zeros when database is empty."""
    response = client.get("/api/jobs/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["sources_count"] == 0
    assert data["jobs_count"] == 0
    assert data["new_this_week"] == 0


def test_stats_counts_active_sources_only(client, active_source, inactive_source):
    """Stats should only count active sources."""
    response = client.get("/api/jobs/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["sources_count"] == 1


def test_stats_excludes_stale_jobs(client, fresh_job, stale_job):
    """Stats should exclude stale jobs from total count."""
    response = client.get("/api/jobs/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["jobs_count"] == 1


def test_stats_new_this_week_includes_recent_jobs(client, fresh_job):
    """New this week should include jobs first seen in last 7 days."""
    response = client.get("/api/jobs/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["new_this_week"] == 1


def test_stats_new_this_week_excludes_old_jobs(client, old_job):
    """New this week should exclude jobs first seen more than 7 days ago."""
    response = client.get("/api/jobs/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["new_this_week"] == 0
    assert data["jobs_count"] == 1  # Still counts in total


def test_stats_new_this_week_excludes_stale_jobs(client, stale_job):
    """New this week should exclude stale jobs even if recent."""
    response = client.get("/api/jobs/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["new_this_week"] == 0


def test_stats_combined_scenario(client, active_source, inactive_source, fresh_job, old_job, stale_job):
    """Test stats with a mix of sources and jobs."""
    response = client.get("/api/jobs/stats")
    assert response.status_code == 200
    data = response.json()
    # 1 active source (inactive_source not counted)
    assert data["sources_count"] == 1
    # 2 non-stale jobs (fresh + old, stale not counted)
    assert data["jobs_count"] == 2
    # 1 new this week (fresh only, old is >7 days, stale excluded)
    assert data["new_this_week"] == 1


def test_stats_returns_html_for_htmx_request(client, fresh_job):
    """Stats should return HTML partial for HTMX requests."""
    response = client.get("/api/jobs/stats", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Check that the HTML contains the expected values
    assert "1" in response.text  # sources_count or jobs_count
    assert "Sources" in response.text
    assert "Jobs Available" in response.text
    assert "New This Week" in response.text
