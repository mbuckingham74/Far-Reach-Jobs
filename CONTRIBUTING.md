# Contributing to Far Reach Jobs

Thank you for your interest in contributing! This guide will help you get started.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git
- (Optional) Python 3.11+ for running tests locally

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/mbuckingham74/Far-Reach-Jobs.git
   cd Far-Reach-Jobs
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your values. For local development, you can use simple passwords. The `ANTHROPIC_API_KEY` is optional (AI features won't work without it).

3. **Create the Docker network** (first time only)
   ```bash
   docker network create npm_default
   ```

4. **Start the services**
   ```bash
   docker compose up -d --build
   ```

5. **Access the app**
   - Main site: http://localhost:8000
   - Admin panel: http://localhost:8000/admin/login

### Stopping the Services

```bash
docker compose down
```

To also remove the database volume (fresh start):
```bash
docker compose down -v
```

## Development Workflow

We use [GitHub Flow](BRANCHING_STRATEGY.md) - a simple branching model:

1. **Create a branch** from `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** with clear commit messages

3. **Run tests** (optional but recommended):
   ```bash
   cd backend
   pip install -r requirements.txt pytest pytest-asyncio
   python -m pytest tests/ -v
   ```

4. **Push and open a PR**:
   ```bash
   git push -u origin feature/your-feature-name
   ```
   Then open a Pull Request on GitHub.

### Branch Naming

| Prefix | Use For | Example |
|--------|---------|---------|
| `feature/` | New functionality | `feature/job-alerts` |
| `fix/` | Bug fixes | `fix/scraper-timeout` |
| `chore/` | Maintenance | `chore/update-deps` |

## Project Structure

```
Far-Reach-Jobs/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entry point
│   │   ├── routers/         # API routes (admin, auth, jobs)
│   │   ├── models/          # SQLAlchemy models
│   │   ├── templates/       # Jinja2 HTML templates
│   │   └── services/        # Business logic
│   ├── scraper/
│   │   ├── runner.py        # Scraper orchestration
│   │   └── sources/         # Scraper implementations
│   └── tests/               # Pytest tests
├── playwright-service/      # Headless browser service
├── frontend/static/         # Static assets
└── docker-compose.yml
```

## Code Style

- **Python**: Follow PEP 8. Use type hints where practical.
- **HTML/Templates**: Use Tailwind CSS utility classes.
- **JavaScript**: Minimal JS - prefer HTMX for interactivity.

## Areas for Contribution

Check the [Roadmap](ROADMAP.md) for planned features. Good first issues:

- **Add a scraper source**: Know an Alaska employer with a jobs page? Add it via the admin panel and document any issues.
- **Improve tests**: We need better test coverage, especially for scrapers.
- **UI/UX improvements**: Mobile responsiveness, accessibility, design polish.
- **Documentation**: Improve these docs, add examples, fix typos.

## Questions?

Open an issue or reach out via the repository discussions.
