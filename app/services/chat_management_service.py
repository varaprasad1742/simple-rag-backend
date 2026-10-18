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

    @staticmethod
    async def update_chat(
        db,
        chat_id: str,
        title: str
    ):
        """
        Update a chat's title
        """
        chat = await ChatRepository.get_by_id(db, chat_id)
        return await ChatRepository.update(db, chat, title=title)

    @staticmethod
    async def delete_chat(
        db,
        chat_id: str
    ):
        """
        Delete a chat and all its messages
        """
        await ChatRepository.delete(db, chat_id)