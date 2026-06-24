import os
import uuid

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.job import Job
from app.workers.tasks import process_csv

from app.models.transaction import Transaction
from app.models.job_summary import JobSummary

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


@router.get("/jobs/{job_id}/status")
def get_job_status(
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

    response = {
        "job_id": job.id,
        "filename": job.filename,
        "status": job.status,
        "row_count_raw": job.row_count_raw,
        "row_count_clean": job.row_count_clean,
        "created_at": job.created_at,
        "completed_at": job.completed_at
    }

    if job.status == "completed":

        summary = (
            db.query(JobSummary)
            .filter(
                JobSummary.job_id == job.id
            )
            .first()
        )

        if summary:

            response["summary"] = {
                "total_spend_inr":
                    summary.total_spend_inr,

                "total_spend_usd":
                    summary.total_spend_usd,

                "anomaly_count":
                    summary.anomaly_count,

                "risk_level":
                    summary.risk_level
            }

    return response

@router.get("/jobs")
def list_jobs(
    status: str = None,
    db: Session = Depends(get_db)
):

    query = db.query(Job)

    if status:
        query = query.filter(
            Job.status == status
        )

    jobs = query.all()

    return [
        {
            "id": job.id,
            "filename": job.filename,
            "status": job.status,
            "row_count_raw": job.row_count_raw,
            "row_count_clean": job.row_count_clean,
            "created_at": job.created_at
        }
        for job in jobs
    ]

@router.get("/jobs/{job_id}/results")
def get_results(
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

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.job_id == job_id
        )
        .all()
    )

    anomalies = (
        db.query(Transaction)
        .filter(
            Transaction.job_id == job_id,
            Transaction.is_anomaly == True
        )
        .all()
    )

    summary = (
        db.query(JobSummary)
        .filter(
            JobSummary.job_id == job_id
        )
        .first()
    )

    category_breakdown = {}

    for tx in transactions:

        category = (
            tx.llm_category
            if tx.llm_category
            else tx.category
        )

        category_breakdown.setdefault(
            category,
            0
        )

        category_breakdown[category] += (
            tx.amount or 0
        )

    return {

        "job": {
            "id": job.id,
            "filename": job.filename,
            "status": job.status
        },

        "summary": {
            "total_spend_inr":
                summary.total_spend_inr
                if summary else 0,

            "total_spend_usd":
                summary.total_spend_usd
                if summary else 0,

            "top_merchants":
                summary.top_merchants
                if summary else [],

            "anomaly_count":
                summary.anomaly_count
                if summary else 0,

            "narrative":
                summary.narrative
                if summary else "",

            "risk_level":
                summary.risk_level
                if summary else ""
        },

        "category_breakdown":
            category_breakdown,

        "anomalies": [
            {
                "txn_id": tx.txn_id,
                "merchant": tx.merchant,
                "amount": tx.amount,
                "reason": tx.anomaly_reason
            }
            for tx in anomalies
        ],

        "transactions": [
            {
                "txn_id": tx.txn_id,
                "merchant": tx.merchant,
                "amount": tx.amount,
                "category":
                    tx.llm_category
                    if tx.llm_category
                    else tx.category
            }
            for tx in transactions
        ]
    }


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

from fastapi.responses import StreamingResponse
from io import StringIO
import csv

@router.get("/jobs/{job_id}/anomalies/download")
def download_anomalies_csv(
    job_id: int,
    db: Session = Depends(get_db)
):

    anomalies = (
        db.query(Transaction)
        .filter(
            Transaction.job_id == job_id,
            Transaction.is_anomaly == True
        )
        .all()
    )

    if not anomalies:
        raise HTTPException(
            status_code=404,
            detail="No anomalies found"
        )

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "txn_id",
        "merchant",
        "amount",
        "currency",
        "anomaly_reason"
    ])

    for tx in anomalies:

        writer.writerow([
            tx.txn_id,
            tx.merchant,
            tx.amount,
            tx.currency,
            tx.anomaly_reason
        ])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition":
            f"attachment; filename=anomalies_job_{job_id}.csv"
        }
    )