import uuid

from datetime import datetime

from sqlalchemy import (
    String,
    Float,
    DateTime,
    Text,
    ForeignKey
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.models.base import Base

from sqlalchemy.orm import (
    relationship
)

class PipelineStep(Base):

    __tablename__ = "pipeline_steps"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(
            uuid.uuid4()
        )
    )

    pipeline_run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey(
            "pipeline_runs.id"
        )
    )

    step_name: Mapped[str] = mapped_column(
        String
    )

    duration: Mapped[float] = mapped_column(
        Float
    )

    status: Mapped[str] = mapped_column(
        String
    )

    trace_metadata: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now
    )


    run = relationship(
        "PipelineRun",
        back_populates="steps"
    )