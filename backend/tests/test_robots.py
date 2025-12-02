"""Tests for robots.txt checker."""

import pytest
from unittest.mock import patch, MagicMock
import httpx

from scraper.robots import (
    RobotsChecker,
    _parse_robots_rules,
    _pattern_matches,
    _can_fetch_with_specificity,
)


class TestSpecificityBasedMatching:
    """Test specificity-based robots.txt rule matching.

    Per Google's robots.txt spec, the most specific (longest matching) rule wins,
    regardless of the order rules appear in the file.
    """

    def test_allow_overrides_disallow_when_more_specific(self):
        """Allow rule should win when it's more specific than Disallow."""
        # This is the paycomonline.net case: Disallow: / but Allow: /v4/ats/web.php/jobs
        robots_content = """
User-agent: *
Disallow: /
Allow: /v4/ats/web.php/jobs
"""
        rules = _parse_robots_rules(robots_content, "*")

        # The /v4/ats/web.php/jobs path should be allowed
        assert _can_fetch_with_specificity(rules, "https://example.com/v4/ats/web.php/jobs") is True
        assert _can_fetch_with_specificity(rules, "https://example.com/v4/ats/web.php/jobs?foo=bar") is True

        # Other paths should still be blocked
        assert _can_fetch_with_specificity(rules, "https://example.com/") is False
        assert _can_fetch_with_specificity(rules, "https://example.com/admin") is False

    def test_disallow_overrides_allow_when_more_specific(self):
        """Disallow rule should win when it's more specific than Allow."""
        robots_content = """
User-agent: *
Allow: /docs
Disallow: /docs/internal
"""
        rules = _parse_robots_rules(robots_content, "*")

        # /docs should be allowed, but /docs/internal should be blocked
        assert _can_fetch_with_specificity(rules, "https://example.com/docs") is True
        assert _can_fetch_with_specificity(rules, "https://example.com/docs/public") is True
        assert _can_fetch_with_specificity(rules, "https://example.com/docs/internal") is False
        assert _can_fetch_with_specificity(rules, "https://example.com/docs/internal/secret") is False

    def test_equal_length_allow_wins(self):
        """When rules have equal specificity, Allow should take precedence."""
        robots_content = """
User-agent: *
Disallow: /page
Allow: /page
"""
        rules = _parse_robots_rules(robots_content, "*")

        # Equal length, Allow wins
        assert _can_fetch_with_specificity(rules, "https://example.com/page") is True

    def test_order_does_not_matter(self):
        """Rule order in the file should not affect the result."""
        # Disallow first
        robots1 = """
User-agent: *
Disallow: /
Allow: /public
"""
        # Allow first
        robots2 = """
User-agent: *
Allow: /public
Disallow: /
"""
        rules1 = _parse_robots_rules(robots1, "*")
        rules2 = _parse_robots_rules(robots2, "*")

        # Both should give the same result
        assert _can_fetch_with_specificity(rules1, "https://example.com/public") is True
        assert _can_fetch_with_specificity(rules2, "https://example.com/public") is True
        assert _can_fetch_with_specificity(rules1, "https://example.com/private") is False
        assert _can_fetch_with_specificity(rules2, "https://example.com/private") is False

    def test_wildcard_in_pattern(self):
        """Wildcard patterns should work correctly."""
        robots_content = """
User-agent: *
Disallow: /
Allow: /api/*/public
"""
        rules = _parse_robots_rules(robots_content, "*")

        assert _can_fetch_with_specificity(rules, "https://example.com/api/v1/public") is True
        assert _can_fetch_with_specificity(rules, "https://example.com/api/v2/public") is True
        assert _can_fetch_with_specificity(rules, "https://example.com/api/v1/private") is False

    def test_end_anchor(self):
        """$ end anchor should work correctly."""
        robots_content = """
User-agent: *
Allow: /
Disallow: /*.pdf$
"""
        rules = _parse_robots_rules(robots_content, "*")

        assert _can_fetch_with_specificity(rules, "https://example.com/doc.pdf") is False
        assert _can_fetch_with_specificity(rules, "https://example.com/doc.pdf?v=1") is True  # Not at end
        assert _can_fetch_with_specificity(rules, "https://example.com/doc.html") is True

    def test_query_string_handling(self):
        """Query strings should be included in path matching."""
        robots_content = """
User-agent: *
Disallow: /
Allow: /v4/ats/web.php/jobs
"""
        rules = _parse_robots_rules(robots_content, "*")

        # Query string should still match the Allow rule
        url_with_query = "https://example.com/v4/ats/web.php/jobs?clientkey=ABC&jpt="
        assert _can_fetch_with_specificity(rules, url_with_query) is True

    def test_no_matching_rules_allows(self):
        """If no rules match, the URL should be allowed."""
        robots_content = """
User-agent: *
Disallow: /admin
"""
        rules = _parse_robots_rules(robots_content, "*")

        assert _can_fetch_with_specificity(rules, "https://example.com/public") is True

    def test_paycomonline_real_robots(self):
        """Test with the actual paycomonline.net robots.txt structure."""
        robots_content = """
User-agent: *
Disallow: /
Allow: /v4/ats/web.php/application/style/logo/
Allow: /v4/ats/web.php/jobs
Allow: /v4/ats/sitemap.php
Allow: /v4/ats/web.php/portal/
Allow: /v4/ats/web.php/portal-customization/logo
Allow: /career-portal/sprawl.json
Allow: /api/ats/job-postings/
Allow: /api/ats/company-name
"""
        rules = _parse_robots_rules(robots_content, "*")

        # Should be allowed
        assert _can_fetch_with_specificity(
            rules,
            "https://www.paycomonline.net/v4/ats/web.php/jobs?clientkey=0CBBB7F6BE4EB8B39E20254F30A93E18&jpt="
        ) is True

        # Should be blocked
        assert _can_fetch_with_specificity(rules, "https://www.paycomonline.net/") is False
        assert _can_fetch_with_specificity(rules, "https://www.paycomonline.net/admin") is False


