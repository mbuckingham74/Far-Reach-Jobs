import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger(__name__)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager

from app.config import get_settings
from app.routers import health, auth, jobs, saved_jobs, admin


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
app.include_router(admin.router, prefix="/admin", tags=["admin"])


# Page routes
@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    """Home page with job listings."""
    from app.dependencies import get_optional_current_user
    from app.models import Job, ScrapeSource
    user = get_optional_current_user(request)

    # Pre-load locations for the filter dropdown (server-side render as fallback)
    locations = (
        db.query(Job.location)
        .filter(Job.is_stale == False, Job.location.isnot(None), Job.location != "")
        .distinct()
        .order_by(Job.location)
        .all()
    )
    location_list = [loc[0] for loc in locations if loc[0]]

    # Pre-load organizations for advanced filters
    organizations = (
        db.query(Job.organization)
        .filter(Job.is_stale == False, Job.organization.isnot(None), Job.organization != "")
        .distinct()
        .order_by(Job.organization)
        .all()
    )
    organization_list = [org[0] for org in organizations if org[0]]

    # Pre-load active sources for advanced filters
    sources = (
        db.query(ScrapeSource)
        .filter(ScrapeSource.is_active == True)
        .order_by(ScrapeSource.name)
        .all()
    )

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "locations": location_list,
        "organizations": organization_list,
        "sources": sources,
    })


@app.get("/login")
def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request, "user": None})


@app.get("/register")
def register_page(request: Request):
    """Registration page."""
    return templates.TemplateResponse("register.html", {"request": request, "user": None})


@app.get("/saved")
def saved_jobs_page(request: Request):
    """Saved jobs page (requires authentication)."""
    from app.dependencies import get_optional_current_user
    from fastapi.responses import RedirectResponse

    user = get_optional_current_user(request)
    if not user:
        return RedirectResponse(url="/login?next=/saved", status_code=302)
    return templates.TemplateResponse("saved.html", {"request": request, "user": user})


@app.get("/contact")
def contact_page(request: Request):
    """Contact page."""
    from app.dependencies import get_optional_current_user
    user = get_optional_current_user(request)
    return templates.TemplateResponse("contact.html", {"request": request, "user": user})


@app.get("/about")
def about_page(request: Request):
    """About Us page."""
    from app.dependencies import get_optional_current_user
    user = get_optional_current_user(request)
    return templates.TemplateResponse("about.html", {"request": request, "user": user})


# Error handlers
def _wants_json(request: Request) -> bool:
    """Check if request expects JSON response (API routes or Accept header)."""
    if request.url.path.startswith("/api/"):
        return True
    accept = request.headers.get("accept", "")
    return "application/json" in accept


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with custom error pages for browser, JSON for API."""
    from fastapi.responses import JSONResponse

    if _wants_json(request):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    if exc.status_code == 404:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "user": None},
            status_code=404
        )
    elif exc.status_code == 500:
        return templates.TemplateResponse(
            "500.html",
            {"request": request, "user": None},
            status_code=500
        )
    # For other HTTP errors, return a generic response
    return HTMLResponse(
        content=f"<h1>Error {exc.status_code}</h1><p>{exc.detail}</p>",
        status_code=exc.status_code
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with 500 error page or JSON for API."""
    from fastapi.responses import JSONResponse

    # Log the exception with request context for debugging
    logger.exception(
        "Unhandled exception: %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )

    if _wants_json(request):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    return templates.TemplateResponse(
        "500.html",
        {"request": request, "user": None},
        status_code=500
    )
