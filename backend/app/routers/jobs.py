from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_optional_current_user
from app.models import Job, SavedJob, ScrapeSource
from app.schemas import JobResponse, JobListResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_model=JobListResponse)
def list_jobs(
    request: Request,
    q: str | None = Query(None, description="Search query for title, organization, description"),
    state: str | None = Query(None, description="Filter by state"),
    location: str | None = Query(None, description="Filter by location"),
    job_type: str | None = Query(None, description="Filter by job type"),
    date_posted: str | None = Query(None, description="Filter by days since posted (1, 7, 30)"),
    organization: str | None = Query(None, description="Filter by organization"),
    source_id: str | None = Query(None, description="Filter by source ID"),
    has_salary: str | None = Query(None, description="Filter jobs with salary info (1 or true)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """List jobs with optional filters and search."""
    # Base query - exclude stale jobs and eager load source for display
    query = db.query(Job).options(joinedload(Job.source)).filter(Job.is_stale == False)

    # Apply search filter (searches title, organization, description)
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Job.title.ilike(search_term),
                Job.organization.ilike(search_term),
                Job.description.ilike(search_term),
                Job.location.ilike(search_term),
            )
        )

    # Apply filters
    if state:
        query = query.filter(Job.state == state)
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if job_type:
        query = query.filter(Job.job_type == job_type)

    # Advanced filters (coerce strings to proper types, handle empty strings)
    date_posted_days = int(date_posted) if date_posted and date_posted.isdigit() else None
    source_id_int = int(source_id) if source_id and source_id.isdigit() else None
    has_salary_bool = has_salary in ("1", "true") if has_salary else False

    if date_posted_days:
        cutoff_date = datetime.utcnow() - timedelta(days=date_posted_days)
        query = query.filter(Job.first_seen_at >= cutoff_date)
    if organization:
        query = query.filter(Job.organization == organization)
    if source_id_int:
        query = query.filter(Job.source_id == source_id_int)
    if has_salary_bool:
        query = query.filter(Job.salary_info.isnot(None), Job.salary_info != "")

    # Get total count before pagination
    total = query.count()

    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page if total > 0 else 0
    offset = (page - 1) * per_page

    # Get paginated results, ordered by most recently seen
    jobs = query.order_by(Job.last_seen_at.desc()).offset(offset).limit(per_page).all()

    # Check if this is an HTMX request - if so, return HTML partial
    if request.headers.get("HX-Request"):
        user = get_optional_current_user(request, db)
        saved_job_ids = set()
        if user:
            saved_jobs = db.query(SavedJob.job_id).filter(SavedJob.user_id == user.id).all()
            saved_job_ids = {sj.job_id for sj in saved_jobs}

        return templates.TemplateResponse(
            "partials/job_list.html",
            {
                "request": request,
                "jobs": jobs,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "q": q or "",
                "location": location or "",
                "job_type": job_type or "",
                "date_posted": date_posted_days or "",
                "organization": organization or "",
                "source_id": source_id_int or "",
                "has_salary": has_salary_bool,
                "user": user,
                "saved_job_ids": saved_job_ids,
            },
        )

    return JobListResponse(
        jobs=jobs,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/states")
def get_states(db: Session = Depends(get_db)):
    """Get list of states that have active jobs."""
    states = (
        db.query(Job.state)
        .filter(Job.is_stale == False, Job.state.isnot(None))
        .distinct()
        .order_by(Job.state)
        .all()
    )
    return {"states": [s[0] for s in states if s[0]]}


@router.get("/locations")
def get_locations(request: Request, db: Session = Depends(get_db)):
    """Get list of unique locations (cities/communities) that have active jobs."""
    import html

    locations = (
        db.query(Job.location)
        .filter(Job.is_stale == False, Job.location.isnot(None), Job.location != "")
        .distinct()
        .order_by(Job.location)
        .all()
    )
    location_list = [loc[0] for loc in locations if loc[0]]

    # Return HTML options for HTMX requests
    if request.headers.get("HX-Request"):
        options_html = '<option value="">All Locations</option>'
        for loc in location_list:
            escaped_loc = html.escape(loc)
            options_html += f'<option value="{escaped_loc}">{escaped_loc}</option>'
        return HTMLResponse(content=options_html)

    return {"locations": location_list}


@router.get("/job-types")
def get_job_types(db: Session = Depends(get_db)):
    """Get list of job types that have active jobs."""
    job_types = (
        db.query(Job.job_type)
        .filter(Job.is_stale == False, Job.job_type.isnot(None))
        .distinct()
        .order_by(Job.job_type)
        .all()
    )
    return {"job_types": [jt[0] for jt in job_types if jt[0]]}


@router.get("/stats")
def get_stats(request: Request, db: Session = Depends(get_db)):
    """Get homepage statistics: active sources, total jobs, new jobs this week."""
    # Count active scrape sources
    sources_count = db.query(ScrapeSource).filter(ScrapeSource.is_active == True).count()

    # Count active (non-stale) jobs
    jobs_count = db.query(Job).filter(Job.is_stale == False).count()

    # Count jobs first seen in the last 7 days
    # Use Python datetime for dialect-agnostic comparison (works with MySQL and SQLite)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    new_this_week = (
        db.query(Job)
        .filter(
            and_(
                Job.is_stale == False,
                Job.first_seen_at >= seven_days_ago,
            )
        )
        .count()
    )

    stats = {
        "sources_count": sources_count,
        "jobs_count": jobs_count,
        "new_this_week": new_this_week,
    }

    # Return HTML partial for HTMX requests
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/stats_banner.html",
            {"request": request, **stats},
        )

    return stats


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a single job by ID. Returns 404 for stale/deleted jobs."""
    job = db.query(Job).filter(Job.id == job_id, Job.is_stale == False).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job
