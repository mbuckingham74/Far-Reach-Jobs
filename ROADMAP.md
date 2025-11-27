# Far Reach Jobs - Roadmap

## Testing Infrastructure

- [ ] **Switch tests from SQLite to MySQL** - Use a separate `far_reach_jobs_test` database on the same MySQL instance for test isolation while matching production behavior. Update `conftest.py` to use MySQL connection and add `MYSQL_TEST_DATABASE` env var.

## Scraping Enhancements

- [ ] **Playwright fallback for JavaScript-heavy sites** - Explore using Playwright as a fallback scraper for sites that require JavaScript rendering. GenericScraper currently uses httpx + BeautifulSoup which only sees static HTML. Playwright would enable scraping SPAs and sites with dynamic content loading. Consider: headless browser resource usage, Docker container size impact, when to trigger fallback vs primary scraper.

## Future Enhancements

(Add items as they come up)
