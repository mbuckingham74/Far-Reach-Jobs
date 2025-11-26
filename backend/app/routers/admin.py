import secrets
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.scrape_source import ScrapeSource
from app.models.job import Job

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()

# Simple session store for admin auth (in production, use Redis or similar)
admin_sessions: dict[str, bool] = {}


def get_admin_user(request: Request) -> bool:
    """Check if request has valid admin session."""
    session_id = request.cookies.get("admin_session")
    if not session_id or session_id not in admin_sessions:
        return False
    return True


def require_admin(request: Request) -> bool:
    """Dependency that requires admin authentication."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401, detail="Admin authentication required")
    return True


@router.get("/login")
def admin_login_page(request: Request):
    """Admin login page."""
    if get_admin_user(request):
        return RedirectResponse(url="/admin", status_code=302)
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.post("/login")
async def admin_login(request: Request):
    """Process admin login."""
    form = await request.form()
    username = form.get("username", "")
    password = form.get("password", "")

    if username == settings.admin_username and password == settings.admin_password:
        session_id = secrets.token_urlsafe(32)
        admin_sessions[session_id] = True
        response = RedirectResponse(url="/admin", status_code=302)
        response.set_cookie(
            key="admin_session",
            value=session_id,
            httponly=True,
            secure=settings.environment == "production",
            samesite="lax",
            max_age=86400,  # 24 hours
        )
        return response

    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "error": "Invalid credentials"},
        status_code=401,
    )


@router.post("/logout")
def admin_logout(request: Request):
    """Admin logout."""
    session_id = request.cookies.get("admin_session")
    if session_id and session_id in admin_sessions:
        del admin_sessions[session_id]
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("admin_session")
    return response


@router.get("")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Admin dashboard."""
    if not get_admin_user(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    sources = db.query(ScrapeSource).order_by(ScrapeSource.created_at.desc()).all()
    job_count = db.query(Job).filter(Job.is_stale == False).count()
    stale_count = db.query(Job).filter(Job.is_stale == True).count()

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "sources": sources,
            "job_count": job_count,
            "stale_count": stale_count,
        },
    )


@router.get("/sources")
def list_sources(request: Request, db: Session = Depends(get_db)):
    """List all scrape sources (HTMX partial)."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    sources = db.query(ScrapeSource).order_by(ScrapeSource.created_at.desc()).all()
    return templates.TemplateResponse(
        "admin/partials/source_list.html",
        {"request": request, "sources": sources},
    )


@router.post("/sources")
async def create_source(request: Request, db: Session = Depends(get_db)):
    """Create a new scrape source."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    form = await request.form()
    name = form.get("name", "").strip()
    base_url = form.get("base_url", "").strip()
    scraper_class = form.get("scraper_class", "GenericScraper").strip()

    if not name or not base_url:
        sources = db.query(ScrapeSource).order_by(ScrapeSource.created_at.desc()).all()
        return templates.TemplateResponse(
            "admin/partials/source_list.html",
            {"request": request, "sources": sources, "error": "Name and URL are required"},
        )

    source = ScrapeSource(
        name=name,
        base_url=base_url,
        scraper_class=scraper_class,
        is_active=True,
    )
    db.add(source)
    db.commit()

    sources = db.query(ScrapeSource).order_by(ScrapeSource.created_at.desc()).all()
    return templates.TemplateResponse(
        "admin/partials/source_list.html",
        {"request": request, "sources": sources, "success": f"Source '{name}' created"},
    )


@router.delete("/sources/{source_id}")
def delete_source(source_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a scrape source."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    source = db.query(ScrapeSource).filter(ScrapeSource.id == source_id).first()
    if source:
        db.delete(source)
        db.commit()

    sources = db.query(ScrapeSource).order_by(ScrapeSource.created_at.desc()).all()
    return templates.TemplateResponse(
        "admin/partials/source_list.html",
        {"request": request, "sources": sources},
    )


@router.post("/sources/{source_id}/toggle")
def toggle_source(source_id: int, request: Request, db: Session = Depends(get_db)):
    """Toggle a scrape source active/inactive."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    source = db.query(ScrapeSource).filter(ScrapeSource.id == source_id).first()
    if source:
        source.is_active = not source.is_active
        db.commit()

    sources = db.query(ScrapeSource).order_by(ScrapeSource.created_at.desc()).all()
    return templates.TemplateResponse(
        "admin/partials/source_list.html",
        {"request": request, "sources": sources},
    )


@router.post("/scrape")
async def trigger_scrape(request: Request, db: Session = Depends(get_db)):
    """Manually trigger a scrape run."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    from scraper.runner import run_all_scrapers

    try:
        # Get active sources
        sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == True).all()
        if not sources:
            return templates.TemplateResponse(
                "admin/partials/scrape_result.html",
                {"request": request, "error": "No active scrape sources configured", "success": False},
            )

        # Run scrapers - returns list of ScrapeResult
        results = run_all_scrapers(db, sources)

        # Commit the changes made by scrapers
        db.commit()

        # Aggregate results for display
        aggregate = {
            "sources_processed": len(results),
            "jobs_found": sum(r.jobs_found for r in results),
            "jobs_new": sum(r.jobs_new for r in results),
            "jobs_updated": sum(r.jobs_updated for r in results),
            "errors": [e for r in results for e in r.errors],
        }

        return templates.TemplateResponse(
            "admin/partials/scrape_result.html",
            {"request": request, "result": aggregate, "success": True},
        )
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            "admin/partials/scrape_result.html",
            {"request": request, "error": str(e), "success": False},
        )
