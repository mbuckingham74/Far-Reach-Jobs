"""Tests for Playwright fallback behavior in GenericScraper."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

from scraper.sources.generic import GenericScraper
from scraper.playwright_fetcher import PlaywrightFetcher


class TestPlaywrightFallback:
    """Tests for Playwright to httpx fallback behavior."""

    @pytest.fixture
    def mock_html(self):
        """Sample HTML with job listings."""
        return """
        <html>
        <body>
            <div class="job-card">
                <h2 class="title"><a href="/jobs/1">Software Engineer</a></h2>
                <span class="location">Anchorage, AK</span>
            </div>
            <div class="job-card">
                <h2 class="title"><a href="/jobs/2">Data Analyst</a></h2>
                <span class="location">Fairbanks, AK</span>
            </div>
        </body>
        </html>
        """

    @pytest.fixture
    def source_config(self):
        """Source configuration with Playwright enabled."""
        return {
            "name": "Test Source",
            "base_url": "https://example.com",
            "listing_url": "https://example.com/jobs",
            "selector_job_container": ".job-card",
            "selector_title": ".title a",
            "selector_url": ".title a",
            "selector_location": ".location",
            "use_playwright": True,
        }

    def test_playwright_success_no_fallback(self, source_config, mock_html):
        """When Playwright succeeds, httpx should not be called."""
        with patch("scraper.sources.generic.get_playwright_fetcher") as mock_get_fetcher:
            # Mock Playwright fetcher to return HTML successfully
            mock_fetcher = Mock(spec=PlaywrightFetcher)
            mock_fetcher.is_available = True
            mock_fetcher.fetch.return_value = BeautifulSoup(mock_html, "lxml")
            mock_get_fetcher.return_value = mock_fetcher

            scraper = GenericScraper(source_config=source_config)

            # Mock robots.txt check to allow
            with patch.object(scraper, "can_fetch", return_value=True):
                with patch.object(scraper, "client") as mock_client:
                    soup = scraper._fetch_page("https://example.com/jobs")

                    # Playwright was called
                    mock_fetcher.fetch.assert_called_once()
                    # httpx was NOT called (no fallback needed)
                    mock_client.get.assert_not_called()
                    # Got valid soup
                    assert soup is not None

    def test_playwright_failure_falls_back_to_httpx(self, source_config, mock_html):
        """When Playwright fails (returns None), should fall back to httpx."""
        with patch("scraper.sources.generic.get_playwright_fetcher") as mock_get_fetcher:
            # Mock Playwright fetcher to return None (failure)
            mock_fetcher = Mock(spec=PlaywrightFetcher)
            mock_fetcher.is_available = True
            mock_fetcher.fetch.return_value = None  # Playwright failed
            mock_get_fetcher.return_value = mock_fetcher

            scraper = GenericScraper(source_config=source_config)

            # Mock robots.txt check to allow
            with patch.object(scraper, "can_fetch", return_value=True):
                # Mock httpx to return HTML
                mock_response = Mock()
                mock_response.text = mock_html
                mock_response.raise_for_status = Mock()

                with patch.object(scraper, "client") as mock_client:
                    mock_client.get.return_value = mock_response

                    soup = scraper._fetch_page("https://example.com/jobs")

                    # Playwright was tried first
                    mock_fetcher.fetch.assert_called_once()
                    # httpx was called as fallback
                    mock_client.get.assert_called_once_with("https://example.com/jobs")
                    # Got valid soup from httpx
                    assert soup is not None

    def test_playwright_unavailable_uses_httpx(self, source_config, mock_html):
        """When Playwright service is unavailable, should use httpx directly."""
        with patch("scraper.sources.generic.get_playwright_fetcher") as mock_get_fetcher:
            # Mock Playwright fetcher as unavailable
            mock_fetcher = Mock(spec=PlaywrightFetcher)
            mock_fetcher.is_available = False
            mock_get_fetcher.return_value = mock_fetcher

            scraper = GenericScraper(source_config=source_config)

            with patch.object(scraper, "can_fetch", return_value=True):
                mock_response = Mock()
                mock_response.text = mock_html
                mock_response.raise_for_status = Mock()

                with patch.object(scraper, "client") as mock_client:
                    mock_client.get.return_value = mock_response

                    soup = scraper._fetch_page("https://example.com/jobs")

                    # Playwright fetch was NOT attempted
                    mock_fetcher.fetch.assert_not_called()
                    # httpx was used instead
                    mock_client.get.assert_called_once()
                    assert soup is not None

    def test_robots_txt_blocks_before_playwright(self, source_config):
        """robots.txt should be checked before attempting Playwright fetch."""
        with patch("scraper.sources.generic.get_playwright_fetcher") as mock_get_fetcher:
            mock_fetcher = Mock(spec=PlaywrightFetcher)
            mock_fetcher.is_available = True
            mock_get_fetcher.return_value = mock_fetcher

            scraper = GenericScraper(source_config=source_config)

            # Mock robots.txt to disallow
            with patch.object(scraper, "can_fetch", return_value=False):
                with patch.object(scraper, "client") as mock_client:
                    soup = scraper._fetch_page("https://example.com/jobs")

                    # Neither Playwright nor httpx should be called
                    mock_fetcher.fetch.assert_not_called()
                    mock_client.get.assert_not_called()
                    # Should return None due to robots.txt block
                    assert soup is None

    def test_playwright_disabled_uses_httpx_only(self, mock_html):
        """When use_playwright=False, should only use httpx."""
        config = {
            "name": "Test Source",
            "base_url": "https://example.com",
            "listing_url": "https://example.com/jobs",
            "selector_job_container": ".job-card",
            "selector_title": ".title a",
            "selector_url": ".title a",
            "use_playwright": False,  # Playwright disabled
        }

        with patch("scraper.sources.generic.get_playwright_fetcher") as mock_get_fetcher:
            scraper = GenericScraper(source_config=config)

            # Fetcher should not even be created when disabled
            # (constructor only creates it if use_playwright is True)
            assert scraper._playwright_fetcher is None

            with patch.object(scraper, "can_fetch", return_value=True):
                mock_response = Mock()
                mock_response.text = mock_html
                mock_response.raise_for_status = Mock()

                with patch.object(scraper, "client") as mock_client:
                    mock_client.get.return_value = mock_response

                    soup = scraper._fetch_page("https://example.com/jobs")

                    mock_client.get.assert_called_once()
                    assert soup is not None


class TestPlaywrightFetcherAvailability:
    """Tests for PlaywrightFetcher availability checks."""

    def test_fetcher_unavailable_without_url(self):
        """Fetcher should report unavailable when service URL not configured."""
        with patch("scraper.playwright_fetcher.get_settings") as mock_settings:
            mock_settings.return_value.playwright_service_url = ""

            fetcher = PlaywrightFetcher()
            assert fetcher.is_available is False

    def test_fetcher_available_with_url(self):
        """Fetcher should report available when service URL is configured."""
        with patch("scraper.playwright_fetcher.get_settings") as mock_settings:
            mock_settings.return_value.playwright_service_url = "http://playwright:3000"

            fetcher = PlaywrightFetcher()
            assert fetcher.is_available is True
