from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

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
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """List jobs with optional filters and search."""
    # Base query - exclude stale jobs
    query = db.query(Job).filter(Job.is_stale == False)

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
                "state": state or "",
                "job_type": job_type or "",
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
    # Use DB-side date calculation to match func.now() used in Job.first_seen_at
    seven_days_ago = func.date_sub(func.now(), text("INTERVAL 7 DAY"))
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
