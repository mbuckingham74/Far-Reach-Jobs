from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

# User-Agent for HTTP requests - avoids naive "Bot" string detection
USER_AGENT = "Mozilla/5.0 (compatible; FarReachJobs/1.0; +https://far-reach-jobs.tachyonfuture.com)"

# User-Agent for robots.txt parsing - must start with bot name for proper rule matching
ROBOTS_USER_AGENT = "FarReachJobs/1.0"


def _parse_robots_rules(content: str, user_agent: str) -> list[tuple[bool, str]]:
    """Parse robots.txt content and return rules for the most specific matching UA group.

    Per the robots.txt spec:
    1. Find the most specific User-agent group that matches (not merged)
    2. A group can have multiple User-agent lines; if ANY matches, the group applies
    3. Specific UA names take precedence over wildcard (*)

    Returns a list of (is_allowed, pattern) tuples for the best matching group.
    """
    ua_lower = user_agent.lower()

    # First pass: identify all groups and their rules
    # A group is: one or more User-agent lines followed by Allow/Disallow rules
    groups: list[tuple[list[str], list[tuple[bool, str]]]] = []
    current_uas: list[str] = []
    current_rules: list[tuple[bool, str]] = []
    in_ua_section = True  # True while we're reading User-agent lines

    for line in content.splitlines():
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue

        # Remove inline comments
        if "#" in line:
            line = line[: line.index("#")].strip()

        if ":" not in line:
            continue

        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()

        if field == "user-agent":
            if not in_ua_section and current_uas:
                # We hit a new User-agent after rules, so save the previous group
                groups.append((current_uas, current_rules))
                current_uas = []
                current_rules = []
            current_uas.append(value.lower())
            in_ua_section = True
        elif field in ("allow", "disallow"):
            in_ua_section = False
            if value:  # Ignore empty values
                is_allowed = field == "allow"
                current_rules.append((is_allowed, value))

    # Don't forget the last group
    if current_uas:
        groups.append((current_uas, current_rules))

    # Second pass: find the best matching group
    # Priority: specific UA match > wildcard match
    best_group: list[tuple[bool, str]] | None = None
    best_is_specific = False  # True if we matched a specific UA (not *)

    for uas, rules in groups:
        # Check if any UA in this group matches us
        matches_specific = False
        matches_wildcard = False

        for ua in uas:
            if ua == "*":
                matches_wildcard = True
            elif ua_lower.startswith(ua):
                matches_specific = True

        # Determine if this group is a better match
        if matches_specific:
            # Specific match always wins; if we already have one, first wins
            if not best_is_specific:
                best_group = rules
                best_is_specific = True
        elif matches_wildcard and best_group is None:
            # Wildcard match, but only if we don't have any match yet
            best_group = rules

    return best_group if best_group is not None else []


def _pattern_matches(pattern: str, path: str) -> bool:
    """Check if a robots.txt pattern matches a URL path.

    Supports:
    - Simple prefix matching (default)
    - * wildcard (matches any sequence)
    - $ end anchor
    """
    # Handle $ anchor at end
    must_end = pattern.endswith("$")
    if must_end:
        pattern = pattern[:-1]

    # Convert robots.txt pattern to regex
    # Escape special regex chars except * which we handle specially
    regex_pattern = ""
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            regex_pattern += ".*"
        else:
            regex_pattern += re.escape(c)
        i += 1

    if must_end:
        regex_pattern += "$"
    else:
        # Default: prefix match
        regex_pattern = "^" + regex_pattern

    try:
        return bool(re.match(regex_pattern, path))
    except re.error:
        return False


