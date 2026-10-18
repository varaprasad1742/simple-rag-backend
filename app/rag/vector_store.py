import os
import asyncio
from qdrant_client import (
    AsyncQdrantClient,
    QdrantClient
)

from qdrant_client.models import (
    Distance,
    VectorParams
)

from app.core.config import (
    settings
)
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

from qdrant_client.models import PayloadSchemaType


class LocalAsyncQdrantAdapter:
    """
    Embedded local disk folder adapter using QdrantClient(path=...).
    Stores collections directly in a local directory without requiring Docker or any server.
    """
    def __init__(self, path: str):
        os.makedirs(path, exist_ok=True)
        self.path = os.path.abspath(path)
        self._sync_client = QdrantClient(path=self.path)

    async def get_collections(self):
        return await asyncio.to_thread(self._sync_client.get_collections)

    async def create_collection(self, **kwargs):
        return await asyncio.to_thread(self._sync_client.create_collection, **kwargs)

    async def create_payload_index(self, **kwargs):
        try:
            return await asyncio.to_thread(self._sync_client.create_payload_index, **kwargs)
        except Exception:
            return None

    async def upsert(self, **kwargs):
        return await asyncio.to_thread(self._sync_client.upsert, **kwargs)

    async def query_points(self, **kwargs):
        def _query():
            query_vec = kwargs.get("query")
            if hasattr(query_vec, "tolist"):
                kwargs["query"] = query_vec.tolist()
            if hasattr(self._sync_client, "query_points"):
                return self._sync_client.query_points(**kwargs)
            hits = self._sync_client.search(
                collection_name=kwargs.get("collection_name"),
                query_vector=kwargs.get("query"),
                limit=kwargs.get("limit", 10),
                query_filter=kwargs.get("query_filter")
            )
            class _Result:
                pass
            res = _Result()
            res.points = hits
            return res

        return await asyncio.to_thread(_query)

    async def delete(self, **kwargs):
        return await asyncio.to_thread(self._sync_client.delete, **kwargs)


def _init_qdrant_client():
    raw_url = (settings.QDRANT_URL or "").strip()
    api_key = settings.QDRANT_API_KEY.strip() if settings.QDRANT_API_KEY and settings.QDRANT_API_KEY.strip() else None

    # Only connect over network if explicitly an external remote cloud URL (https://) and not localhost
    is_remote_cloud = (
        raw_url.startswith("https://") 
        and "localhost" not in raw_url 
        and "127.0.0.1" not in raw_url
    )

    if is_remote_cloud:
        return AsyncQdrantClient(url=raw_url, api_key=api_key)

    # Local disk directory mode (embedded folder storage)
    # Default to "./data/qdrant" if localhost or relative path is provided
    if raw_url and not raw_url.startswith("http://") and not raw_url.startswith("https://"):
        storage_path = raw_url
    else:
        storage_path = "./data/qdrant"

    os.makedirs(storage_path, exist_ok=True)
    return LocalAsyncQdrantAdapter(path=storage_path)


class VectorStore:

    client = _init_qdrant_client()
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
        
        if cls.COLLECTION_NAME not in names:

            await cls.client.create_collection(
                collection_name=
                cls.COLLECTION_NAME,

                vectors_config=
                VectorParams(
                    size=384,
                    distance=Distance.COSINE
                )
            )

            await cls.client.create_payload_index(
                collection_name=cls.COLLECTION_NAME,
                field_name="user_id",
                field_schema=PayloadSchemaType.KEYWORD
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
    
        for chunk, embedding in zip(
            chunks,
            embeddings
        ):

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

    @classmethod
    async def delete_document_vectors(cls, document_id: str):
        try:
            await cls.client.delete(
                collection_name=cls.COLLECTION_NAME,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            )
        except Exception:
            pass