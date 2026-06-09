from groq import AsyncGroq

from app.core.config import (
    settings
)

from app.observability.decorators import (
    observe
)


class LLMService:

    client = AsyncGroq(
        api_key=settings.GROQ_API_KEY
    )

    @classmethod
    @observe("generate_answer")
    async def generate(
        cls,
        context: str,
        messages
    ):

        prompt = f"""
You are a RAG assistant.

Use ONLY the provided sources.

Rules:
1. Do not mention SOURCE labels in the answer.
2. Write a natural answer.
3. At the end of each sentence, cite the source number using [1], [2], etc.
4. If multiple sources support a statement, cite all of them.
5. If the answer is not present in the sources, say:
   "I don't have enough information in the provided sources."

Sources:
{context}

Answer:
"""     
        llm_messages = [
                    {
                "role":"system",
                "content":prompt
            }
        ]
        llm_messages.extend(messages)
        response = await (
            cls.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=llm_messages
            )
        )

        return (
            response
            .choices[0]
            .message.content
        )