import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


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
        logger.info(f"Verification email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
