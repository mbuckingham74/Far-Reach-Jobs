# Far Reach Jobs - Roadmap

## Testing Infrastructure

- [ ] **Switch tests from SQLite to MySQL** - Use a separate `far_reach_jobs_test` database on the same MySQL instance for test isolation while matching production behavior. Update `conftest.py` to use MySQL connection and add `MYSQL_TEST_DATABASE` env var.

## Completed

- [x] **Playwright fallback for JavaScript-heavy sites** (Phase 1P) - Implemented as a separate Docker container (`playwright-service`) running Node.js + Playwright. GenericScraper now has a `use_playwright` toggle per source. Includes automatic httpx fallback if Playwright fails, robots.txt compliance, and test coverage.

## Future Enhancements

(Add items as they come up)
