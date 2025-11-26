# Far Reach Jobs - Implementation Status

**Last Updated:** 2025-11-25
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
- Alembic migrations (001: initial schema, 002: verification token expiry)
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

## Remaining Work

### Scrapers (Phase 2)
- No concrete scrapers exist yet - user will provide URLs to scrape
- Scheduler runs in production (noon/midnight Alaska time)

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
- is_active, last_scraped_at, created_at

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

### robots.txt Handling
- Respects Disallow rules and Crawl-delay
- User-Agent: `FarReachJobsBot/1.0`
- "Warn but allow" if robots.txt fetch fails

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
6. ✅ Alembic migrations applied (001, 002)
7. ✅ NPM proxy host configured with SSL
8. ✅ Health endpoint verified: https://far-reach-jobs.tachyonfuture.com/api/health

## Notes

1. **Gitleaks** is used to prevent secret leaks - all secrets in server .env only
2. **Scheduler** runs daily at noon Alaska time (production only)
3. **To redeploy:** `ssh michael@tachyonfuture.com` then `cd ~/apps/far-reach-jobs && git pull && docker compose up -d --build`
