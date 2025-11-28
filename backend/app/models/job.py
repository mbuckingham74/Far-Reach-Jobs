import re

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("scrape_sources.id"), nullable=False)
    external_id = Column(String(255), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    organization = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    state = Column(String(50), nullable=True, index=True)
    description = Column(Text, nullable=True)
    job_type = Column(String(100), nullable=True, index=True)
    salary_info = Column(String(255), nullable=True)
    url = Column(String(1000), nullable=False)
    first_seen_at = Column(DateTime, server_default=func.now())
    last_seen_at = Column(DateTime, server_default=func.now())
    is_stale = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    source = relationship("ScrapeSource", back_populates="jobs")
    saved_by = relationship("SavedJob", back_populates="job", cascade="all, delete-orphan")

    @property
    def display_job_type(self) -> str | None:
        """Return cleaned job type for display.

        Handles specific patterns like "80 Full time" -> "Full-Time".
        Returns the original value for other job types (Contract, etc).
        Returns None for category-style values that aren't employment types.
        """
        if not self.job_type:
            return None

        job_type_lower = self.job_type.lower().strip()

        # Pattern: "80 Full time" or "40 Part time" - hours followed by full/part
        hours_type_match = re.match(r"^(\d+)\s+(full|part)\s*[-\s]?time\s*$", job_type_lower, re.IGNORECASE)
        if hours_type_match:
            employment_type = hours_type_match.group(2).lower()
            if employment_type == "full":
                return "Full-Time"
            else:
                return "Part-Time"

        # Normalize common full-time/part-time variations
        if re.match(r"^full\s*[-\s]?time$", job_type_lower):
            return "Full-Time"
        if re.match(r"^part\s*[-\s]?time$", job_type_lower):
            return "Part-Time"

        # Keep other valid employment types as-is
        valid_types = [
            "contract", "temporary", "temp", "seasonal", "internship",
            "intern", "volunteer", "per diem", "prn", "on-call", "casual",
            "regular", "permanent", "freelance", "consulting"
        ]
        for valid in valid_types:
            if valid in job_type_lower:
                # Return the original with proper casing if it's primarily this type
                return self.job_type.strip()

        # Filter out category-style values that aren't employment types
        # These are job categories, not employment types
        category_keywords = [
            "healthcare", "administrative", "management", "education",
            "clinical", "nursing", "finance", "marketing", "executive",
            "facilities", "maintenance", "support", "program", "open",
            "various", "multiple"
        ]
        for keyword in category_keywords:
            if keyword in job_type_lower:
                return None

        # For anything else, return the original value
        return self.job_type.strip()

    __table_args__ = (
        Index("ix_jobs_stale_last_seen", "is_stale", "last_seen_at"),
        Index("ix_jobs_location", "location"),
    )
