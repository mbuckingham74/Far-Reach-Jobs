# Far Reach Jobs - Roadmap

## Testing Infrastructure

- [ ] **Switch tests from SQLite to MySQL** - Use a separate `far_reach_jobs_test` database on the same MySQL instance for test isolation while matching production behavior. Update `conftest.py` to use MySQL connection and add `MYSQL_TEST_DATABASE` env var.

- [ ] **Add tests for multiple listing URLs** - Unit tests for `GenericScraper.get_job_listing_urls()` to verify it handles empty lines, whitespace, single URL, and multiple URLs correctly. Also test the AI analyzer's first-URL selection logic in `admin.py`.

## Completed

- [x] **Playwright for all scraping** (Phase 1P) - Implemented as a separate Docker container (`playwright-service`) running Node.js + Playwright. **Playwright is now always used** for all scrapers (GenericScraper, DynamicScraper, AI analysis) - no manual toggle needed. Includes automatic httpx fallback if Playwright service is unavailable, robots.txt compliance, and test coverage.

## Future Enhancements

- [ ] **Salary scraping** - Configure `selector_salary` for sources that display salary info on job listings. Once data is available, re-enable the "Has Salary Info" filter in advanced filters. Priority sources to check: ANTHC, Alaska Job Center Network, state/municipal jobs.

- [ ] **Map view** - Overlay job postings on an interactive map of Alaska. Show markers for each community with job counts, click to filter jobs by location. Consider using Leaflet.js with OpenStreetMap tiles or Mapbox. Requires geocoding job locations to lat/lng coordinates (could use a lookup table for known Alaska communities).
