from datetime import datetime
from pydantic import BaseModel


class JobBase(BaseModel):
    title: str
    organization: str | None = None
    location: str | None = None
    state: str | None = None
    description: str | None = None
    job_type: str | None = None
    salary_info: str | None = None
    url: str


class JobResponse(JobBase):
    id: int
    first_seen_at: datetime
    last_seen_at: datetime
    is_stale: bool

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class JobFilters(BaseModel):
    """Query parameters for filtering jobs."""
    q: str | None = None  # Search query
    state: str | None = None
    location: str | None = None
    job_type: str | None = None
    page: int = 1
    per_page: int = 20
