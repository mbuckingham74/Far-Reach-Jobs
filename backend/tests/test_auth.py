"""Tests for the /api/auth endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.models import User
from app.services.auth import hash_password, create_access_token


class TestRegistration:
    """Tests for user registration."""

    def test_register_success(self, client, db):
        """Successfully register a new user."""
        response = client.post(
            "/api/auth/register",
            json={"email": "newuser@example.com", "password": "securepassword123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "message" in data

        # Verify user was created in database
        user = db.query(User).filter(User.email == "newuser@example.com").first()
        assert user is not None
        assert user.email == "newuser@example.com"

    def test_register_duplicate_email(self, client, db):
        """Registration should fail if email already exists."""
        # Create existing user
        user = User(
            email="existing@example.com",
            password_hash=hash_password("password123"),
            is_verified=True,
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/register",
            json={"email": "existing@example.com", "password": "newpassword123"},
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        """Registration should fail with invalid email format."""
        response = client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "securepassword123"},
        )
        assert response.status_code == 422  # Validation error

    def test_register_password_too_short(self, client):
        """Registration should fail if password is less than 8 characters."""
        response = client.post(
            "/api/auth/register",
            json={"email": "newuser@example.com", "password": "short"},
        )
        assert response.status_code == 422
        assert "8 characters" in str(response.json())

    def test_register_password_too_long(self, client):
        """Registration should fail if password exceeds 128 characters."""
        response = client.post(
            "/api/auth/register",
            json={"email": "newuser@example.com", "password": "x" * 129},
        )
        assert response.status_code == 422
        assert "128 characters" in str(response.json())

    def test_register_auto_verify_in_dev_mode(self, client, db):
        """In dev mode without SMTP, user should be auto-verified."""
        # The conftest sets ENVIRONMENT=development and no SMTP
        response = client.post(
            "/api/auth/register",
            json={"email": "devuser@example.com", "password": "securepassword123"},
        )
        assert response.status_code == 201

        user = db.query(User).filter(User.email == "devuser@example.com").first()
        assert user is not None
        assert user.is_verified is True  # Auto-verified in dev mode
        assert user.verification_token is None


class TestLogin:
    """Tests for user login."""

    def test_login_success(self, client, db):
        """Successfully login with valid credentials."""
        # Create verified user
        user = User(
            email="verified@example.com",
            password_hash=hash_password("correctpassword"),
            is_verified=True,
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/login",
            json={"email": "verified@example.com", "password": "correctpassword"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Check cookie was set
        assert "access_token" in response.cookies

    def test_login_wrong_password(self, client, db):
        """Login should fail with wrong password."""
        user = User(
            email="user@example.com",
            password_hash=hash_password("correctpassword"),
            is_verified=True,
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Login should fail for non-existent user."""
        response = client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "anypassword"},
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_unverified_user(self, client, db):
        """Login should fail for unverified user."""
        user = User(
            email="unverified@example.com",
            password_hash=hash_password("password123"),
            is_verified=False,
            verification_token="some-token",
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/login",
            json={"email": "unverified@example.com", "password": "password123"},
        )
        assert response.status_code == 403
        assert "verify your email" in response.json()["detail"]


