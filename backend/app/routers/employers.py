import logging
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.schemas.employer import JobSubmission, CareersPageSubmission
from app.services.email import (
    send_job_submission_notification,
    send_careers_page_submission_notification,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/submit-job")
async def submit_job(submission: JobSubmission):
    """
    Submit a job posting for review.

    This endpoint receives job submissions from employers and sends
    a notification email to the admin for review.
    """
    logger.info(
        f"Job submission received: {submission.title} at {submission.organization}"
    )

    # Send notification email to admin
    email_sent = send_job_submission_notification(
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

    if not email_sent:
        logger.warning(
            f"Failed to send job submission notification for: {submission.title}"
        )
        # Still return success to the user - we don't want to expose email issues
        # The submission is logged, so admin can still see it

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
    logger.info(
        f"Careers page submission received: {submission.organization} - {submission.careers_url}"
    )

    # Send notification email to admin
    email_sent = send_careers_page_submission_notification(
        organization=submission.organization,
        careers_url=submission.careers_url,
        contact_email=submission.contact_email,
        notes=submission.notes,
    )

    if not email_sent:
        logger.warning(
            f"Failed to send careers page notification for: {submission.organization}"
        )
        # Still return success to the user

    return {
        "message": "Thank you! Your careers page has been submitted. We'll set up automatic job scraping and contact you if we have questions.",
        "success": True,
    }
