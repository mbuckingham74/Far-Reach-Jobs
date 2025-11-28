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
| 2 | Jobs API | 34 | ✅ Complete | [#53](https://github.com/mbuckingham74/Far-Reach-Jobs/pull/53) |
| 3 | Saved Jobs | 18 | ✅ Complete | [#54](https://github.com/mbuckingham74/Far-Reach-Jobs/pull/54) |
| 4 | Scraper Utilities | 43 | ✅ Complete | [#55](https://github.com/mbuckingham74/Far-Reach-Jobs/pull/55) |
| 5 | Admin Panel | 62 | ✅ Complete | [#56](https://github.com/mbuckingham74/Far-Reach-Jobs/pull/56) |
| 6 | Models | - | ⏳ Pending | - |

**Total Tests:** 196 (181 new + 15 existing)

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

## 2. Jobs API Tests ✅

**File:** `backend/tests/test_jobs.py`
**Endpoints:** `/api/jobs/*`

### Coverage
- [x] List jobs (5 tests)
  - Empty database, excludes stale, pagination, limits, ordering
- [x] Search (6 tests)
  - By title, organization, description, location, case-insensitive, no results
- [x] Filters (12 tests)
  - State, location, job type, organization, source_id, date posted (1/7/30 days), combined, invalid params
- [x] Get single job (3 tests)
  - Success, not found, stale returns 404
- [x] Reference endpoints (8 tests)
  - States list, locations list, job types list, HTMX HTML responses

---

## 3. Saved Jobs Tests ✅

**File:** `backend/tests/test_saved_jobs.py`
**Endpoints:** `/api/saved-jobs/*`

### Coverage
- [x] List saved jobs (5 tests)
  - Unauthenticated 401, empty list, with jobs, user isolation, ordering
- [x] Save job (5 tests)
  - Unauthenticated 401, success, idempotent, nonexistent 404, stale 404
- [x] Unsave job (4 tests)
  - Unauthenticated 401, success, not saved, other user's job
- [x] HTMX responses (4 tests)
  - List, save, unsave from listing, unsave from saved page

---

## 4. Admin Panel Tests ✅

**File:** `backend/tests/test_admin.py`
**Endpoints:** `/admin/*`

### Coverage

#### Authentication (10 tests)
- [x] Admin login page render
- [x] Admin login redirects if already logged in
- [x] Admin login success
- [x] Admin login wrong username/password
- [x] Admin login empty credentials
- [x] Admin logout success
- [x] Admin logout clears session
- [x] Dashboard requires auth
- [x] Dashboard accessible when authenticated

#### Dashboard (3 tests)
- [x] Dashboard shows job counts (with regex validation of actual values)
- [x] Dashboard shows sources via HTMX
- [x] Dashboard shows disabled source count

#### Source Management (12 tests)
- [x] List sources requires auth
- [x] List sources returns active only
- [x] Create source requires auth
- [x] Create source success
- [x] Create source validation (missing name/URL)
- [x] Delete source requires auth
- [x] Delete source success
- [x] Delete nonexistent source (idempotent)
- [x] Toggle source requires auth
- [x] Toggle active to inactive
- [x] Toggle inactive to active

#### Disabled Sources (6 tests)
- [x] Disabled sources page requires auth
- [x] Disabled sources page accessible
- [x] Disabled sources list requires auth
- [x] Disabled sources list returns inactive only
- [x] Disabled count link requires auth
- [x] Disabled count returns count

#### Source Edit (8 tests)
- [x] Edit page requires auth
- [x] Edit page accessible
- [x] Edit page nonexistent source redirects
- [x] Edit source requires auth
- [x] Edit source success
- [x] Edit source validation (name, URL, URL format)

#### Source Configure (7 tests)
- [x] Configure page requires auth
- [x] Configure page accessible
- [x] Configure page nonexistent source redirects
- [x] Configure source requires auth
- [x] Configure source success
- [x] Configure source warns on missing selectors
- [x] Configure source checkbox (use_playwright)

#### Scrape History (4 tests)
- [x] History page requires auth
- [x] History page accessible
- [x] History page shows logs (verifies table content)
- [x] History page shows stats (with regex validation of computed aggregates)

#### Trigger Scrape (6 tests)
- [x] Scrape all requires auth
- [x] Scrape all no sources
- [x] Scrape all success (mocked)
- [x] Scrape single requires auth
- [x] Scrape single not found
- [x] Scrape single success (mocked)

#### AI Features (6 tests)
- [x] Analyze requires auth
- [x] Analyze nonexistent source
- [x] Analyze AI not available
- [x] Generate scraper requires auth
- [x] Generate scraper nonexistent source
- [x] Generate scraper AI not available

### Key Test Fixtures
- `admin_client` - TestClient with admin session cookie

---

## 5. Scraper Utility Tests ✅

**File:** `backend/tests/test_scraper_utils.py`
**Module:** `backend/scraper/utils.py`

### Coverage
- [x] `normalize_state()` (9 tests)
  - Full names, lowercase, mixed case, abbreviations, whitespace, empty, invalid
- [x] `extract_state_from_location()` (10 tests)
  - City/ST, City/ST ZIP, full names, case-insensitive, empty, invalid, substring caveat
- [x] `clean_text()` (7 tests)
  - Multiple spaces, newlines/tabs, leading/trailing, mixed, already clean, empty
- [x] `extract_salary()` (8 tests)
  - Dollar amounts, ranges, hourly, annual, in descriptions, no match, empty
- [x] `normalize_job_type()` (9 tests)
  - Full-time, part-time, seasonal, contract, temporary, internship, unknown, empty

### Known Limitations
- Substring matching for state names may cause false positives (e.g., "Texasville" → TX)

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
