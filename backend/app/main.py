import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
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


# Page routes
@app.get("/")
def home(request: Request):
    """Home page with job listings."""
    from app.dependencies import get_optional_current_user
    user = get_optional_current_user(request)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


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


# Error handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with custom error pages."""
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
    """Handle unexpected exceptions with 500 error page."""
    return templates.TemplateResponse(
        "500.html",
        {"request": request, "user": None},
        status_code=500
    )
