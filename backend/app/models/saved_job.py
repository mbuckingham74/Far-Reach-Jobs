from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    saved_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="saved_jobs")
    job = relationship("Job", back_populates="saved_by")

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job"),
    )
