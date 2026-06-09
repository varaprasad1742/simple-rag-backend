import uuid

from datetime import datetime

from sqlalchemy import (
    String,
    DateTime
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.models.base import Base
from sqlalchemy.orm import (
    relationship
)

class PipelineRun(Base):

    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(
            uuid.uuid4()
        )
    )

    trace_id: Mapped[str] = mapped_column(
        String,
        index=True
    )

    user_id: Mapped[str] = mapped_column(
        String,
        index=True
    )

    pipeline_type: Mapped[str] = mapped_column(
        String
    )

    status: Mapped[str] = mapped_column(
        String
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now
    )


    steps = relationship(
        "PipelineStep",
        back_populates="run",
        cascade="all, delete-orphan"
    )