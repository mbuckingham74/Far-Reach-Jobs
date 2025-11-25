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

    __table_args__ = (
        Index("ix_jobs_stale_last_seen", "is_stale", "last_seen_at"),
        Index("ix_jobs_location", "location"),
    )
