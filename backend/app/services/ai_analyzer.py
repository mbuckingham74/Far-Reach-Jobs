"""
AI-powered job listing page analyzer using Claude API.

Analyzes HTML pages to suggest CSS selectors for the GenericScraper,
and generates custom scraper code for sites that can't use GenericScraper.
"""

import json
import logging
import re
import httpx
from dataclasses import dataclass
from anthropic import AsyncAnthropic

from app.config import get_settings
from scraper.playwright_fetcher import get_playwright_fetcher

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """You are an expert web scraper analyzing a job listings page. Your task is to identify CSS selectors that can be used to extract job information from this HTML.

Analyze the HTML and identify:
1. The repeating container element for each job listing
2. Within each container, the elements containing:
   - Job title (required)
   - Job URL/link (required)
   - Organization/company name (optional)
   - Location (optional)
   - Job type (full-time, part-time, etc.) (optional)
   - Salary information (optional)
   - Job description/summary (optional)

3. If there's pagination, identify the "next page" link selector

Rules for selectors:
- Use CSS selectors that are specific enough to match the target elements but general enough to work across all job listings
- Prefer class-based selectors (.class-name) over complex nested selectors when possible
- For the URL, also note which attribute contains the URL (usually "href")
- If a field doesn't exist in the HTML, leave it empty

Respond with ONLY a JSON object in this exact format (no markdown, no explanation):
{
    "can_use_generic_scraper": true,
    "reason": "Brief explanation of why generic scraper will/won't work",
    "selectors": {
        "job_container": ".job-card",
        "title": ".job-title",
        "url": "a.job-link",
        "url_attribute": "href",
        "organization": ".company-name",
        "location": ".location",
        "job_type": ".job-type",
        "salary": ".salary",
        "description": ".description",
        "next_page": "a.next"
    },
    "jobs_found": 5,
    "sample_job": {
        "title": "Example Job Title",
        "url": "/jobs/123",
        "organization": "Example Company",
        "location": "Anchorage, AK"
    },
    "notes": "Any important notes about the page structure"
}

If the page structure is too complex for the generic scraper (e.g., requires JavaScript rendering, complex iframe structures, or API calls), set can_use_generic_scraper to false and explain why in the reason field.

Here is the HTML to analyze:

"""


@dataclass
class SelectorSuggestions:
    """Results from AI analysis of a job listing page."""
    can_use_generic_scraper: bool
    reason: str
    job_container: str | None = None
    title: str | None = None
    url: str | None = None
    url_attribute: str = "href"
    organization: str | None = None
    location: str | None = None
    job_type: str | None = None
    salary: str | None = None
    description: str | None = None
    next_page: str | None = None
    jobs_found: int = 0
    sample_job: dict | None = None
    notes: str | None = None
    error: str | None = None


def is_ai_analysis_available() -> bool:
    """Check if AI analysis is available (API key configured)."""
    settings = get_settings()
    return bool(settings.anthropic_api_key)


async def fetch_page_html(url: str, use_playwright: bool = False) -> str:
    """Fetch HTML content from a URL.

    Args:
        url: URL to fetch
        use_playwright: If True, use Playwright service for browser-based fetch
    """
    # Try Playwright first if enabled
    if use_playwright:
        fetcher = get_playwright_fetcher()
        if fetcher.is_available:
            logger.info(f"Using Playwright to fetch page for AI analysis: {url}")
            soup = fetcher.fetch(url)
            if soup is not None:
                return str(soup)
            logger.warning(f"Playwright fetch failed for {url}, falling back to httpx")
        else:
            logger.warning("Playwright requested but service not available, using httpx")

    # Fall back to httpx
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; FarReachJobs/1.0; +https://far-reach-jobs.tachyonfuture.com)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers=headers
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def truncate_html(html: str, max_chars: int = 100000) -> str:
    """Truncate HTML to stay within token limits while keeping structure."""
    if len(html) <= max_chars:
        return html

    # Try to truncate at a tag boundary
    truncated = html[:max_chars]
    last_close = truncated.rfind('>')
    if last_close > max_chars - 1000:
        truncated = truncated[:last_close + 1]

    return truncated + "\n<!-- HTML truncated for analysis -->"


