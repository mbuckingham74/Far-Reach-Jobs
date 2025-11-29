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

We respect `robots.txt` and identify ourselves as `FarReachJobs/1.0` in our User-Agent string.

## Features

- Search and filter by keyword, city/community, and job type
- Save jobs to your account for later
- Dark mode support
- Mobile-friendly design
- Daily scraping at noon Alaska time

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy + MySQL
- **Frontend:** HTMX + Jinja2 + Tailwind CSS
- **Scraping:** httpx + BeautifulSoup + APScheduler
- **Deployment:** Docker Compose with Nginx Proxy Manager

## Adding Job Sources (Admin)

Far Reach Jobs uses a configurable scraper system. New job sources can be added via the admin panel without writing code:

1. Go to Admin Dashboard → Add Scrape Source
2. Enter the source name and base URL
3. Click "Configure" on the new source
4. Click **"Analyze Page with AI"** to automatically detect CSS selectors
5. Review the suggested selectors and click "Apply All Suggestions"
6. Set a **Default Location** (e.g., "Bethel") for sources where jobs don't have individual locations
7. Save configuration and click "Scrape" to test

### AI-Powered Configuration

The admin panel includes AI-powered tools to simplify scraper setup:

- **Analyze Page with AI** - Automatically suggests CSS selectors by analyzing the page structure
- **Generate Custom Scraper** - For complex sites that can't use the generic scraper, AI generates Python code tailored to that site's unique structure

The scraper respects `robots.txt` rules and uses crawl delays when specified.

## Development

### Quick Start

```bash
# Clone and setup
git clone https://github.com/mbuckingham74/Far-Reach-Jobs.git
cd Far-Reach-Jobs
cp .env.example .env

# Create Docker network (first time only)
docker network create npm_default

# Start services
docker compose up -d --build
```

Then visit http://localhost:8000

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed setup instructions.

## Contributing

We welcome contributions! Check out:

- [CONTRIBUTING.md](CONTRIBUTING.md) - Setup and guidelines
- [ROADMAP.md](ROADMAP.md) - Planned features
- [Issues](https://github.com/mbuckingham74/Far-Reach-Jobs/issues) - Open tasks

Good first contributions:
- Suggest new Alaska job sources via the "New Job Source" issue template
- Improve test coverage
- UI/UX enhancements

## For Employers

If you're an employer in remote Alaska and want your jobs included, or if you'd like to be excluded from scraping, please open an issue or contact us.

## License

MIT
