# Far Reach Jobs - Implementation Status

**Last Updated:** 2025-11-29
**Repository:** https://github.com/mbuckingham74/Far-Reach-Jobs
**Domain:** far-reach-jobs.tachyonfuture.com

## Project Overview

Job aggregator for Alaska bush communities and extremely rural US towns (pop < 10k). Scrapes public org sites, allows users to save jobs, and redirects to original listings to apply.

## Technology Stack

- **Backend:** FastAPI + SQLAlchemy + MySQL 8
- **Frontend:** HTMX + Jinja2 + Tailwind CSS (no SPA)
- **Scraping:** httpx + BeautifulSoup + APScheduler
- **Auth:** JWT in httpOnly cookies, bcrypt passwords
- **Deployment:** Docker Compose on tachyonfuture.com with NPM for SSL

## Completed Phases

### Phase 1A: Foundation ✅
- Git repo initialized, pushed to GitHub
- Docker Compose configuration
- FastAPI app structure with health check
- SQLAlchemy models: User, Job, SavedJob, ScrapeSource
- Alembic migrations (001: initial schema, 002: verification token expiry, 003: scrape logs, 004: last_scrape_success)
- APScheduler setup (noon/midnight Alaska time)

**Key Files:**
- `backend/app/main.py` - FastAPI entry point
- `backend/app/config.py` - Environment config with validation
- `backend/app/database.py` - SQLAlchemy setup
- `backend/app/models/` - User, Job, SavedJob, ScrapeSource
- `docker-compose.yml` - Container orchestration

### Phase 1B: Authentication ✅
- User registration with email verification
- JWT login with httpOnly secure cookies
- Gmail SMTP for verification emails
- Auto-verify in dev when SMTP not configured
- Password validation (8-128 chars)
- 24-hour verification token expiry

**Key Files:**
- `backend/app/routers/auth.py` - Auth endpoints
- `backend/app/services/auth.py` - Password hashing, JWT
- `backend/app/services/email.py` - Gmail SMTP
- `backend/app/dependencies.py` - Auth middleware
- `backend/app/templates/login.html`, `register.html`

**API Endpoints:**
- POST `/api/auth/register` - Create account
- POST `/api/auth/login` - Login, set cookie
- GET `/api/auth/verify/{token}` - Verify email
- POST `/api/auth/logout` - Clear cookie
- POST `/api/auth/resend-verification` - Resend email
- GET `/api/auth/me` - Get current user

### Phase 1C: Scraper Infrastructure ✅
- BaseScraper abstract class with robots.txt compliance
- RobotsChecker for fetching/parsing robots.txt
- Scraper runner with job upsert (insert or update)
- In-memory deduplication for same-scrape duplicates
- Updates job content fields when source changes
- Stale job lifecycle: mark after 24h, delete after 7 days

**Key Files:**
- `backend/scraper/base.py` - BaseScraper class
- `backend/scraper/robots.py` - RobotsChecker
- `backend/scraper/runner.py` - Scraper execution + job upsert
- `backend/scraper/scheduler.py` - APScheduler integration
- `backend/scraper/utils.py` - State normalization, salary extraction
- `backend/scraper/sources/__init__.py` - Scraper registration docs

**Scraper Registration:**
```python
from scraper import BaseScraper, ScrapedJob, register_scraper

@register_scraper
class MyOrgScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "My Organization"

    @property
    def base_url(self) -> str:
        return "https://example.com"

    def get_job_listing_urls(self) -> list[str]:
        return ["https://example.com/jobs"]

    def parse_job_listing_page(self, soup, url) -> list[ScrapedJob]:
        # Parse and return jobs
        pass
```

### Phase 1D: Job Display & Search ✅
- [x] Job listing API with filters (location, job_type, keyword)
- [x] Full-text search implementation (ILIKE on title, org, description, location)
- [x] Home page with HTMX job list
- [x] Filter UI components (search input, location dropdown, job type dropdown)
- [x] Job card component with "Apply" link
- [x] Pagination with HTMX navigation
- [x] Dynamic location filter (server-side rendered from database)
- [x] Default location fallback for sources without location selectors

**Key Files:**
- `backend/app/routers/jobs.py` - Job listing API with filters
- `backend/app/schemas/job.py` - Job response schemas
- `backend/app/templates/index.html` - Home page with filters
- `backend/app/templates/partials/job_list.html` - HTMX job list partial

**API Endpoints:**
- GET `/api/jobs` - List jobs with filters (q, location, job_type, page, per_page)
- GET `/api/jobs/locations` - Get unique locations with active jobs (HTMX-aware)
- GET `/api/jobs/states` - Get states with active jobs
- GET `/api/jobs/job-types` - Get job types with active jobs
- GET `/api/jobs/{id}` - Get single job by ID

### Phase 1E: Saved Jobs ✅
- [x] Save/unsave job endpoints with HTMX button swap
- [x] Saved jobs page with stale job warnings
- [x] Save button on job cards (HTMX toggle)
- [x] Stale jobs shown with warning on saved page; deleted jobs cascade-removed

**Key Files:**
- `backend/app/routers/saved_jobs.py` - Save/unsave endpoints
- `backend/app/templates/saved.html` - Saved jobs page
- `backend/app/templates/partials/save_button.html` - HTMX save/unsave button
- `backend/app/templates/partials/saved_job_list.html` - Saved jobs list partial