async def analyze_with_claude(html: str) -> SelectorSuggestions:
    """Send HTML to Claude for analysis and get selector suggestions."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        return SelectorSuggestions(
            can_use_generic_scraper=False,
            reason="Anthropic API key not configured",
            error="ANTHROPIC_API_KEY not set in environment"
        )

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Truncate HTML to avoid token limits
    truncated_html = truncate_html(html)

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": ANALYSIS_PROMPT + truncated_html
                }
            ]
        )

        # Extract the response text
        response_text = message.content[0].text.strip()

        # Parse JSON response
        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first and last lines (```json and ```)
            response_text = "\n".join(lines[1:-1])

        data = json.loads(response_text)

        selectors = data.get("selectors", {})

        return SelectorSuggestions(
            can_use_generic_scraper=data.get("can_use_generic_scraper", False),
            reason=data.get("reason", ""),
            job_container=selectors.get("job_container"),
            title=selectors.get("title"),
            url=selectors.get("url"),
            url_attribute=selectors.get("url_attribute", "href"),
            organization=selectors.get("organization"),
            location=selectors.get("location"),
            job_type=selectors.get("job_type"),
            salary=selectors.get("salary"),
            description=selectors.get("description"),
            next_page=selectors.get("next_page"),
            jobs_found=data.get("jobs_found", 0),
            sample_job=data.get("sample_job"),
            notes=data.get("notes")
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        logger.debug(f"Response was: {response_text[:500]}")
        return SelectorSuggestions(
            can_use_generic_scraper=False,
            reason="Failed to parse AI response",
            error=f"JSON parse error: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Claude API error: {e}")
        return SelectorSuggestions(
            can_use_generic_scraper=False,
            reason="AI analysis failed",
            error=str(e)
        )


async def analyze_job_page(url: str, use_playwright: bool = False) -> SelectorSuggestions:
    """
    Fetch a job listing page and analyze it with Claude.

    Args:
        url: URL to analyze
        use_playwright: If True, use Playwright service for browser-based fetch

    Returns SelectorSuggestions with recommended CSS selectors.
    """
    try:
        html = await fetch_page_html(url, use_playwright=use_playwright)
        return await analyze_with_claude(html)
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching {url}: {e}")
        return SelectorSuggestions(
            can_use_generic_scraper=False,
            reason=f"Failed to fetch page: HTTP {e.response.status_code}",
            error=f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error fetching {url}: {e}")
        return SelectorSuggestions(
            can_use_generic_scraper=False,
            reason=f"Failed to fetch page: {type(e).__name__}",
            error=str(e)
        )
    except Exception as e:
        logger.exception(f"Error analyzing {url}: {e}")
        return SelectorSuggestions(
            can_use_generic_scraper=False,
            reason="Analysis failed",
            error=str(e)
        )


# --- Custom Scraper Generation ---

SCRAPER_GENERATION_PROMPT = """You are an expert Python developer specializing in web scraping. Generate a custom scraper class for the given job listings page.

The scraper must:
1. Inherit from BaseScraper
2. Implement these required properties and methods:
   - source_name (str property): Human-readable name for this source
   - base_url (str property): The base URL of the website
   - get_job_listing_urls(): Return a list of URLs to scrape
   - parse_job_listing_page(soup, url): Parse BeautifulSoup and return list of ScrapedJob objects

Here's the base class and ScrapedJob dataclass for reference:

```python
@dataclass
class ScrapedJob:
    external_id: str        # Unique ID (use self.generate_external_id(url))
    title: str              # Job title (required)
    url: str                # Full URL to job posting (required)
    organization: str | None = None   # Company/org name
    location: str | None = None       # Job location
    state: str | None = None          # US state abbreviation (e.g., "AK")
    description: str | None = None    # Job description/summary
    job_type: str | None = None       # full-time, part-time, etc.
    salary_info: str | None = None    # Salary information

class BaseScraper(ABC):
    def generate_external_id(self, url: str) -> str:
        # Generate unique ID from URL - use this!
    def fetch_page(self, url: str) -> BeautifulSoup | None:
        # Fetch and parse a page - available to use
```