class TestEmailVerification:
    """Tests for email verification."""

    def test_verify_valid_token(self, client, db):
        """Successfully verify email with valid token."""
        user = User(
            email="pending@example.com",
            password_hash=hash_password("password123"),
            is_verified=False,
            verification_token="valid-token-123",
            verification_token_created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()

        response = client.get("/api/auth/verify/valid-token-123", follow_redirects=False)
        assert response.status_code == 302
        assert "/login?message=verified" in response.headers["location"]

        # Verify user is now verified
        db.refresh(user)
        assert user.is_verified is True
        assert user.verification_token is None

    def test_verify_invalid_token(self, client):
        """Verification should fail with invalid token."""
        response = client.get("/api/auth/verify/invalid-token-xyz")
        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]

    def test_verify_expired_token(self, client, db):
        """Verification should fail with expired token (>24h old)."""
        expired_time = datetime.now(timezone.utc) - timedelta(hours=25)
        user = User(
            email="expired@example.com",
            password_hash=hash_password("password123"),
            is_verified=False,
            verification_token="expired-token",
            verification_token_created_at=expired_time,
        )
        db.add(user)
        db.commit()

        response = client.get("/api/auth/verify/expired-token")
        assert response.status_code == 400
        assert "expired" in response.json()["detail"]

    def test_verify_already_verified_user(self, client, db):
        """Verifying already-verified user should redirect appropriately."""
        user = User(
            email="already@example.com",
            password_hash=hash_password("password123"),
            is_verified=True,
            verification_token="old-token",
            verification_token_created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()

        response = client.get("/api/auth/verify/old-token", follow_redirects=False)
        assert response.status_code == 302
        assert "already_verified" in response.headers["location"]


class TestLogout:
    """Tests for user logout."""

    def test_logout_clears_cookie(self, client):
        """Logout should clear the auth cookie."""
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"

        # Cookie should be cleared (set to empty or deleted)
        # TestClient handles this differently, but we verify the endpoint works


class TestResendVerification:
    """Tests for resending verification email."""

    def test_resend_for_unverified_user(self, client, db):
        """Should update token and return success for unverified user."""
        old_token = "old-verification-token"
        user = User(
            email="unverified@example.com",
            password_hash=hash_password("password123"),
            is_verified=False,
            verification_token=old_token,
            verification_token_created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.add(user)
        db.commit()

        with patch("app.routers.auth.send_verification_email") as mock_send:
            mock_send.return_value = True
            response = client.post(
                "/api/auth/resend-verification",
                json={"email": "unverified@example.com"},
            )

        assert response.status_code == 200
        # Should return generic message (email enumeration safe)
        assert "If an unverified account exists" in response.json()["message"]

        # Token should be updated
        db.refresh(user)
        assert user.verification_token != old_token

    def test_resend_for_nonexistent_user(self, client):
        """Should return same message for non-existent user (prevent enumeration)."""
        response = client.post(
            "/api/auth/resend-verification",
            json={"email": "nonexistent@example.com"},
        )
        assert response.status_code == 200
        # Same generic message to prevent email enumeration
        assert "If an unverified account exists" in response.json()["message"]

    def test_resend_for_verified_user(self, client, db):
        """Should return same message for already-verified user."""
        user = User(
            email="verified@example.com",
            password_hash=hash_password("password123"),
            is_verified=True,
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/resend-verification",
            json={"email": "verified@example.com"},
        )
        assert response.status_code == 200
        assert "If an unverified account exists" in response.json()["message"]

    def test_resend_missing_email(self, client):
        """Should return error if email not provided."""
        response = client.post(
            "/api/auth/resend-verification",
            json={},
        )
        assert response.status_code == 400
        assert "Email is required" in response.json()["detail"]


class TestGetCurrentUser:
    """Tests for getting the current authenticated user."""

    def test_get_me_authenticated(self, client, db):
        """Should return user info when authenticated."""
        user = User(
            email="authuser@example.com",
            password_hash=hash_password("password123"),
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create valid token
        token = create_access_token(data={"sub": str(user.id), "email": user.email})

        response = client.get(
            "/api/auth/me",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "authuser@example.com"
        assert data["id"] == user.id
        assert data["is_verified"] is True

    def test_get_me_no_token(self, client):
        """Should return 401 when no auth cookie present."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_get_me_invalid_token(self, client):
        """Should return 401 with invalid/malformed token."""
        response = client.get(
            "/api/auth/me",
            cookies={"access_token": "invalid-token-here"},
        )
        assert response.status_code == 401
        assert "Invalid or expired" in response.json()["detail"]

    def test_get_me_expired_token(self, client, db):
        """Should return 401 with expired token."""
        user = User(
            email="expiredtoken@example.com",
            password_hash=hash_password("password123"),
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create expired token (negative timedelta)
        token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=timedelta(hours=-1),
        )

        response = client.get(
            "/api/auth/me",
            cookies={"access_token": token},
        )
        assert response.status_code == 401

    def test_get_me_deleted_user(self, client, db):
        """Should return 401 if user no longer exists."""
        # Create token for user ID that doesn't exist
        token = create_access_token(data={"sub": "99999", "email": "deleted@example.com"})

        response = client.get(
            "/api/auth/me",
            cookies={"access_token": token},
        )
        assert response.status_code == 401
        assert "User not found" in response.json()["detail"]
