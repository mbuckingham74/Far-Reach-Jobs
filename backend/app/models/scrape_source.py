from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ScrapeSource(Base):
    __tablename__ = "scrape_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    base_url = Column(String(1000), nullable=False)
    scraper_class = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    last_scraped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    jobs = relationship("Job", back_populates="source")