**API Endpoints:**
- GET `/api/saved-jobs` - List user's saved jobs
- POST `/api/saved-jobs/{job_id}` - Save a job
- DELETE `/api/saved-jobs/{job_id}` - Unsave a job

### Phase 1F: Polish & Deploy ✅
- [x] Tailwind CSS styling via CDN
- [x] Responsive design (mobile-first with sm: breakpoints)
- [x] Error pages (404, 500) with custom handlers
- [x] NPM reverse proxy configuration
- [x] Production deployment to tachyonfuture.com
- [x] Let's Encrypt SSL certificate
- [ ] Initial scrape run (awaiting scraper URLs)
- [ ] Beta launch

### Phase 1G: Dark Mode ✅
- [x] Dark mode toggle in header (sun/moon icons)
- [x] System preference detection (prefers-color-scheme)
- [x] LocalStorage persistence across sessions
- [x] No flash on page load (dark mode applied before render)
- [x] All templates updated with dark: variants
- [x] Works for all users (logged in or not)

### Phase 1H: Admin Scrape History ✅
- [x] Scrape history page at `/admin/history`
- [x] ScrapeLog model tracks each scrape run
- [x] Shows trigger type, duration, jobs found/added/updated
- [x] Error display with JSON parsing
- [x] Summary stats (total runs, success rate, totals)

**Key Files:**
- `backend/app/models/scrape_log.py` - ScrapeLog model
- `backend/app/templates/admin/history.html` - History page template

### Phase 1I: Scrape Notification Emails ✅
- [x] Email notifications after each scrape run (manual or scheduled)
- [x] HTML formatted email with summary table
- [x] Shows: execution time, trigger type, duration, sources processed
- [x] Shows: jobs added, updated, removed (stale)
- [x] Error table with source name and error message
- [x] Link to admin scrape history page
- [x] Plain text fallback for email clients

**Key Files:**
- `backend/app/services/email.py` - `ScrapeNotificationData` and `send_scrape_notification()`
- `backend/app/config.py` - `admin_email` setting

**Configuration:**
```env
ADMIN_EMAIL=michael.buckingham74@gmail.com
```

