# Far Reach Jobs

An ethical job aggregator for remote Alaskan communities, bush villages, and tribal organizations. Find opportunities in places most job boards don't reach.

**Live site:** [far-reach-jobs.tachyonfuture.com](https://far-reach-jobs.tachyonfuture.com/)

## About

Far Reach Jobs aggregates job listings from employers in Alaska's most remote communities - bush villages, tribal organizations, rural hospitals, and small-town governments. Instead of duplicating listings, we link directly back to the original source so you can apply there.

### Why This Exists

Job seekers interested in remote Alaska face a fragmented landscape - positions are scattered across dozens of small employer websites, tribal organization portals, and government HR systems. Far Reach Jobs brings them together in one searchable place.

### How It Works

1. **We scrape public job pages** from employers in remote Alaska
2. **Jobs appear here** with location, organization, and job type
3. **Click "Apply"** to go directly to the original listing
4. **Save jobs** to track positions you're interested in

We respect `robots.txt` and identify ourselves as `FarReachJobsBot/1.0`.

## Features

- Search and filter by keyword, state, and job type
- Save jobs to your account for later
- Dark mode support
- Mobile-friendly design
- Daily scraping at noon Alaska time

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy + MySQL
- **Frontend:** HTMX + Jinja2 + Tailwind CSS
- **Scraping:** httpx + BeautifulSoup + APScheduler
- **Deployment:** Docker Compose with Nginx Proxy Manager

## For Employers

If you're an employer in remote Alaska and want your jobs included, or if you'd like to be excluded from scraping, please open an issue or contact us.

## License

MIT
