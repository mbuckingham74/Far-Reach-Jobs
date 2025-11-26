import secrets
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from sqlalchemy import func as sql_func

from app.config import get_settings
from app.database import get_db
from app.models.scrape_source import ScrapeSource
from app.models.scrape_log import ScrapeLog
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
    response = templates.TemplateResponse(
        "admin/partials/source_list.html",
        {"request": request, "sources": sources, "success": f"Source '{name}' created"},
    )
    response.headers["HX-Trigger"] = "sourceCreated"
    return response


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


@router.get("/history")
def scrape_history(request: Request, db: Session = Depends(get_db)):
    """Scrape history page showing all past scrape runs."""
    if not get_admin_user(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    # Get recent scrape logs for display (paginated)
    logs = (
        db.query(ScrapeLog)
        .order_by(ScrapeLog.started_at.desc())
        .limit(100)
        .all()
    )

    # Calculate all-time summary stats with aggregate queries
    total_runs = db.query(sql_func.count(ScrapeLog.id)).scalar() or 0
    successful_runs = (
        db.query(sql_func.count(ScrapeLog.id))
        .filter(ScrapeLog.success == True)
        .scalar() or 0
    )
    failed_runs = total_runs - successful_runs
    total_jobs_added = (
        db.query(sql_func.sum(ScrapeLog.jobs_added)).scalar() or 0
    )
    total_jobs_updated = (
        db.query(sql_func.sum(ScrapeLog.jobs_updated)).scalar() or 0
    )

    return templates.TemplateResponse(
        "admin/history.html",
        {
            "request": request,
            "logs": logs,
            "stats": {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "total_jobs_added": total_jobs_added,
                "total_jobs_updated": total_jobs_updated,
            },
        },
    )


@router.post("/scrape")
async def trigger_scrape(request: Request, db: Session = Depends(get_db)):
    """Manually trigger a scrape run."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    import time
    from datetime import datetime, timezone
    from scraper.runner import run_all_scrapers
    from app.services.email import send_scrape_notification, ScrapeNotificationData

    try:
        # Get active sources
        sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == True).all()
        if not sources:
            return templates.TemplateResponse(
                "admin/partials/scrape_result.html",
                {"request": request, "error": "No active scrape sources configured", "success": False},
            )

        # Track timing
        start_time = time.time()
        execution_time = datetime.now(timezone.utc)

        # Run scrapers - returns list of ScrapeResult
        results = run_all_scrapers(db, sources)

        # Commit the changes made by scrapers
        db.commit()

        duration = time.time() - start_time

        # Aggregate results for display
        aggregate = {
            "sources_processed": len(results),
            "jobs_found": sum(r.jobs_found for r in results),
            "jobs_new": sum(r.jobs_new for r in results),
            "jobs_updated": sum(r.jobs_updated for r in results),
            "errors": [e for r in results for e in r.errors],
        }

        # Send notification email
        errors_with_source = []
        for result in results:
            for error in result.errors:
                errors_with_source.append((result.source_name, error))

        notification_data = ScrapeNotificationData(
            execution_time=execution_time,
            trigger_type="manual",
            duration_seconds=duration,
            sources_processed=len(results),
            jobs_added=aggregate["jobs_new"],
            jobs_updated=aggregate["jobs_updated"],
            jobs_removed=0,  # Manual scrape doesn't run stale cleanup
            errors=errors_with_source,
        )
        send_scrape_notification(notification_data)

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
