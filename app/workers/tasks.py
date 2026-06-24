from app.workers.celery_worker import celery_app

from datetime import datetime

from app.database.database import SessionLocal
from app.models.job import Job
from app.models.transaction import Transaction

import pandas as pd
import os

import json
import time

from app.models.job_summary import JobSummary

from app.services.gemini_service import (
    classify_transactions,
    generate_summary
)

@celery_app.task
def process_csv(job_id, file_path):

    db = SessionLocal()

    try:

        job = db.query(Job).filter(
            Job.id == job_id
        ).first()

        if not job:
            return False

        job.status = "processing"
        db.commit()

        # --------------------
        # READ CSV
        # --------------------

        df = pd.read_csv(file_path)

        raw_count = len(df)

        # --------------------
        # CLEANING
        # --------------------

        df = df.drop_duplicates()

        if "category" in df.columns:

            df["category"] = (
                df["category"]
                .fillna("")
                .replace("", "Uncategorised")
            )

        if "status" in df.columns:

            df["status"] = (
                df["status"]
                .astype(str)
                .str.upper()
            )

        if "currency" in df.columns:

            df["currency"] = (
                df["currency"]
                .astype(str)
                .str.upper()
            )

        if "amount" in df.columns:

            df["amount"] = (
                df["amount"]
                .astype(str)
                .str.replace("$", "", regex=False)
            )

            df["amount"] = pd.to_numeric(
                df["amount"],
                errors="coerce"
            ).fillna(0)

        if "date" in df.columns:

            df["date"] = pd.to_datetime(
                df["date"],
                errors="coerce"
            ).dt.strftime("%Y-%m-%d")

        clean_count = len(df)

        # --------------------
        # SAVE CLEANED FILE
        # --------------------

        os.makedirs(
            "/app/processed",
            exist_ok=True
        )

        processed_file = (
            f"/app/processed/cleaned_{job_id}.csv"
        )

        df.to_csv(
            processed_file,
            index=False
        )

        # --------------------
        # ANOMALY DETECTION
        # --------------------

        account_medians = (
            df.groupby("account_id")["amount"]
            .median()
            .to_dict()
        )

        domestic_brands = [
            "swiggy",
            "ola",
            "irctc"
        ]

        # --------------------
        # STORE TRANSACTIONS
        # --------------------

        for _, row in df.iterrows():

            median_amount = account_medians.get(
                row["account_id"],
                0
            )

            is_anomaly = False
            anomaly_reason = None

            if row["amount"] > (3 * median_amount):

                is_anomaly = True

                anomaly_reason = (
                    "Amount exceeds 3x account median"
                )
                
            merchant = str(row.get("merchant", "")).strip().lower()

            if (
                str(row.get("currency", "")).upper() == "USD"
                and merchant in domestic_brands
            ):

                is_anomaly = True

                if anomaly_reason:

                    anomaly_reason += (
                        ", Domestic brand with USD"
                    )

                else:

                    anomaly_reason = (
                        "Domestic brand with USD"
                    )

            transaction = Transaction(

                job_id=job.id,

                txn_id=str(
                    row.get("txn_id", "")
                ),

                date=str(
                    row.get("date", "")
                ),

                merchant=str(
                    row.get("merchant", "")
                ),

                amount=float(
                    row.get("amount", 0)
                ),

                currency=str(
                    row.get("currency", "")
                ),

                status=str(
                    row.get("status", "")
                ),

                category=str(
                    row.get("category", "")
                ),

                account_id=str(
                    row.get("account_id", "")
                ),

                notes=str(
                    row.get("notes", "")
                ),

                is_anomaly=is_anomaly,

                anomaly_reason=anomaly_reason
            )

            db.add(transaction)

        db.commit()

        # --------------------
        # LLM CLASSIFICATION
        # --------------------

        uncategorised = (
            db.query(Transaction)
            .filter(
                Transaction.job_id == job.id,
                Transaction.category == "Uncategorised"
            )
            .all()
        )

        if uncategorised:

            batch = []

            for tx in uncategorised:

                batch.append({
                    "id": tx.id,
                    "merchant": tx.merchant,
                    "notes": tx.notes
                })

            response_text = None

            for attempt in range(3):

                try:

                    response_text = (
                        classify_transactions(
                            batch
                        )
                    )

                    break

                except Exception as e:

                    print(
                        f"CLASSIFICATION ATTEMPT {attempt+1} FAILED:"
                    )

                    print(e)

                    time.sleep(
                        2 ** attempt
                    )

            if response_text:

                try:

                    response_text = (
                        response_text
                        .replace(
                            "```json",
                            ""
                        )
                        .replace(
                            "```",
                            ""
                        )
                        .strip()
                    )

                    print("RAW CLASSIFICATION RESPONSE")
                    print(response_text)
                    data = json.loads(
                        response_text
                    )

                    for item in data:

                        tx = (
                            db.query(Transaction)
                            .filter(
                                Transaction.id
                                == item["id"]
                            )
                            .first()
                        )

                        if tx:

                            tx.llm_category = (
                                item["category"]
                            )

                            tx.llm_raw_response = (
                                response_text
                            )

                    db.commit()

                except Exception as e:

                    print("CLASSIFICATION JSON ERROR")

                    print(response_text)

                    print(e)

                    for tx in uncategorised:

                        tx.llm_failed = True

                    db.commit()

            else:

                for tx in uncategorised:

                    tx.llm_failed = True

                db.commit()

        # --------------------
        # SUMMARY DATA
        # --------------------

        anomaly_count = (
            db.query(Transaction)
            .filter(
                Transaction.job_id == job.id,
                Transaction.is_anomaly == True
            )
            .count()
        )

        total_inr = float(
            df[
                df["currency"] == "INR"
            ]["amount"].sum()
        )

        total_usd = float(
            df[
                df["currency"] == "USD"
            ]["amount"].sum()
        )

        top_merchants = (
            df["merchant"]
            .value_counts()
            .head(3)
            .index
            .tolist()
        )

        summary_response = None

        for attempt in range(3):

            try:

                summary_response = generate_summary(
                    {
                        "total_spend_inr": total_inr,
                        "total_spend_usd": total_usd,
                        "top_merchants": top_merchants,
                        "anomaly_count": anomaly_count
                    }
                )

                break

            
            except Exception as e:

                print(
                    f"SUMMARY ATTEMPT {attempt+1} FAILED:"
                )

                print(e)

                time.sleep(
                    2 ** attempt
                )

        if not summary_response:

            job.completed_at = datetime.utcnow()
            
            job.status = "completed"

            db.commit()

            return True

        summary_response = (
            summary_response
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        print("RAW SUMMARY RESPONSE")
        print(summary_response)
        summary_json = json.loads(
            summary_response
        )

        job_summary = JobSummary(

            job_id=job.id,

            total_spend_inr=
            summary_json["total_spend_inr"],

            total_spend_usd=
            summary_json["total_spend_usd"],

            top_merchants=
            summary_json["top_merchants"],

            anomaly_count=
            summary_json["anomaly_count"],

            narrative=
            summary_json["narrative"],

            risk_level=
            summary_json["risk_level"]
        )

        db.add(job_summary)

        db.commit()

        # --------------------
        # COMPLETE JOB
        # --------------------

        job.row_count_raw = raw_count
        job.row_count_clean = clean_count
        job.processed_filename = processed_file
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.status = "completed"

        db.commit()

        return True

    except Exception as e:

        print(e)

        if job:

            job.status = "failed"
            job.error_message = str(e)

            db.commit()

        return False

    finally:

        db.close()