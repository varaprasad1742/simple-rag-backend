import uuid

from sqlalchemy import String, Text

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.models.base import Base


class Document(Base):

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    user_id: Mapped[str] = mapped_column(
        String,
        index=True
    )

    filename: Mapped[str] = mapped_column(
        String
    )

    file_path: Mapped[str] = mapped_column(
        String
    )

    status: Mapped[str] = mapped_column(
        String,
        default="uploaded"
    )

    text_content: Mapped[str | None] = mapped_column(
    Text,
    nullable=True
)