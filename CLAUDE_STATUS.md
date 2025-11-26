# Far Reach Jobs - Implementation Status

**Last Updated:** 2025-11-26
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
- [x] Job listing API with filters (state, location, job_type, keyword)
- [x] Full-text search implementation (ILIKE on title, org, description, location)
- [x] Home page with HTMX job list
- [x] Filter UI components (search input, state dropdown, job type dropdown)
- [x] Job card component with "Apply" link
- [x] Pagination with HTMX navigation

**Key Files:**
- `backend/app/routers/jobs.py` - Job listing API with filters
- `backend/app/schemas/job.py` - Job response schemas
- `backend/app/templates/index.html` - Home page with filters
- `backend/app/templates/partials/job_list.html` - HTMX job list partial

**API Endpoints:**
- GET `/api/jobs` - List jobs with filters (q, state, job_type, page, per_page)
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

**Key Files:**
- `backend/app/routers/admin.py` - `trigger_single_source_scrape()` endpoint
- `backend/app/models/scrape_source.py` - `last_scrape_success` field
- `backend/app/templates/admin/partials/source_list.html` - Scrape button and status badge
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

**How to Add a New Job Source:**
1. Go to Admin Dashboard → Add Scrape Source
2. Enter source name and base URL
3. Click "Configure" on the new source
4. Use browser DevTools to inspect the job listing page
5. Enter CSS selectors for job container, title, and URL (required)
6. Optionally add selectors for organization, location, salary, etc.
7. Save configuration and click "Scrape" to test

**API Endpoints:**
- GET `/admin/sources/{id}/configure` - Configuration page
- POST `/admin/sources/{id}/configure` - Save configuration

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
- listing_url (GenericScraper: page containing job listings)
- selector_job_container, selector_title, selector_url (required for GenericScraper)
- selector_organization, selector_location, selector_job_type
- selector_salary, selector_description
- url_attribute, selector_next_page, max_pages

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
- "Warn but allow" if robots.txt fetch fails
- Sites without robots.txt (404) allow all paths

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
6. ✅ Alembic migrations applied (001, 002, 003, 004)
7. ✅ NPM proxy host configured with SSL
8. ✅ Health endpoint verified: https://far-reach-jobs.tachyonfuture.com/api/health

## Notes

1. **Gitleaks** is used to prevent secret leaks - all secrets in server .env only
2. **Scheduler** runs daily at noon Alaska time (production only)
3. **To redeploy:** `ssh michael@tachyonfuture.com` then `cd ~/apps/far-reach-jobs && git pull && docker compose up -d --build`
