# Claude Code Instructions

## Testing

- User ALWAYS tests in a fresh Chrome Guest Profile window (no cached state, localStorage, cookies, etc.)
- When debugging browser issues, assume no prior state exists
- Hard refresh suggestions are less relevant since Guest Profile starts clean

## Project Context

- **Live URL:** https://far-reach-jobs.tachyonfuture.com/
- **Tech Stack:** FastAPI + Jinja2 + HTMX + Tailwind CSS (CDN) + MySQL
- **Deployment:** Docker Compose on tachyonfuture.com server

## Deployment

To deploy changes:
```bash
ssh michael@tachyonfuture.com "cd ~/apps/far-reach-jobs && git pull && docker compose up -d --build"
```

## Key Files

- `backend/app/templates/base.html` - Base template with Tailwind config and dark mode
- `backend/app/main.py` - FastAPI application entry point
- `CLAUDE_STATUS.md` - Detailed implementation status and progress tracking
