import os
import uuid

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.job import Job
from app.workers.tasks import process_csv

router = APIRouter()

UPLOAD_DIR = "uploads"


@router.post("/jobs/upload")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Create uploads directory if it doesn't exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}_{file.filename}"

    # Save file
    file_path = os.path.join(
        UPLOAD_DIR,
        unique_filename
    )

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Create job record
    job = Job(
        filename=unique_filename,
        status="pending"
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # Send task to Celery
    process_csv.delay(
        job.id,
        file_path
    )

    return {
        "job_id": job.id,
        "filename": unique_filename,
        "status": job.status
    }


@router.get("/jobs/{job_id}")
def get_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return {
        "job_id": job.id,
        "filename": job.filename,
        "status": job.status
    }