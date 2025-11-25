from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_saved_jobs():
    """List user's saved jobs - To be implemented in Phase 1E."""
    return {"message": "Saved jobs listing endpoint - coming soon", "saved_jobs": []}


@router.post("/{job_id}")
async def save_job(job_id: int):
    """Save a job - To be implemented in Phase 1E."""
    return {"message": "Save job endpoint - coming soon", "job_id": job_id}


@router.delete("/{job_id}")
async def unsave_job(job_id: int):
    """Unsave a job - To be implemented in Phase 1E."""
    return {"message": "Unsave job endpoint - coming soon", "job_id": job_id}
