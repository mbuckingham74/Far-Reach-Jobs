import logging
import secrets
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from sqlalchemy import func as sql_func

logger = logging.getLogger(__name__)

from app.config import get_settings
from app.database import get_db
from app.models.scrape_source import ScrapeSource
from app.models.scrape_log import ScrapeLog
from app.models.job import Job
from app.services.ai_analyzer import analyze_job_page, is_ai_analysis_available, generate_scraper_for_url

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

    active_sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == True).order_by(ScrapeSource.created_at.desc()).all()
    disabled_count = db.query(ScrapeSource).filter(ScrapeSource.is_active == False).count()
    job_count = db.query(Job).filter(Job.is_stale == False).count()
    stale_count = db.query(Job).filter(Job.is_stale == True).count()

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "sources": active_sources,
            "disabled_count": disabled_count,
            "job_count": job_count,
            "stale_count": stale_count,
        },
    )


@router.get("/sources")
def list_sources(request: Request, db: Session = Depends(get_db)):
    """List active scrape sources (HTMX partial)."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == True).order_by(ScrapeSource.created_at.desc()).all()
    return templates.TemplateResponse(
        "admin/partials/source_list.html",
        {"request": request, "sources": sources},
    )


@router.get("/sources/disabled")
def disabled_sources_page(request: Request, db: Session = Depends(get_db)):
    """Disabled sources page."""
    if not get_admin_user(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    disabled_sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == False).order_by(ScrapeSource.created_at.desc()).all()

    return templates.TemplateResponse(
        "admin/disabled_sources.html",
        {
            "request": request,
            "sources": disabled_sources,
        },
    )


@router.get("/sources/disabled/list")
def list_disabled_sources(request: Request, db: Session = Depends(get_db)):
    """List disabled scrape sources (HTMX partial)."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == False).order_by(ScrapeSource.created_at.desc()).all()
    return templates.TemplateResponse(
        "admin/partials/source_list.html",
        {"request": request, "sources": sources, "show_disabled": True},
    )


