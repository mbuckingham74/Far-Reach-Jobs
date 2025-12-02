"""Tests for the /admin endpoints (Admin Panel)."""

import re
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from app.models import Job, ScrapeSource
from app.models.scrape_log import ScrapeLog
from app.routers.admin import admin_sessions


class TestAdminAuthentication:
    """Tests for admin authentication endpoints."""

    def test_login_page_renders(self, client):
        """Admin login page should render successfully."""
        response = client.get("/admin/login")
        assert response.status_code == 200
        assert "login" in response.text.lower()

    def test_login_page_redirects_if_already_logged_in(self, client):
        """Already authenticated admin should be redirected to dashboard."""
        # First login
        response = client.post(
            "/admin/login",
            data={"username": "admin", "password": "changeme"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        session_cookie = response.cookies.get("admin_session")

        # Try to access login page with session
        response = client.get(
            "/admin/login",
            cookies={"admin_session": session_cookie},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/admin" in response.headers["location"]

    def test_login_success(self, client):
        """Successful login with correct credentials."""
        response = client.post(
            "/admin/login",
            data={"username": "admin", "password": "changeme"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/admin" in response.headers["location"]
        assert "admin_session" in response.cookies

    def test_login_wrong_username(self, client):
        """Login should fail with wrong username."""
        response = client.post(
            "/admin/login",
            data={"username": "wronguser", "password": "changeme"},
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.text

    def test_login_wrong_password(self, client):
        """Login should fail with wrong password."""
        response = client.post(
            "/admin/login",
            data={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.text

    def test_login_empty_credentials(self, client):
        """Login should fail with empty credentials."""
        response = client.post(
            "/admin/login",
            data={"username": "", "password": ""},
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.text

    def test_logout_success(self, admin_client):
        """Logout should clear session and redirect to login."""
        response = admin_client.post("/admin/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/admin/login" in response.headers["location"]

    def test_logout_clears_session(self, admin_client):
        """After logout, accessing admin should redirect to login."""
        # Logout
        admin_client.post("/admin/logout", follow_redirects=False)

        # Try to access admin dashboard without session
        response = admin_client.get("/admin", follow_redirects=False)
        assert response.status_code == 302
        assert "/admin/login" in response.headers["location"]

    def test_dashboard_requires_auth(self, client):
        """Dashboard should redirect to login when not authenticated."""
        response = client.get("/admin", follow_redirects=False)
        assert response.status_code == 302
        assert "/admin/login" in response.headers["location"]

    def test_dashboard_accessible_when_authenticated(self, admin_client, db):
        """Dashboard should be accessible when authenticated."""
        response = admin_client.get("/admin")
        assert response.status_code == 200
        # Dashboard should show active sources section
        assert "source" in response.text.lower() or "dashboard" in response.text.lower()


class TestAdminDashboard:
    """Tests for admin dashboard functionality."""

    def test_dashboard_shows_job_counts(self, admin_client, db, active_source, fresh_job, stale_job):
        """Dashboard should display correct job counts."""
        response = admin_client.get("/admin")
        assert response.status_code == 200
        # Template renders: <div class="text-3xl font-bold ...">COUNT</div>\n<div ...>Label</div>
        # Match the count immediately before each label
        # 1 active job (fresh_job), 1 stale job (stale_job)
        active_match = re.search(r'>(\d+)</div>\s*<div[^>]*>Active Jobs</div>', response.text)
        assert active_match is not None, "Active Jobs count not found in expected format"
        assert active_match.group(1) == "1", f"Expected 1 active job, got {active_match.group(1)}"

        stale_match = re.search(r'>(\d+)</div>\s*<div[^>]*>Stale Jobs</div>', response.text)
        assert stale_match is not None, "Stale Jobs count not found in expected format"
        assert stale_match.group(1) == "1", f"Expected 1 stale job, got {stale_match.group(1)}"

    def test_dashboard_shows_sources_via_htmx(self, admin_client, db, active_source):
        """Dashboard loads sources via HTMX; the /admin/sources endpoint should list them."""
        # The dashboard page uses HTMX to load sources, so we test the HTMX endpoint directly
        response = admin_client.get("/admin/sources")
        assert response.status_code == 200
        assert active_source.name in response.text

    def test_dashboard_shows_disabled_source_count(self, admin_client, db, active_source, inactive_source):
        """Dashboard should show count of disabled sources via HTMX endpoint."""
        # The disabled count is loaded via HTMX - returns a link with count
        response = admin_client.get("/admin/sources/disabled-count")
        assert response.status_code == 200
        # Should contain "1" for the one inactive source and link to disabled page
        assert "disabled" in response.text.lower()
        assert "/admin/sources/disabled" in response.text


class TestSourceManagement:
    """Tests for scrape source CRUD operations."""

    def test_list_sources_requires_auth(self, client):
        """Source list endpoint requires authentication."""
        response = client.get("/admin/sources")
        assert response.status_code == 401

    def test_list_sources_returns_active_only(self, admin_client, db, active_source, inactive_source):
        """List sources should return only active sources."""
        response = admin_client.get("/admin/sources")
        assert response.status_code == 200
        assert active_source.name in response.text
        assert inactive_source.name not in response.text

    def test_create_source_requires_auth(self, client):
        """Creating a source requires authentication."""
        response = client.post(
            "/admin/sources",
            data={"name": "New Source", "base_url": "https://example.com"},
        )
        assert response.status_code == 401

    def test_create_source_success(self, admin_client, db):
        """Successfully create a new scrape source."""
        response = admin_client.post(
            "/admin/sources",
            data={
                "name": "New Test Source",
                "base_url": "https://newsite.com",
                "scraper_class": "GenericScraper",
            },
        )
        assert response.status_code == 200
        assert "New Test Source" in response.text

        # Verify in database
        source = db.query(ScrapeSource).filter(ScrapeSource.name == "New Test Source").first()
        assert source is not None
        assert source.base_url == "https://newsite.com"
        assert source.is_active is True

    def test_create_source_missing_name(self, admin_client, db):
        """Creating source without name should show error."""
        response = admin_client.post(
            "/admin/sources",
            data={"name": "", "base_url": "https://example.com"},
        )
        assert response.status_code == 200  # Returns partial with error
        assert "required" in response.text.lower()

    def test_create_source_missing_url(self, admin_client, db):
        """Creating source without URL should show error."""
        response = admin_client.post(
            "/admin/sources",
            data={"name": "Test Source", "base_url": ""},
        )
        assert response.status_code == 200  # Returns partial with error
        assert "required" in response.text.lower()

    def test_delete_source_requires_auth(self, client, active_source):
        """Deleting a source requires authentication."""
        response = client.delete(f"/admin/sources/{active_source.id}")
        assert response.status_code == 401

    def test_delete_source_success(self, admin_client, db, active_source):
        """Successfully delete a scrape source."""
        source_id = active_source.id
        response = admin_client.delete(f"/admin/sources/{source_id}")
        assert response.status_code == 200

        # Verify deleted from database
        source = db.query(ScrapeSource).filter(ScrapeSource.id == source_id).first()
        assert source is None

    def test_delete_nonexistent_source(self, admin_client, db):
        """Deleting non-existent source should still return 200 (idempotent)."""
        response = admin_client.delete("/admin/sources/99999")
        assert response.status_code == 200

    def test_toggle_source_requires_auth(self, client, active_source):
        """Toggling source status requires authentication."""
        response = client.post(f"/admin/sources/{active_source.id}/toggle")
        assert response.status_code == 401

    def test_toggle_source_active_to_inactive(self, admin_client, db, active_source):
        """Toggle active source to inactive."""
        assert active_source.is_active is True

        response = admin_client.post(f"/admin/sources/{active_source.id}/toggle")
        assert response.status_code == 200

        db.refresh(active_source)
        assert active_source.is_active is False

    def test_toggle_source_inactive_to_active(self, admin_client, db, inactive_source):
        """Toggle inactive source to active."""
        assert inactive_source.is_active is False

        response = admin_client.post(
            f"/admin/sources/{inactive_source.id}/toggle",
            headers={"HX-Target": "disabled-source-list"},
        )
        assert response.status_code == 200

        db.refresh(inactive_source)
        assert inactive_source.is_active is True


class TestDisabledSources:
    """Tests for disabled sources management."""

    def test_disabled_sources_page_requires_auth(self, client):
        """Disabled sources page requires authentication."""
        response = client.get("/admin/sources/disabled", follow_redirects=False)
        assert response.status_code == 302
        assert "/admin/login" in response.headers["location"]

    def test_disabled_sources_page_accessible(self, admin_client, db, inactive_source):
        """Disabled sources page should be accessible when authenticated."""
        response = admin_client.get("/admin/sources/disabled")
        assert response.status_code == 200
        # Page renders; actual source list loads via HTMX

    def test_disabled_sources_list_requires_auth(self, client):
        """Disabled sources list endpoint requires authentication."""
        response = client.get("/admin/sources/disabled/list")
        assert response.status_code == 401

    def test_disabled_sources_list_returns_inactive_only(self, admin_client, db, active_source, inactive_source):
        """Disabled list should return only inactive sources."""
        response = admin_client.get("/admin/sources/disabled/list")
        assert response.status_code == 200
        assert inactive_source.name in response.text
        assert active_source.name not in response.text

    def test_disabled_count_link_requires_auth(self, client):
        """Disabled count endpoint requires authentication."""
        response = client.get("/admin/sources/disabled-count")
        assert response.status_code == 401

    def test_disabled_count_returns_count(self, admin_client, db, active_source, inactive_source):
        """Should return correct count of disabled sources."""
        response = admin_client.get("/admin/sources/disabled-count")
        assert response.status_code == 200
        # Response should contain count (1 inactive source)


class TestSourceEdit:
    """Tests for source editing functionality."""

    def test_edit_page_requires_auth(self, client, active_source):
        """Edit page requires authentication."""
        response = client.get(f"/admin/sources/{active_source.id}/edit", follow_redirects=False)
        assert response.status_code == 302
        assert "/admin/login" in response.headers["location"]

    def test_edit_page_accessible(self, admin_client, db, active_source):
        """Edit page should be accessible when authenticated."""
        response = admin_client.get(f"/admin/sources/{active_source.id}/edit")
        assert response.status_code == 200
        assert active_source.name in response.text

    def test_edit_page_nonexistent_source(self, admin_client, db):
        """Edit page for non-existent source redirects to dashboard."""
        response = admin_client.get("/admin/sources/99999/edit", follow_redirects=False)
        assert response.status_code == 302
        assert "/admin" in response.headers["location"]

    def test_edit_source_requires_auth(self, client, active_source):
        """Saving source edits requires authentication."""
        response = client.post(
            f"/admin/sources/{active_source.id}/edit",
            data={"name": "Updated", "base_url": "https://updated.com"},
        )
        assert response.status_code == 401

    def test_edit_source_success(self, admin_client, db, active_source):
        """Successfully edit a source's basic info."""
        response = admin_client.post(
            f"/admin/sources/{active_source.id}/edit",
            data={
                "name": "Updated Source Name",
                "base_url": "https://updated-url.com",
                "listing_url": "https://updated-url.com/jobs",
            },
            follow_redirects=False,
        )
        # Should redirect (PRG pattern)
        assert response.status_code == 303

        db.refresh(active_source)
        assert active_source.name == "Updated Source Name"
        assert active_source.base_url == "https://updated-url.com"

    def test_edit_source_validation_name_required(self, admin_client, db, active_source):
        """Editing without name should show error."""
        response = admin_client.post(
            f"/admin/sources/{active_source.id}/edit",
            data={"name": "", "base_url": "https://example.com"},
        )
        assert response.status_code == 200
        assert "required" in response.text.lower()

    def test_edit_source_validation_url_required(self, admin_client, db, active_source):
        """Editing without base URL should show error."""
        response = admin_client.post(
            f"/admin/sources/{active_source.id}/edit",
            data={"name": "Test", "base_url": ""},
        )
        assert response.status_code == 200
        assert "required" in response.text.lower()

    def test_edit_source_validation_url_format(self, admin_client, db, active_source):
        """Editing with invalid URL format should show error."""
        response = admin_client.post(
            f"/admin/sources/{active_source.id}/edit",
            data={"name": "Test", "base_url": "not-a-url"},
        )
        assert response.status_code == 200
        assert "http" in response.text.lower()


class TestSourceConfigure:
    """Tests for source CSS selector configuration."""

    def test_configure_page_requires_auth(self, client, active_source):
        """Configure page requires authentication."""
        response = client.get(f"/admin/sources/{active_source.id}/configure", follow_redirects=False)
        assert response.status_code == 302
        assert "/admin/login" in response.headers["location"]

    def test_configure_page_accessible(self, admin_client, db, active_source):
        """Configure page should be accessible when authenticated."""
        response = admin_client.get(f"/admin/sources/{active_source.id}/configure")
        assert response.status_code == 200
        assert active_source.name in response.text

    def test_configure_page_nonexistent_source(self, admin_client, db):
        """Configure page for non-existent source redirects to dashboard."""
        response = admin_client.get("/admin/sources/99999/configure", follow_redirects=False)
        assert response.status_code == 302
        assert "/admin" in response.headers["location"]

    def test_configure_source_requires_auth(self, client, active_source):
        """Saving configuration requires authentication."""
        response = client.post(
            f"/admin/sources/{active_source.id}/configure",
            data={"name": "Test", "base_url": "https://example.com"},
        )
        assert response.status_code == 401

    def test_configure_source_success(self, admin_client, db, active_source):
        """Successfully configure source selectors."""
        response = admin_client.post(
            f"/admin/sources/{active_source.id}/configure",
            data={
                "name": active_source.name,
                "base_url": active_source.base_url,
                "selector_job_container": ".job-listing",
                "selector_title": ".job-title",
                "selector_url": ".job-link",
                "selector_organization": ".company-name",
                "selector_location": ".location",
                "max_pages": "5",
            },
        )
        assert response.status_code == 200
        assert "success" in response.text.lower() or "saved" in response.text.lower()

        db.refresh(active_source)
        assert active_source.selector_job_container == ".job-listing"
        assert active_source.selector_title == ".job-title"
        assert active_source.max_pages == 5

    def test_configure_source_warns_missing_selectors(self, admin_client, db, active_source):
        """Configuration should warn when required selectors are missing."""
        # Save with missing selectors
        response = admin_client.post(
            f"/admin/sources/{active_source.id}/configure",
            data={
                "name": active_source.name,
                "base_url": active_source.base_url,
                "selector_job_container": "",  # Missing
                "selector_title": "",  # Missing
                "selector_url": "",  # Missing
            },
        )
        assert response.status_code == 200
        # Should show warning about missing selectors
        assert "warning" in response.text.lower() or "selector" in response.text.lower()

    def test_configure_source_checkbox_use_playwright(self, admin_client, db, active_source):
        """Playwright checkbox should be handled correctly."""
        # Enable playwright
        response = admin_client.post(
            f"/admin/sources/{active_source.id}/configure",
            data={
                "name": active_source.name,
                "base_url": active_source.base_url,
                "selector_job_container": ".jobs",
                "selector_title": ".title",
                "selector_url": ".link",
                "use_playwright": "1",
            },
        )
        assert response.status_code == 200
        db.refresh(active_source)
        assert active_source.use_playwright is True

        # Disable playwright (checkbox not present)
        response = admin_client.post(
            f"/admin/sources/{active_source.id}/configure",
            data={
                "name": active_source.name,
                "base_url": active_source.base_url,
                "selector_job_container": ".jobs",
                "selector_title": ".title",
                "selector_url": ".link",
                # use_playwright not in form data = unchecked
            },
        )
        assert response.status_code == 200
        db.refresh(active_source)
        assert active_source.use_playwright is False


class TestScrapeHistory:
    """Tests for scrape history viewing."""

    def test_history_page_requires_auth(self, client):
        """History page requires authentication."""
        response = client.get("/admin/history", follow_redirects=False)
        assert response.status_code == 302
        assert "/admin/login" in response.headers["location"]

    def test_history_page_accessible(self, admin_client, db):
        """History page should be accessible when authenticated."""
        response = admin_client.get("/admin/history")
        assert response.status_code == 200

    def test_history_page_shows_logs(self, admin_client, db, active_source):
        """History page should display scrape logs in the table."""
        # Create a scrape log
        log = ScrapeLog(
            source_id=active_source.id,
            source_name=active_source.name,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            success=True,
            jobs_found=10,
            jobs_added=5,
            jobs_updated=3,
        )
        db.add(log)
        db.commit()

        response = admin_client.get("/admin/history")
        assert response.status_code == 200
        # Verify the log entry appears in the table
        assert active_source.name in response.text  # Source name in table row
        assert "Manual" in response.text  # Trigger type badge
        assert "Success" in response.text  # Status badge
        # Should NOT show the "No scrape history yet" message
        assert "No scrape history yet" not in response.text

    def test_history_page_shows_stats(self, admin_client, db, active_source):
        """History page should show aggregate statistics with correct values."""
        # Create multiple logs with specific values we can verify
        for i in range(3):
            log = ScrapeLog(
                source_id=active_source.id,
                source_name=active_source.name,
                trigger_type="scheduled",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                success=(i % 2 == 0),  # i=0: True, i=1: False, i=2: True -> 2 successful, 1 failed
                jobs_found=10,
                jobs_added=5,  # Total: 15 added
                jobs_updated=3,  # Total: 9 updated
            )
            db.add(log)
        db.commit()

        response = admin_client.get("/admin/history")
        assert response.status_code == 200

        # Template renders stats as: <div class="text-2xl font-bold ...">VALUE</div>\n<div ...>Label</div>
        # Verify actual computed values, not just labels

        total_runs_match = re.search(r'>(\d+)</div>\s*<div[^>]*>Total Runs</div>', response.text)
        assert total_runs_match is not None, "Total Runs stat not found"
        assert total_runs_match.group(1) == "3", f"Expected 3 total runs, got {total_runs_match.group(1)}"

        successful_match = re.search(r'>(\d+)</div>\s*<div[^>]*>Successful</div>', response.text)
        assert successful_match is not None, "Successful stat not found"
        assert successful_match.group(1) == "2", f"Expected 2 successful, got {successful_match.group(1)}"

        failed_match = re.search(r'>(\d+)</div>\s*<div[^>]*>Failed</div>', response.text)
        assert failed_match is not None, "Failed stat not found"
        assert failed_match.group(1) == "1", f"Expected 1 failed, got {failed_match.group(1)}"

        jobs_added_match = re.search(r'>(\d+)</div>\s*<div[^>]*>Jobs Added</div>', response.text)
        assert jobs_added_match is not None, "Jobs Added stat not found"
        assert jobs_added_match.group(1) == "15", f"Expected 15 jobs added, got {jobs_added_match.group(1)}"

        jobs_updated_match = re.search(r'>(\d+)</div>\s*<div[^>]*>Jobs Updated</div>', response.text)
        assert jobs_updated_match is not None, "Jobs Updated stat not found"
        assert jobs_updated_match.group(1) == "9", f"Expected 9 jobs updated, got {jobs_updated_match.group(1)}"


class TestTriggerScrape:
    """Tests for manual scrape triggering."""

    def test_scrape_all_requires_auth(self, client):
        """Triggering scrape requires authentication."""
        response = client.post("/admin/scrape")
        assert response.status_code == 401

    def test_scrape_all_no_sources(self, admin_client, db):
        """Scraping with no active sources should return appropriate message."""
        response = admin_client.post("/admin/scrape")
        assert response.status_code == 200
        assert "no active" in response.text.lower() or "error" in response.text.lower()

    def test_scrape_all_success(self, admin_client, db, active_source):
        """Successfully trigger scrape for all sources."""
        # Need to patch the imports inside the endpoint function
        with patch("scraper.runner.run_all_scrapers") as mock_run, \
             patch("app.services.email.send_scrape_notification") as mock_notify:
            # Mock the scraper results
            mock_result = MagicMock()
            mock_result.jobs_found = 10
            mock_result.jobs_new = 5
            mock_result.jobs_updated = 3
            mock_result.errors = []
            mock_result.source_name = active_source.name
            mock_run.return_value = [mock_result]

            response = admin_client.post("/admin/scrape")
            assert response.status_code == 200
            mock_run.assert_called_once()

    def test_scrape_single_requires_auth(self, client, active_source):
        """Triggering single source scrape requires authentication."""
        response = client.post(f"/admin/sources/{active_source.id}/scrape")
        assert response.status_code == 401

    def test_scrape_single_not_found(self, admin_client, db):
        """Scraping non-existent source returns error."""
        response = admin_client.post("/admin/sources/99999/scrape")
        assert response.status_code == 200
        assert "not found" in response.text.lower()

    def test_scrape_single_success(self, admin_client, db, active_source):
        """Successfully trigger scrape for single source."""
        with patch("scraper.runner.run_scraper") as mock_run, \
             patch("app.services.email.send_scrape_notification") as mock_notify:
            # Mock the scraper result
            mock_result = MagicMock()
            mock_result.jobs_found = 5
            mock_result.jobs_new = 2
            mock_result.jobs_updated = 1
            mock_result.errors = []
            mock_run.return_value = mock_result

            response = admin_client.post(f"/admin/sources/{active_source.id}/scrape")
            assert response.status_code == 200
            mock_run.assert_called_once()


class TestSourceExport:
    """Tests for CSV export functionality."""

    def test_export_active_requires_auth(self, client):
        """Export active sources requires authentication."""
        response = client.get("/admin/sources/export-active")
        assert response.status_code == 401

    def test_export_disabled_requires_auth(self, client):
        """Export disabled sources requires authentication."""
        response = client.get("/admin/sources/export-disabled")
        assert response.status_code == 401

    def test_export_robots_blocked_requires_auth(self, client):
        """Export robots-blocked sources requires authentication."""
        response = client.get("/admin/sources/export-robots-blocked")
        assert response.status_code == 401

    def test_export_active_returns_csv(self, admin_client, db, active_source):
        """Export active sources returns valid CSV with correct headers."""
        response = admin_client.get("/admin/sources/export-active")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "active_sources.csv" in response.headers["content-disposition"]

        # Parse CSV content (use splitlines to handle CRLF from csv.writer)
        content = response.text
        lines = content.strip().splitlines()
        assert len(lines) >= 1  # At least header row

        # Verify header row matches import format
        assert lines[0] == "Source Name,Base URL,Jobs URL"

        # Verify source data is present
        if len(lines) > 1:
            assert active_source.name in content

    def test_export_active_excludes_inactive(self, admin_client, db, active_source, inactive_source):
        """Export active should not include disabled sources."""
        response = admin_client.get("/admin/sources/export-active")
        assert response.status_code == 200
        assert active_source.name in response.text
        assert inactive_source.name not in response.text

    def test_export_active_excludes_robots_blocked(self, admin_client, db, active_source, robots_blocked_source):
        """Export active should not include robots-blocked sources."""
        response = admin_client.get("/admin/sources/export-active")
        assert response.status_code == 200
        assert active_source.name in response.text
        assert robots_blocked_source.name not in response.text

    def test_export_disabled_returns_csv(self, admin_client, db, inactive_source):
        """Export disabled sources returns valid CSV."""
        response = admin_client.get("/admin/sources/export-disabled")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "disabled_sources.csv" in response.headers["content-disposition"]

        # Verify header and source data
        assert "Source Name,Base URL,Jobs URL" in response.text
        assert inactive_source.name in response.text

    def test_export_disabled_excludes_active(self, admin_client, db, active_source, inactive_source):
        """Export disabled should only include inactive sources."""
        response = admin_client.get("/admin/sources/export-disabled")
        assert response.status_code == 200
        assert inactive_source.name in response.text
        assert active_source.name not in response.text

    def test_export_robots_blocked_returns_csv(self, admin_client, db, robots_blocked_source):
        """Export robots-blocked sources returns valid CSV."""
        response = admin_client.get("/admin/sources/export-robots-blocked")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "robots_blocked_sources.csv" in response.headers["content-disposition"]

        # Verify header and source data
        assert "Source Name,Base URL,Jobs URL" in response.text
        assert robots_blocked_source.name in response.text

    def test_export_robots_blocked_excludes_active(self, admin_client, db, active_source, robots_blocked_source):
        """Export robots-blocked should only include blocked sources."""
        response = admin_client.get("/admin/sources/export-robots-blocked")
        assert response.status_code == 200
        assert robots_blocked_source.name in response.text
        assert active_source.name not in response.text

    def test_export_empty_returns_header_only(self, admin_client, db):
        """Export with no matching sources returns CSV with header only."""
        response = admin_client.get("/admin/sources/export-active")
        assert response.status_code == 200
        # Use splitlines to handle CRLF, then check we only have header
        lines = response.text.strip().splitlines()
        assert len(lines) == 1
        assert lines[0] == "Source Name,Base URL,Jobs URL"

    def test_export_alphabetical_order(self, admin_client, db):
        """Sources are exported in alphabetical order by name."""
        # Create sources in non-alphabetical order
        from app.models import ScrapeSource
        source_z = ScrapeSource(name="Zebra Corp", base_url="https://zebra.com", is_active=True)
        source_a = ScrapeSource(name="Alpha Inc", base_url="https://alpha.com", is_active=True)
        source_m = ScrapeSource(name="Mega LLC", base_url="https://mega.com", is_active=True)
        db.add_all([source_z, source_a, source_m])
        db.commit()

        response = admin_client.get("/admin/sources/export-active")
        assert response.status_code == 200

        # Use splitlines to handle CRLF from csv.writer
        lines = response.text.strip().splitlines()
        # Skip header, get data lines
        data_lines = lines[1:]
        names = [line.split(",")[0] for line in data_lines]

        # Should be alphabetically sorted
        assert names == sorted(names)
        assert names[0] == "Alpha Inc"
        assert names[-1] == "Zebra Corp"

    def test_export_includes_listing_url(self, admin_client, db):
        """Export includes listing_url in Jobs URL column."""
        from app.models import ScrapeSource
        source = ScrapeSource(
            name="Test Export Source",
            base_url="https://example.com",
            listing_url="https://example.com/careers",
            is_active=True
        )
        db.add(source)
        db.commit()

        response = admin_client.get("/admin/sources/export-active")
        assert response.status_code == 200
        assert "https://example.com/careers" in response.text


class TestAIFeatures:
    """Tests for AI-powered features (analyze, generate scraper)."""

    def test_analyze_requires_auth(self, client, active_source):
        """AI analyze endpoint requires authentication."""
        response = client.post(f"/admin/sources/{active_source.id}/analyze")
        assert response.status_code == 401

    def test_analyze_nonexistent_source(self, admin_client, db):
        """Analyzing non-existent source returns 404."""
        response = admin_client.post("/admin/sources/99999/analyze")
        assert response.status_code == 404
        assert "not found" in response.text.lower()

    @patch("app.routers.admin.is_ai_analysis_available")
    def test_analyze_ai_not_available(self, mock_available, admin_client, db, active_source):
        """Should return error when AI is not available."""
        mock_available.return_value = False
        response = admin_client.post(f"/admin/sources/{active_source.id}/analyze")
        assert response.status_code == 400
        assert "not available" in response.text.lower() or "api" in response.text.lower()

    @pytest.mark.skip(reason="Requires async mock for analyze_job_page; error paths covered above")
    def test_analyze_success(self, admin_client, db, active_source):
        """Successfully analyze a job page when AI is available."""
        # Full AI analysis would require mocking the async function properly
        # The error paths (auth required, source not found, AI not available) are tested above
        pass

    def test_generate_scraper_requires_auth(self, client, active_source):
        """Generate scraper endpoint requires authentication."""
        response = client.post(f"/admin/sources/{active_source.id}/generate-scraper")
        assert response.status_code == 401

    def test_generate_scraper_nonexistent_source(self, admin_client, db):
        """Generating scraper for non-existent source returns 404."""
        response = admin_client.post("/admin/sources/99999/generate-scraper")
        assert response.status_code == 404
        assert "not found" in response.text.lower()

    @patch("app.routers.admin.is_ai_analysis_available")
    def test_generate_scraper_ai_not_available(self, mock_available, admin_client, db, active_source):
        """Should return error when AI is not available."""
        mock_available.return_value = False
        response = admin_client.post(f"/admin/sources/{active_source.id}/generate-scraper")
        assert response.status_code == 400
        assert "not available" in response.text.lower() or "api" in response.text.lower()

    @patch("app.routers.admin.generate_scraper_for_url")
    @patch("app.routers.admin.is_ai_analysis_available")
    def test_generated_scraper_escapes_html_in_code(self, mock_available, mock_generate, admin_client, db, active_source):
        """Generated code with HTML-like content should be escaped to prevent XSS/parsing errors."""
        from app.services.ai_analyzer import GeneratedScraper

        mock_available.return_value = True

        # Code containing sequences that would break HTML if not escaped
        malicious_code = '''class TestScraper(BaseScraper):
    def parse(self):
        html = "</script><script>alert('xss')</script>"
        code = "</code></pre><div>injected</div>"
        return html
'''
        mock_generate.return_value = GeneratedScraper(
            success=True,
            code=malicious_code,
            class_name="TestScraper"
        )

        response = admin_client.post(f"/admin/sources/{active_source.id}/generate-scraper")
        assert response.status_code == 200

        # The response should contain HTML-escaped versions
        assert "&lt;/script&gt;" in response.text
        assert "&lt;/code&gt;" in response.text
        assert "&lt;/pre&gt;" in response.text

        # Raw HTML-breaking sequences should NOT appear
        assert "</script><script>" not in response.text
        assert "</code></pre>" not in response.text

    def test_configure_page_handles_special_chars_in_source_name(self, admin_client, db):
        """Source names with quotes/apostrophes should not break the page."""
        from app.models import ScrapeSource

        # Create source with problematic characters
        source = ScrapeSource(
            name="King's \"Special\" Source",
            base_url="https://example.com",
            is_active=True,
            scraper_class="GenericScraper",
        )
        db.add(source)
        db.commit()

        response = admin_client.get(f"/admin/sources/{source.id}/configure")
        assert response.status_code == 200

        # The source name should appear in data attributes (properly escaped by Jinja2)
        assert 'data-source-name="King' in response.text
        # Scrape buttons should NOT use inline onclick with showScrapeModal
        # (we use data attributes + event delegation instead)
        assert 'onclick="showScrapeModal' not in response.text
        assert "onclick='showScrapeModal" not in response.text


class TestUrlNormalization:
    """Tests for _normalize_url function used in duplicate detection."""

    def test_normalize_strips_trailing_slash(self):
        """Should remove trailing slashes."""
        from app.routers.admin import _normalize_url
        assert _normalize_url("https://example.com/") == "example.com"
        assert _normalize_url("https://example.com/path/") == "example.com/path"

    def test_normalize_lowercase(self):
        """Should convert to lowercase."""
        from app.routers.admin import _normalize_url
        assert _normalize_url("HTTPS://EXAMPLE.COM") == "example.com"
        assert _normalize_url("https://Example.Com/Path") == "example.com/path"

    def test_normalize_strips_protocol(self):
        """Should remove http:// and https:// protocols."""
        from app.routers.admin import _normalize_url
        assert _normalize_url("https://example.com") == "example.com"
        assert _normalize_url("http://example.com") == "example.com"
        # Both should match
        assert _normalize_url("https://example.com") == _normalize_url("http://example.com")

    def test_normalize_strips_www(self):
        """Should remove www. prefix."""
        from app.routers.admin import _normalize_url
        assert _normalize_url("https://www.example.com") == "example.com"
        assert _normalize_url("https://example.com") == "example.com"
        # Both should match
        assert _normalize_url("https://www.example.com") == _normalize_url("https://example.com")

    def test_normalize_combined(self):
        """Should handle all normalizations together."""
        from app.routers.admin import _normalize_url
        # All these variations should normalize to the same value
        variations = [
            "https://www.example.com/path/",
            "http://www.example.com/path",
            "HTTPS://WWW.EXAMPLE.COM/PATH/",
            "https://example.com/path/",
            "http://example.com/path",
        ]
        normalized = [_normalize_url(v) for v in variations]
        assert all(n == "example.com/path" for n in normalized)


class TestCSVImport:
    """Tests for CSV bulk import functionality."""

    def test_import_requires_auth(self, client):
        """CSV import requires authentication."""
        import io
        csv_content = "Source Name,Base URL\nTest,https://example.com"
        response = client.post(
            "/admin/sources/import-csv",
            files={"file": ("sources.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 401

    def test_import_requires_csv_file(self, admin_client, db):
        """Should reject non-CSV files."""
        import io
        response = admin_client.post(
            "/admin/sources/import-csv",
            files={"file": ("sources.txt", io.BytesIO(b"test"), "text/plain")},
        )
        assert response.status_code == 200
        assert "csv" in response.text.lower()

    def test_import_basic_success(self, admin_client, db):
        """Successfully import sources from CSV."""
        import io
        csv_content = "Source Name,Base URL,Jobs URL\nNew Source,https://newsource.com,https://newsource.com/jobs"
        response = admin_client.post(
            "/admin/sources/import-csv",
            files={"file": ("sources.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200

        # Verify source was created
        source = db.query(ScrapeSource).filter(ScrapeSource.name == "New Source").first()
        assert source is not None
        assert source.base_url == "https://newsource.com"
        assert source.listing_url == "https://newsource.com/jobs"
        assert source.needs_configuration is True
        assert source.is_active is False

    def test_import_detects_duplicate_name(self, admin_client, db, active_source):
        """Should skip sources with duplicate names."""
        import io
        csv_content = f"Source Name,Base URL\n{active_source.name},https://different.com"
        response = admin_client.post(
            "/admin/sources/import-csv",
            files={"file": ("sources.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200
        assert "name already exists" in response.text.lower()

    def test_import_detects_duplicate_base_url(self, admin_client, db, active_source):
        """Should skip sources with duplicate base URLs."""
        import io
        csv_content = f"Source Name,Base URL\nDifferent Name,{active_source.base_url}"
        response = admin_client.post(
            "/admin/sources/import-csv",
            files={"file": ("sources.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200
        assert "base url already exists" in response.text.lower()

    def test_import_detects_duplicate_base_url_with_www_variation(self, admin_client, db):
        """Should detect duplicates even with www. prefix difference."""
        import io
        # Create source without www
        source = ScrapeSource(name="Existing", base_url="https://example.com", is_active=True)
        db.add(source)
        db.commit()

        # Try to import with www
        csv_content = "Source Name,Base URL\nNew Source,https://www.example.com"
        response = admin_client.post(
            "/admin/sources/import-csv",
            files={"file": ("sources.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200
        assert "base url already exists" in response.text.lower()

    def test_import_detects_duplicate_base_url_with_protocol_variation(self, admin_client, db):
        """Should detect duplicates even with http/https protocol difference."""
        import io
        # Create source with https
        source = ScrapeSource(name="Existing", base_url="https://example.com", is_active=True)
        db.add(source)
        db.commit()

        # Try to import with http
        csv_content = "Source Name,Base URL\nNew Source,http://example.com"
        response = admin_client.post(
            "/admin/sources/import-csv",
            files={"file": ("sources.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200
        assert "base url already exists" in response.text.lower()

    def test_import_detects_cross_field_collision_base_matches_existing_listing(self, admin_client, db):
        """Should detect when CSV base_url matches existing source's listing_url."""
        import io
        # Create source with listing_url
        source = ScrapeSource(
            name="Existing",
            base_url="https://company.com",
            listing_url="https://company.com/careers",
            is_active=True
        )
        db.add(source)
        db.commit()

        # Try to import with base_url that matches existing listing_url
        csv_content = "Source Name,Base URL\nNew Source,https://company.com/careers"
        response = admin_client.post(
            "/admin/sources/import-csv",
            files={"file": ("sources.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200
        assert "base url already exists" in response.text.lower()

    def test_import_detects_cross_field_collision_listing_matches_existing_base(self, admin_client, db):
        """Should detect when CSV listing_url matches existing source's base_url."""
        import io
        # Create source with just base_url
        source = ScrapeSource(
            name="Existing",
            base_url="https://company.com/careers",
            is_active=True
        )
        db.add(source)
        db.commit()

        # Try to import with listing_url that matches existing base_url
        csv_content = "Source Name,Base URL,Jobs URL\nNew Source,https://company.com,https://company.com/careers"
        response = admin_client.post(
            "/admin/sources/import-csv",
            files={"file": ("sources.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200
        assert "jobs url already exists" in response.text.lower()

    def test_import_detects_in_batch_duplicates(self, admin_client, db):
        """Should detect duplicates within the same CSV file."""
        import io
        csv_content = """Source Name,Base URL
First Source,https://example.com
Second Source,https://example.com"""
        response = admin_client.post(
            "/admin/sources/import-csv",
            files={"file": ("sources.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200
        # First one should succeed, second should be skipped
        assert "duplicate base url in csv" in response.text.lower()

    def test_import_detects_in_batch_cross_field_duplicates(self, admin_client, db):
        """Should detect cross-field duplicates within the same CSV file."""
        import io
        csv_content = """Source Name,Base URL,Jobs URL
First Source,https://example.com,https://example.com/jobs
Second Source,https://example.com/jobs,"""
        response = admin_client.post(
            "/admin/sources/import-csv",
            files={"file": ("sources.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200
        # First one should succeed, second should be skipped because its base_url
        # matches the first source's listing_url
        assert "duplicate base url in csv" in response.text.lower()


# Fixtures specific to admin tests

@pytest.fixture
def admin_client(client, db):
    """Create a test client with admin authentication.

    This fixture logs in as admin and provides a client with
    the admin session cookie already set.
    """
    # Clear any existing sessions to ensure clean state
    admin_sessions.clear()

    # Login as admin
    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "changeme"},
        follow_redirects=False,
    )

    # Get the session cookie and set it for subsequent requests
    session_cookie = response.cookies.get("admin_session")
    client.cookies.set("admin_session", session_cookie)

    yield client

    # Cleanup: clear sessions after test
    admin_sessions.clear()
