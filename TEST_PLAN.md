# Test Suite Development Plan

This document tracks our progress building comprehensive test coverage for Far Reach Jobs.

## Quick Start

Run all tests:
```bash
docker compose -f docker-compose.test.yml run --rm test
```

## Current Status

| # | Area | Tests | Status | PR |
|---|------|-------|--------|-----|
| 1 | Authentication | 24 | ✅ Complete | [#52](https://github.com/mbuckingham74/Far-Reach-Jobs/pull/52) |
| 2 | Jobs API | - | ⏳ Pending | - |
| 3 | Saved Jobs | - | ⏳ Pending | - |
| 4 | Admin Panel | - | ⏳ Pending | - |
| 5 | Scraper Utilities | - | ⏳ Pending | - |
| 6 | Models | - | ⏳ Pending | - |

**Total Tests:** 39 (24 new + 15 existing)

---

## 1. Authentication Tests ✅

**File:** `backend/tests/test_auth.py`
**Endpoints:** `/api/auth/*`

### Coverage
- [x] Registration (6 tests)
  - Success, duplicate email, invalid email, password validation, auto-verify dev mode
- [x] Login (4 tests)
  - Success with cookie, wrong password, non-existent user, unverified user blocked
- [x] Email Verification (4 tests)
  - Valid token, invalid token, expired token, already verified
- [x] Logout (1 test)
- [x] Resend Verification (4 tests)
  - Token refresh, email enumeration protection
- [x] Get Current User (5 tests)
  - Authenticated, no token, invalid token, expired token, deleted user

### Bugs Found & Fixed
1. **Timezone comparison bug** in email verification - comparing naive vs aware datetimes
2. **bcrypt/passlib compatibility** - pinned bcrypt to 4.0.1

---

## 2. Jobs API Tests ⏳

**File:** `backend/tests/test_jobs.py` (to create)
**Endpoints:** `/api/jobs/*`

### Planned Coverage
- [ ] List jobs with pagination
- [ ] Search by keyword (title, org, description, location)
- [ ] Filter by state
- [ ] Filter by location
- [ ] Filter by job type
- [ ] Filter by date posted (1/7/30 days)
- [ ] Filter by organization
- [ ] Filter by source
- [ ] Get single job by ID
- [ ] 404 for stale job
- [ ] Get states list
- [ ] Get locations list
- [ ] Get job types list
- [ ] HTMX partial responses

### Key Test Fixtures Needed
- Multiple jobs with various attributes
- Jobs from different sources
- Jobs in different states/locations
- Jobs with different ages (for date filtering)

---

## 3. Saved Jobs Tests ⏳

**File:** `backend/tests/test_saved_jobs.py` (to create)
**Endpoints:** `/api/saved-jobs/*`

### Planned Coverage
- [ ] List saved jobs (authenticated)
- [ ] List saved jobs (unauthenticated - 401)
- [ ] Save a job
- [ ] Save already-saved job (idempotent)
- [ ] Unsave a job
- [ ] Unsave from saved page vs listing (context-aware response)
- [ ] Save non-existent job
- [ ] HTMX responses

### Key Test Fixtures Needed
- Authenticated user fixture
- User with saved jobs
- Multiple users (isolation testing)

---

## 4. Admin Panel Tests ⏳

**File:** `backend/tests/test_admin.py` (to create)
**Endpoints:** `/admin/*`

### Planned Coverage

#### Authentication
- [ ] Admin login page render
- [ ] Admin login success
- [ ] Admin login wrong credentials
- [ ] Admin logout
- [ ] Protected routes redirect to login

#### Source Management
- [ ] List sources
- [ ] Create source
- [ ] Edit source
- [ ] Delete source
- [ ] Toggle source active/inactive
- [ ] Configure selectors
- [ ] View disabled sources

#### Scraping
- [ ] Trigger scrape all
- [ ] Trigger single source scrape
- [ ] Scrape history view

#### AI Features (if API key available)
- [ ] Analyze page for selectors
- [ ] Generate scraper code

### Key Test Fixtures Needed
- Admin session cookie fixture
- Sources with various configurations

---

## 5. Scraper Utility Tests ⏳

**File:** `backend/tests/test_scraper_utils.py` (to create)
**Module:** `backend/scraper/utils.py`

### Planned Coverage
- [ ] `normalize_state()` - full names, abbreviations, edge cases
- [ ] `extract_state_from_location()` - various location formats
- [ ] `clean_text()` - whitespace normalization
- [ ] `extract_salary()` - various salary formats
- [ ] `normalize_job_type()` - standardization

### Test Data Examples
```python
# State normalization
"Alaska" -> "AK"
"alaska" -> "AK"
"AK" -> "AK"
"ak" -> "AK"

# Location parsing
"Anchorage, AK" -> "AK"
"Fairbanks, Alaska" -> "AK"
"Remote - Alaska" -> "AK"

# Salary extraction
"$50,000 - $70,000/year" -> "$50,000 - $70,000/year"
"$25/hour" -> "$25/hour"
"DOE" -> "DOE"
```

---

## 6. Model Tests ⏳

**File:** `backend/tests/test_models.py` (to create)
**Models:** User, Job, SavedJob, ScrapeSource, ScrapeLog

### Planned Coverage
- [ ] User email uniqueness constraint
- [ ] Job external_id + source_id uniqueness
- [ ] SavedJob user_id + job_id uniqueness
- [ ] Cascade delete behaviors
- [ ] Relationship loading (user.saved_jobs, job.source, etc.)
- [ ] Default values (created_at, is_stale, etc.)

---

## Existing Tests (Pre-existing)

### Stats Tests
**File:** `backend/tests/test_stats.py` (8 tests)
- Empty database stats
- Active sources only counting
- Stale job exclusion
- New this week filtering
- Combined scenarios
- HTMX response

### Playwright Fallback Tests
**File:** `backend/tests/test_playwright_fallback.py` (7 tests)
- Playwright success (no fallback)
- Playwright failure (falls back to httpx)
- Playwright unavailable
- robots.txt blocking
- Playwright disabled config
- Fetcher availability checks

---

## Session Workflow

Each session should:

1. **Start**: Check this document for next pending area
2. **Branch**: `git checkout main && git pull && git checkout -b feature/<area>-tests`
3. **Implement**: Write tests for the area
4. **Test**: `docker compose -f docker-compose.test.yml run --rm test`
5. **PR**: Create PR and wait for review
6. **Merge**: After approval, merge and update this document
7. **Repeat**: Move to next area

---

## Notes

- Tests use in-memory SQLite (see `conftest.py`)
- Environment set to `development` for tests
- Some tests may need mocking (email, AI API, external HTTP)
- HTMX tests check for `HX-Request` header handling