@router.get("/sources/disabled-count")
def disabled_count_link(request: Request, db: Session = Depends(get_db)):
    """Return the disabled sources count link (HTMX partial)."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    disabled_count = db.query(ScrapeSource).filter(ScrapeSource.is_active == False).count()
    return templates.TemplateResponse(
        "admin/partials/disabled_count_link.html",
        {"request": request, "disabled_count": disabled_count},
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
        sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == True).order_by(ScrapeSource.created_at.desc()).all()
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

    try:
        db.commit()
    except Exception as e:
        logger.error(f"Failed to create source '{name}': {e}")
        db.rollback()
        sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == True).order_by(ScrapeSource.created_at.desc()).all()
        return templates.TemplateResponse(
            "admin/partials/source_list.html",
            {"request": request, "sources": sources, "error": "Failed to create source. Please try again."},
        )

    sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == True).order_by(ScrapeSource.created_at.desc()).all()
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

    # Check if request came from disabled sources page
    hx_target = request.headers.get("HX-Target", "")
    show_disabled = hx_target == "disabled-source-list"

    source = db.query(ScrapeSource).filter(ScrapeSource.id == source_id).first()
    if source:
        db.delete(source)
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to delete source {source_id}: {e}")
            db.rollback()
            if show_disabled:
                sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == False).order_by(ScrapeSource.created_at.desc()).all()
            else:
                sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == True).order_by(ScrapeSource.created_at.desc()).all()
            return templates.TemplateResponse(
                "admin/partials/source_list.html",
                {"request": request, "sources": sources, "show_disabled": show_disabled, "error": "Failed to delete source. Please try again."},
            )

    if show_disabled:
        sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == False).order_by(ScrapeSource.created_at.desc()).all()
    else:
        sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == True).order_by(ScrapeSource.created_at.desc()).all()
    return templates.TemplateResponse(
        "admin/partials/source_list.html",
        {"request": request, "sources": sources, "show_disabled": show_disabled},
    )


@router.post("/sources/{source_id}/toggle")
def toggle_source(source_id: int, request: Request, db: Session = Depends(get_db)):
    """Toggle a scrape source active/inactive."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    # Check if request came from disabled sources page
    hx_target = request.headers.get("HX-Target", "")
    show_disabled = hx_target == "disabled-source-list"

    source = db.query(ScrapeSource).filter(ScrapeSource.id == source_id).first()
    if source:
        source.is_active = not source.is_active
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to toggle source {source_id}: {e}")
            db.rollback()
            if show_disabled:
                sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == False).order_by(ScrapeSource.created_at.desc()).all()
            else:
                sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == True).order_by(ScrapeSource.created_at.desc()).all()
            return templates.TemplateResponse(
                "admin/partials/source_list.html",
                {"request": request, "sources": sources, "show_disabled": show_disabled, "error": "Failed to toggle source. Please try again."},
            )

    # After toggling, return the appropriate list
    if show_disabled:
        sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == False).order_by(ScrapeSource.created_at.desc()).all()
    else:
        sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == True).order_by(ScrapeSource.created_at.desc()).all()
    return templates.TemplateResponse(
        "admin/partials/source_list.html",
        {"request": request, "sources": sources, "show_disabled": show_disabled},
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
    """Manually trigger a scrape run for all active sources."""
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
            response = templates.TemplateResponse(
                "admin/partials/scrape_modal_result.html",
                {"request": request, "error": "No active scrape sources configured", "success": False},
            )
            response.headers["HX-Trigger"] = "refreshSourceList"
            return response

        # Track timing
        start_time = time.time()
        execution_time = datetime.now(timezone.utc)

        # Run scrapers - returns list of ScrapeResult
        # Note: run_all_scrapers commits after each source for transaction isolation
        results = run_all_scrapers(db, sources)

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

        response = templates.TemplateResponse(
            "admin/partials/scrape_modal_result.html",
            {"request": request, "result": aggregate, "success": True},
        )
        response.headers["HX-Trigger"] = "refreshSourceList"
        return response
    except Exception as e:
        logger.error(f"Manual scrape failed: {e}")
        db.rollback()
        response = templates.TemplateResponse(
            "admin/partials/scrape_modal_result.html",
            {"request": request, "error": "Scrape failed. Check logs for details.", "success": False},
        )
        response.headers["HX-Trigger"] = "refreshSourceList"
        return response


@router.post("/sources/{source_id}/scrape")
async def trigger_single_source_scrape(source_id: int, request: Request, db: Session = Depends(get_db)):
    """Manually trigger a scrape for a single source."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    import time
    from datetime import datetime, timezone
    from scraper.runner import run_scraper
    from app.services.email import send_scrape_notification, ScrapeNotificationData

    source = db.query(ScrapeSource).filter(ScrapeSource.id == source_id).first()
    if not source:
        response = templates.TemplateResponse(
            "admin/partials/scrape_modal_result.html",
            {"request": request, "error": "Source not found", "success": False},
        )
        response.headers["HX-Trigger"] = "refreshSourceList"
        return response

    try:
        # Track timing
        start_time = time.time()
        execution_time = datetime.now(timezone.utc)

        # Run scraper for single source
        result = run_scraper(db, source, trigger_type="manual")
        db.commit()

        duration = time.time() - start_time

        # Send notification email
        errors_with_source = [(source.name, e) for e in result.errors]

        notification_data = ScrapeNotificationData(
            execution_time=execution_time,
            trigger_type=f"manual (single: {source.name})",
            duration_seconds=duration,
            sources_processed=1,
            jobs_added=result.jobs_new,
            jobs_updated=result.jobs_updated,
            jobs_removed=0,
            errors=errors_with_source,
        )
        send_scrape_notification(notification_data)

        # Build result for modal display
        modal_result = {
            "sources_processed": 1,
            "jobs_found": result.jobs_found,
            "jobs_new": result.jobs_new,
            "jobs_updated": result.jobs_updated,
            "errors": result.errors,
        }

        response = templates.TemplateResponse(
            "admin/partials/scrape_modal_result.html",
            {
                "request": request,
                "result": modal_result,
                "source_name": source.name,
                "success": True,
            },
        )
        response.headers["HX-Trigger"] = "refreshSourceList"
        return response

    except Exception as e:
        logger.exception(f"Single source scrape failed for {source.name}: {e}")
        db.rollback()
        response = templates.TemplateResponse(
            "admin/partials/scrape_modal_result.html",
            {
                "request": request,
                "source_name": source.name,
                "error": "Scrape failed. Check logs for details.",
                "success": False,
            },
        )
        response.headers["HX-Trigger"] = "refreshSourceList"
        return response


@router.get("/sources/{source_id}/edit")
def edit_source_page(source_id: int, request: Request, saved: str = None, db: Session = Depends(get_db)):
    """Edit source basic info (name, URLs)."""
    if not get_admin_user(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    source = db.query(ScrapeSource).filter(ScrapeSource.id == source_id).first()
    if not source:
        return RedirectResponse(url="/admin", status_code=302)

    context = {"request": request, "source": source}
    if saved:
        context["success"] = "Source updated successfully"

    return templates.TemplateResponse("admin/edit_source.html", context)


@router.post("/sources/{source_id}/edit")
async def save_source_edit(source_id: int, request: Request, db: Session = Depends(get_db)):
    """Save source basic info changes."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    source = db.query(ScrapeSource).filter(ScrapeSource.id == source_id).first()
    if not source:
        return RedirectResponse(url="/admin", status_code=302)

    form = await request.form()
    name = form.get("name", "").strip()
    base_url = form.get("base_url", "").strip()
    listing_url = form.get("listing_url", "").strip() or None

    # Validation
    errors = []
    if not name:
        errors.append("Source name is required")
    if not base_url:
        errors.append("Base URL is required")
    if base_url and not (base_url.startswith("http://") or base_url.startswith("https://")):
        errors.append("Base URL must start with http:// or https://")
    if listing_url and not (listing_url.startswith("http://") or listing_url.startswith("https://")):
        errors.append("Listing URL must start with http:// or https://")

    if errors:
        # Pass back submitted values so user doesn't lose their input
        source.name = name
        source.base_url = base_url
        source.listing_url = listing_url
        return templates.TemplateResponse(
            "admin/edit_source.html",
            {"request": request, "source": source, "error": "; ".join(errors)},
        )

    source.name = name
    source.base_url = base_url
    source.listing_url = listing_url

    try:
        db.commit()
        # PRG pattern: redirect to GET to avoid form resubmission on refresh
        response = RedirectResponse(url=f"/admin/sources/{source_id}/edit?saved=1", status_code=303)
        return response
    except Exception as e:
        logger.error(f"Failed to update source {source_id}: {e}")
        db.rollback()
        return templates.TemplateResponse(
            "admin/edit_source.html",
            {"request": request, "source": source, "error": "Failed to save changes. Please try again."},
        )


@router.get("/sources/{source_id}/configure")
def configure_source_page(source_id: int, request: Request, db: Session = Depends(get_db)):
    """Source configuration page for CSS selectors."""
    if not get_admin_user(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    source = db.query(ScrapeSource).filter(ScrapeSource.id == source_id).first()
    if not source:
        return RedirectResponse(url="/admin", status_code=302)

    return templates.TemplateResponse(
        "admin/configure_source.html",
        {"request": request, "source": source},
    )


@router.post("/sources/{source_id}/configure")
async def save_source_configuration(source_id: int, request: Request, db: Session = Depends(get_db)):
    """Save source CSS selector configuration."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    source = db.query(ScrapeSource).filter(ScrapeSource.id == source_id).first()
    if not source:
        return RedirectResponse(url="/admin", status_code=302)

    form = await request.form()

    # Extract and validate form values
    name = form.get("name", "").strip()
    base_url = form.get("base_url", "").strip()
    selector_job_container = form.get("selector_job_container", "").strip() or None
    selector_title = form.get("selector_title", "").strip() or None
    selector_url = form.get("selector_url", "").strip() or None

    # Server-side validation for required fields
    errors = []
    if not name:
        errors.append("Source name is required")
    if not base_url:
        errors.append("Base URL is required")
    if base_url and not (base_url.startswith("http://") or base_url.startswith("https://")):
        errors.append("Base URL must start with http:// or https://")

    if errors:
        return templates.TemplateResponse(
            "admin/configure_source.html",
            {"request": request, "source": source, "error": "; ".join(errors)},
        )

    # Update source configuration
    source.name = name
    source.base_url = base_url
    source.listing_url = form.get("listing_url", "").strip() or None
    source.selector_job_container = selector_job_container
    source.selector_title = selector_title
    source.selector_url = selector_url
    source.selector_organization = form.get("selector_organization", "").strip() or None
    source.selector_location = form.get("selector_location", "").strip() or None
    source.selector_job_type = form.get("selector_job_type", "").strip() or None
    source.selector_salary = form.get("selector_salary", "").strip() or None
    source.selector_description = form.get("selector_description", "").strip() or None
    source.url_attribute = form.get("url_attribute", "href").strip() or "href"
    source.selector_next_page = form.get("selector_next_page", "").strip() or None
    source.default_location = form.get("default_location", "").strip() or None

    max_pages_str = form.get("max_pages", "10").strip()
    try:
        source.max_pages = int(max_pages_str) if max_pages_str else 10
    except ValueError:
        source.max_pages = 10

    # Checkbox: present in form data only when checked
    source.use_playwright = form.get("use_playwright") == "1"

    try:
        db.commit()
        # Check if selectors are missing and add warning
        missing_selectors = []
        if source.scraper_class == "GenericScraper":
            if not selector_job_container:
                missing_selectors.append("Job Container")
            if not selector_title:
                missing_selectors.append("Title")
            if not selector_url:
                missing_selectors.append("URL")

        if missing_selectors:
            # Only show warning, no success banner - scraping won't work without selectors
            warning = f"Configuration saved, but scraping won't work until these selectors are set: {', '.join(missing_selectors)}"
            return templates.TemplateResponse(
                "admin/configure_source.html",
                {"request": request, "source": source, "warning": warning},
            )

        return templates.TemplateResponse(
            "admin/configure_source.html",
            {"request": request, "source": source, "success": "Configuration saved successfully"},
        )
    except Exception as e:
        logger.error(f"Failed to save source configuration for {source_id}: {e}")
        db.rollback()
        return templates.TemplateResponse(
            "admin/configure_source.html",
            {"request": request, "source": source, "error": "Failed to save configuration. Please try again."},
        )


@router.post("/sources/{source_id}/analyze")
async def analyze_source_page(source_id: int, request: Request, db: Session = Depends(get_db)):
    """Use AI to analyze the job listing page and suggest CSS selectors."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    source = db.query(ScrapeSource).filter(ScrapeSource.id == source_id).first()
    if not source:
        return HTMLResponse(
            '<div class="text-red-600 dark:text-red-400">Source not found</div>',
            status_code=404
        )

    if not is_ai_analysis_available():
        return HTMLResponse(
            '<div class="text-red-600 dark:text-red-400">AI analysis not available. Set ANTHROPIC_API_KEY in environment.</div>',
            status_code=400
        )

    # Read Browser Mode toggle from form (not database) so it works without saving first
    form = await request.form()
    use_playwright = form.get("use_playwright") == "1"

    # Use first non-empty listing_url if set (supports multiple URLs separated by newlines),
    # otherwise fall back to base_url
    listing_url = source.listing_url or ""
    listing_urls = [url.strip() for url in listing_url.split('\n') if url.strip()]
    url_to_analyze = listing_urls[0] if listing_urls else source.base_url

    try:
        # Use Playwright if Browser Mode toggle is checked
        suggestions = await analyze_job_page(url_to_analyze, use_playwright=use_playwright)

        return templates.TemplateResponse(
            "admin/partials/ai_suggestions.html",
            {
                "request": request,
                "suggestions": suggestions,
                "source": source,
            },
        )
    except Exception as e:
        logger.exception(f"AI analysis failed for source {source_id}: {e}")
        return HTMLResponse(
            f'<div class="text-red-600 dark:text-red-400">Analysis failed: {str(e)}</div>',
            status_code=500
        )


@router.post("/sources/{source_id}/generate-scraper")
async def generate_custom_scraper_code(source_id: int, request: Request, db: Session = Depends(get_db)):
    """Use AI to generate a custom scraper class for sites that can't use GenericScraper."""
    if not get_admin_user(request):
        raise HTTPException(status_code=401)

    source = db.query(ScrapeSource).filter(ScrapeSource.id == source_id).first()
    if not source:
        return HTMLResponse(
            '<div class="text-red-600 dark:text-red-400">Source not found</div>',
            status_code=404
        )

    if not is_ai_analysis_available():
        return HTMLResponse(
            '<div class="text-red-600 dark:text-red-400">AI not available. Set ANTHROPIC_API_KEY in environment.</div>',
            status_code=400
        )

    # Read Browser Mode toggle from form
    form = await request.form()
    use_playwright = form.get("use_playwright") == "1"

    # Get the listing URL
    listing_url = source.listing_url or ""
    listing_urls = [url.strip() for url in listing_url.split('\n') if url.strip()]
    url_to_analyze = listing_urls[0] if listing_urls else source.base_url

    try:
        result = await generate_scraper_for_url(
            source_name=source.name,
            base_url=source.base_url,
            listing_url=url_to_analyze,
            use_playwright=use_playwright
        )

        if result.success:
            # Save the generated code to the source
            source.custom_scraper_code = result.code
            db.commit()

        return templates.TemplateResponse(
            "admin/partials/generated_scraper.html",
            {
                "request": request,
                "result": result,
                "source": source,
            },
        )
    except Exception as e:
        logger.exception(f"Scraper generation failed for source {source_id}: {e}")
        return HTMLResponse(
            f'<div class="text-red-600 dark:text-red-400">Generation failed: {str(e)}</div>',
            status_code=500
        )
