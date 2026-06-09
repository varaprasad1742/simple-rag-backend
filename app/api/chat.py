from fastapi import (
    APIRouter,
    Depends,
    HTTPException, BackgroundTasks
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

from app.services.chat_service import (
    ChatService
)

from app.services.chat_management_service import (
    ChatManagementService
)

from app.repositories.chat_repository import (
    ChatRepository
)

from app.repositories.message_repository import (
    MessageRepository
)

from app.schemas.chat import (
    ChatRequest,
    CreateChatRequest,
    ChatResponse
)
import json 

router = APIRouter(
    prefix="/chats",
    tags=["Chats"]
)

@router.post("")
async def create_chat(
    payload: CreateChatRequest,
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):

    chat = await (
        ChatManagementService.create_chat(
            db=db,
            user_id=current_user.id,
            title=payload.title
        )
    )

    return {
        "id": chat.id,
        "title": chat.title
    }


@router.get("")
async def get_chats(
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):

    chats = await (
        ChatRepository.get_user_chats(
            db,
            current_user.id
        )
    )

    return chats


@router.get("/{chat_id}")
async def get_chat(
    chat_id: str,
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):
    chat = await (
        ChatRepository.get_by_id(
            db,
            chat_id
        )
    )

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )
    
    messages = await (
        MessageRepository.get_chat_messages(
            db,
            chat_id
        )
    )
    return {
        "id": chat.id,
        "title": chat.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "citations": json.loads(m.citations) if m.citations else [],
                "created_at": m.created_at
            }
            for m in messages
        ]
    }

@router.post(
    "/{chat_id}/messages",
    response_model=ChatResponse
)
async def send_message(
    chat_id: str,
    payload: ChatRequest,
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):
    chat = await (
        ChatRepository.get_by_id(
            db,
            chat_id
        )
    )

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )
    
    return await (
        ChatService.chat(
            query=payload.query,
            user_id=current_user.id,
            chat_id=chat_id,
            db=db,
        )
    )


@router.put("/{chat_id}")
async def update_chat(
    chat_id: str,
    title: str,
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):
    """
    Update chat title
    """
    chat = await (
        ChatRepository.get_by_id(
            db,
            chat_id
        )
    )

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )
    
    updated_chat = await ChatManagementService.update_chat(
        db=db,
        chat_id=chat_id,
        title=title
    )
    
    return {
        "id": updated_chat.id,
        "title": updated_chat.title
    }


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: str,
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):
    """
    Delete a chat and all its messages
    """
    chat = await (
        ChatRepository.get_by_id(
            db,
            chat_id
        )
    )

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )
    
    await ChatManagementService.delete_chat(
        db=db,
        chat_id=chat_id
    )
    
    return {
        "message": f"Chat {chat_id} deleted successfully",
        "status": "success"
    }


@router.delete("/{chat_id}/messages/{message_id}")
async def delete_message(
    chat_id: str,
    message_id: str,
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):
    """
    Delete a message from a chat
    """
    chat = await (
        ChatRepository.get_by_id(
            db,
            chat_id
        )
    )

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )
    
    message = await MessageRepository.get_by_id(
        db,
        message_id
    )
    
    if not message or message.chat_id != chat_id:
        raise HTTPException(
            status_code=404,
            detail="Message not found"
        )
    
    await MessageRepository.delete(db, message_id)
    
    return {
        "message": f"Message {message_id} deleted successfully",
        "status": "success"
    }