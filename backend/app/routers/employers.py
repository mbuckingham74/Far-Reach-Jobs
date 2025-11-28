import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas.employer import JobSubmission, CareersPageSubmission
from app.services.email import (
    send_job_submission_notification,
    send_careers_page_submission_notification,
)
from app.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


def _send_job_email(submission: JobSubmission) -> None:
    """Background task to send job submission email."""
    try:
        send_job_submission_notification(
            title=submission.title,
            organization=submission.organization,
            location=submission.location,
            url=submission.url,
            contact_email=submission.contact_email,
            state=submission.state,
            description=submission.description,
            job_type=submission.job_type,
            salary_info=submission.salary_info,
        )
    except Exception as e:
        logger.error(f"Background email failed for job submission: {e}")


def _send_careers_email(submission: CareersPageSubmission) -> None:
    """Background task to send careers page submission email."""
    try:
        send_careers_page_submission_notification(
            organization=submission.organization,
            careers_url=submission.careers_url,
            contact_email=submission.contact_email,
            notes=submission.notes,
        )
    except Exception as e:
        logger.error(f"Background email failed for careers page submission: {e}")


@router.post("/submit-job")
async def submit_job(submission: JobSubmission, background_tasks: BackgroundTasks):
    """
    Submit a job posting for review.

    This endpoint receives job submissions from employers and sends
    a notification email to the admin for review.
    """
    # Check if email is configured - if not, we can't process submissions
    if not settings.admin_email:
        logger.error("Job submission received but ADMIN_EMAIL not configured")
        raise HTTPException(
            status_code=503,
            detail="Submissions are temporarily unavailable. Please try again later or contact us directly.",
        )

    logger.info(
        f"Job submission received: {submission.title} at {submission.organization} "
        f"(contact: {submission.contact_email})"
    )

    # Send email in background to avoid blocking
    background_tasks.add_task(_send_job_email, submission)

    return {
        "message": "Thank you! Your job has been submitted for review. We'll add it to our listings shortly.",
        "success": True,
    }


@router.post("/submit-careers-page")
async def submit_careers_page(
    submission: CareersPageSubmission, background_tasks: BackgroundTasks
):
    """
    Submit a careers page URL for automatic scraping.

    This endpoint receives careers page submissions from employers and sends
    a notification email to the admin to set up scraping.
    """
    # Check if email is configured - if not, we can't process submissions
    if not settings.admin_email:
        logger.error("Careers page submission received but ADMIN_EMAIL not configured")
        raise HTTPException(
            status_code=503,
            detail="Submissions are temporarily unavailable. Please try again later or contact us directly.",
        )

    logger.info(
        f"Careers page submission received: {submission.organization} - {submission.careers_url} "
        f"(contact: {submission.contact_email})"
    )

    # Send email in background to avoid blocking
    background_tasks.add_task(_send_careers_email, submission)

    return {
        "message": "Thank you! Your careers page has been submitted. We'll set up automatic job scraping and contact you if we have questions.",
        "success": True,
    }
