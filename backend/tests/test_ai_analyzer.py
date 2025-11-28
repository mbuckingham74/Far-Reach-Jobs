"""Tests for AI analyzer code extraction."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ai_analyzer import generate_custom_scraper


class TestCodeExtraction:
    """Test that code is properly extracted from various AI response formats."""

    @pytest.fixture
    def mock_anthropic(self):
        """Create a mock Anthropic client."""
        with patch("app.services.ai_analyzer.AsyncAnthropic") as mock:
            yield mock

    @pytest.fixture
    def mock_settings(self):
        """Mock settings with API key."""
        with patch("app.services.ai_analyzer.get_settings") as mock:
            mock.return_value.anthropic_api_key = "test-key"
            yield mock

    @pytest.mark.asyncio
    async def test_extracts_code_from_markdown_with_explanation(
        self, mock_anthropic, mock_settings
    ):
        """Test extracting code when AI returns explanation + code block."""
        ai_response = '''Looking at this HTML, I can see this is an ADP Workforce Now career portal.

Based on the URL pattern and structure, here's a custom scraper:

```python
class TestScraper(BaseScraper):
    @property
    def source_name(self):
        return "Test Source"

    @property
    def base_url(self):
        return "https://example.com"

    def get_job_listing_urls(self):
        return ["https://example.com/jobs"]

    def parse_job_listing_page(self, soup, url):
        return []
```

This scraper handles the dynamic content by looking for various selectors.'''

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=ai_response)]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client

        result = await generate_custom_scraper(
            source_name="Test",
            base_url="https://example.com",
            listing_url="https://example.com/jobs",
            html="<html></html>",
        )

        assert result.success is True
        assert result.class_name == "TestScraper"
        assert "class TestScraper(BaseScraper)" in result.code
        # Should NOT contain explanation text
        assert "Looking at this HTML" not in result.code
        assert "This scraper handles" not in result.code

    @pytest.mark.asyncio
    async def test_extracts_code_from_pure_markdown_block(
        self, mock_anthropic, mock_settings
    ):
        """Test extracting code when AI returns just a code block."""
        ai_response = '''```python
class CleanScraper(BaseScraper):
    @property
    def source_name(self):
        return "Clean Source"

    @property
    def base_url(self):
        return "https://example.com"

    def get_job_listing_urls(self):
        return []

    def parse_job_listing_page(self, soup, url):
        return []
```'''

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=ai_response)]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client

        result = await generate_custom_scraper(
            source_name="Test",
            base_url="https://example.com",
            listing_url="https://example.com/jobs",
            html="<html></html>",
        )

        assert result.success is True
        assert result.class_name == "CleanScraper"
        assert "```" not in result.code

    @pytest.mark.asyncio
    async def test_extracts_code_without_python_lang_specifier(
        self, mock_anthropic, mock_settings
    ):
        """Test extracting code from block without 'python' specifier."""
        ai_response = '''Here's the scraper:

```
class NoLangScraper(BaseScraper):
    @property
    def source_name(self):
        return "No Lang"

    @property
    def base_url(self):
        return "https://example.com"

    def get_job_listing_urls(self):
        return []

    def parse_job_listing_page(self, soup, url):
        return []
```'''

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=ai_response)]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client

        result = await generate_custom_scraper(
            source_name="Test",
            base_url="https://example.com",
            listing_url="https://example.com/jobs",
            html="<html></html>",
        )

        assert result.success is True
        assert result.class_name == "NoLangScraper"

    @pytest.mark.asyncio
    async def test_handles_raw_code_without_markdown(
        self, mock_anthropic, mock_settings
    ):
        """Test that raw code (no markdown) is handled correctly."""
        ai_response = '''class RawScraper(BaseScraper):
    @property
    def source_name(self):
        return "Raw Source"

    @property
    def base_url(self):
        return "https://example.com"

    def get_job_listing_urls(self):
        return []

    def parse_job_listing_page(self, soup, url):
        return []'''

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=ai_response)]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client

        result = await generate_custom_scraper(
            source_name="Test",
            base_url="https://example.com",
            listing_url="https://example.com/jobs",
            html="<html></html>",
        )

        assert result.success is True
        assert result.class_name == "RawScraper"

    @pytest.mark.asyncio
    async def test_strips_import_statements(self, mock_anthropic, mock_settings):
        """Test that import statements are stripped from the code."""
        ai_response = '''```python
from scraper.base import BaseScraper, ScrapedJob
import re
from urllib.parse import urljoin

class ImportScraper(BaseScraper):
    @property
    def source_name(self):
        return "Import Test"

    @property
    def base_url(self):
        return "https://example.com"

    def get_job_listing_urls(self):
        return []

    def parse_job_listing_page(self, soup, url):
        return []
```'''

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=ai_response)]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client

        result = await generate_custom_scraper(
            source_name="Test",
            base_url="https://example.com",
            listing_url="https://example.com/jobs",
            html="<html></html>",
        )

        assert result.success is True
        assert "from scraper.base import" not in result.code
        assert "import re" not in result.code
        assert "from urllib.parse import" not in result.code

    @pytest.mark.asyncio
    async def test_rejects_response_without_required_methods(
        self, mock_anthropic, mock_settings
    ):
        """Test that incomplete scrapers are rejected."""
        ai_response = '''```python
class IncompleteScraper(BaseScraper):
    @property
    def source_name(self):
        return "Incomplete"
```'''

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=ai_response)]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client

        result = await generate_custom_scraper(
            source_name="Test",
            base_url="https://example.com",
            listing_url="https://example.com/jobs",
            html="<html></html>",
        )

        assert result.success is False
        assert "missing required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_extracts_code_from_unterminated_code_block(
        self, mock_anthropic, mock_settings
    ):
        """Test fallback extraction when closing ``` is missing.

        When the regex can't find a complete ```...``` block, the fallback
        line-by-line parser should still extract code after an opening fence.
        """
        ai_response = '''Here's your scraper:

```python
class UnterminatedScraper(BaseScraper):
    @property
    def source_name(self):
        return "Unterminated"

    @property
    def base_url(self):
        return "https://example.com"

    def get_job_listing_urls(self):
        return []

    def parse_job_listing_page(self, soup, url):
        return []'''  # Note: no closing ```

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=ai_response)]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client

        result = await generate_custom_scraper(
            source_name="Test",
            base_url="https://example.com",
            listing_url="https://example.com/jobs",
            html="<html></html>",
        )

        assert result.success is True
        assert result.class_name == "UnterminatedScraper"
        assert "class UnterminatedScraper(BaseScraper)" in result.code
        # Should NOT contain the preamble text
        assert "Here's your scraper" not in result.code
        assert "```" not in result.code
