from app.observability.decorators import (
    observe
)

from app.repositories.chunk_repository import (
    ChunkRepository
)

from app.rag.embedder import (
    EmbeddingModel
)

from app.rag.vector_store import (
    VectorStore
)
from app.services.trace_service import TraceService

class IndexService:

    @staticmethod
    @observe("Indexing Document - Step 2.3")
    async def index_document(
        document_id: str,
        db
    ):

        chunks = await (
            ChunkRepository.get_by_document(
                db,
                document_id
            )
        )

        if not chunks:
            return 0

        texts = [
            chunk.content
            for chunk in chunks
        ]

        embeddings = await (
            EmbeddingModel.embed_chunks(
                texts
            )
        )

        await (
            VectorStore.upsert_chunks(
                chunks,
                embeddings
            )
        )

        await (
            ChunkRepository.mark_indexed(
                db,
                [
                    chunk.id
                    for chunk in chunks
                ]
            )
        )
        await TraceService.save_current_trace(
            db=db,
            pipeline_type="Document Uploading"
        )
        return len(chunks)