class TestPatternMatches:
    """Test the _pattern_matches helper function."""

    def test_simple_prefix_match(self):
        assert _pattern_matches("/foo", "/foo") is True
        assert _pattern_matches("/foo", "/foobar") is True
        assert _pattern_matches("/foo", "/foo/bar") is True
        assert _pattern_matches("/foo", "/bar") is False

    def test_wildcard_match(self):
        assert _pattern_matches("/a*b", "/ab") is True
        assert _pattern_matches("/a*b", "/aXXXb") is True
        assert _pattern_matches("/a*b", "/aXXXbYYY") is True  # Prefix match

    def test_end_anchor_match(self):
        assert _pattern_matches("/foo$", "/foo") is True
        assert _pattern_matches("/foo$", "/foobar") is False
        assert _pattern_matches("/*.pdf$", "/doc.pdf") is True
        assert _pattern_matches("/*.pdf$", "/doc.pdf?v=1") is False


class TestParseRobotsRules:
    """Test the _parse_robots_rules helper function."""

    def test_parses_allow_and_disallow(self):
        content = """
User-agent: *
Allow: /public
Disallow: /private
"""
        rules = _parse_robots_rules(content, "*")
        assert (True, "/public") in rules
        assert (False, "/private") in rules

    def test_ignores_other_user_agents(self):
        content = """
User-agent: Googlebot
Allow: /google-only

User-agent: *
Disallow: /blocked
"""
        rules = _parse_robots_rules(content, "*")
        assert (False, "/blocked") in rules
        assert (True, "/google-only") not in rules

    def test_handles_comments(self):
        content = """
User-agent: * # This is a comment
Disallow: /private # Another comment
# Full line comment
Allow: /public
"""
        rules = _parse_robots_rules(content, "*")
        assert (False, "/private") in rules
        assert (True, "/public") in rules

    def test_ignores_empty_values(self):
        content = """
User-agent: *
Disallow:
Allow: /public
"""
        rules = _parse_robots_rules(content, "*")
        assert len(rules) == 1
        assert (True, "/public") in rules

    def test_specific_ua_takes_precedence_over_wildcard(self):
        """Specific UA group should be used instead of wildcard, not merged."""
        content = """
User-agent: FarReachJobs
Allow: /

User-agent: *
Disallow: /private
"""
        # For FarReachJobs, should use the specific group (Allow: /) only
        rules = _parse_robots_rules(content, "FarReachJobs")
        assert (True, "/") in rules
        assert (False, "/private") not in rules  # Should NOT be merged from wildcard

        # For other bots, should use wildcard
        rules_other = _parse_robots_rules(content, "OtherBot")
        assert (False, "/private") in rules_other
        assert (True, "/") not in rules_other

    def test_multiple_ua_lines_in_group(self):
        """A group with multiple User-agent lines should match if ANY line matches."""
        content = """
User-agent: FarReachJobs
User-agent: OtherBot
Allow: /shared
Disallow: /secret
"""
        # Both FarReachJobs and OtherBot should get these rules
        rules_far = _parse_robots_rules(content, "FarReachJobs")
        assert (True, "/shared") in rules_far
        assert (False, "/secret") in rules_far

        rules_other = _parse_robots_rules(content, "OtherBot")
        assert (True, "/shared") in rules_other
        assert (False, "/secret") in rules_other

        # A third bot should NOT match this group
        rules_third = _parse_robots_rules(content, "ThirdBot")
        assert len(rules_third) == 0

    def test_multiple_ua_lines_with_wildcard(self):
        """Group with both specific UA and wildcard should match both."""
        content = """
User-agent: FarReachJobs
User-agent: *
Allow: /docs
Disallow: /admin
"""
        # FarReachJobs matches specifically
        rules_far = _parse_robots_rules(content, "FarReachJobs")
        assert (True, "/docs") in rules_far

        # Other bots match via wildcard
        rules_other = _parse_robots_rules(content, "RandomBot")
        assert (True, "/docs") in rules_other

    def test_first_specific_match_wins(self):
        """If multiple specific groups match, first one wins."""
        content = """
User-agent: FarReachJobs
Allow: /first

User-agent: FarReachJobs
Allow: /second
"""
        rules = _parse_robots_rules(content, "FarReachJobs")
        assert (True, "/first") in rules
        assert (True, "/second") not in rules

    def test_specific_after_wildcard_still_wins(self):
        """Specific UA group wins even if it comes after wildcard."""
        content = """
User-agent: *
Disallow: /blocked

User-agent: FarReachJobs
Allow: /
"""
        rules = _parse_robots_rules(content, "FarReachJobs")
        assert (True, "/") in rules
        assert (False, "/blocked") not in rules


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
