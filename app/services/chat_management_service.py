from app.models.chat import (
    Chat
)

from app.repositories.chat_repository import (
    ChatRepository
)


class ChatManagementService:

    @staticmethod
    async def create_chat(
        db,
        user_id: str,
        title: str
    ):

        chat = Chat(
            user_id=user_id,
            title=title
        )

        return await (
            ChatRepository.create(
                db,
                chat
            )
        )

    @staticmethod
    async def list_chats(
        db,
        user_id: str
    ):

        return await (
            ChatRepository.get_user_chats(
                db,
                user_id
            )
        )