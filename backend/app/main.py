import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from app.config import get_settings
from app.routers import health, auth, jobs, saved_jobs


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only start scheduler in production or if explicitly enabled
    # This prevents duplicate schedulers during development with --reload
    if settings.environment == "production" or os.getenv("ENABLE_SCHEDULER", "").lower() == "true":
        from scraper.scheduler import start_scheduler
        start_scheduler()
    yield
    # Shutdown: Clean up scheduler if it was started
    if settings.environment == "production" or os.getenv("ENABLE_SCHEDULER", "").lower() == "true":
        from scraper.scheduler import shutdown_scheduler
        shutdown_scheduler()


app = FastAPI(
    title="Far Reach Jobs",
    description="Job listings from Alaska bush and rural US communities",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files - handle both Docker (static/) and local development (../frontend/static/)
static_dir = Path("static")
if not static_dir.exists():
    static_dir = Path(__file__).parent.parent.parent / "frontend" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(saved_jobs.router, prefix="/api/saved-jobs", tags=["saved-jobs"])


# Page routes will be added here
@app.get("/")
async def home():
    from fastapi.responses import HTMLResponse
    from fastapi import Request
    # Placeholder - will be implemented in Phase 1D
    return HTMLResponse("<h1>Far Reach Jobs - Coming Soon</h1>")
