from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

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

router = APIRouter()

COOKIE_NAME = "access_token"


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

    # Create user with hashed password
    verification_token = generate_verification_token()
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        is_verified=False,
        verification_token=verification_token,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send verification email
    email_sent = send_verification_email(user.email, verification_token)
    if not email_sent:
        # Log warning but don't fail - user can request new verification email
        pass

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

    # Set httpOnly cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=True,  # HTTPS only
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

    if user.is_verified:
        return RedirectResponse(url="/login?message=already_verified", status_code=302)

    # Mark user as verified
    user.is_verified = True
    user.verification_token = None
    db.commit()

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
        db.commit()
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
    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user
