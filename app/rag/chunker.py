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

    MAX_TOKENS = 256

    MIN_CHUNK_TOKENS = 128

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


class RecursiveChunker:
    """
    High-throughput recursive token chunker for larger documents.
    Recursively splits using separators ["\n\n", "\n", ". ", " ", ""]
    to produce balanced, context-preserving chunks with token overlap.
    """
    CHUNK_SIZE = 384
    CHUNK_OVERLAP = 64
    SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    tokenizer = tiktoken.get_encoding("cl100k_base")

    @classmethod
    def count_tokens(cls, text: str) -> int:
        return len(cls.tokenizer.encode(text))

    @classmethod
    def _split_text_recursive(cls, text: str, separators: list[str]) -> list[str]:
        if not text.strip():
            return []

        if cls.count_tokens(text) <= cls.CHUNK_SIZE or not separators:
            return [text]

        sep = separators[0]
        next_separators = separators[1:]

        if sep == "":
            tokens = cls.tokenizer.encode(text)
            fragments = []
            for i in range(0, len(tokens), cls.CHUNK_SIZE):
                fragments.append(cls.tokenizer.decode(tokens[i : i + cls.CHUNK_SIZE]))
            return fragments

        if sep in text:
            splits = text.split(sep)
        else:
            return cls._split_text_recursive(text, next_separators)

        result = []
        for piece in splits:
            piece_str = piece.strip()
            if not piece_str:
                continue
            if cls.count_tokens(piece_str) <= cls.CHUNK_SIZE:
                result.append(piece_str)
            else:
                result.extend(cls._split_text_recursive(piece_str, next_separators))

        return result

    @classmethod
    @observe("Recursive chunking Step 2.2.1")
    async def chunk_text(cls, pages: list[dict]) -> list[dict]:
        fragments = []
        for page in pages:
            page_text = page.get("text", "")
            if not page_text.strip():
                continue
            page_frags = cls._split_text_recursive(page_text, cls.SEPARATORS)
            for frag in page_frags:
                fragments.append({
                    "user_id": page["user_id"],
                    "document_id": page["document_id"],
                    "filename": page["filename"],
                    "page_number": page["page_number"],
                    "text": frag,
                    "tokens": cls.count_tokens(frag)
                })

        if not fragments:
            return []

        chunks = []
        chunk_index = 0
        current_chunk_fragments = []
        current_tokens = 0

        for frag in fragments:
            frag_tokens = frag["tokens"]
            if current_chunk_fragments and (current_tokens + frag_tokens > cls.CHUNK_SIZE):
                chunks.append(cls._build_chunk(chunk_index, current_chunk_fragments, current_tokens))
                chunk_index += 1

                overlap_fragments = []
                overlap_tokens = 0
                for prev in reversed(current_chunk_fragments):
                    if overlap_tokens + prev["tokens"] > cls.CHUNK_OVERLAP:
                        break
                    overlap_fragments.insert(0, prev)
                    overlap_tokens += prev["tokens"]

                current_chunk_fragments = overlap_fragments + [frag]
                current_tokens = overlap_tokens + frag_tokens
            else:
                current_chunk_fragments.append(frag)
                current_tokens += frag_tokens

        if current_chunk_fragments:
            chunks.append(cls._build_chunk(chunk_index, current_chunk_fragments, current_tokens))

        return chunks

    @classmethod
    def _build_chunk(cls, chunk_index: int, frags: list[dict], token_count: int) -> dict:
        first = frags[0]
        pages = [f["page_number"] for f in frags]
        content = "\n\n".join(f["text"] for f in frags)
        return {
            "user_id": first["user_id"],
            "document_id": first["document_id"],
            "filename": first["filename"],
            "chunk_index": chunk_index,
            "start_page": min(pages),
            "end_page": max(pages),
            "token_count": token_count,
            "content": content
        }


class ChunkerRouter:
    """
    Selects chunker strategy dynamically based on document size:
    - Standard/Small documents (<= 2500 tokens & <= 5 pages): SemanticParagraphChunker
      (optimal for high-precision semantic boundaries).
    - Large documents (> 2500 tokens or > 5 pages): RecursiveChunker
      (optimal for throughput and deep content without embedding bottlenecks).
    """
    LARGE_DOC_TOKEN_THRESHOLD = 2500
    LARGE_DOC_PAGE_THRESHOLD = 5

    @classmethod
    @observe("Chunker Selection Step 2.2.0")
    async def chunk_document(cls, pages: list[dict]) -> tuple[list[dict], str, dict]:
        tokenizer = tiktoken.get_encoding("cl100k_base")
        total_tokens = sum(len(tokenizer.encode(p.get("text", ""))) for p in pages)
        page_count = len(pages)

        is_large = (
            total_tokens > cls.LARGE_DOC_TOKEN_THRESHOLD
            or page_count > cls.LARGE_DOC_PAGE_THRESHOLD
        )

        if is_large:
            strategy = "RecursiveChunker"
            reason = (
                f"Document size ({total_tokens} tokens, {page_count} pages) exceeds threshold "
                f"({cls.LARGE_DOC_TOKEN_THRESHOLD} tokens / {cls.LARGE_DOC_PAGE_THRESHOLD} pages). "
                f"Switched to high-performance RecursiveChunker."
            )
            chunks = await RecursiveChunker.chunk_text(pages)
        else:
            strategy = "SemanticParagraphChunker"
            reason = (
                f"Document size ({total_tokens} tokens, {page_count} pages) is within standard threshold. "
                f"Using SemanticParagraphChunker for semantic boundary alignment."
            )
            chunks = await SemanticParagraphChunker.chunk_text(pages)

        stats = {
            "strategy": strategy,
            "total_tokens": total_tokens,
            "page_count": page_count,
            "total_chunks": len(chunks),
            "reason": reason
        }

        return chunks, strategy, stats