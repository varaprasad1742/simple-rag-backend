from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Depends,
    HTTPException
)

from sqlalchemy.ext.asyncio import (
    AsyncSession
)

from app.core.database import (
    get_db
)

from app.core.dependencies import (
    get_current_user
)

from app.schemas.document import (
    DocumentResponse
)

from app.services.document_service import (
    DocumentService
)

from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


@router.get("")
async def list_documents(
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):
    """
    Get all documents for the current user
    """
    documents = await (
        DocumentRepository
        .get_user_documents(
            db,
            current_user.id
        )
    )
    
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "file_path": doc.file_path,
        }
        for doc in documents
    ]


@router.post(
    "/upload",
    response_model=DocumentResponse
)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):
    
    return await (
        DocumentService.save_file(
            file=file,
            user_id=current_user.id,
            db=db
        )
    )

@router.get(
    "/{document_id}/chunks"
)
async def get_chunks(
    document_id: str,
    db: AsyncSession = Depends(
        get_db
    )
):

    chunks = await (
        ChunkRepository
        .get_by_document(
            db,
            document_id
        )
    )

    return [
        {
            "chunk_index":
                chunk.chunk_index,

            "filename":
                chunk.filename,

            "start_page":
                chunk.start_page,

            "end_page":
                chunk.end_page,

            "token_count":
                chunk.token_count,

            "indexed":
                chunk.indexed,
            "content":
                chunk.content
        }
        for chunk in chunks
    ]


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):
    """
    Get single document details with metadata
    """
    document = await (
        DocumentRepository
        .get_by_id(
            db,
            document_id
        )
    )
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    
    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )
    
    return {
        "id": document.id,
        "filename": document.filename,
        "file_path": document.file_path,
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):
    """
    Delete a document and all its associated chunks
    """
    document = await (
        DocumentRepository
        .get_by_id(
            db,
            document_id
        )
    )
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    
    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )
    
    await DocumentRepository.delete(db, document_id)
    
    return {
        "message": f"Document {document_id} deleted successfully",
        "status": "success"
    }