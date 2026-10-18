import logging
from groq import AsyncGroq

from app.core.config import (
    settings
)

from app.observability.decorators import (
    observe
)

logger = logging.getLogger(__name__)


class LLMService:

    client = AsyncGroq(
        api_key=settings.GROQ_API_KEY
    )
    FALLBACK_MODELS = [
        "llama-3.1-8b-instant","openai/gpt-oss-20b","openai/gpt-oss-120b"
    ]

    @classmethod
    @observe("generate_answer")
    async def generate(
        cls,
        context: str,
        messages: list = None,
        query: str = None
    ):

        system_instruction = (
            "You are CogniRAG, an intelligent and helpful AI assistant for question answering over documents.\n\n"
            "You will be provided with Reference Sources extracted from the user's uploaded documents, along with the user's Question.\n\n"
            "GUIDELINES:\n"
            "1. Answer the question thoroughly, clearly, and directly based on the Reference Sources.\n"
            "2. Whenever citing information from a source, include its bracketed source index like [1] or [2] (e.g., 'According to [1], the system uses...').\n"
            "3. Mention document metadata like file name or page numbers when helpful (e.g., 'In Report.pdf (Page 4)...').\n"
            "4. For general pleasantries or greetings (e.g., 'hello', 'hi', 'how are you'), respond warmly and invite questions about the uploaded files.\n"
            "5. If the sources partially answer the question, provide all available details from the sources with citations and note what information is missing.\n"
            "6. If the sources contain no relevant information to answer the question, politely explain that the provided document excerpts do not mention this topic.\n"
            "7. Do not invent facts or citations that are not supported by the Reference Sources."
        )

        current_query = query
        history_turns = []
        if messages:
            if not current_query and messages[-1].get("role") == "user":
                current_query = messages[-1].get("content", "")
                history_turns = messages[:-1]
            elif current_query and messages[-1].get("role") == "user" and messages[-1].get("content") == current_query:
                history_turns = messages[:-1]
            else:
                history_turns = list(messages)

        user_content = (
            f"Reference Sources:\n"
            f"{context.strip() if context and context.strip() else 'No relevant document sources found in knowledge base.'}\n\n"
            f"Question:\n{current_query or 'Please summarize the provided documents.'}"
        )

        llm_messages = [{"role": "system", "content": system_instruction}]

        for turn in history_turns:
            role = turn.get("role")
            content = turn.get("content")
            if role in ("user", "assistant") and content:
                llm_messages.append({"role": role, "content": content})

        llm_messages.append({"role": "user", "content": user_content})

        preferred_model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant") or "llama-3.1-8b-instant"
        models_to_try = [preferred_model]
        for m in cls.FALLBACK_MODELS:
            if m and m not in models_to_try:
                models_to_try.append(m)

        last_error = None
        for model_name in models_to_try:
            try:
                response = await cls.client.chat.completions.create(
                    model=model_name,
                    messages=llm_messages,
                    temperature=0.2,
                    max_tokens=1500
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if any(x in err_msg.lower() for x in ["not_found", "does not exist", "not have access", "404", "model_decommissioned"]):
                    logger.warning("Groq model %s failed (%s), attempting fallback...", model_name, err_msg)
                    continue
                logger.warning("Groq error with model %s: %s. Attempting fallback...", model_name, err_msg)
                continue

        if last_error:
            raise last_error
        raise RuntimeError("No LLM models could be reached.")

    @classmethod
    @observe("query_transformation")
    async def transform_query(
        cls,
        original_query: str,
        current_query: str,
        iteration: int,
        reason: str = None
    ) -> str:
        prompt = (
            f"Original user question: \"{original_query}\"\n"
            f"Previous search query: \"{current_query}\"\n"
            f"Reason previous retrieval needed refinement: {reason or 'Candidate passages lacked sufficient relevance or coverage'}\n\n"
            f"Generate an alternative, optimized search query to retrieve relevant facts from document embeddings.\n"
            f"Guidelines:\n"
            f"- Expand key abbreviations, add relevant domain synonyms, or clarify the core intent.\n"
            f"- Keep it concise (under 20 words).\n"
            f"- Do not use boolean operators like AND/OR.\n"
            f"- Return ONLY the rewritten query text, with no quotes or explanations."
        )
        preferred_model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant") or "llama-3.1-8b-instant"
        for model_name in [preferred_model, "llama-3.1-8b-instant"]:
            try:
                response = await cls.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert query reformulation engine for dense and lexical vector retrieval. Output only the transformed query."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=60
                )
                transformed = response.choices[0].message.content.strip().strip('"').strip("'")
                if transformed:
                    return transformed
            except Exception as e:
                logger.warning("Query transformation failed with %s: %s", model_name, e)
                continue
        return original_query

    @classmethod
    @observe("evaluate_retrieval")
    async def evaluate_retrieval(
        cls,
        query: str,
        results: list
    ) -> dict:
        if not results:
            return {
                "is_sufficient": False,
                "confidence": 0.0,
                "reason": "No document passages were retrieved."
            }

        scores = [float(r.score) for r in results if hasattr(r, "score") and r.score is not None]
        top_score = max(scores) if scores else 0.0

        if top_score >= 1.5:
            return {
                "is_sufficient": True,
                "confidence": 0.95,
                "reason": f"High relevance cross-encoder match (score: {top_score:.2f})."
            }

        if top_score <= -2.5:
            return {
                "is_sufficient": False,
                "confidence": 0.2,
                "reason": f"Very low cross-encoder score ({top_score:.2f}) indicates poor semantic overlap."
            }

        # Check content relevance with LLM grader
        passages_text = "\n---\n".join([
            f"[{idx+1}] {(r.payload or {}).get('content', '')[:160]}"
            for idx, r in enumerate(results[:3])
        ])
        eval_prompt = (
            f"User Question: \"{query}\"\n\n"
            f"Retrieved Passages:\n{passages_text}\n\n"
            f"Do these passages contain relevant information to answer the question?\n"
            f"Return a JSON object: {{\"is_sufficient\": true/false, \"confidence\": 0.0-1.0, \"reason\": \"short reason\"}}"
        )
        preferred_model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant") or "llama-3.1-8b-instant"
        try:
            resp = await cls.client.chat.completions.create(
                model=preferred_model,
                messages=[
                    {"role": "system", "content": "You are a retrieval evaluator. Output valid JSON only."},
                    {"role": "user", "content": eval_prompt}
                ],
                temperature=0.1,
                max_tokens=80
            )
            raw = resp.choices[0].message.content.strip()
            if "{" in raw and "}" in raw:
                import json
                raw_json = raw[raw.find("{"):raw.rfind("}") + 1]
                data = json.loads(raw_json)
                return {
                    "is_sufficient": bool(data.get("is_sufficient", False)),
                    "confidence": float(data.get("confidence", 0.5)),
                    "reason": str(data.get("reason", "Graded by evaluator agent"))
                }
        except Exception as e:
            logger.warning("LLM evaluation failed (%s), using score heuristic", e)

        is_suff = top_score > 0.0
        return {
            "is_sufficient": is_suff,
            "confidence": 0.7 if is_suff else 0.4,
            "reason": f"Reranker top score {top_score:.2f} {'passed' if is_suff else 'below'} confidence threshold."
        }