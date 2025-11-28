import html
import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class ScrapeNotificationData:
    """Data for scrape notification email."""
    execution_time: datetime
    trigger_type: str  # "manual" or "scheduled"
    duration_seconds: float
    sources_processed: int
    jobs_added: int
    jobs_updated: int
    jobs_removed: int
    errors: list[tuple[str, str]]  # List of (url/source, error_message)


def send_verification_email(to_email: str, verification_token: str) -> bool:
    """Send an email verification link to the user.

    Returns True if email was sent successfully, False otherwise.
    """
    verification_url = f"{settings.app_url}/api/auth/verify/{verification_token}"

    subject = "Verify your Far Reach Jobs account"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{
                display: inline-block;
                padding: 12px 24px;
                background-color: #2b6cb0;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                margin: 20px 0;
            }}
            .footer {{ color: #666; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Welcome to Far Reach Jobs!</h1>
            <p>Thank you for registering. Please verify your email address to complete your registration.</p>
            <a href="{verification_url}" class="button">Verify Email Address</a>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all;">{verification_url}</p>
            <p>This link will expire in 24 hours.</p>
            <div class="footer">
                <p>If you didn't create an account with Far Reach Jobs, you can safely ignore this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Welcome to Far Reach Jobs!

    Thank you for registering. Please verify your email address by clicking the link below:

    {verification_url}

    This link will expire in 24 hours.

    If you didn't create an account with Far Reach Jobs, you can safely ignore this email.
    """

    return _send_email(to_email, subject, html_body, text_body)


def _send_email(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Send an email via SMTP. Returns True on success."""
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("SMTP credentials not configured, skipping email send")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.from_email or settings.smtp_user
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info(f"Email sent to {to_email}: {subject[:50]}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_scrape_notification(data: ScrapeNotificationData) -> bool:
    """Send a scrape run notification email to the admin.

    Returns True if email was sent successfully, False otherwise.
    """
    if not settings.admin_email:
        logger.debug("No admin_email configured, skipping scrape notification")
        return False

    # Format duration nicely
    minutes, seconds = divmod(int(data.duration_seconds), 60)
    if minutes > 0:
        duration_str = f"{minutes}m {seconds}s"
    else:
        duration_str = f"{seconds}s"

    # Determine success/failure status
    has_errors = len(data.errors) > 0
    status_emoji = "⚠️" if has_errors else "✅"
    status_text = "Completed with Errors" if has_errors else "Completed Successfully"

    subject = f"{status_emoji} Far Reach Jobs Scrape: {status_text}"

    # Build the errors table HTML
    errors_html = ""
    errors_text = ""
    if data.errors:
        error_rows = ""
        for source, error in data.errors:
            # Escape HTML in error messages (handles <, >, &, quotes)
            safe_source = html.escape(source)
            safe_error = html.escape(error)
            error_rows += f"""
                <tr>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-size: 13px; word-break: break-word;">{safe_source}</td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-size: 13px; color: #c53030; word-break: break-word;">{safe_error}</td>
                </tr>
            """
            errors_text += f"  - {source}: {error}\n"

        errors_html = f"""
            <h2 style="color: #c53030; margin-top: 30px; margin-bottom: 15px; font-size: 18px;">Errors ({len(data.errors)})</h2>
            <table style="width: 100%; border-collapse: collapse; background: #fff5f5; border-radius: 8px; overflow: hidden;">
                <thead>
                    <tr style="background: #fed7d7;">
                        <th style="padding: 10px 12px; text-align: left; font-weight: 600; font-size: 13px;">Source/URL</th>
                        <th style="padding: 10px 12px; text-align: left; font-weight: 600; font-size: 13px;">Error</th>
                    </tr>
                </thead>
                <tbody>
                    {error_rows}
                </tbody>
            </table>
        """
        errors_text = f"\nErrors ({len(data.errors)}):\n{errors_text}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f7fafc; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 30px; }}
            h1 {{ color: #2d3748; margin-top: 0; font-size: 24px; }}
            .status {{ display: inline-block; padding: 6px 12px; border-radius: 4px; font-weight: 600; margin-bottom: 20px; }}
            .status.success {{ background: #c6f6d5; color: #276749; }}
            .status.warning {{ background: #feebc8; color: #c05621; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            .summary-table td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }}
            .summary-table td:first-child {{ font-weight: 600; color: #4a5568; width: 50%; }}
            .summary-table td:last-child {{ color: #2d3748; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Scrape Run Report</h1>
            <div class="status {'warning' if has_errors else 'success'}">{status_emoji} {status_text}</div>

            <h2 style="color: #4a5568; margin-top: 25px; margin-bottom: 15px; font-size: 18px;">Summary</h2>
            <table class="summary-table" style="background: #f7fafc; border-radius: 8px; overflow: hidden;">
                <tr>
                    <td>Execution Time</td>
                    <td>{data.execution_time.strftime("%Y-%m-%d %H:%M:%S UTC")}</td>
                </tr>
                <tr>
                    <td>Trigger Type</td>
                    <td style="text-transform: capitalize;">{data.trigger_type}</td>
                </tr>
                <tr>
                    <td>Duration</td>
                    <td>{duration_str}</td>
                </tr>
                <tr>
                    <td>Sources Processed</td>
                    <td>{data.sources_processed}</td>
                </tr>
                <tr>
                    <td>Jobs Added</td>
                    <td style="color: #276749; font-weight: 600;">{data.jobs_added}</td>
                </tr>
                <tr>
                    <td>Jobs Updated</td>
                    <td>{data.jobs_updated}</td>
                </tr>
                <tr>
                    <td>Jobs Removed (Stale)</td>
                    <td style="color: #c53030;">{data.jobs_removed}</td>
                </tr>
            </table>

            {errors_html}

            <div class="footer">
                <p>This is an automated notification from Far Reach Jobs.</p>
                <p><a href="{settings.app_url}/admin/history" style="color: #2b6cb0;">View full scrape history</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
Far Reach Jobs - Scrape Run Report
==================================

Status: {status_text}

Summary:
  - Execution Time: {data.execution_time.strftime("%Y-%m-%d %H:%M:%S UTC")}
  - Trigger Type: {data.trigger_type.capitalize()}
  - Duration: {duration_str}
  - Sources Processed: {data.sources_processed}
  - Jobs Added: {data.jobs_added}
  - Jobs Updated: {data.jobs_updated}
  - Jobs Removed (Stale): {data.jobs_removed}
{errors_text}
---
View full scrape history: {settings.app_url}/admin/history
"""

    return _send_email(settings.admin_email, subject, html_body, text_body)


def send_job_submission_notification(
    title: str,
    organization: str,
    location: str,
    url: str,
    contact_email: str,
    state: str | None = None,
    description: str | None = None,
    job_type: str | None = None,
    salary_info: str | None = None,
) -> bool:
    """Send notification to admin about a new job submission from an employer.

    Returns True if email was sent successfully, False otherwise.
    """
    if not settings.admin_email:
        logger.debug("No admin_email configured, skipping job submission notification")
        return False

    # Escape all user input for HTML
    safe_title = html.escape(title)
    safe_org = html.escape(organization)
    safe_location = html.escape(location)
    safe_url = html.escape(url)
    safe_email = html.escape(contact_email)
    safe_state = html.escape(state) if state else "Not specified"
    safe_description = html.escape(description) if description else "Not provided"
    safe_job_type = html.escape(job_type) if job_type else "Not specified"
    safe_salary = html.escape(salary_info) if salary_info else "Not specified"

    subject = f"New Job Submission: {safe_title} at {safe_org}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f7fafc; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 30px; }}
            h1 {{ color: #2d3748; margin-top: 0; font-size: 24px; }}
            .badge {{ display: inline-block; padding: 6px 12px; border-radius: 4px; font-weight: 600; margin-bottom: 20px; background: #bee3f8; color: #2b6cb0; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            .info-table td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
            .info-table td:first-child {{ font-weight: 600; color: #4a5568; width: 30%; }}
            .info-table td:last-child {{ color: #2d3748; }}
            .description {{ background: #f7fafc; padding: 15px; border-radius: 6px; margin-top: 20px; }}
            .description h3 {{ margin-top: 0; color: #4a5568; font-size: 14px; }}
            .description p {{ margin-bottom: 0; color: #2d3748; white-space: pre-wrap; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 12px; }}
            .button {{ display: inline-block; padding: 10px 20px; background: #2b6cb0; color: white; text-decoration: none; border-radius: 4px; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>New Job Submission</h1>
            <div class="badge">Requires Review</div>

            <table class="info-table" style="background: #f7fafc; border-radius: 8px; overflow: hidden;">
                <tr>
                    <td>Job Title</td>
                    <td><strong>{safe_title}</strong></td>
                </tr>
                <tr>
                    <td>Organization</td>
                    <td>{safe_org}</td>
                </tr>
                <tr>
                    <td>Location</td>
                    <td>{safe_location}</td>
                </tr>
                <tr>
                    <td>State</td>
                    <td>{safe_state}</td>
                </tr>
                <tr>
                    <td>Job Type</td>
                    <td>{safe_job_type}</td>
                </tr>
                <tr>
                    <td>Salary</td>
                    <td>{safe_salary}</td>
                </tr>
                <tr>
                    <td>Job URL</td>
                    <td><a href="{safe_url}" style="color: #2b6cb0;">{safe_url}</a></td>
                </tr>
                <tr>
                    <td>Contact Email</td>
                    <td><a href="mailto:{safe_email}" style="color: #2b6cb0;">{safe_email}</a></td>
                </tr>
            </table>

            <div class="description">
                <h3>Description</h3>
                <p>{safe_description}</p>
            </div>

            <a href="{settings.app_url}/admin" class="button">Go to Admin Panel</a>

            <div class="footer">
                <p>This job was submitted through the For Employers form on Far Reach Jobs.</p>
                <p>To add this job, create a new scrape source or manually add it to the database.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
New Job Submission - Far Reach Jobs
===================================

Job Title: {title}
Organization: {organization}
Location: {location}
State: {state or 'Not specified'}
Job Type: {job_type or 'Not specified'}
Salary: {salary_info or 'Not specified'}
Job URL: {url}
Contact Email: {contact_email}

Description:
{description or 'Not provided'}

---
This job was submitted through the For Employers form.
Admin Panel: {settings.app_url}/admin
"""

    return _send_email(settings.admin_email, subject, html_body, text_body)


def send_careers_page_submission_notification(
    organization: str,
    careers_url: str,
    contact_email: str,
    notes: str | None = None,
) -> bool:
    """Send notification to admin about a careers page URL submission.

    Returns True if email was sent successfully, False otherwise.
    """
    if not settings.admin_email:
        logger.debug("No admin_email configured, skipping careers page notification")
        return False

    # Escape all user input for HTML
    safe_org = html.escape(organization)
    safe_url = html.escape(careers_url)
    safe_email = html.escape(contact_email)
    safe_notes = html.escape(notes) if notes else "None provided"

    subject = f"New Careers Page Submission: {safe_org}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f7fafc; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 30px; }}
            h1 {{ color: #2d3748; margin-top: 0; font-size: 24px; }}
            .badge {{ display: inline-block; padding: 6px 12px; border-radius: 4px; font-weight: 600; margin-bottom: 20px; background: #c6f6d5; color: #276749; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            .info-table td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
            .info-table td:first-child {{ font-weight: 600; color: #4a5568; width: 30%; }}
            .info-table td:last-child {{ color: #2d3748; }}
            .notes {{ background: #f7fafc; padding: 15px; border-radius: 6px; margin-top: 20px; }}
            .notes h3 {{ margin-top: 0; color: #4a5568; font-size: 14px; }}
            .notes p {{ margin-bottom: 0; color: #2d3748; white-space: pre-wrap; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 12px; }}
            .button {{ display: inline-block; padding: 10px 20px; background: #2b6cb0; color: white; text-decoration: none; border-radius: 4px; margin-top: 15px; margin-right: 10px; }}
            .button.secondary {{ background: #718096; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>New Careers Page Submission</h1>
            <div class="badge">New Source Request</div>

            <p style="color: #4a5568; margin-bottom: 20px;">
                An employer has submitted their careers page URL to be added as a scrape source.
            </p>

            <table class="info-table" style="background: #f7fafc; border-radius: 8px; overflow: hidden;">
                <tr>
                    <td>Organization</td>
                    <td><strong>{safe_org}</strong></td>
                </tr>
                <tr>
                    <td>Careers Page URL</td>
                    <td><a href="{safe_url}" style="color: #2b6cb0;">{safe_url}</a></td>
                </tr>
                <tr>
                    <td>Contact Email</td>
                    <td><a href="mailto:{safe_email}" style="color: #2b6cb0;">{safe_email}</a></td>
                </tr>
            </table>

            <div class="notes">
                <h3>Additional Notes</h3>
                <p>{safe_notes}</p>
            </div>

            <a href="{safe_url}" class="button">Visit Careers Page</a>
            <a href="{settings.app_url}/admin" class="button secondary">Go to Admin Panel</a>

            <div class="footer">
                <p>This careers page was submitted through the For Employers form on Far Reach Jobs.</p>
                <p>Next steps: Visit the careers page, add it as a scrape source, and configure the selectors.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
New Careers Page Submission - Far Reach Jobs
=============================================

Organization: {organization}
Careers Page URL: {careers_url}
Contact Email: {contact_email}

Additional Notes:
{notes or 'None provided'}

---
This careers page was submitted through the For Employers form.

Next steps:
1. Visit the careers page
2. Add it as a scrape source in the admin panel
3. Configure the CSS selectors

Admin Panel: {settings.app_url}/admin
"""

    return _send_email(settings.admin_email, subject, html_body, text_body)
