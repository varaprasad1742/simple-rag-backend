import uuid

from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    Text, 
    Boolean
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.models.base import Base
from uuid import uuid4
class Chunk(Base):

    __tablename__ = "chunks"

    from uuid import uuid4

    id = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid4())
    )

    user_id: Mapped[str] = mapped_column(
        String,
        index=True
    )

    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id")
    )

    filename: Mapped[str] = mapped_column(
        String
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer
    )

    start_page: Mapped[int] = mapped_column(
        Integer
    )

    end_page: Mapped[int] = mapped_column(
        Integer
    )

    token_count: Mapped[int] = mapped_column(
        Integer
    )

    content: Mapped[str] = mapped_column(
        Text
    )


    indexed: Mapped[bool] = mapped_column(
            Boolean,
            default=False
        )