Guidelines:
- Use BeautifulSoup selectors (.select(), .select_one(), .find(), .find_all())
- Always use self.generate_external_id(job_url) for external_id
- Convert relative URLs to absolute using urljoin
- Handle missing elements gracefully (check if None before accessing)
- Extract as much information as possible from the HTML
- Add comments explaining non-obvious selector choices
- For Alaska-based sources, default state to "AK" if not specified

Source configuration:
- Source name: {source_name}
- Base URL: {base_url}
- Listing URL: {listing_url}

Return ONLY the Python class code (no markdown, no explanation), starting with any needed imports and ending with the class definition. The class name should be a valid Python identifier based on the source name.

Here is the HTML to analyze:

"""


@dataclass
class GeneratedScraper:
    """Result of AI scraper generation."""
    success: bool
    code: str | None = None
    class_name: str | None = None
    error: str | None = None


def sanitize_class_name(name: str) -> str:
    """Convert a source name to a valid Python class name."""
    # Remove special characters, keep alphanumeric and spaces
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    # Convert to PascalCase
    words = clean.split()
    pascal = ''.join(word.capitalize() for word in words)
    # Ensure it starts with a letter
    if pascal and not pascal[0].isalpha():
        pascal = 'Source' + pascal
    return pascal + 'Scraper' if pascal else 'CustomScraper'


async def generate_custom_scraper(
    source_name: str,
    base_url: str,
    listing_url: str,
    html: str
) -> GeneratedScraper:
    """Generate a custom scraper class using AI.

    Args:
        source_name: Human-readable name for the source
        base_url: Base URL of the website
        listing_url: URL of the job listings page
        html: HTML content of the listings page

    Returns:
        GeneratedScraper with the generated code or error
    """
    settings = get_settings()

    if not settings.anthropic_api_key:
        return GeneratedScraper(
            success=False,
            error="ANTHROPIC_API_KEY not set in environment"
        )

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Truncate HTML
    truncated_html = truncate_html(html)

    # Build the prompt with source info
    prompt = SCRAPER_GENERATION_PROMPT.format(
        source_name=source_name,
        base_url=base_url,
        listing_url=listing_url
    ) + truncated_html

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = message.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Find the first and last ``` lines
            start_idx = 0
            end_idx = len(lines)
            for i, line in enumerate(lines):
                if line.startswith("```") and i == 0:
                    start_idx = 1
                elif line.startswith("```"):
                    end_idx = i
                    break
            response_text = "\n".join(lines[start_idx:end_idx])

        # Extract the class name from the code
        class_match = re.search(r'class\s+(\w+)\s*\(', response_text)
        class_name = class_match.group(1) if class_match else sanitize_class_name(source_name)

        return GeneratedScraper(
            success=True,
            code=response_text,
            class_name=class_name
        )

    except Exception as e:
        logger.exception(f"Error generating custom scraper: {e}")
        return GeneratedScraper(
            success=False,
            error=str(e)
        )


async def generate_scraper_for_url(
    source_name: str,
    base_url: str,
    listing_url: str,
    use_playwright: bool = False
) -> GeneratedScraper:
    """Fetch a page and generate a custom scraper for it.

    Args:
        source_name: Human-readable name for the source
        base_url: Base URL of the website
        listing_url: URL of the job listings page
        use_playwright: If True, use Playwright for browser-based fetch

    Returns:
        GeneratedScraper with the generated code or error
    """
    try:
        html = await fetch_page_html(listing_url, use_playwright=use_playwright)
        return await generate_custom_scraper(source_name, base_url, listing_url, html)
    except httpx.HTTPStatusError as e:
        return GeneratedScraper(
            success=False,
            error=f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
        )
    except httpx.RequestError as e:
        return GeneratedScraper(
            success=False,
            error=str(e)
        )
    except Exception as e:
        logger.exception(f"Error generating scraper for {listing_url}: {e}")
        return GeneratedScraper(
            success=False,
            error=str(e)
        )
