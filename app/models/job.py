from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from app.database.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)

    filename = Column(String, nullable=False)

    status = Column(
        String,
        nullable=False,
        default="pending"
    )

    row_count_raw = Column(
        Integer,
        nullable=True
    )

    row_count_clean = Column(
        Integer,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    completed_at = Column(
        DateTime,
        nullable=True
    )

    processed_filename = Column(
        String,
        nullable=True
    )

    error_message = Column(
        String,
        nullable=True
    )