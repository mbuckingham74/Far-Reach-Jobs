import re
from pydantic import BaseModel, field_validator
from typing import Optional, List


class BulkSourceEntry(BaseModel):
    """Single entry in a bulk source submission."""
    organization: str
    base_url: str
    careers_url: Optional[str] = None

    @field_validator("organization")
    @classmethod
    def validate_organization(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Organization name must be at least 2 characters")
        if len(v) > 255:
            raise ValueError("Organization name must be less than 255 characters")
        # Block HTML/script injection
        if re.search(r"<[^>]+>", v):
            raise ValueError("Organization name contains invalid characters")
        return v

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
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

    @field_validator("careers_url", mode="before")
    @classmethod
    def validate_careers_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("Careers URL must start with http:// or https://")
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


class BulkSourceSubmission(BaseModel):
    """Schema for employer bulk source submission via CSV."""
    contact_email: str
    sources: List[BulkSourceEntry]
    notes: Optional[str] = None

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, v: str) -> str:
        v = v.strip().lower()
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email address")
        if len(v) > 255:
            raise ValueError("Email must be less than 255 characters")
        return v

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v: List[BulkSourceEntry]) -> List[BulkSourceEntry]:
        if len(v) == 0:
            raise ValueError("At least one source is required")
        if len(v) > 100:
            raise ValueError("Maximum 100 sources per submission")
        return v

    @field_validator("notes", mode="before")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) > 2000:
            raise ValueError("Notes must be less than 2000 characters")
        return v


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

    @field_validator("state", mode="before")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) > 50:
            raise ValueError("State must be less than 50 characters")
        return v

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) > 5000:
            raise ValueError("Description must be less than 5000 characters")
        return v

    @field_validator("job_type", mode="before")
    @classmethod
    def validate_job_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) > 100:
            raise ValueError("Job type must be less than 100 characters")
        return v

    @field_validator("salary_info", mode="before")
    @classmethod
    def validate_salary_info(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) > 255:
            raise ValueError("Salary info must be less than 255 characters")
        return v


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
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) > 2000:
            raise ValueError("Notes must be less than 2000 characters")
        return v