def _can_fetch_with_specificity(rules: list[tuple[bool, str]], url: str) -> bool:
    """Determine if a URL can be fetched using specificity-based matching.

    Per Google's robots.txt spec, the most specific (longest matching) rule wins.
    If multiple rules have the same length, Allow takes precedence over Disallow.
    """
    parsed = urlparse(url)
    path = parsed.path
    if parsed.query:
        path += "?" + parsed.query

    # Find all matching rules with their specificity (pattern length)
    matches: list[tuple[int, bool, str]] = []
    for is_allowed, pattern in rules:
        if _pattern_matches(pattern, path):
            # Specificity = length of the pattern (excluding wildcards for comparison)
            specificity = len(pattern.replace("*", ""))
            matches.append((specificity, is_allowed, pattern))

    if not matches:
        # No rules match = allowed
        return True

    # Sort by specificity (descending), then by is_allowed (True > False)
    # This means: longest match wins, and if tied, Allow beats Disallow
    matches.sort(key=lambda x: (x[0], x[1]), reverse=True)

    best_match = matches[0]
    logger.debug(f"Best matching rule for {path}: {'Allow' if best_match[1] else 'Disallow'} {best_match[2]}")
    return best_match[1]


class RobotsChecker:
    """Check robots.txt compliance for URLs.

    Handles cross-domain checks by caching robots.txt parsers per domain.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self._base_domain = urlparse(base_url).netloc
        # Cache of domain -> (parser, no_robots, crawl_delay, raw_content)
        self._domain_cache: dict[str, tuple[RobotFileParser, bool, float | None, str]] = {}
        # Legacy attributes for backwards compatibility
        self.parser = RobotFileParser()
        self.crawl_delay: float | None = None
        self._loaded = False
        self._no_robots = False  # True if site has no robots.txt (all allowed)
        self._raw_content: str = ""  # Cached raw robots.txt content

    def _load_for_domain(self, domain: str, scheme: str = "https") -> tuple[RobotFileParser, bool, float | None, str] | None:
        """Load robots.txt for a specific domain.

        Args:
            domain: The domain (netloc) to fetch robots.txt for
            scheme: URL scheme to use (http or https)

        Returns (parser, no_robots, crawl_delay, raw_content) or None on failure.
        """
        robots_url = f"{scheme}://{domain}/robots.txt"

        # Try with SSL verification first, then retry without if it fails
        # Some sites have broken certificate chains (missing intermediates)
        for verify_ssl in [True, False]:
            try:
                response = httpx.get(
                    robots_url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=10.0,
                    follow_redirects=True,
                    verify=verify_ssl,
                )
                if not verify_ssl:
                    logger.warning(f"SSL verification disabled for {robots_url} due to certificate issues")

                parser = RobotFileParser()
                if response.status_code == 200:
                    raw_content = response.text
                    parser.parse(raw_content.splitlines())
                    # Get crawl delay - check both UAs and use the most restrictive
                    delay_bot = parser.crawl_delay(ROBOTS_USER_AGENT)
                    delay_mozilla = parser.crawl_delay("Mozilla")
                    delays = [d for d in [delay_bot, delay_mozilla] if d is not None]
                    crawl_delay = max(delays) if delays else None
                    logger.info(f"Loaded robots.txt from {robots_url}")
                    return (parser, False, crawl_delay, raw_content)
                elif response.status_code == 404:
                    # No robots.txt = all allowed
                    parser.parse([])
                    logger.info(f"No robots.txt found at {robots_url}, all paths allowed")
                    return (parser, True, None, "(No robots.txt found - 404)")
                else:
                    logger.warning(f"Unexpected status {response.status_code} for {robots_url}")
                    # Store the error as raw content for reporting
                    self._raw_content = f"(HTTP {response.status_code} from {robots_url})"
                    return None
            except Exception as e:
                # If SSL verification failed, retry without it
                if verify_ssl and "CERTIFICATE_VERIFY_FAILED" in str(e):
                    logger.warning(f"SSL verification failed for {robots_url}, retrying without verification")
                    continue
                logger.error(f"Failed to fetch robots.txt from {robots_url}: {e}")
                # Store the error as raw content for reporting
                self._raw_content = f"(Failed to fetch {robots_url}: {e})"
                return None

        # Should not reach here, but just in case
        return None

    def load(self) -> bool:
        """Fetch and parse robots.txt for the base domain. Returns True if successful."""
        base_scheme = urlparse(self.base_url).scheme or "https"
        result = self._load_for_domain(self._base_domain, scheme=base_scheme)
        if result is None:
            return False

        self.parser, self._no_robots, self.crawl_delay, self._raw_content = result
        self._loaded = True
        self._domain_cache[self._base_domain] = result
        return True

    def _check_with_specificity(self, raw_content: str, url: str) -> bool:
        """Check URL access using specificity-based matching.

        Uses our custom parser that implements Google's robots.txt spec correctly:
        the most specific (longest matching) rule wins, regardless of order.

        Checks both our bot name and Mozilla UA, honoring the most restrictive.
        """
        # Parse rules for both user agents
        rules_bot = _parse_robots_rules(raw_content, ROBOTS_USER_AGENT)
        rules_mozilla = _parse_robots_rules(raw_content, "Mozilla")

        # Check both UAs - if either disallows, we don't fetch
        allowed_bot = _can_fetch_with_specificity(rules_bot, url)
        allowed_mozilla = _can_fetch_with_specificity(rules_mozilla, url)

        return allowed_bot and allowed_mozilla

    def can_fetch(self, url: str) -> bool:
        """Check if the given URL can be fetched according to robots.txt.

        Handles cross-domain URLs by loading the robots.txt for the URL's domain
        if it differs from the base domain.

        Uses specificity-based matching per Google's robots.txt spec:
        the most specific (longest matching) rule wins, regardless of order.
        This fixes Python's RobotFileParser which incorrectly uses first-match-wins.

        Checks both our bot name and Mozilla UA, honoring the most restrictive.
        """
        # Determine which domain's robots.txt to check
        parsed_url = urlparse(url)
        url_domain = parsed_url.netloc
        url_scheme = parsed_url.scheme or "https"

        # Check if we need to load robots.txt for a different domain
        if url_domain != self._base_domain:
            # Check cache first
            if url_domain not in self._domain_cache:
                result = self._load_for_domain(url_domain, scheme=url_scheme)
                if result is None:
                    # If we can't load robots.txt, be conservative and allow
                    logger.warning(f"Could not load robots.txt for {url_domain}, allowing fetch by default")
                    return True
                self._domain_cache[url_domain] = result

            _, no_robots, _, raw_content = self._domain_cache[url_domain]
            if no_robots:
                return True
            return self._check_with_specificity(raw_content, url)

        # Same domain - use the base domain's robots.txt
        if not self._loaded:
            if not self.load():
                # If we can't load robots.txt, be conservative and allow
                logger.warning("Could not load robots.txt, allowing fetch by default")
                return True

        # No robots.txt = all allowed
        if self._no_robots:
            return True

        # Use our specificity-based matching instead of RobotFileParser.can_fetch()
        return self._check_with_specificity(self._raw_content, url)

    def get_crawl_delay(self) -> float:
        """Get the crawl delay in seconds. Returns 1.0 if not specified."""
        if self.crawl_delay is not None:
            return self.crawl_delay
        return 1.0  # Default 1 second between requests

    def get_robots_txt_content(self, url: str | None = None, max_chars: int = 2000) -> str:
        """Return the cached robots.txt content for display.

        Uses the content cached during load() - no additional network request.

        Args:
            url: URL to get robots.txt for. If None, uses base domain's cached content.
            max_chars: Maximum characters to return (default 2000 to avoid bloating error logs)

        Returns:
            Cached robots.txt content (possibly truncated) or error message.
        """
        content = ""

        if url:
            parsed = urlparse(url)
            url_domain = parsed.netloc
            # Check if we have cached content for this domain
            if url_domain in self._domain_cache:
                _, _, _, content = self._domain_cache[url_domain]
            elif url_domain == self._base_domain:
                content = self._raw_content
            else:
                content = "(Content not cached for this domain)"
        else:
            content = self._raw_content

        if not content:
            content = "(No robots.txt content available)"

        # Truncate if too long
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n... (truncated, {len(content)} total chars)"

        return content
