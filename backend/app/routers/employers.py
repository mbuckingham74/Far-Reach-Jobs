import asyncio
import csv
import io
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import ValidationError

from app.schemas.employer import JobSubmission, CareersPageSubmission, BulkSourceEntry
from app.services.email import (
    send_job_submission_notification,
    send_careers_page_submission_notification,
    send_bulk_source_submission_notification,
)
from app.config import get_settings

# Max file size: 512KB (more conservative for public endpoint)
MAX_CSV_SIZE = 512 * 1024
# Max rows per submission
MAX_ROWS = 100

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


def _normalize_column_name(name: str) -> str:
    """Normalize column name for flexible matching."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _validate_email(email: str) -> str:
    """Validate and normalize email address."""
    email = email.strip().lower()
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        raise ValueError("Invalid email address")
    if len(email) > 255:
        raise ValueError("Email must be less than 255 characters")
    return email


@router.post("/submit-bulk-sources")
async def submit_bulk_sources(
    file: UploadFile = File(...),
    contact_email: str = Form(...),
    notes: str = Form(None),
):
    """
    Submit multiple job sources via CSV for review.

    This endpoint receives a CSV file with job source information and sends
    a notification email to the admin for review. The CSV should have columns:
    - Organization (required)
    - Base URL (required)
    - Careers URL (optional)

    This does NOT directly add sources to the database - it only notifies
    the admin who will review and add them manually.
    """
    # Check if email is fully configured
    _check_email_configured()

    # Validate contact email
    try:
        contact_email = _validate_email(contact_email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validate notes length
    if notes:
        notes = notes.strip()
        if len(notes) > 2000:
            raise HTTPException(status_code=400, detail="Notes must be less than 2000 characters")
        if not notes:
            notes = None

    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV file")

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_CSV_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_CSV_SIZE // 1024}KB.",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    # Parse CSV
    try:
        text = content.decode("utf-8-sig")  # Handle BOM if present
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Could not decode file. Please use UTF-8 encoding.")

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file has no headers")

    # Map column names flexibly
    column_map = {}
    normalized_fields = {_normalize_column_name(f): f for f in reader.fieldnames}

    # Required: Organization
    for variant in ["organization", "organisationname", "orgname", "org", "name", "sourcename", "source"]:
        if variant in normalized_fields:
            column_map["organization"] = normalized_fields[variant]
            break
    if "organization" not in column_map:
        raise HTTPException(
            status_code=400,
            detail="CSV must have an 'Organization' or 'Source Name' column",
        )

    # Required: Base URL
    for variant in ["baseurl", "base", "url", "website", "homepage", "siteurl"]:
        if variant in normalized_fields:
            column_map["base_url"] = normalized_fields[variant]
            break
    if "base_url" not in column_map:
        raise HTTPException(
            status_code=400,
            detail="CSV must have a 'Base URL' or 'URL' column",
        )

    # Optional: Careers URL
    for variant in ["careersurl", "careers", "jobsurl", "jobs", "careerspage", "jobspage"]:
        if variant in normalized_fields:
            column_map["careers_url"] = normalized_fields[variant]
            break

    # Parse and validate rows
    sources = []
    errors = []
    row_count = 0

    for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        row_count += 1

        if row_count > MAX_ROWS:
            raise HTTPException(
                status_code=400,
                detail=f"Too many rows. Maximum is {MAX_ROWS} sources per submission.",
            )

        org = row.get(column_map["organization"], "").strip()
        base_url = row.get(column_map["base_url"], "").strip()
        careers_url = row.get(column_map.get("careers_url", ""), "").strip() if "careers_url" in column_map else None

        # Skip empty rows
        if not org and not base_url:
            continue

        # Validate using Pydantic schema
        try:
            entry = BulkSourceEntry(
                organization=org,
                base_url=base_url,
                careers_url=careers_url if careers_url else None,
            )
            sources.append({
                "organization": entry.organization,
                "base_url": entry.base_url,
                "careers_url": entry.careers_url,
            })
        except ValidationError as e:
            # Extract the first error message
            error_msg = e.errors()[0].get("msg", "Invalid data")
            errors.append(f"Row {row_num}: {error_msg}")

    if not sources and not errors:
        raise HTTPException(status_code=400, detail="No valid sources found in CSV")

    # If there are too many errors, reject the submission
    if len(errors) > 10:
        raise HTTPException(
            status_code=400,
            detail=f"Too many errors in CSV ({len(errors)} rows). Please fix and resubmit. First errors: {'; '.join(errors[:5])}",
        )

    if not sources:
        raise HTTPException(
            status_code=400,
            detail=f"No valid sources found. Errors: {'; '.join(errors[:5])}",
        )

    logger.info(
        f"Bulk source submission received: {len(sources)} sources from {contact_email} "
        f"({len(errors)} rows with errors)"
    )

    # Send email notification
    loop = asyncio.get_event_loop()
    try:
        email_sent = await loop.run_in_executor(
            _email_executor,
            lambda: send_bulk_source_submission_notification(
                contact_email=contact_email,
                sources=sources,
                notes=notes,
            ),
        )

        if not email_sent:
            logger.error(f"Email send returned False for bulk sources from {contact_email}")
            raise HTTPException(
                status_code=503,
                detail="Unable to process your submission right now. Please try again later or contact us directly.",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Email send failed for bulk source submission: {e}")
        raise HTTPException(
            status_code=503,
            detail="Unable to process your submission right now. Please try again later or contact us directly.",
        )

    # Build response message
    message = f"Thank you! Your {len(sources)} source(s) have been submitted for review."
    if errors:
        message += f" Note: {len(errors)} row(s) had validation errors and were skipped."

    return {
        "message": message,
        "success": True,
        "sources_submitted": len(sources),
        "rows_skipped": len(errors),
    }
