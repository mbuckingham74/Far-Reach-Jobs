# Far Reach Jobs - Implementation Plan

## Project Overview

**Purpose:** Aggregate job listings from Alaska bush communities and extremely rural US towns (population < 10k) into a single searchable platform.

**Domain:** far-reach-jobs.tachyonfuture.com

**Repository:** GitHub public repo `Far-Reach-Jobs`

---

## Technology Stack

### Frontend
- **HTMX** - Dynamic interactions without full SPA complexity
- **Jinja2** - Server-side templating
- **Tailwind CSS** - Utility-first styling, minimal custom CSS
- No build step required, keeps things simple

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for MySQL
- **Pydantic** - Data validation
- **Passlib + python-jose** - Authentication (password hashing + JWT)

### Scraping
- **Scrapy** or **httpx + BeautifulSoup** - Web scraping
- **robotsparser** - Respect robots.txt
- **APScheduler** - In-process scheduling (noon/midnight PST)

### Infrastructure
- **Docker Compose** - Container orchestration
- **MySQL 8** - Existing container on tachyonfuture.com (local connection)
- **NPM (nginx proxy manager)** - SSL termination and reverse proxy

---

## Project Structure

```
far-reach-jobs/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── PLAN.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Environment configuration
│   │   ├── database.py          # SQLAlchemy setup
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── job.py
│   │   │   ├── saved_job.py
│   │   │   └── scrape_source.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── job.py
│   │   │   └── auth.py
│   │   │
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # Login, register, verify email
│   │   │   ├── jobs.py          # Job listing, search, filtering
│   │   │   ├── saved_jobs.py    # Save/unsave jobs
│   │   │   └── health.py        # Health check endpoint
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # Password hashing, JWT, email verification
│   │   │   ├── email.py         # Gmail SMTP for verification emails
│   │   │   └── jobs.py          # Job search/filtering logic
│   │   │
│   │   └── templates/
│   │       ├── base.html
│   │       ├── index.html       # Home/job listing page
│   │       ├── job_list.html    # HTMX partial for job results
│   │       ├── job_card.html    # Single job card partial
│   │       ├── login.html
│   │       ├── register.html
│   │       ├── verify_email.html
│   │       ├── saved_jobs.html
│   │       └── emails/
│   │           └── verify.html  # Email verification template
│   │
│   └── scraper/
│       ├── __init__.py
│       ├── scheduler.py         # APScheduler setup (noon/midnight PST)
│       ├── base.py              # Base scraper class
│       ├── robots.py            # robots.txt parser/checker
│       ├── sources/
│       │   ├── __init__.py
│       │   └── ...              # Individual site scrapers
│       └── utils.py             # Common scraping utilities
│
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css       # Tailwind output + custom styles
│   │   ├── js/
│   │   │   └── app.js           # Minimal JS (HTMX config, etc.)
│   │   └── images/
│   │       └── logo.svg
│   │
│   └── tailwind.config.js       # Tailwind configuration
│
└── scripts/
    ├── init_db.py               # Database initialization
    └── add_source.py            # CLI to add new scrape sources
```

---

## Database Schema

### users
| Column | Type | Notes |
|--------|------|-------|
| id | INT | Primary key, auto-increment |
| email | VARCHAR(255) | Unique, indexed |
| password_hash | VARCHAR(255) | bcrypt hash |
| is_verified | BOOLEAN | Default false |
| verification_token | VARCHAR(255) | Nullable, for email verification |
| created_at | DATETIME | Default now |
| updated_at | DATETIME | Auto-update |

### jobs
| Column | Type | Notes |
|--------|------|-------|
| id | INT | Primary key, auto-increment |
| source_id | INT | FK to scrape_sources |
| external_id | VARCHAR(255) | Unique ID from source (URL hash or job ID) |
| title | VARCHAR(500) | Job title |
| organization | VARCHAR(255) | Employer name |
| location | VARCHAR(255) | City/region |
| state | VARCHAR(50) | State abbreviation |
| description | TEXT | Full job description |
| job_type | VARCHAR(100) | Full-time, Part-time, Seasonal, etc. |
| salary_info | VARCHAR(255) | Salary range if available |
| url | VARCHAR(1000) | Original job posting URL |
| first_seen_at | DATETIME | When scraper first found it |
| last_seen_at | DATETIME | Updated each scrape |
| is_stale | BOOLEAN | True if missing 2+ scrapes |
| created_at | DATETIME | Default now |
| updated_at | DATETIME | Auto-update |

