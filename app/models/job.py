from sqlalchemy import Column, Integer, String

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

    processed_filename = Column(
        String,
        nullable=True
    )

    error_message = Column(
        String,
        nullable=True
    )