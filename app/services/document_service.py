import os

from fastapi import UploadFile

from app.models.document import (
    Document
)

from app.repositories.document_repository import (
    DocumentRepository
)

from app.observability.decorators import (
    observe
)
from app.rag.parser import (
    PDFParser
)
from app.models.chunk import Chunk

from app.rag.chunker import (
    SemanticParagraphChunker
)

from app.models.chunk import Chunk

from app.repositories.chunk_repository import (
    ChunkRepository
)

from app.services.index_service import IndexService

from app.services.cache_service import CacheService

class DocumentService:

    @staticmethod
    @observe(f"File Uploading - Step 1")
    async def save_file(
        file: UploadFile,
        user_id: str,
        db
    ):

        user_dir = (
            f"uploads/{user_id}"
        )

        os.makedirs(
            user_dir,
            exist_ok=True
        )

        file_path = (
            f"{user_dir}/{file.filename}"
        )

        content = await file.read()

        with open(
            file_path,
            "wb"
        ) as f:
            f.write(content)

        document = Document(
            user_id=user_id,
            filename=file.filename,
            file_path=file_path,
        )
        document = await (
            DocumentRepository.create(
                db,
                document
            )
        )

        await DocumentService.process_document(
            document,
            db
        )
        CacheService.invalidate_user(
            user_id
        )
        return document
    
    @staticmethod
    @observe("Document Processing Step 2")
    async def process_document(
        document,
        db
    ):

        pages = await (
            PDFParser.extract_pages(
                file_path=document.file_path,
                user_id=document.user_id,
                document_id=document.id,
                filename=document.filename
            )
        )

        await DocumentService.create_chunks(
            pages=pages,
            document=document,
            db=db
        )
        await (
            IndexService.index_document(
                document.id,
                db
            )
        )   
        return document

    @staticmethod
    @observe("Creating Chunks Step 2.2")
    async def create_chunks(
        pages,
        document,
        db
    ):

        chunks = await (
            SemanticParagraphChunker.chunk_text(
                pages
            )
        )

        entities = []

        for chunk in chunks:

            entities.append(
                Chunk(
                    user_id=chunk["user_id"],

                    document_id=chunk[
                        "document_id"
                    ],

                    filename=chunk[
                        "filename"
                    ],

                    chunk_index=chunk[
                        "chunk_index"
                    ],

                    start_page=chunk[
                        "start_page"
                    ],

                    end_page=chunk[
                        "end_page"
                    ],

                    token_count=chunk[
                        "token_count"
                    ],

                    content=chunk[
                        "content"
                    ]
                )
            )

        await ChunkRepository.bulk_create(
            db,
            entities
        )

        return len(entities)