**Indexes:** (state), (location), (job_type), (is_stale, last_seen_at), (external_id - unique)

### saved_jobs
| Column | Type | Notes |
|--------|------|-------|
| id | INT | Primary key, auto-increment |
| user_id | INT | FK to users |
| job_id | INT | FK to jobs |
| saved_at | DATETIME | Default now |

**Unique constraint:** (user_id, job_id)

### scrape_sources
| Column | Type | Notes |
|--------|------|-------|
| id | INT | Primary key, auto-increment |
| name | VARCHAR(255) | Human-readable name |
| base_url | VARCHAR(1000) | Website base URL |
| scraper_class | VARCHAR(255) | Python class name for this source |
| is_active | BOOLEAN | Enable/disable scraping |
| last_scraped_at | DATETIME | Last successful scrape |
| created_at | DATETIME | Default now |

---

## Job Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                      Job Lifecycle                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Scraper finds job] ──► INSERT with first_seen_at          │
│         │                last_seen_at = now                 │
│         │                is_stale = false                   │
│         ▼                                                   │
│  [Scraper runs again]                                       │
│         │                                                   │
│    ┌────┴────┐                                              │
│    │         │                                              │
│  Found    Not Found                                         │
│    │         │                                              │
│    ▼         ▼                                              │
│  UPDATE    (no action, last_seen_at unchanged)              │
│  last_seen_at = now                                         │
│         │                                                   │
│         ▼                                                   │
│  [Scheduled task checks for stale jobs]                     │
│  WHERE last_seen_at < NOW() - 24 hours                      │
│         │                                                   │
│         ▼                                                   │
│  SET is_stale = true (hidden from search)                   │
│         │                                                   │
│         ▼                                                   │
│  [After 7 days stale]                                       │
│  DELETE job (and cascade saved_jobs)                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register new user |
| POST | /api/auth/login | Login, returns JWT |
| GET | /api/auth/verify/{token} | Verify email |
| POST | /api/auth/logout | Clear session |

### Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/jobs | List jobs with filters |
| GET | /api/jobs/{id} | Get single job details |

**Query parameters for /api/jobs:**
- `q` - Keyword search (title, description, organization)
- `state` - Filter by state
- `location` - Filter by location/city
- `job_type` - Filter by job type
- `page` - Pagination
- `per_page` - Results per page (default 20)

### Saved Jobs (authenticated)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/saved-jobs | List user's saved jobs |
| POST | /api/saved-jobs/{job_id} | Save a job |
| DELETE | /api/saved-jobs/{job_id} | Unsave a job |

### Pages (HTML)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Home page with job listings |
| GET | /login | Login page |
| GET | /register | Registration page |
| GET | /saved | Saved jobs page (auth required) |

---

## Search & Filtering

Based on scraped data, users can filter by:

1. **Keyword search** - Full-text search across title, description, organization
2. **State** - Dropdown of states with jobs (Alaska primary, plus rural US)
3. **Location/City** - Text input or dropdown of known locations
4. **Job Type** - Full-time, Part-time, Seasonal, Contract, etc.
5. **Date Posted** - Last 24h, Last 7 days, Last 30 days, All

**Implementation:**
- HTMX will send filter changes to `/api/jobs`
- Returns HTML partial (`job_list.html`) that replaces results
- Debounced keyword search (300ms delay)
- URL state updated for shareable/bookmarkable searches

---

## Scraper Design

### Base Scraper Class
```python
class BaseScraper:
    source_name: str
    base_url: str

    def check_robots_txt(self) -> bool
    def fetch_job_listings(self) -> List[RawJob]
    def parse_job(self, raw_data) -> JobCreate
    def run(self) -> ScraperResult
```

### robots.txt Compliance
- Parse robots.txt before each scrape run
- Respect Crawl-delay if specified
- Skip disallowed paths
- Identify as "FarReachJobsBot/1.0"

