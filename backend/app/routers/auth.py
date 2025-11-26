import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse, LoginRequest, TokenResponse, MessageResponse
from app.services import (
    hash_password,
    verify_password,
    create_access_token,
    generate_verification_token,
    send_verification_email,
)

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

COOKIE_NAME = "access_token"
VERIFICATION_TOKEN_EXPIRY_HOURS = 24


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and send verification email."""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if SMTP is configured - if not in dev, auto-verify
    smtp_configured = bool(settings.smtp_user and settings.smtp_password)
    auto_verify = not smtp_configured and settings.environment == "development"

    # Create user with hashed password
    verification_token = None if auto_verify else generate_verification_token()
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        is_verified=auto_verify,
        verification_token=verification_token,
        verification_token_created_at=None if auto_verify else datetime.now(timezone.utc),
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.exception("Failed to create user account for %s", user_data.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create account. Please try again later."
        )

    if auto_verify:
        return MessageResponse(
            message="Registration successful. You can now log in. (Dev mode: auto-verified)"
        )

    # Send verification email
    email_sent = send_verification_email(user.email, verification_token)
    if not email_sent:
        logger.warning(
            "Failed to send verification email to %s - user can request resend",
            user.email,
        )
        return MessageResponse(
            message="Registration successful, but we couldn't send the verification email. "
                    "Please use 'Resend verification email' on the login page."
        )

    return MessageResponse(
        message="Registration successful. Please check your email to verify your account."
    )


@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login and receive JWT token (also set as httpOnly cookie)."""
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in"
        )

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    # Set httpOnly cookie - secure only in production (HTTPS)
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=60 * 60 * 24,  # 24 hours
    )

    return TokenResponse(access_token=access_token)


@router.get("/verify/{token}")
def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify email address using the token sent via email."""
    user = db.query(User).filter(User.verification_token == token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    # Check token expiry
    if user.verification_token_created_at:
        from datetime import timedelta
        expiry_time = user.verification_token_created_at + timedelta(hours=VERIFICATION_TOKEN_EXPIRY_HOURS)
        if datetime.now(timezone.utc) > expiry_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token has expired. Please request a new one."
            )

    if user.is_verified:
        return RedirectResponse(url="/login?message=already_verified", status_code=302)

    # Mark user as verified
    user.is_verified = True
    user.verification_token = None
    user.verification_token_created_at = None
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to verify user %s", user.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to verify account. Please try again later."
        )

    return RedirectResponse(url="/login?message=verified", status_code=302)


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    """Logout by clearing the auth cookie."""
    response.delete_cookie(key=COOKIE_NAME)
    return MessageResponse(message="Successfully logged out")


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(email_data: dict, db: Session = Depends(get_db)):
    """Resend verification email if user exists and is not verified."""
    email = email_data.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )

    user = db.query(User).filter(User.email == email).first()

    # Always return success to prevent email enumeration
    if user and not user.is_verified:
        verification_token = generate_verification_token()
        user.verification_token = verification_token
        user.verification_token_created_at = datetime.now(timezone.utc)
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to update verification token for %s", user.email)
            # Return generic message to prevent email enumeration
            return MessageResponse(
                message="If an unverified account exists with this email, a verification link has been sent."
            )
        send_verification_email(user.email, verification_token)

    return MessageResponse(
        message="If an unverified account exists with this email, a verification link has been sent."
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Get the currently authenticated user."""
    from app.services.auth import decode_access_token

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = payload.get("sub")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = db.query(User).filter(User.id == user_id_int).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user
