"""
AI-powered job listing page analyzer using Claude API.

Analyzes HTML pages to suggest CSS selectors for the GenericScraper.
"""

import logging
import httpx
from dataclasses import dataclass
from anthropic import Anthropic

from app.config import get_settings

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


async def fetch_page_html(url: str) -> str:
    """Fetch HTML content from a URL."""
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": "FarReachJobsBot/1.0 (job aggregator; +https://far-reach-jobs.tachyonfuture.com)"
        }
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


def analyze_with_claude(html: str) -> SelectorSuggestions:
    """Send HTML to Claude for analysis and get selector suggestions."""
    import json

    settings = get_settings()

    if not settings.anthropic_api_key:
        return SelectorSuggestions(
            can_use_generic_scraper=False,
            reason="Anthropic API key not configured",
            error="ANTHROPIC_API_KEY not set in environment"
        )

    client = Anthropic(api_key=settings.anthropic_api_key)

    # Truncate HTML to avoid token limits
    truncated_html = truncate_html(html)

    try:
        message = client.messages.create(
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


async def analyze_job_page(url: str) -> SelectorSuggestions:
    """
    Fetch a job listing page and analyze it with Claude.

    Returns SelectorSuggestions with recommended CSS selectors.
    """
    try:
        html = await fetch_page_html(url)
        return analyze_with_claude(html)
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
