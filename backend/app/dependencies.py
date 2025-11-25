from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth import decode_access_token

COOKIE_NAME = "access_token"


def get_optional_current_user(request: Request, db: Session = None) -> User | None:
    """Get the current user if authenticated, None otherwise.

    This is useful for pages that show different content based on auth status.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    # Get DB session if not provided
    if db is None:
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()
            return user
        finally:
            db.close()

    return db.query(User).filter(User.id == int(user_id)).first()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get the current authenticated user. Raises 401 if not authenticated.

    Use this as a dependency for protected routes.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
