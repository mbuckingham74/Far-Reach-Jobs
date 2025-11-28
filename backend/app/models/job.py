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
        """Return normalized job type for display (Full-Time or Part-Time).

        Parses job_type field which may contain hours (e.g., "80 Full time")
        and normalizes to standard format. Jobs with <40 hours are Part-Time.
        """
        if not self.job_type:
            return None

        job_type_lower = self.job_type.lower()

        # Check for explicit part-time
        if "part" in job_type_lower:
            return "Part-Time"

        # Check for explicit full-time
        if "full" in job_type_lower:
            # Check if there's an hours number that indicates part-time
            hours_match = re.search(r"(\d+)", self.job_type)
            if hours_match:
                hours = int(hours_match.group(1))
                # Hours per pay period: 80 = full-time (40hrs/week * 2 weeks)
                # Less than 80 hours per pay period or less than 40 hours/week = part-time
                if hours < 40:
                    return "Part-Time"
            return "Full-Time"

        # If just a number with no full/part indication, try to infer
        hours_match = re.search(r"^(\d+)\s*$", self.job_type.strip())
        if hours_match:
            hours = int(hours_match.group(1))
            if hours >= 40:
                return "Full-Time"
            else:
                return "Part-Time"

        # Return None for non-standard job types (like "Healthcare", "Administrative")
        # These aren't really job types (full/part time) but categories
        return None

    __table_args__ = (
        Index("ix_jobs_stale_last_seen", "is_stale", "last_seen_at"),
        Index("ix_jobs_location", "location"),
    )
