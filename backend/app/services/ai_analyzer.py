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

IMPORTANT: The following are ALREADY IMPORTED and available. DO NOT redefine them:
- BaseScraper (the base class to inherit from)
- ScrapedJob (the dataclass to return)
- BeautifulSoup
- urljoin (from urllib.parse)
- re
- json

ScrapedJob fields for reference (DO NOT redefine this class):
- external_id: str        # Use self.generate_external_id(url)
- title: str              # Job title (required)
- url: str                # Full URL to job posting (required)
- organization: str | None = None
- location: str | None = None
- state: str | None = None   # US state abbreviation (e.g., "AK")
- description: str | None = None
- job_type: str | None = None
- salary_info: str | None = None

BaseScraper methods available (DO NOT redefine this class):
- self.generate_external_id(url: str) -> str  # Generate unique ID from URL
- self.fetch_page(url: str) -> BeautifulSoup | None  # Fetch and parse a page

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

Return ONLY your scraper class definition. DO NOT include:
- Import statements (already available)
- BaseScraper or ScrapedJob class definitions (already available)
- Markdown code blocks
- Explanations

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

        # Log the first part of the response for debugging
        logger.info(f"AI scraper generation response (first 500 chars): {response_text[:500]}")

        # Extract code from markdown code blocks anywhere in the response
        # This handles cases where the AI returns explanation text before/after the code
        code_block_match = re.search(r'```(?:python)?\s*\n(.*?)```', response_text, re.DOTALL)
        if code_block_match:
            response_text = code_block_match.group(1).strip()
            logger.info(f"Extracted code block from markdown (length: {len(response_text)})")
        elif "```" in response_text:
            # Fallback: try to find any code block even if malformed
            lines = response_text.split("\n")
            in_code_block = False
            code_lines = []
            for line in lines:
                if line.strip().startswith("```"):
                    if in_code_block:
                        break  # End of code block
                    else:
                        in_code_block = True
                        continue
                if in_code_block:
                    code_lines.append(line)
            if code_lines:
                response_text = "\n".join(code_lines)
                logger.info(f"Extracted code via fallback method (length: {len(response_text)})")

        # Strip out any import statements and class redefinitions that the AI shouldn't have included
        # These are already provided in the exec namespace
        lines = response_text.split("\n")
        cleaned_lines = []
        skip_until_class = False
        in_unwanted_class = False
        unwanted_class_indent = 0

        for line in lines:
            stripped = line.lstrip()
            current_indent = len(line) - len(stripped)

            # Skip import statements
            if stripped.startswith(("from ", "import ")):
                continue

            # Skip @dataclass decorator
            if stripped.startswith("@dataclass"):
                continue

            # Detect unwanted class definitions (BaseScraper, ScrapedJob)
            if stripped.startswith("class BaseScraper") or stripped.startswith("class ScrapedJob"):
                in_unwanted_class = True
                unwanted_class_indent = current_indent
                continue

            # If we're in an unwanted class, skip until we hit a line at same or lower indent
            if in_unwanted_class:
                if stripped and current_indent <= unwanted_class_indent:
                    in_unwanted_class = False
                    # Don't skip this line - check if it's wanted
                    if not stripped.startswith("class BaseScraper") and not stripped.startswith("class ScrapedJob"):
                        cleaned_lines.append(line)
                continue

            cleaned_lines.append(line)

        response_text = "\n".join(cleaned_lines).strip()
        logger.info(f"Cleaned code (first 300 chars): {response_text[:300]}")

        # Validate the generated code
        if not response_text or len(response_text.strip()) < 50:
            return GeneratedScraper(
                success=False,
                error="AI returned empty or too short response"
            )

        # Check for required class definition
        class_match = re.search(r'class\s+(\w+)\s*\(\s*BaseScraper\s*\)', response_text)
        if not class_match:
            # Try looser match (any class inheriting from something)
            class_match = re.search(r'class\s+(\w+)\s*\(', response_text)
            if not class_match:
                logger.error(f"No class definition found in response. Response length: {len(response_text)}")
                return GeneratedScraper(
                    success=False,
                    error="Generated code does not contain a valid class definition"
                )
            logger.warning(f"Generated scraper class doesn't explicitly inherit from BaseScraper")

        class_name = class_match.group(1)

        # Check for required methods
        required_patterns = [
            (r'def\s+source_name\s*\(|source_name\s*=', "source_name property"),
            (r'def\s+base_url\s*\(|base_url\s*=', "base_url property"),
            (r'def\s+get_job_listing_urls\s*\(', "get_job_listing_urls method"),
            (r'def\s+parse_job_listing_page\s*\(', "parse_job_listing_page method"),
        ]

        missing = []
        for pattern, name in required_patterns:
            if not re.search(pattern, response_text):
                missing.append(name)

        if missing:
            return GeneratedScraper(
                success=False,
                error=f"Generated code missing required: {', '.join(missing)}"
            )

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
