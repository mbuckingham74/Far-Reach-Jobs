from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ScrapeSource(Base):
    __tablename__ = "scrape_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    base_url = Column(String(1000), nullable=False)
    scraper_class = Column(String(255), nullable=False, default="GenericScraper")
    is_active = Column(Boolean, default=True)
    last_scraped_at = Column(DateTime, nullable=True)
    last_scrape_success = Column(Boolean, nullable=True)  # True=success, False=fail, None=never run
    created_at = Column(DateTime, server_default=func.now())

    # GenericScraper configuration - CSS selectors for parsing job listings
    # The listing_url is the page containing job listings (can be same as base_url)
    listing_url = Column(String(1000), nullable=True)
    # CSS selector for individual job containers (e.g., ".job-card", "tr.job-row")
    selector_job_container = Column(String(500), nullable=True)
    # CSS selectors for fields within each job container
    selector_title = Column(String(500), nullable=True)
    selector_url = Column(String(500), nullable=True)
    selector_organization = Column(String(500), nullable=True)
    selector_location = Column(String(500), nullable=True)
    selector_job_type = Column(String(500), nullable=True)
    selector_salary = Column(String(500), nullable=True)
    selector_description = Column(String(500), nullable=True)
    # Optional: attribute to extract URL from (default: "href")
    url_attribute = Column(String(100), nullable=True, default="href")
    # Optional: pagination selector for multi-page listings
    selector_next_page = Column(String(500), nullable=True)
    # Optional: max pages to scrape (default: 10)
    max_pages = Column(Integer, nullable=True, default=10)

    jobs = relationship("Job", back_populates="source", cascade="all, delete-orphan")
