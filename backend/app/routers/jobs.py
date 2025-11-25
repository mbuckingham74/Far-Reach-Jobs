from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_jobs():
    """List jobs with optional filters - To be implemented in Phase 1D."""
    return {"message": "Job listing endpoint - coming soon", "jobs": []}


@router.get("/{job_id}")
async def get_job(job_id: int):
    """Get a single job by ID - To be implemented in Phase 1D."""
    return {"message": "Job detail endpoint - coming soon", "job_id": job_id}