### Phase 1J: Error Handling & Transaction Safety ✅
- [x] Per-source transaction isolation (commit after each source)
- [x] Per-job savepoints (failed jobs don't roll back successful ones)
- [x] Sanitized error messages in UI (no DB internals exposed)
- [x] Full exception logging for debugging
- [x] Catastrophic failure logging (ScrapeLog written even when scraper crashes)
- [x] Accurate stats in ScrapeLog and email notifications

**Key Changes:**
- `run_all_scrapers()` commits after each source for isolation
- `db.begin_nested()` creates savepoints for each job upsert
- Failed savepoints roll back only that job, counters/seen_ids stay accurate
- Admin routes log full exceptions, show user-friendly messages
- Catastrophic scraper failures still write ScrapeLog entries

### Phase 1K: Route-Level Error Handling ✅
- [x] Global exception handler logs exceptions with request context (method, path)
- [x] Auth routes wrap commits with try/except/rollback (register, verify, resend)
- [x] Email send failures surface user-friendly message with resend instructions
- [x] Saved jobs routes wrap commits with try/except/rollback
- [x] HTMX error partial for graceful save/unsave failure recovery

**Key Files:**
- `backend/app/main.py` - Global exception handler with logging
- `backend/app/routers/auth.py` - Protected commits, email failure messaging
- `backend/app/routers/saved_jobs.py` - Protected commits, HTMX error partials
- `backend/app/templates/partials/save_button_error.html` - Retry button partial

**Key Changes:**
- `general_exception_handler()` now calls `logger.exception()` before returning 500
- All `db.commit()` calls in auth/saved_jobs wrapped with try/except/rollback
- Failed email sends return actionable message instead of silent pass
- HTMX callers get "Error - Retry" button instead of broken UI on DB failures

### Phase 1L: Single-Source Scraping ✅
- [x] "Scrape" button for each source in admin panel (blue, next to Delete)
- [x] Single-source scrape endpoint with HTMX integration
- [x] `last_scrape_success` field tracks success/fail status per source
- [x] Success/Failed badge displayed under Last Scraped timestamp
- [x] Single-source scrapes logged to scrape history
- [x] Email notifications sent for single-source scrapes
- [x] Edge cases handled: unknown scraper class, catastrophic failures
- [x] Scrape progress modal with loading spinner and results display
- [x] Modal shows stats (jobs found, new, updated) on success
- [x] Modal shows error with "View Logs" link on failure
- [x] Source list auto-refreshes after scrape completes (via HX-Trigger)

**Key Files:**
- `backend/app/routers/admin.py` - `trigger_single_source_scrape()` endpoint
- `backend/app/models/scrape_source.py` - `last_scrape_success` field
- `backend/app/templates/admin/partials/source_list.html` - Scrape button and status badge
- `backend/app/templates/admin/partials/scrape_modal_result.html` - Modal result partial
- `backend/app/templates/admin/dashboard.html` - Modal HTML and JavaScript
- `backend/scraper/runner.py` - Status tracking in `run_scraper()` and `run_all_scrapers()`
- `backend/alembic/versions/004_add_last_scrape_success.py` - Migration

**API Endpoints:**
- POST `/admin/sources/{id}/scrape` - Trigger scrape for single source

### Phase 1M: GenericScraper ✅
- [x] Configurable scraper using CSS selectors (no code required per source)
- [x] Admin configuration page for each source at `/admin/sources/{id}/configure`
- [x] Required selectors: job container, title, URL
- [x] Optional selectors: organization, location, job type, salary, description
- [x] Pagination support with next-page selector and max pages limit
- [x] Server-side validation for required fields
- [x] Relative URL resolution against current page (handles ./path and ../path)
- [x] GenericScraper is default for new sources

**Key Files:**
- `backend/scraper/sources/generic.py` - GenericScraper implementation
- `backend/app/templates/admin/configure_source.html` - Configuration form
- `backend/app/routers/admin.py` - Configure endpoints (GET/POST)
- `backend/app/models/scrape_source.py` - Selector fields
- `backend/alembic/versions/005_add_generic_scraper_fields.py` - Migration

**ScrapeSource Selector Fields:**
- `listing_url` - Page containing job listings (defaults to base_url)
- `selector_job_container` - CSS selector for each job's container element
- `selector_title` - CSS selector for job title within container
- `selector_url` - CSS selector for job link within container
- `selector_organization` - CSS selector for organization name
- `selector_location` - CSS selector for location
- `selector_job_type` - CSS selector for job type
- `selector_salary` - CSS selector for salary info
- `selector_description` - CSS selector for description
- `url_attribute` - Attribute to extract URL from (default: "href")
- `selector_next_page` - CSS selector for pagination next link
- `max_pages` - Maximum pages to scrape (default: 10)
- `default_location` - Fallback location when scraper doesn't extract one (e.g., "Bethel" for City of Bethel jobs)

**How to Add a New Job Source:**

*Option A: Single Source*
1. Go to Admin Dashboard → Add Scrape Source
2. Enter source name and base URL
3. Click "Configure" on the new source
4. Use browser DevTools to inspect the job listing page
5. Enter CSS selectors for job container, title, and URL (required)
6. Optionally add selectors for organization, location, salary, etc.
7. Save configuration and click "Scrape" to test

*Option B: Bulk Import via CSV*
1. Prepare a CSV file with columns: `Source Name`, `Base URL`, `Jobs URL` (optional)
2. Go to Admin Dashboard → Bulk Import from CSV
3. Upload the CSV file
4. Review results (sources are imported as disabled)
5. Go to Disabled Sources, configure each source, then enable it

**API Endpoints:**
- GET `/admin/sources/{id}/configure` - Configuration page
- POST `/admin/sources/{id}/configure` - Save configuration

### Phase 1N: Homepage Stats Banner ✅
- [x] Stats banner on homepage showing key metrics
- [x] Three stats: Sources count, Jobs Available, New This Week
- [x] "New This Week" uses rolling 7-day window based on `first_seen_at`
- [x] HTMX-loaded with placeholder while fetching
- [x] Responsive grid (stacked on mobile, 3-col on sm+)
- [x] Semantic colors: blue (sources), purple (jobs), green (new)
- [x] Dark mode support

**Key Files:**
- `backend/app/routers/jobs.py` - `/api/jobs/stats` endpoint
- `backend/app/templates/index.html` - Stats banner placeholder
- `backend/app/templates/partials/stats_banner.html` - HTMX partial

**API Endpoints:**
- GET `/api/jobs/stats` - Returns `sources_count`, `jobs_count`, `new_this_week`

### Phase 1O: Testing Infrastructure ✅
- [x] Pytest configuration (`backend/pytest.ini`)
- [x] Test fixtures for database, client, sources, jobs (`backend/tests/conftest.py`)
- [x] Dev dependencies in separate file (`backend/requirements-dev.txt`)
- [x] Stats endpoint tests covering edge cases

**Key Files:**
- `backend/pytest.ini` - Pytest configuration
- `backend/requirements-dev.txt` - Test dependencies (includes base requirements)
- `backend/tests/conftest.py` - Fixtures for DB, client, sample data
- `backend/tests/test_stats.py` - Stats endpoint tests

**Running Tests:**
```bash
# Install dev dependencies
pip install -r backend/requirements-dev.txt

# Run tests
cd backend && pytest tests/ -v
```

**Note:** Tests currently use SQLite for speed. See `ROADMAP.md` for planned MySQL test migration.

### Phase 1P: Playwright Browser Rendering ✅
- [x] Separate `playwright-service` Docker container (Node.js + Playwright)
- [x] **Playwright is now always used** for all scraping operations
- [x] GenericScraper, DynamicScraper, AI analysis all use Playwright by default
- [x] Automatic fallback to httpx if Playwright service is unavailable
- [x] robots.txt compliance checked before any fetch (Playwright or httpx)
- [x] Test suite for fallback behavior (`test_playwright_fallback.py`)
- [x] **Interactive page support:** Dropdown selection and button clicks for JS-heavy pages
- [x] **SSL bypass:** Automatic retry without SSL verification for sites with broken certs

**Key Files:**
- `playwright-service/` - Node.js service with Express API
- `backend/scraper/playwright_fetcher.py` - Python client for Playwright service
- `backend/scraper/sources/generic.py` - `_fetch_page()` with Playwright/httpx logic
- `backend/scraper/runner.py` - Always enables Playwright for all scrapers
- `backend/alembic/versions/006_add_use_playwright.py` - Migration (legacy)

**Interactive Page Features (Playwright):**
- `selectActions` - Array of `{selector, value}` for dropdown selection before page extraction
- `clickSelector` - CSS selector for button/link to click after page loads
- `clickWaitFor` - CSS selector to wait for after clicking (e.g., results table)
- Useful for Oracle E-Business Suite, UKG, and other JS-heavy job portals

**Architecture:**
```
┌─────────────────┐    HTTP POST     ┌─────────────────────┐
│  web container  │ ───────────────► │ playwright container │
│  (FastAPI)      │    /fetch        │ (Node.js + Chromium) │
└─────────────────┘                  └─────────────────────┘
```

**Why Playwright is Always Used:**
- A few seconds overhead is negligible compared to failing on JS-heavy sites
- No need to manually toggle "Browser Mode" - it just works
- Handles bot protection (Cloudflare), SPAs, and dynamic content automatically

**Configuration:**
```env
# Set automatically by docker-compose
PLAYWRIGHT_SERVICE_URL=http://playwright:3000
```

## Remaining Work

### Scrapers (Phase 2)
- GenericScraper is ready - configure sources via admin panel
- Scheduler runs in production (noon/midnight Alaska time)
- Add job sources by configuring CSS selectors in admin

## Database Schema

### users
- id, email, password_hash, is_verified
- verification_token, verification_token_created_at
- created_at, updated_at

### jobs
- id, source_id (FK), external_id (unique)
- title, organization, location, state
- description, job_type, salary_info, url
- first_seen_at, last_seen_at, is_stale
- created_at, updated_at

### saved_jobs
- id, user_id (FK), job_id (FK), saved_at
- Unique constraint: (user_id, job_id)

### scrape_sources
- id, name, base_url, scraper_class
- is_active, last_scraped_at, last_scrape_success, created_at
- needs_configuration (True for bulk imports awaiting CSS selector setup)
- robots_blocked, robots_blocked_at (tracks robots.txt blocking status)
- skip_robots_check (bypass robots.txt for public job boards with restrictive rules)
- listing_url (GenericScraper: page containing job listings)
- selector_job_container, selector_title, selector_url (required for GenericScraper)
- selector_organization, selector_location, selector_job_type
- selector_salary, selector_description
- url_attribute, selector_next_page, max_pages
- use_playwright (enables headless browser for bot-protected sites)
- default_location (fallback location when selector doesn't find one)
- default_state (fallback state code, e.g., "AK" for Alaska-only sources)
- custom_scraper_code (AI-generated Python code for custom scrapers)
- sitemap_url (SitemapScraper: URL of the XML sitemap)
- sitemap_url_pattern (SitemapScraper: regex to filter URLs)
- organization (SitemapScraper: organization name for all jobs)

## Environment Variables

```env
# Database
MYSQL_HOST=host.docker.internal
MYSQL_PORT=3306
MYSQL_DATABASE=far_reach_jobs
MYSQL_USER=far_reach_jobs
MYSQL_PASSWORD=<password>

# Auth
SECRET_KEY=<64-char-random>  # Required in production
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# Email (Gmail SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<email>
SMTP_PASSWORD=<app-password>
FROM_EMAIL=noreply@far-reach-jobs.tachyonfuture.com

# App
APP_URL=https://far-reach-jobs.tachyonfuture.com
ENVIRONMENT=development|production

# Admin
ADMIN_USERNAME=<username>
ADMIN_PASSWORD=<password>
ADMIN_EMAIL=<email>  # Receives scrape notification emails

# AI Features
ANTHROPIC_API_KEY=<api-key>  # Required for AI selector analysis and custom scraper generation
```

## Important Implementation Details

### Cookie Security
- `secure=True` only in production (allows HTTP in dev)
- `httponly=True`, `samesite=lax`
- Logout uses POST via JS (not GET link)

### Email Verification
- 24-hour token expiry enforced
- Auto-verify in dev when SMTP not configured
- Token stored with timestamp in `verification_token_created_at`

### Scraper Job Lifecycle
1. New job: `first_seen_at = now`, `last_seen_at = now`, `is_stale = False`
2. Seen again: `last_seen_at = now`, content fields updated if changed
3. Not seen for 48h: `is_stale = True` (2 missed daily scrapes)
4. Stale for 7 days: Deleted from database

### Scraper Transaction Handling
- **Per-source isolation:** Each source commits independently so failures don't affect other sources
- **Per-job savepoints:** `db.begin_nested()` wraps each job upsert; failures roll back only that job
- **Accurate accounting:** Counters and `seen_ids` only updated after successful savepoint
- **Catastrophic failures:** Even if `run_scraper()` crashes, a ScrapeLog entry is written

### robots.txt Handling
- Respects Disallow rules and Crawl-delay
- HTTP User-Agent: `Mozilla/5.0 (compatible; FarReachJobs/1.0; +https://far-reach-jobs.tachyonfuture.com)`
- robots.txt compliance checks both `FarReachJobs` and `Mozilla` UAs, honoring the most restrictive
- Uses maximum crawl delay from either UA-specific rule
- **Fail-closed security:** If robots.txt fetch fails, source is marked as blocked (not allowed)
- Sites without robots.txt (404) allow all paths
- Blocked sources moved to separate admin page, excluded from scheduled/bulk scrapes
- Raw robots.txt content cached during load for error reporting (2KB limit)

## Server Info

**Server IP:** 62.72.5.248 (tachyonfuture.com)
**Domain:** far-reach-jobs.tachyonfuture.com
**DNS:** Unproxied A record pointing to server IP (propagated)
**Deployed:** ~/apps/far-reach-jobs on server

### NPM (Nginx Proxy Manager)
- NPM manages SSL termination (Let's Encrypt, cert ID 25)
- Login: michael.buckingham74@gmail.com (password in server .env)
- Proxy host ID: 23, forwards to `far-reach-jobs-web:8000`
- Network: `npm_network`

### MySQL 8
- Dedicated container: `far-reach-jobs-mysql`
- Database/user: `far_reach_jobs`
- Credentials in server .env file

### Gmail SMTP
- User: michael.buckingham74@gmail.com
- App password stored in server .env (format: xxxx xxxx xxxx xxxx)

## Deployment (Completed)

1. ✅ SSH to server, cloned repo to `~/apps/far-reach-jobs`
2. ✅ Created `.env` with production values
3. ✅ MySQL container auto-creates database and user
4. ✅ docker-compose.yml joins NPM network
5. ✅ `docker compose up -d --build`
6. ✅ Alembic migrations applied (001-011)
7. ✅ NPM proxy host configured with SSL
8. ✅ Health endpoint verified: https://far-reach-jobs.tachyonfuture.com/api/health

## Working Source Configurations

This section documents CSS selectors that have been tested and work for specific job sources.

### City of Kotzebue
- **URL:** `http://www.cityofkotzebue.com/jobs`
- **Container:** `tbody tr`
- **Title:** `td.views-field-title .tablesaw-cell-content a`
- **URL:** `td.views-field-title .tablesaw-cell-content a`
- **Notes:** The page uses a responsive table (tablesaw). The title selector must target `td.views-field-title` (not just `.views-field-title`) to avoid matching the `<th>` header row's sort link.

### City of Dillingham
- **URL:** `https://www.dillinghamak.us/jobs`
- **Container:** `tr.odd, tr.even`
- **Title:** `.views-field-title a`
- **URL:** `.views-field-title a`

### Foraker Group
- **URL:** `https://www.forakergroup.org/site/index.cfm/cboard`
- **Container:** `.row.cboardrow`
- **Title:** `h4`
- **URL:** `.row.cboardrow`

### Tanana Chiefs Conference (Oracle E-Business Suite)
- **URL:** `https://careers.tananachiefs.org/OA_HTML/OA.jsp?OAFunc=TCC_IRC_ALL_JOBS`
- **Type:** DynamicScraper with custom code (requires Playwright + skip_robots_check)
- **Flags:** `use_playwright=True`, `skip_robots_check=True`
- **Interactive:** Selects "All Open Reqs" dropdown, clicks Search button
- **Notes:** Oracle E-Business Suite uses JavaScript onclick handlers instead of real hrefs. Job IDs extracted from anchor text (e.g., `IRC47603`). Detail URLs from hidden input fields.

### Alaska Airlines (SitemapScraper)
- **Base URL:** `https://careers.alaskaair.com`
- **Type:** SitemapScraper
- **Sitemap URL:** `https://careers.alaskaair.com/sitemaps/jobs_1.xml`
- **URL Pattern:** `-ak/` (filters to Alaska jobs only)
- **Organization:** `Alaska Airlines`
- **Default State:** `AK`
- **Notes:** JavaScript-heavy Vue/Nuxt site that returns 404 for direct URL access with query params. Uses sitemap to extract job URLs containing location and title in the path structure (e.g., `/kotzebue-ak/customer-service-agent/`). Fast and reliable (~1 second vs 2.5 minutes for Playwright approach).

### Phase 1Q: AI-Powered Selector Detection ✅
- [x] AI analysis endpoint using Claude API
- [x] "Analyze Page with AI" button on source configuration page
- [x] Claude analyzes HTML and suggests CSS selectors
- [x] "Apply" buttons to fill individual selectors
- [x] "Apply All Suggestions" button for one-click configuration
- [x] Compatibility indicator (Generic Scraper Compatible / May Need Custom Scraper)
- [x] Sample job preview showing extracted data
- [x] Always uses Playwright for reliable JS rendering

**Key Files:**
- `backend/app/services/ai_analyzer.py` - Claude API integration, HTML analysis
- `backend/app/routers/admin.py` - `/admin/sources/{id}/analyze` endpoint
- `backend/app/templates/admin/partials/ai_suggestions.html` - Results UI

**Configuration:**
```env
ANTHROPIC_API_KEY=<your-api-key>
```

### Phase 1R: AI Custom Scraper Generation ✅
- [x] "Generate Custom Scraper" button when AI indicates site needs custom handling
- [x] Claude generates complete Python scraper class from HTML
- [x] Generated code validated for required class structure and methods
- [x] Code displayed with syntax highlighting and copy button
- [x] Generated code saved to `custom_scraper_code` field for later use
- [x] Validation checks: class definition, BaseScraper inheritance, required methods

**Key Files:**
- `backend/app/services/ai_analyzer.py` - `generate_scraper_for_url()`, `SCRAPER_GENERATION_PROMPT`
- `backend/app/routers/admin.py` - `/admin/sources/{id}/generate-scraper` endpoint
- `backend/app/templates/admin/partials/generated_scraper.html` - Code display UI
- `backend/app/models/scrape_source.py` - `custom_scraper_code` field
- `backend/alembic/versions/009_add_custom_scraper_code.py` - Migration

**Workflow:**
1. Add new source in admin panel
2. Click "Analyze Page with AI"
3. If "May Need Custom Scraper" appears, click "Generate Custom Scraper"
4. Review generated Python code
5. Copy code and create file in `backend/scraper/sources/`
6. Register scraper and update source's `scraper_class` field

**Validation:**
Generated code must contain:
- Class inheriting from `BaseScraper`
- `source_name` property
- `base_url` property
- `get_job_listing_urls()` method
- `parse_job_listing_page()` method

### Phase 1S: Docker DNS Fix ✅
- [x] Explicit DNS servers (8.8.8.8, 8.8.4.4) added to web container
- [x] Fixes intermittent DNS resolution failures in Docker
- [x] Required for AI analysis to fetch external websites reliably

**Key Files:**
- `docker-compose.yml` - `dns` configuration for web service

### Phase 1T: About Us Page ✅
- [x] About page at `/about` with project story and mission
- [x] Sections: Origin Story, Mission, Ethical Principles, Target Audience, Community Project
- [x] Ethical principles: robots.txt compliance, direct employer links, no data collection, no ads
- [x] Header navigation link (after dark mode toggle)
- [x] Footer navigation link
- [x] Dark mode support

**Key Files:**
- `backend/app/templates/about.html` - About page template
- `backend/app/main.py` - `/about` route

### Phase 1U: For Employers Page ✅
- [x] Employer portal at `/employers` with three submission options
- [x] Job submission form with full validation (title, org, location, URL, etc.)
- [x] Careers page URL submission for automatic scraping setup
- [x] Bulk source submission via CSV (see Phase 1X)
- [x] Input validation with SQL injection and XSS protection
- [x] Email notifications to admin for all submission types
- [x] Header and footer navigation links
- [x] Tabbed interface for switching between submission types
- [x] Success/error messaging with form reset on success
- [x] Updated About page with "For Employers" CTA section

**Key Files:**
- `backend/app/templates/employers.html` - For Employers page template
- `backend/app/routers/employers.py` - API endpoints for submissions
- `backend/app/schemas/employer.py` - Pydantic validation schemas
- `backend/app/services/email.py` - Notification email functions
- `backend/app/main.py` - `/employers` route

**API Endpoints:**
- POST `/api/employers/submit-job` - Submit a single job posting
- POST `/api/employers/submit-careers-page` - Submit careers page URL for scraping
- POST `/api/employers/submit-bulk-sources` - Submit CSV of sources for admin review

**Security:**
- URL validation blocks SQL injection chars (`'`, `"`, `;`)
- URL validation blocks XSS (`<script`, `javascript:`, `data:`)
- Email validation with regex pattern matching
- All user input HTML-escaped in notification emails
- Max length limits on all fields (state: 50, description: 5000, job_type: 100, salary: 255)

**Reliability:**
- Pre-flight check for ADMIN_EMAIL and SMTP credentials before accepting submissions
- Returns 503 if email config missing or SMTP send fails (no false success messages)
- SMTP calls run in ThreadPoolExecutor to avoid blocking event loop
- Submissions only succeed if email actually sends

### Phase 1V: Robots.txt Blocked Sources Management ✅
- [x] Automatic detection of robots.txt blocking during scrape attempts
- [x] Separate admin page for robots-blocked sources at `/admin/sources/robots-blocked`
- [x] "Recheck" button that re-fetches robots.txt before unblocking
- [x] Robots-blocked sources excluded from scheduled and bulk scrapes
- [x] Fail-closed security: sources blocked if robots.txt fetch fails
- [x] Robots.txt content displayed in scrape error reports
- [x] Content caching to avoid duplicate network requests
- [x] 2KB truncation limit to prevent log bloat
- [x] `skip_robots_check` flag for sites with overly restrictive robots.txt (e.g., blanket `Disallow: /`)
- [x] SSL bypass for robots.txt fetch (handles sites with broken certificate chains)

**Key Files:**
- `backend/app/models/scrape_source.py` - `robots_blocked`, `robots_blocked_at` fields
- `backend/scraper/runner.py` - `check_robots_blocked()` pre-flight check
- `backend/scraper/robots.py` - `get_robots_txt_content()` with caching
- `backend/app/routers/admin.py` - Robots-blocked page, recheck endpoint
- `backend/app/templates/admin/robots_blocked_sources.html` - Blocked sources page
- `backend/alembic/versions/011_add_robots_blocked.py` - Migration

**Database Fields:**
- `robots_blocked` (Boolean) - True if site's robots.txt disallows crawling
- `robots_blocked_at` (DateTime) - Timestamp when blocking was detected
- `skip_robots_check` (Boolean) - Bypass robots.txt for public job boards with restrictive rules

**API Endpoints:**
- GET `/admin/sources/robots-blocked` - Page listing robots-blocked sources
- GET `/admin/sources/robots-blocked/list` - HTMX partial for blocked source list
- GET `/admin/sources/robots-blocked/count` - HTMX partial for count badge
- POST `/admin/sources/{id}/recheck-robots` - Re-fetch robots.txt and unblock if allowed

**Behavior:**
1. Before scraping, `check_robots_blocked()` verifies robots.txt allows access
2. If blocked or fetch fails (fail-closed), source is marked `robots_blocked=True`
3. Robots-blocked sources appear on separate admin page, not in main source list
4. Admin can click "Recheck" to re-verify robots.txt (e.g., after site whitelist)
5. If recheck passes, source is moved back to active sources
6. Error reports include cached robots.txt content for debugging

### Phase 1W: CSV Bulk Import ✅
- [x] Bulk import sources from CSV file via admin dashboard
- [x] Flexible column name matching (Source Name/Name, Base URL/URL, Jobs URL)
- [x] Imported sources created with `needs_configuration=True` (go to Needs Configuration page)
- [x] In-batch duplicate detection (prevents duplicates within same CSV)
- [x] Database duplicate detection with URL normalization (case, trailing slashes)
- [x] 1MB file size limit for safety
- [x] Prefetched existing sources for O(1) duplicate lookups
- [x] Detailed result feedback (added, skipped with reasons, errors)
- [x] HTMX integration with auto-refresh of source lists

**Key Files:**
- `backend/app/routers/admin.py` - `import_sources_csv()` endpoint, `_normalize_url()` helper
- `backend/app/templates/admin/dashboard.html` - CSV upload form UI
- `backend/app/templates/admin/partials/csv_import_result.html` - Import results partial

**API Endpoints:**
- POST `/admin/sources/import-csv` - Upload CSV file to bulk import sources

**CSV Format:**
```csv
Source Name,Base URL,Jobs URL
City of Bethel,https://www.cityofbethel.net,https://www.cityofbethel.net/jobs
NANA Regional,https://nana.com,https://nana.com/careers
Yukon-Kuskokwim Health,https://www.ykhc.org,https://www.ykhc.org/employment
```

**Column Name Variants Accepted:**
- Source Name: `Source Name`, `Name`, `Source`, `Organization`, `Org`
- Base URL: `Base URL`, `Base_URL`, `BaseURL`, `URL`, `Website`
- Jobs URL (optional): `Jobs URL`, `Jobs_URL`, `JobsURL`, `Listing URL`, `Listing_URL`, `Careers URL`, `Careers_URL`

**Workflow:**
1. Go to Admin Dashboard → Bulk Import from CSV section
2. Click "View CSV format example" for format reference
3. Upload CSV file with source names and URLs
4. Review import results (added count, skipped with reasons, errors)
5. Click "Configure Imported Sources" → goes to Needs Configuration page
6. For each source: Configure → Test Scrape → auto-enabled when jobs found

**Deduplication Logic:**
- Names compared case-insensitively
- URLs normalized: lowercase, trailing slashes stripped
- Checks both existing database sources AND within the same CSV file
- Skipped sources show specific reason (name exists, URL exists, duplicate in CSV)

### Phase 1X: Employer Bulk Source Submission ✅
- [x] Public bulk import form on For Employers page (`/employers` → "Bulk Import" tab)
- [x] CSV upload with validation (Organization, Base URL required; Careers URL optional)
- [x] Pydantic validation schemas with strict input sanitization
- [x] URL injection protection (SQL, XSS, JavaScript, data: URLs blocked)
- [x] HTML tag blocking in organization names
- [x] 512KB file size limit (conservative for public endpoint)
- [x] Maximum 100 sources per submission
- [x] Email notification to admin with all submitted sources
- [x] Does NOT auto-add to database (admin review required)
- [x] Detailed success/error messaging with skipped row counts

**Key Files:**
- `backend/app/templates/employers.html` - Bulk Import tab with CSV upload form
- `backend/app/routers/employers.py` - `/submit-bulk-sources` endpoint
- `backend/app/schemas/employer.py` - `BulkSourceEntry`, `BulkSourceSubmission` schemas
- `backend/app/services/email.py` - `send_bulk_source_submission_notification()`

**API Endpoints:**
- POST `/api/employers/submit-bulk-sources` - Upload CSV of sources for admin review

**Security:**
- URL validation blocks: `'`, `"`, `;` (SQL injection), `<script`, `javascript:`, `data:`, whitespace
- Organization name blocks HTML tags (`<...>`)
- Email validation with regex pattern
- All user input HTML-escaped in notification emails
- More conservative limits than admin bulk import (512KB vs 1MB, same 100 row limit)

**CSV Format:**
```csv
Organization,Base URL,Careers URL
City of Bethel,https://www.cityofbethel.net,https://www.cityofbethel.net/jobs
NANA Regional,https://nana.com,https://nana.com/careers
```

**Workflow:**
1. Employer goes to For Employers → "Bulk Import" tab
2. Uploads CSV file with organization names and URLs
3. Provides contact email and optional notes
4. Admin receives email notification with all sources
5. Admin reviews and adds sources via admin CSV import

### Phase 1Z: SitemapScraper ✅
- [x] New scraper type for extracting jobs from XML sitemaps
- [x] Parses job title, location, and state from URL structure
- [x] URL pattern filtering (e.g., `-ak/` for Alaska jobs)
- [x] Recursive sitemap index handling (fetches child sitemaps)
- [x] robots.txt compliance for child sitemaps
- [x] Admin UI for configuring sitemap URL, pattern, and organization
- [x] SitemapScraper option in Add Source and Configure Source dropdowns
- [x] Database migration for sitemap_url, sitemap_url_pattern, organization fields

**Key Files:**
- `backend/scraper/sources/sitemap.py` - SitemapScraper implementation
- `backend/app/models/scrape_source.py` - sitemap fields
- `backend/alembic/versions/015_add_sitemap_scraper_fields.py` - Migration
- `backend/app/templates/admin/configure_source.html` - Sitemap config UI

**When to Use:**
- Site is JavaScript-heavy (Vue, React, Angular) and returns 404 for direct URL access
- Site has an XML sitemap at `/sitemap.xml` or similar
- Job URLs contain structured data (e.g., `/kotzebue-ak/customer-service-agent/`)
- No public API available

**Configuration:**
- `sitemap_url`: URL of the XML sitemap (e.g., `https://careers.alaskaair.com/sitemaps/jobs_1.xml`)
- `sitemap_url_pattern`: Regex to filter URLs (e.g., `-ak/` for Alaska jobs only)
- `organization`: Organization name for all jobs (e.g., "Alaska Airlines")
- `default_state`: Fallback state code (e.g., "AK")

**URL Parsing:**
- Location: Extracts from URL patterns like `/kotzebue-ak/` → "Kotzebue, AK"
- Title: Extracts from URL slug like `/customer-service-agent/` → "Customer Service Agent"
- External ID: Uses UUID/hex segment from URL path

**Example: Alaska Airlines**
```
Sitemap URL: https://careers.alaskaair.com/sitemaps/jobs_1.xml
URL Pattern: -ak/
Organization: Alaska Airlines
Default State: AK
```

### Phase 1Y: Needs Configuration Page & Auto-Enable ✅
- [x] Separate "Needs Configuration" page for bulk-imported sources
- [x] `needs_configuration` Boolean field on ScrapeSource model
- [x] Bulk imports set `needs_configuration=True` instead of just `is_active=False`
- [x] Disabled page excludes needs_configuration sources (keeps them separate)
- [x] Dashboard shows "Needs Configuration (N)" link when count > 0
- [x] Auto-enable on successful scrape: when jobs_found > 0 and no errors
- [x] "Source enabled!" message in scrape result modal after auto-enable
- [x] Manual Enable button as fallback (for sources with 0 current jobs)
- [x] Mark Disabled button moves source to Disabled page
- [x] Export CSV of needs-configuration sources
- [x] Consistent filtering across all source list endpoints

**Key Files:**
- `backend/app/models/scrape_source.py` - `needs_configuration` field
- `backend/alembic/versions/014_add_needs_configuration.py` - Migration
- `backend/app/routers/admin.py` - Needs configuration endpoints, auto-enable logic
- `backend/app/templates/admin/needs_configuration.html` - Dedicated page
- `backend/app/templates/admin/partials/needs_configuration_count_link.html` - Dashboard count
- `backend/app/templates/admin/partials/source_list.html` - Actions for needs_configuration
- `backend/app/templates/admin/partials/scrape_modal_result.html` - Auto-enabled message

**Database Fields:**
- `needs_configuration` (Boolean) - True for bulk-imported sources awaiting CSS selector setup

**API Endpoints:**
- GET `/admin/sources/needs-configuration` - Page listing sources needing configuration
- GET `/admin/sources/needs-configuration/list` - HTMX partial for source list
- GET `/admin/sources/needs-configuration-count` - HTMX partial for count badge
- POST `/admin/sources/{id}/mark-disabled` - Move source from needs-config to disabled
- GET `/admin/sources/export-needs-configuration` - Export CSV of needs-config sources

**Source Categories:**
1. **Active** - Configured and scraping (`is_active=True`)
2. **Needs Configuration** - Bulk imported, awaiting setup (`needs_configuration=True`)
3. **Disabled** - Tried to configure but couldn't make work (`is_active=False`, `needs_configuration=False`)
4. **Robots Blocked** - Site disallows crawling (`robots_blocked=True`)

**Auto-Enable Flow:**
1. Admin clicks Configure on a needs-configuration source
2. Admin sets up CSS selectors and clicks Test Scrape
3. If scrape finds jobs (>0) with no errors → source auto-enabled
4. Source moves to Active list, "Source enabled!" shown in modal
5. If 0 jobs or errors → stays in Needs Configuration for further work
6. Manual Enable button available for sources with correct config but 0 current openings

**Workflow:**
1. Bulk import CSV → sources go to "Needs Configuration" page
2. For each source: Configure selectors → Test Scrape
3. Success with jobs → auto-enabled, moves to Active
4. Can't configure → Mark Disabled (moves to Disabled page)
5. Robots.txt block → automatically moves to Robots Blocked page

## CSS Selector Troubleshooting

Common issues when configuring GenericScraper:

1. **Matching header rows instead of data rows**
   - Problem: Selector like `.views-field-title a` matches both `<th>` and `<td>` elements
   - Solution: Be specific with `td.views-field-title a` to exclude headers

2. **Only one job found when page has many**
   - Check if selector matches header row (common with table-based layouts)
   - Verify container selector matches ALL job rows, not just the first

3. **Title is blank or generic text**
   - Inspect what text the selector actually captures
   - May need to add intermediate selectors (e.g., `.tablesaw-cell-content a`)

4. **URLs are relative or malformed**
   - GenericScraper automatically resolves relative URLs against the page URL
   - Check `url_attribute` is set correctly (usually "href")

5. **Cloudflare/bot protection blocking**
   - Playwright handles this automatically (always enabled)
   - Check Playwright service logs: `docker compose logs playwright`

## Notes

1. **Gitleaks** is used to prevent secret leaks - all secrets in server .env only
2. **Scheduler** runs daily at noon Alaska time (production only)
3. **To redeploy:** `ssh michael@tachyonfuture.com` then `cd ~/apps/far-reach-jobs && git pull && docker compose up -d --build`
