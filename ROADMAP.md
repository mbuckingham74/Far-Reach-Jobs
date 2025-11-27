# Far Reach Jobs - Roadmap

## Testing Infrastructure

- [ ] **Switch tests from SQLite to MySQL** - Use a separate `far_reach_jobs_test` database on the same MySQL instance for test isolation while matching production behavior. Update `conftest.py` to use MySQL connection and add `MYSQL_TEST_DATABASE` env var.

- [ ] **Add tests for multiple listing URLs** - Unit tests for `GenericScraper.get_job_listing_urls()` to verify it handles empty lines, whitespace, single URL, and multiple URLs correctly. Also test the AI analyzer's first-URL selection logic in `admin.py`.

## Completed

- [x] **Playwright fallback for JavaScript-heavy sites** (Phase 1P) - Implemented as a separate Docker container (`playwright-service`) running Node.js + Playwright. GenericScraper now has a `use_playwright` toggle per source. Includes automatic httpx fallback if Playwright fails, robots.txt compliance, and test coverage.

## Future Enhancements

- [ ] **Salary scraping** - Configure `selector_salary` for sources that display salary info on job listings. Once data is available, re-enable the "Has Salary Info" filter in advanced filters. Priority sources to check: ANTHC, Alaska Job Center Network, state/municipal jobs.
