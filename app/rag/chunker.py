import asyncio
import re

import numpy as np
import tiktoken

from app.observability.decorators import (
    observe
)

from app.rag.embedder import (
    EmbeddingModel
)


class SemanticParagraphChunker:

    MAX_TOKENS = 512

    MIN_CHUNK_TOKENS = 256

    OVERLAP_TOKENS = 50

    SIMILARITY_THRESHOLD = 0.75

    EMBEDDING_BATCH_SIZE = 256

    tokenizer = tiktoken.get_encoding(
        "cl100k_base"
    )

    @classmethod
    def count_tokens(
        cls,
        text: str
    ) -> int:

        return len(
            cls.tokenizer.encode(text)
        )

    @staticmethod
    def cosine_similarity(
        a,
        b
    ) -> float:

        return float(
            np.dot(a, b)
        )

    @classmethod
    def extract_paragraphs(
        cls,
        pages: list[dict]
    ) -> list[dict]:

        paragraphs = []

        for page in pages:

            page_text = re.sub(
                r"\n{3,}",
                "\n\n",
                page["text"]
            )

            raw_paragraphs = (
                page_text.split("\n\n")
            )

            for paragraph in raw_paragraphs:

                paragraph = (
                    paragraph.strip()
                )

                if not paragraph:
                    continue

                paragraphs.append(
                        {
                            "user_id": page["user_id"],
                            "document_id": page["document_id"],
                            "filename": page["filename"],
                            "page_number": page["page_number"],
                            "paragraph": paragraph
                        }
                    )

        return paragraphs

    @classmethod
    @observe("embed_paragraphs Step 2.2.1.1")
    async def embed_paragraphs(
        cls,
        paragraphs: list[dict]
    ):

        texts = [
            p["paragraph"]
            for p in paragraphs
        ]

        embeddings = []

        for start in range(
            0,
            len(texts),
            cls.EMBEDDING_BATCH_SIZE
        ):

            batch = texts[
                start:
                start + cls.EMBEDDING_BATCH_SIZE
            ]

            batch_embeddings = (
                await asyncio.to_thread(
                    EmbeddingModel.model.encode,
                    batch,
                    batch_size=32,
                    normalize_embeddings=True,
                    show_progress_bar=False
                )
            )

            embeddings.extend(
                batch_embeddings
            )

        return embeddings

    @classmethod
    def build_chunk(
        cls,
        chunk_index: int,
        current_chunk: list[dict],
        current_tokens: int
    ) -> dict:

        content = "\n\n".join(
            p["paragraph"]
            for p in current_chunk
        )

        pages = [
            p["page_number"]
            for p in current_chunk
        ]

        first = current_chunk[0]

        return {
            "user_id":
                first["user_id"],

            "document_id":
                first["document_id"],

            "filename":
                first["filename"],

            "chunk_index":
                chunk_index,

            "start_page":
                min(pages),

            "end_page":
                max(pages),

            "token_count":
                current_tokens,

            "content":
                content
        }

    @classmethod
    @observe("Semantic chunking Step 2.2.1")
    async def chunk_text(
        cls,
        pages: list[dict]
    ) -> list[dict]:

        paragraphs = (
            cls.extract_paragraphs(
                pages
            )
        )

        if not paragraphs:
            return []

        embeddings = (
            await cls.embed_paragraphs(
                paragraphs
            )
        )

        chunks = []

        chunk_index = 0

        current_chunk = [
            paragraphs[0]
        ]

        current_tokens = (
            cls.count_tokens(
                paragraphs[0][
                    "paragraph"
                ]
            )
        )

        for idx in range(
            1,
            len(paragraphs)
        ):

            paragraph = (
                paragraphs[idx]
            )

            paragraph_text = (
                paragraph[
                    "paragraph"
                ]
            )

            paragraph_tokens = (
                cls.count_tokens(
                    paragraph_text
                )
            )

            similarity = (
                cls.cosine_similarity(
                    embeddings[idx - 1],
                    embeddings[idx]
                )
            )

            semantic_break = (
                similarity
                < cls.SIMILARITY_THRESHOLD
                and current_tokens
                >= cls.MIN_CHUNK_TOKENS
            )

            token_limit_exceeded = (
                current_tokens
                + paragraph_tokens
                > cls.MAX_TOKENS
            )

            if (
                semantic_break
                or token_limit_exceeded
            ):

                chunks.append(
                    cls.build_chunk(
                        chunk_index,
                        current_chunk,
                        current_tokens
                    )
                )

                chunk_index += 1

                overlap = []

                overlap_tokens = 0

                for old in reversed(
                    current_chunk
                ):

                    tokens = (
                        cls.count_tokens(
                            old[
                                "paragraph"
                            ]
                        )
                    )

                    if (
                        overlap_tokens
                        + tokens
                        > cls.OVERLAP_TOKENS
                    ):
                        break

                    overlap.insert(
                        0,
                        old
                    )

                    overlap_tokens += (
                        tokens
                    )

                current_chunk = (
                    overlap
                    + [paragraph]
                )

                current_tokens = (
                    overlap_tokens
                    + paragraph_tokens
                )

            else:

                current_chunk.append(
                    paragraph
                )

                current_tokens += (
                    paragraph_tokens
                )

        if current_chunk:

            chunks.append(
                cls.build_chunk(
                    chunk_index,
                    current_chunk,
                    current_tokens
                )
            )

        return chunks