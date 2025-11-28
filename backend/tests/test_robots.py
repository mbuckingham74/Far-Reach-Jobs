"""Tests for robots.txt checker."""

import pytest
from unittest.mock import patch, MagicMock
import httpx

from scraper.robots import RobotsChecker


class TestRobotsCheckerCrossDomain:
    """Test cross-domain robots.txt checking."""

    @pytest.fixture
    def mock_httpx_get(self):
        """Mock httpx.get to return different robots.txt for different domains."""
        def get_response(url, **kwargs):
            response = MagicMock()

            if "example.com" in url:
                # example.com blocks everything for unknown UAs
                response.status_code = 200
                response.text = """
User-agent: *
Disallow: /
"""
            elif "jobs.example.org" in url:
                # jobs.example.org allows everything
                response.status_code = 200
                response.text = """
User-agent: *
Allow: /
"""
            elif "norobots.example.net" in url:
                # No robots.txt
                response.status_code = 404
                response.text = "Not Found"
            else:
                response.status_code = 200
                response.text = ""

            return response

        with patch("scraper.robots.httpx.get", side_effect=get_response):
            yield

    def test_cross_domain_uses_target_domain_robots(self, mock_httpx_get):
        """When fetching URL from different domain, check that domain's robots.txt."""
        # Initialize checker with example.com (which blocks everything)
        checker = RobotsChecker("https://example.com")

        # Check URL on jobs.example.org (which allows everything)
        # Should check jobs.example.org's robots.txt, not example.com's
        assert checker.can_fetch("https://jobs.example.org/careers") is True

    def test_same_domain_uses_base_robots(self, mock_httpx_get):
        """When fetching URL from same domain, use the base domain's robots.txt."""
        # Initialize checker with example.com (which blocks everything)
        checker = RobotsChecker("https://example.com")

        # Check URL on example.com - should be blocked
        assert checker.can_fetch("https://example.com/private") is False

    def test_cross_domain_caches_results(self, mock_httpx_get):
        """Cross-domain robots.txt results should be cached."""
        checker = RobotsChecker("https://example.com")

        # First call loads robots.txt for jobs.example.org
        assert checker.can_fetch("https://jobs.example.org/page1") is True

        # Second call should use cached result
        assert checker.can_fetch("https://jobs.example.org/page2") is True

        # Check that it's in the cache
        assert "jobs.example.org" in checker._domain_cache

    def test_cross_domain_no_robots_allows_all(self, mock_httpx_get):
        """When target domain has no robots.txt (404), allow all paths."""
        checker = RobotsChecker("https://example.com")

        # norobots.example.net returns 404 for robots.txt
        assert checker.can_fetch("https://norobots.example.net/anything") is True

    def test_real_world_scenario_bbahc(self, mock_httpx_get):
        """Simulate BBAHC scenario: base URL blocks, listing URL on different domain allows.

        BBAHC's base URL (bbahc.org) has robots.txt that blocks everything for unknown UAs.
        But their job listings are on ADP (workforcenow.adp.com) which should be checked
        against ADP's robots.txt, not BBAHC's.
        """
        # Simulate bbahc.org blocking everything
        def get_response(url, **kwargs):
            response = MagicMock()
            if "bbahc.org" in url:
                response.status_code = 200
                response.text = """
User-agent: Googlebot
Allow: /

User-agent: *
Disallow: /
"""
            elif "workforcenow.adp.com" in url:
                # ADP doesn't have a traditional robots.txt (redirects to login)
                # Our code follows redirects and gets HTML, which parses as empty rules
                response.status_code = 200
                response.text = "<html>login page</html>"  # Not valid robots.txt
            return response

        with patch("scraper.robots.httpx.get", side_effect=get_response):
            checker = RobotsChecker("https://www.bbahc.org")

            # URL on bbahc.org should be blocked (for non-Googlebot)
            assert checker.can_fetch("https://www.bbahc.org/admin") is False

            # URL on ADP should be allowed (invalid robots.txt = allow)
            adp_url = "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html"
            assert checker.can_fetch(adp_url) is True


class TestRobotsCheckerHttpScheme:
    """Test that HTTP scheme is preserved for HTTP-only sites."""

    def test_http_base_url_uses_http_for_robots(self):
        """When base_url is HTTP, robots.txt should be fetched via HTTP."""
        fetched_urls = []

        def capture_url(url, **kwargs):
            fetched_urls.append(url)
            response = MagicMock()
            response.status_code = 200
            response.text = "User-agent: *\nAllow: /"
            return response

        with patch("scraper.robots.httpx.get", side_effect=capture_url):
            checker = RobotsChecker("http://www.cityofkotzebue.com/jobs")
            checker.load()

            # Should have fetched http:// not https://
            assert len(fetched_urls) == 1
            assert fetched_urls[0].startswith("http://")
            assert "https://" not in fetched_urls[0]

    def test_cross_domain_http_url_uses_http(self):
        """When checking an HTTP URL on different domain, use HTTP for robots.txt."""
        fetched_urls = []

        def capture_url(url, **kwargs):
            fetched_urls.append(url)
            response = MagicMock()
            response.status_code = 200
            response.text = "User-agent: *\nAllow: /"
            return response

        with patch("scraper.robots.httpx.get", side_effect=capture_url):
            # Base URL is HTTPS
            checker = RobotsChecker("https://example.com")

            # Check an HTTP URL on a different domain
            checker.can_fetch("http://httponly.example.org/jobs")

            # Should have fetched http://httponly.example.org/robots.txt
            http_fetches = [u for u in fetched_urls if "httponly.example.org" in u]
            assert len(http_fetches) == 1
            assert http_fetches[0] == "http://httponly.example.org/robots.txt"
