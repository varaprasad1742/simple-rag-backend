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
        if not results:
            return []
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
        reranked = []
        for result, score in zip(results, scores):
            try:
                result.score = float(score)
            except Exception:
                pass
            reranked.append((result, float(score)))

        reranked.sort(
            key=lambda x: x[1],
            reverse=True
        )
        return [
            result
            for result, score
            in reranked[:top_k]
        ]