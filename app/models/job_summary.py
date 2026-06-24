from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Text,
    JSON
)

from app.database.database import Base


class JobSummary(Base):

    __tablename__ = "job_summaries"

    id = Column(Integer, primary_key=True)

    job_id = Column(
        Integer,
        nullable=False
    )

    total_spend_inr = Column(
        Float,
        default=0
    )

    total_spend_usd = Column(
        Float,
        default=0
    )

    top_merchants = Column(
        JSON,
        nullable=True
    )

    anomaly_count = Column(
        Integer,
        default=0
    )

    narrative = Column(
        Text,
        nullable=True
    )

    risk_level = Column(
        String,
        nullable=True
    )