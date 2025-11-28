"""URL detection utilities for specialized scrapers.

These are lightweight string utilities that don't require database or heavy dependencies,
making them safe to import in tests without pulling in the full application stack.
"""


def is_adp_workforce_url(url: str | None) -> bool:
    """Check if a URL is an ADP WorkforceNow careers portal."""
    if not url:
        return False
    return "workforcenow.adp.com" in url.lower()


def is_ultipro_url(url: str | None) -> bool:
    """Check if a URL is an UltiPro/UKG career portal."""
    if not url:
        return False
    url_lower = url.lower()
    # UltiPro/UKG URLs can be:
    # - recruiting2.ultipro.com or recruiting.ultipro.com (legacy)
    # - rec.pro.ukg.net (newer UKG Pro Recruiting)
    return "ultipro.com" in url_lower or "rec.pro.ukg.net" in url_lower