### Scheduling
- APScheduler running in the FastAPI process
- Two daily runs: 12:00 PM PST and 12:00 AM PST
- Stale job cleanup runs after each scrape

### Error Handling
- Log all scrape attempts and results
- Continue to next source if one fails
- Alert mechanism for repeated failures (future enhancement)

---

## Authentication Flow

### Registration
1. User submits email + password
2. Password hashed with bcrypt
3. Verification token generated
4. User created with is_verified=false
5. Verification email sent via Gmail SMTP
6. User clicks link → /api/auth/verify/{token}
7. is_verified set to true

### Login
1. User submits email + password
2. Password verified against hash
3. Check is_verified = true
4. JWT token generated (24h expiry)
5. Token stored in httpOnly cookie

### Protected Routes
- Middleware checks JWT cookie
- Invalid/expired → redirect to login
- HTMX requests return 401 for client-side redirect

---

## Environment Variables

```env
# Database
MYSQL_HOST=host.docker.internal  # or actual MySQL container network
MYSQL_PORT=3306
MYSQL_DATABASE=far_reach_jobs
MYSQL_USER=far_reach_jobs
MYSQL_PASSWORD=<secure_password>

# Auth
SECRET_KEY=<random_64_char_string>
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# Email (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=<app_password>
FROM_EMAIL=noreply@far-reach-jobs.tachyonfuture.com

# App
APP_URL=https://far-reach-jobs.tachyonfuture.com
ENVIRONMENT=production
```

---

## Implementation Phases

### Phase 1A: Foundation (Backend Setup)
- [ ] Initialize Git repository
- [ ] Create Docker Compose configuration
- [ ] Set up FastAPI application structure
- [ ] Configure SQLAlchemy with MySQL connection
- [ ] Create Alembic migrations for all tables
- [ ] Implement health check endpoint
- [ ] Test database connectivity

### Phase 1B: Authentication System
- [ ] User registration endpoint
- [ ] Password hashing service
- [ ] Email verification service (Gmail SMTP)
- [ ] Login endpoint with JWT
- [ ] Auth middleware
- [ ] Login/Register HTML pages

### Phase 1C: Scraper Infrastructure
- [ ] Base scraper class with robots.txt support
- [ ] APScheduler integration
- [ ] Scrape source management
- [ ] Job upsert logic (insert or update last_seen_at)
- [ ] Stale job detection and cleanup
- [ ] Add initial Alaska/rural sources (URLs provided by user)

### Phase 1D: Job Display & Search
- [ ] Job listing API with filters
- [ ] Full-text search implementation
- [ ] Home page with HTMX job list
- [ ] Filter UI (state, location, job type, date)
- [ ] Job card component with "Apply" link
- [ ] Pagination

### Phase 1E: Saved Jobs
- [ ] Save/unsave job endpoints
- [ ] Saved jobs page
- [ ] Save button on job cards (HTMX toggle)
- [ ] Handle saved jobs when job becomes stale/deleted

### Phase 1F: Polish & Deploy
- [ ] Tailwind CSS styling
- [ ] Responsive design
- [ ] Error pages (404, 500)
- [ ] NPM reverse proxy configuration
- [ ] Production environment setup
- [ ] Initial scrape run
- [ ] Beta launch

---

## Future Enhancements (Post Phase 1)

- Job alerts via email (notify when new jobs match criteria)
- Admin panel for managing sources
- More granular location data (coordinates, distance search)
- Job categories/tags
- Resume upload for one-click apply prep
- Analytics dashboard
- Rate limiting and abuse prevention
- Additional rural US regions

---

## Questions Resolved

✅ Frontend: HTMX + Jinja2 + Tailwind CSS
✅ Backend: FastAPI
✅ Scrape schedule: 2x daily (noon/midnight PST)
✅ Auth: Email/password with verification (Gmail SMTP)
✅ Job removal: Stale after 24h (2 missed scrapes), delete after 7 days stale
✅ SSL: Handled by NPM
✅ Database: Local MySQL 8 container connection
✅ Structure: /frontend and /backend separation

---

## Ready to Implement

This plan is ready for your approval. Once approved, I'll begin with Phase 1A (Foundation) and work through each phase systematically.
