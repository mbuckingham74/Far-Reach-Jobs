import re
from pydantic import BaseModel, field_validator, HttpUrl
from typing import Optional


class JobSubmission(BaseModel):
    """Schema for employer job submission form."""
    title: str
    organization: str
    location: str
    state: Optional[str] = None
    description: Optional[str] = None
    job_type: Optional[str] = None
    salary_info: Optional[str] = None
    url: str
    contact_email: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Job title must be at least 3 characters")
        if len(v) > 500:
            raise ValueError("Job title must be less than 500 characters")
        return v

    @field_validator("organization")
    @classmethod
    def validate_organization(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Organization name must be at least 2 characters")
        if len(v) > 255:
            raise ValueError("Organization name must be less than 255 characters")
        return v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Location must be at least 2 characters")
        if len(v) > 255:
            raise ValueError("Location must be less than 255 characters")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        # Basic URL validation - must start with http:// or https://
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        # Block common injection patterns
        dangerous_patterns = [
            r"['\";]",  # SQL injection chars
            r"<script",  # XSS
            r"javascript:",  # JS injection
            r"data:",  # Data URLs
            r"\s",  # No whitespace in URLs
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("URL contains invalid characters")
        if len(v) > 1000:
            raise ValueError("URL must be less than 1000 characters")
        return v

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, v: str) -> str:
        v = v.strip().lower()
        # Basic email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email address")
        if len(v) > 255:
            raise ValueError("Email must be less than 255 characters")
        return v

    @field_validator("description", "job_type", "salary_info", "state", mode="before")
    @classmethod
    def strip_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class CareersPageSubmission(BaseModel):
    """Schema for employer careers page URL submission."""
    organization: str
    careers_url: str
    contact_email: str
    notes: Optional[str] = None

    @field_validator("organization")
    @classmethod
    def validate_organization(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Organization name must be at least 2 characters")
        if len(v) > 255:
            raise ValueError("Organization name must be less than 255 characters")
        return v

    @field_validator("careers_url")
    @classmethod
    def validate_careers_url(cls, v: str) -> str:
        v = v.strip()
        # Basic URL validation - must start with http:// or https://
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        # Block common injection patterns
        dangerous_patterns = [
            r"['\";]",  # SQL injection chars
            r"<script",  # XSS
            r"javascript:",  # JS injection
            r"data:",  # Data URLs
            r"\s",  # No whitespace in URLs
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("URL contains invalid characters")
        if len(v) > 1000:
            raise ValueError("URL must be less than 1000 characters")
        return v

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, v: str) -> str:
        v = v.strip().lower()
        # Basic email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email address")
        if len(v) > 255:
            raise ValueError("Email must be less than 255 characters")
        return v

    @field_validator("notes", mode="before")
    @classmethod
    def strip_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 2000:
            raise ValueError("Notes must be less than 2000 characters")
        return v if v else None
