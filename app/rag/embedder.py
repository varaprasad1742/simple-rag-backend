import asyncio

from sentence_transformers import (
    SentenceTransformer
)

from app.observability.decorators import (
    observe
)
from app.services.cache_service import CacheService

class EmbeddingModel:

    model = SentenceTransformer(
        "BAAI/bge-small-en-v1.5"
    )

    @classmethod
    @observe("embed_chunks Step - 2.3.1")
    async def embed_chunks(
        cls,
        texts: list[str]
    ):

        embeddings = (
            await asyncio.to_thread(
                cls.model.encode,
                texts,
                batch_size=32,
                normalize_embeddings=True,
                show_progress_bar=False
            )
        )

        return embeddings
    
    @classmethod
    @observe("embed_query")
    async def embed_query(
        cls,
        query: str
    ):
        cached = (
            CacheService
            .get_embedding(
                query
            )
        )

        if cached:
            CacheService.trace_cache("Embedding query cache",True)
            return cached
        embedding = await asyncio.to_thread(
            cls.model.encode,
            query,
            normalize_embeddings=True
        )
        CacheService.set_embedding(
            query,
            embedding.tolist()
        )
        return embedding.tolist()