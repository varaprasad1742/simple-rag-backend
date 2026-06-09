import asyncio

from sentence_transformers import (
    CrossEncoder
)

from app.observability.decorators import (
    observe
)

class Reranker:

    model = CrossEncoder(
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

    @classmethod
    @observe("rerank")
    async def rerank(
        cls,
        query: str,
        results,
        top_k: int = 5
    ):
        pairs = []
        
        for result in results:
            pairs.append(
                (
                    query,
                    result.payload[
                        "content"
                    ]
                )
            )
        scores = await asyncio.to_thread(
            cls.model.predict,
            pairs
        )
        reranked = list(
            zip(
                results,
                scores
            )
        )
        reranked.sort(
            key=lambda x: x[1],
            reverse=True
        )
        return [
            result
            for result, score
            in reranked[:top_k]
        ]