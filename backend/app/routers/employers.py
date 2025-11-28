import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException

from app.schemas.employer import JobSubmission, CareersPageSubmission
from app.services.email import (
    send_job_submission_notification,
    send_careers_page_submission_notification,
)
from app.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

# Thread pool for blocking SMTP operations
_email_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="email_")


def _check_email_configured() -> None:
    """Raise 503 if email is not properly configured."""
    if not settings.admin_email:
        raise HTTPException(
            status_code=503,
            detail="Submissions are temporarily unavailable. Please try again later or contact us directly.",
        )
    if not settings.smtp_user or not settings.smtp_password:
        raise HTTPException(
            status_code=503,
            detail="Submissions are temporarily unavailable. Please try again later or contact us directly.",
        )


@router.post("/submit-job")
async def submit_job(submission: JobSubmission):
    """
    Submit a job posting for review.

    This endpoint receives job submissions from employers and sends
    a notification email to the admin for review.
    """
    # Check if email is fully configured before accepting the submission
    _check_email_configured()

    logger.info(
        f"Job submission received: {submission.title} at {submission.organization} "
        f"(contact: {submission.contact_email})"
    )

    # Run blocking SMTP in thread pool to avoid blocking event loop
    loop = asyncio.get_event_loop()
    try:
        email_sent = await loop.run_in_executor(
            _email_executor,
            lambda: send_job_submission_notification(
                title=submission.title,
                organization=submission.organization,
                location=submission.location,
                url=submission.url,
                contact_email=submission.contact_email,
                state=submission.state,
                description=submission.description,
                job_type=submission.job_type,
                salary_info=submission.salary_info,
            ),
        )

        if not email_sent:
            logger.error(f"Email send returned False for job: {submission.title}")
            raise HTTPException(
                status_code=503,
                detail="Unable to process your submission right now. Please try again later or contact us directly.",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Email send failed for job submission: {e}")
        raise HTTPException(
            status_code=503,
            detail="Unable to process your submission right now. Please try again later or contact us directly.",
        )

    return {
        "message": "Thank you! Your job has been submitted for review. We'll add it to our listings shortly.",
        "success": True,
    }


@router.post("/submit-careers-page")
async def submit_careers_page(submission: CareersPageSubmission):
    """
    Submit a careers page URL for automatic scraping.

    This endpoint receives careers page submissions from employers and sends
    a notification email to the admin to set up scraping.
    """
    # Check if email is fully configured before accepting the submission
    _check_email_configured()

    logger.info(
        f"Careers page submission received: {submission.organization} - {submission.careers_url} "
        f"(contact: {submission.contact_email})"
    )

    # Run blocking SMTP in thread pool to avoid blocking event loop
    loop = asyncio.get_event_loop()
    try:
        email_sent = await loop.run_in_executor(
            _email_executor,
            lambda: send_careers_page_submission_notification(
                organization=submission.organization,
                careers_url=submission.careers_url,
                contact_email=submission.contact_email,
                notes=submission.notes,
            ),
        )

        if not email_sent:
            logger.error(f"Email send returned False for careers page: {submission.organization}")
            raise HTTPException(
                status_code=503,
                detail="Unable to process your submission right now. Please try again later or contact us directly.",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Email send failed for careers page submission: {e}")
        raise HTTPException(
            status_code=503,
            detail="Unable to process your submission right now. Please try again later or contact us directly.",
        )

    return {
        "message": "Thank you! Your careers page has been submitted. We'll set up automatic job scraping and contact you if we have questions.",
        "success": True,
    }
