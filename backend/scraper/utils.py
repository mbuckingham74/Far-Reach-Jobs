import re
from typing import Optional


# US State abbreviations
US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}

# Reverse mapping
STATE_ABBREVS = {v: v for v in US_STATES.values()}


def normalize_state(state_input: str | None) -> str | None:
    """Normalize a state name or abbreviation to its 2-letter code."""
    if not state_input:
        return None

    state_clean = state_input.strip().lower()

    # Check if it's already an abbreviation
    if state_clean.upper() in STATE_ABBREVS:
        return state_clean.upper()

    # Check if it's a full name
    if state_clean in US_STATES:
        return US_STATES[state_clean]

    return None


def extract_state_from_location(location: str | None) -> str | None:
    """Try to extract a state abbreviation from a location string."""
    if not location:
        return None

    # Look for 2-letter state codes (usually at end after comma)
    # e.g., "Anchorage, AK" or "Nome, Alaska"
    patterns = [
        r",\s*([A-Z]{2})\s*$",  # ", AK" at end
        r",\s*([A-Z]{2})\s+\d{5}",  # ", AK 99501" with zip
        r"\b([A-Z]{2})\s+\d{5}",  # "AK 99501" anywhere
    ]

    for pattern in patterns:
        match = re.search(pattern, location)
        if match:
            abbrev = match.group(1)
            if abbrev in STATE_ABBREVS:
                return abbrev

    # Try full state names
    location_lower = location.lower()
    for state_name, abbrev in US_STATES.items():
        if state_name in location_lower:
            return abbrev

    return None


def clean_text(text: str | None) -> str | None:
    """Clean up text by normalizing whitespace."""
    if not text:
        return None
    # Replace multiple whitespace with single space, strip
    return re.sub(r"\s+", " ", text).strip()


def extract_salary(text: str | None) -> str | None:
    """Try to extract salary information from text."""
    if not text:
        return None

    # Common salary patterns
    patterns = [
        r"\$[\d,]+(?:\s*-\s*\$[\d,]+)?(?:\s*(?:per|/)\s*(?:hour|hr|year|yr|annual|month|mo))?",
        r"[\d,]+(?:\s*-\s*[\d,]+)?\s*(?:per|/)\s*(?:hour|hr|year|yr|annual|month|mo)",
        r"(?:salary|pay|wage|compensation)[:\s]*\$?[\d,]+(?:\s*-\s*\$?[\d,]+)?",
    ]

    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return clean_text(match.group(0))

    return None


def normalize_job_type(job_type: str | None) -> str | None:
    """Normalize job type to standard values."""
    if not job_type:
        return None

    job_type_lower = job_type.lower()

    if any(term in job_type_lower for term in ["full-time", "full time", "fulltime"]):
        return "Full-time"
    if any(term in job_type_lower for term in ["part-time", "part time", "parttime"]):
        return "Part-time"
    if "seasonal" in job_type_lower:
        return "Seasonal"
    if "contract" in job_type_lower:
        return "Contract"
    if "temporary" in job_type_lower or "temp" in job_type_lower:
        return "Temporary"
    if "intern" in job_type_lower:
        return "Internship"

    return clean_text(job_type)
