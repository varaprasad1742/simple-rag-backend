from app.rag.embedder import (
    EmbeddingModel
)

from app.rag.vector_store import (
    VectorStore
)

from app.services.llm_service import (
    LLMService
)

from app.observability.decorators import (
    observe
)
from app.rag.reranker import (
    Reranker
)
from app.services.cache_service import CacheService
from app.repositories.message_repository import MessageRepository
from app.models.message import Message
from app.observability.collector import update_step_metadata

import json
from app.services.trace_service import TraceService


class ChatService:

    @staticmethod
    def build_context(
        results
    ):

        contexts = []
        citations = []
        for idx, result in enumerate(
            results,
            start=1
            ):

            contexts.append(
                f"""
        [SOURCE {idx}]

        {result.payload["content"]}
        """
            )

            citations.append(
                {
                    "id": idx,

                    "document_id": result.payload["document_id"],

                    "filename":
                    result.payload["filename"],

                    "start_page":
                    result.payload["start_page"],

                    "end_page":
                    result.payload["end_page"],

                    "content":
                    result.payload["content"]
                }
            )

        return "\n\n".join(contexts), citations

    @staticmethod
    @observe("Starting chat")
    async def chat(
        query: str,
        user_id: str,
        chat_id: str,
        db,
       
    ):
        cached_answer = (
            CacheService
            .get_response(
                user_id,
                query
            )
        )
        
            
        await MessageRepository.create(
            db,
            Message(
                chat_id=chat_id,
                role="user",
                content=query
            )
        )
        if cached_answer:
            answer,citations = cached_answer
            CacheService.trace_cache("Response Cache",True)
            await MessageRepository.create(
                db,
                Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=answer,
                    citations=json.dumps(
                        citations
                    )
                )
            )

            await TraceService.save_current_trace(
                db=db,
                pipeline_type="Chat"
            )
            return {
                "answer": answer,
                "citations": citations
            }
        history = await (
            MessageRepository
            .get_recent_messages(
                db,
                chat_id,
                limit=10
            )
        )
        messages = []

        for msg in history:

            messages.append(
                {
                    "role":
                    msg.role,

                    "content":
                    msg.content
                }
            )
        query_embedding = await (
            EmbeddingModel.embed_query(
                query
            )
        )
        cached_results = (
            CacheService
            .get_retrieval(
                user_id,
                query
            )
        )
        if cached_results:
            results = cached_results
            CacheService.trace_cache(
            "Retrieval Cache",
            True
        )
        else:
            results = await (
                VectorStore.search(
                    user_id=user_id,
                    query_embedding=
                    query_embedding
                )
            )
            CacheService.set_retrieval(user_id,query,results)

        retrieved_chunks = []
        for r in results:
            retrieved_chunks.append({"document_id":r.payload["document_id"],"filename":r.payload["filename"],"page":r.payload["start_page"],"score":r.score,"content":r.payload["content"][:300]})
        update_step_metadata("vector_search",retrieved_chunks)

        results = await (
            Reranker.rerank(
                query=query,
                results=results,
                top_k=5
            )
        )
        retrieved_chunks = []
        for r in results:
            retrieved_chunks.append({"document_id":r.payload["document_id"],"filename":r.payload["filename"],"page":r.payload["start_page"],"score":r.score,"content":r.payload["content"][:300]})
        update_step_metadata("rerank",retrieved_chunks)

        context, citations = (
            ChatService.build_context(
                results
            )
        )
        
        
        answer = await (
                LLMService.generate(
                    context=context,
                    messages=messages
                )
            )
        CacheService.set_response(
                user_id,
                query,
                answer, citations
            )

        update_step_metadata("generate_answer",{"query": query,"context_chunks":len(results),"model":"llama-3.3-70b-versatile",})

        await MessageRepository.create(
            db,
            Message(
                chat_id=chat_id,
                role="assistant",
                content=answer,
                citations=json.dumps(
                    citations
                )
            )
        )

        await TraceService.save_current_trace(
            db=db,
            pipeline_type="Chat"
        )
        return {
            "answer": answer,
            "citations": citations
        }