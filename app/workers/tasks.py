from app.workers.celery_worker import celery_app
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.job import Job

import pandas as pd
import os


@celery_app.task
def process_csv(job_id, file_path):

    db = SessionLocal()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()

        if not job:
            return False

        job.status = "processing"
        db.commit()

        # Read CSV
        df = pd.read_csv(file_path)

        # Remove duplicate rows
        df = df.drop_duplicates()

        # Fill missing categories
        if "category" in df.columns:
            df["category"] = df["category"].fillna("Uncategorised")

        # Uppercase status
        if "status" in df.columns:
            df["status"] = df["status"].astype(str).str.upper()

        # Remove currency symbols
        if "amount" in df.columns:
            df["amount"] = (
                df["amount"]
                .astype(str)
                .str.replace("$", "", regex=False)
            )

        # Normalize dates
        if "date" in df.columns:
            df["date"] = pd.to_datetime(
                df["date"],
                errors="coerce"
            ).dt.strftime("%Y-%m-%d")

        # Create processed folder
        os.makedirs("processed", exist_ok=True)

        processed_file = f"processed/cleaned_{job_id}.csv"

        # Save cleaned CSV
        df.to_csv(
            processed_file,
            index=False
        )

        job.status = "completed"
        db.commit()

        return True

    except Exception as e:

        if job:
            job.status = "failed"
            db.commit()

        print(e)
        return False

    finally:
        db.close()