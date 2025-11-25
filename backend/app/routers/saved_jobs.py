from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Job, SavedJob, User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def list_saved_jobs(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List user's saved jobs."""
    saved_jobs = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == user.id)
        .join(Job)
        .order_by(SavedJob.saved_at.desc())
        .all()
    )

    # Check if this is an HTMX request
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/saved_job_list.html",
            {
                "request": request,
                "saved_jobs": saved_jobs,
                "user": user,
            },
        )

    return {
        "saved_jobs": [
            {
                "id": sj.id,
                "job_id": sj.job_id,
                "saved_at": sj.saved_at.isoformat(),
                "job": {
                    "id": sj.job.id,
                    "title": sj.job.title,
                    "organization": sj.job.organization,
                    "location": sj.job.location,
                    "state": sj.job.state,
                    "job_type": sj.job.job_type,
                    "salary_info": sj.job.salary_info,
                    "url": sj.job.url,
                    "is_stale": sj.job.is_stale,
                },
            }
            for sj in saved_jobs
        ]
    }


@router.post("/{job_id}")
def save_job(
    job_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a job for the current user."""
    # Check if job exists and is not stale
    job = db.query(Job).filter(Job.id == job_id, Job.is_stale == False).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check if already saved
    existing = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == user.id, SavedJob.job_id == job_id)
        .first()
    )

    if existing:
        # Already saved - return unsave button (idempotent)
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "partials/save_button.html",
                {"request": request, "job": job, "is_saved": True},
            )
        return {"message": "Job already saved", "job_id": job_id}

    # Save the job
    saved_job = SavedJob(user_id=user.id, job_id=job_id)
    db.add(saved_job)
    db.commit()

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/save_button.html",
            {"request": request, "job": job, "is_saved": True},
        )

    return {"message": "Job saved", "job_id": job_id}


@router.delete("/{job_id}")
def unsave_job(
    job_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a saved job for the current user."""
    saved_job = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == user.id, SavedJob.job_id == job_id)
        .first()
    )

    if not saved_job:
        # Not saved - return save button (idempotent)
        job = db.query(Job).filter(Job.id == job_id).first()
        if request.headers.get("HX-Request") and job:
            return templates.TemplateResponse(
                "partials/save_button.html",
                {"request": request, "job": job, "is_saved": False},
            )
        return {"message": "Job was not saved", "job_id": job_id}

    # Get the job before deleting saved_job
    job = saved_job.job

    db.delete(saved_job)
    db.commit()

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/save_button.html",
            {"request": request, "job": job, "is_saved": False},
        )

    return {"message": "Job unsaved", "job_id": job_id}
