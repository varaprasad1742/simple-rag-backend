from qdrant_client import (
    AsyncQdrantClient
)

from qdrant_client.models import (
    Distance,
    VectorParams
)

from app.core.config import (
    settings
)
import asyncio
from app.rag.embedder import EmbeddingModel

from app.observability.decorators import (
    observe
)
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue
)

from qdrant_client.models import (
    PointStruct
)


class VectorStore:

    # client = AsyncQdrantClient(
    #     url=settings.QDRANT_URL,
    #     api_key = settings.QDRANT_API_KEY
    # )
    client = AsyncQdrantClient(path="./qdrant")
    COLLECTION_NAME = "documents"
    @classmethod
    async def create_collection(
        cls
    ):

        collections = (
            await cls.client.get_collections()
        )

        names = {
            c.name
            for c in collections.collections
        }

        if cls.COLLECTION_NAME in names:
            return

        await cls.client.create_collection(
            collection_name=
            cls.COLLECTION_NAME,

            vectors_config=
            VectorParams(
                size=384,
                distance=Distance.COSINE
            )
        )

    @classmethod
    @observe("embed_chunks")
    async def embed_chunks(
        cls,
        chunks: list[str]
    ):

        embeddings = await asyncio.to_thread(
            EmbeddingModel.model.encode,
            chunks,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        return embeddings
    

    @classmethod
    @observe("qdrant_upsert Step 2.3.2")
    async def upsert_chunks(
        cls,
        chunks,
        embeddings
    ):
        await cls.create_collection()
        points = []
        print(chunks)
        for chunk, embedding in zip(
            chunks,
            embeddings
        ):
            print(chunk.content)
            points.append(
                PointStruct(
                    id=chunk.id,

                    vector=
                    embedding.tolist(),

                    payload={

                        "user_id":
                        chunk.user_id,

                        "document_id":
                        chunk.document_id,

                        "filename":
                        chunk.filename,

                        "chunk_index":
                        chunk.chunk_index,

                        "start_page":
                        chunk.start_page,

                        "end_page":
                        chunk.end_page,

                        "token_count":
                        chunk.token_count,

                        "content":
                        chunk.content
                    }
                )
            )

        await cls.client.upsert(
            collection_name=
            cls.COLLECTION_NAME,

            points=points
        )

    @classmethod
    @observe("vector_search")
    async def search(
        cls,
        user_id: str,
        query_embedding,
        limit: int = 10
    ):

        results = await cls.client.query_points(
            collection_name=
            cls.COLLECTION_NAME,

            query=
            query_embedding,

            limit=limit,

            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(
                            value=user_id
                        )
                    )
                ]
            )
        )
        
        return results.points
    

    @staticmethod
    def build_context(
        results
    ):
        contexts = []
        
        for hit in results:

            contexts.append(hit.payload["content"])

        return "\n\n".join(
            contexts
        )