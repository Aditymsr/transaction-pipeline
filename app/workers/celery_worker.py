from celery import Celery
import os

celery_app = Celery(
    "transaction_pipeline",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL"),
    include=["app.workers.tasks"]
)