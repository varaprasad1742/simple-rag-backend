from sqlalchemy.ext.asyncio import (
    AsyncSession
)

from app.models.chunk import Chunk
from sqlalchemy import select
from sqlalchemy import update

from app.models.chunk import Chunk

class ChunkRepository:

    @staticmethod
    async def bulk_create(
        db: AsyncSession,
        chunks: list[Chunk]
    ):

        db.add_all(chunks)

        await db.commit()

        return chunks
    

    @staticmethod
    async def get_by_document(
        db,
        document_id: str
    ):

        result = await db.execute(
            select(Chunk)
            .where(
                Chunk.document_id
                == document_id
            )
            .order_by(
                Chunk.chunk_index
            )
        )

        return result.scalars().all()
        
    @staticmethod
    async def mark_indexed(
        db,
        chunk_ids: list[str]
    ):

        await db.execute(
            update(Chunk)
            .where(
                Chunk.id.in_(
                    chunk_ids
                )
            )
            .values(
                indexed=True
            )
        )

        await db.commit()