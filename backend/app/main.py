from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from app.config import get_settings
from app.routers import health, auth, jobs, saved_jobs


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize scheduler for scraping
    from scraper.scheduler import start_scheduler
    start_scheduler()
    yield
    # Shutdown: Clean up scheduler
    from scraper.scheduler import shutdown_scheduler
    shutdown_scheduler()


app = FastAPI(
    title="Far Reach Jobs",
    description="Job listings from Alaska bush and rural US communities",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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
