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
from app.observability.collector import update_step_metadata, get_steps
from app.core.request_context import trace_id_ctx

import json
from app.services.trace_service import TraceService
from app.core.config import settings


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
            payload = result.payload or {}
            filename = payload.get("filename", "Document")
            start_page = payload.get("start_page", 1)
            end_page = payload.get("end_page", start_page)
            content = payload.get("content", "").strip()
            doc_id = payload.get("document_id", "")
            chunk_index = payload.get("chunk_index", 0)

            page_info = f"Page {start_page}" if start_page == end_page else f"Pages {start_page}–{end_page}"

            contexts.append(
                f"[SOURCE {idx}] (Document: {filename}, {page_info}):\n"
                f"{content}"
            )

            citations.append(
                {
                    "id": idx,
                    "document_id": doc_id,
                    "filename": filename,
                    "start_page": start_page,
                    "end_page": end_page,
                    "chunk_index": chunk_index,
                    "content": content
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
            run = await TraceService.save_current_trace(
                db=db,
                pipeline_type="Chat"
            )
            trace_id = run.trace_id if run else trace_id_ctx.get()
            raw_steps = get_steps()
            clean_steps = [
                {
                    "name": s["name"],
                    "duration": round(s["duration"], 4) if isinstance(s.get("duration"), (int, float)) else s.get("duration", 0),
                    "status": s.get("status", "success"),
                    "trace_metadata": s.get("trace_metadata", {})
                }
                for s in raw_steps
            ]
            await MessageRepository.create(
                db,
                Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=answer,
                    citations=json.dumps(
                        citations
                    ),
                    trace_id=trace_id,
                    steps_data=json.dumps(clean_steps)
                )
            )

            return {
                "answer": answer,
                "citations": citations,
                "trace_id": trace_id,
                "steps": clean_steps
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
        MAX_AGENTIC_LOOPS = 3
        current_search_query = query
        accumulated_results = []
        transformations = []
        eval_reason = None
        loop_count = 0

        conversational_phrases = {"hi", "hello", "hey", "who are you", "help", "thank you", "thanks"}
        is_greeting = query.strip().lower() in conversational_phrases

        for iteration in range(1, MAX_AGENTIC_LOOPS + 1):
            loop_count = iteration

            # Query Transformation step if iteration > 1
            if iteration > 1:
                transformed = await LLMService.transform_query(
                    original_query=query,
                    current_query=current_search_query,
                    iteration=iteration,
                    reason=eval_reason
                )
                transformations.append({
                    "loop": iteration,
                    "previous_query": current_search_query,
                    "transformed_query": transformed,
                    "reason": eval_reason
                })
                update_step_metadata("query_transformation", {
                    "loop": iteration,
                    "original_query": query,
                    "previous_query": current_search_query,
                    "transformed_query": transformed,
                    "reason": eval_reason
                })
                current_search_query = transformed

            # Step A: Query Dense Embedding
            query_embedding = await (
                EmbeddingModel.embed_query(
                    current_search_query
                )
            )
            update_step_metadata("embed_query", {
                "loop": iteration,
                "query": current_search_query,
                "model": "BAAI/bge-small-en-v1.5",
                "dimension": 384
            })

            # Step B: Semantic Vector Search
            cached_results = (
                CacheService.get_retrieval(
                    user_id,
                    current_search_query
                )
            )
            if cached_results:
                search_results = cached_results
                CacheService.trace_cache(
                    "Retrieval Cache",
                    True
                )
            else:
                search_results = await (
                    VectorStore.search(
                        user_id=user_id,
                        query_embedding=query_embedding
                    )
                )
                CacheService.set_retrieval(user_id, current_search_query, search_results)

            retrieved_chunks = []
            for r in search_results:
                p = r.payload or {}
                retrieved_chunks.append({
                    "document_id": p.get("document_id", ""),
                    "filename": p.get("filename", "Unknown"),
                    "page": p.get("start_page", 1),
                    "score": round(float(r.score), 4) if hasattr(r, "score") and r.score is not None else 0.0,
                    "content": p.get("content", "")[:300]
                })
            update_step_metadata("vector_search", {
                "loop": iteration,
                "query": current_search_query,
                "count": len(retrieved_chunks),
                "chunks": retrieved_chunks
            })

            # Step C: Cross-Encoder Rerank
            reranked_results = await (
                Reranker.rerank(
                    query=current_search_query,
                    results=search_results,
                    top_k=5
                )
            )
            reranked_chunks = []
            for r in reranked_results:
                p = r.payload or {}
                reranked_chunks.append({
                    "document_id": p.get("document_id", ""),
                    "filename": p.get("filename", "Unknown"),
                    "page": p.get("start_page", 1),
                    "score": round(float(r.score), 4) if hasattr(r, "score") and r.score is not None else 0.0,
                    "content": p.get("content", "")[:300]
                })
            update_step_metadata("rerank", {
                "loop": iteration,
                "query": current_search_query,
                "count": len(reranked_chunks),
                "chunks": reranked_chunks
            })

            # Merge into accumulated unique candidate results
            for r in reranked_results:
                payload = getattr(r, "payload", {}) or {}
                key = (payload.get("document_id"), payload.get("chunk_index"), payload.get("start_page"))
                if not any(
                    (getattr(item, "payload", {}) or {}).get("document_id") == key[0] and
                    (getattr(item, "payload", {}) or {}).get("chunk_index") == key[1] and
                    (getattr(item, "payload", {}) or {}).get("start_page") == key[2]
                    for item in accumulated_results
                ):
                    accumulated_results.append(r)

            # Step D: Agentic Relevance Evaluation / Sufficiency Grader
            if is_greeting:
                eval_result = {"is_sufficient": True, "confidence": 1.0, "reason": "Conversational prompt, document retrieval not strictly required"}
            else:
                eval_result = await LLMService.evaluate_retrieval(query=query, results=reranked_results)

            eval_reason = eval_result.get("reason", "Passages require further specificity")
            update_step_metadata("evaluate_retrieval", {
                "loop": iteration,
                "query": current_search_query,
                "is_sufficient": eval_result.get("is_sufficient", False),
                "confidence": eval_result.get("confidence", 0.5),
                "reason": eval_reason
            })

            # Early break if retrieved context is deemed sufficient
            if eval_result.get("is_sufficient", False):
                break

            # Stop if maximum loop count reached
            if iteration >= MAX_AGENTIC_LOOPS:
                break

        # Select top 5 accumulated passages sorted by score
        final_results = sorted(
            accumulated_results,
            key=lambda x: getattr(x, "score", 0.0) if hasattr(x, "score") and x.score is not None else 0.0,
            reverse=True
        )[:5]

        context, citations = (
            ChatService.build_context(
                final_results
            )
        )
        
        answer = await (
            LLMService.generate(
                context=context,
                messages=messages,
                query=query
            )
        )
        CacheService.set_response(
            user_id,
            query,
            answer, citations
        )

        active_model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant") or "llama-3.1-8b-instant"
        update_step_metadata("generate_answer", {
            "query": query,
            "model": active_model,
            "agentic_loops": loop_count,
            "transformations": transformations,
            "context_chunks": len(citations),
            "sources": [
                {
                    "id": c["id"],
                    "filename": c["filename"],
                    "pages": f"{c['start_page']}-{c['end_page']}" if c['start_page'] != c['end_page'] else f"Page {c['start_page']}"
                }
                for c in citations
            ]
        })

        run = await TraceService.save_current_trace(
            db=db,
            pipeline_type="Chat"
        )
        trace_id = run.trace_id if run else trace_id_ctx.get()
        raw_steps = get_steps()
        clean_steps = [
            {
                "name": s["name"],
                "duration": round(s["duration"], 4) if isinstance(s.get("duration"), (int, float)) else s.get("duration", 0),
                "status": s.get("status", "success"),
                "trace_metadata": s.get("trace_metadata", {})
            }
            for s in raw_steps
        ]

        await MessageRepository.create(
            db,
            Message(
                chat_id=chat_id,
                role="assistant",
                content=answer,
                citations=json.dumps(
                    citations
                ),
                trace_id=trace_id,
                steps_data=json.dumps(clean_steps)
            )
        )

        return {
            "answer": answer,
            "citations": citations,
            "trace_id": trace_id,
            "steps": clean_steps
        }