from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ScrapeLog(Base):
    """Log of individual scrape runs for tracking history and metrics."""
    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("scrape_sources.id", ondelete="SET NULL"), nullable=True)
    source_name = Column(String(255), nullable=False)  # Preserved even if source deleted

    # Run metadata
    trigger_type = Column(String(50), nullable=False)  # "manual" or "scheduled"
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, server_default=func.now())
    duration_seconds = Column(Integer, nullable=True)

    # Results
    success = Column(Boolean, default=True)
    jobs_found = Column(Integer, default=0)
    jobs_added = Column(Integer, default=0)
    jobs_updated = Column(Integer, default=0)
    jobs_removed = Column(Integer, default=0)  # For future stale job cleanup tracking
    errors = Column(Text, nullable=True)  # JSON array of error messages

    # Relationships
    source = relationship("ScrapeSource", backref="scrape_logs")
