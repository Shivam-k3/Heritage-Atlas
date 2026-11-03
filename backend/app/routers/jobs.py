"""Background job status."""

from fastapi import APIRouter, HTTPException

from ..db import connect
from ..repositories import images as images_repo
from ..schemas import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int) -> dict:
    with connect() as conn:
        job = images_repo.get_job(conn, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job
