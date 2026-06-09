from sqlalchemy import (
    select,
    delete
)

from app.models.chat import (
    Chat
)


class ChatRepository:

    @staticmethod
    async def create(
        db,
        chat: Chat
    ):

        db.add(chat)

        await db.commit()

        await db.refresh(chat)

        return chat

    @staticmethod
    async def get_by_id(
        db,
        chat_id: str
    ):

        result = await db.execute(
            select(Chat)
            .where(
                Chat.id == chat_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_chats(
        db,
        user_id: str
    ):

        result = await db.execute(
            select(Chat)
            .where(
                Chat.user_id == user_id
            )
            .order_by(
                Chat.updated_at.desc()
            )
        )

        return result.scalars().all()

    @staticmethod
    async def touch(
        db,
        chat: Chat
    ):

        await db.commit()

        await db.refresh(chat)

        return chat

    @staticmethod
    async def update(
        db,
        chat: Chat,
        title: str = None
    ):
        """
        Update chat title
        """
        if title:
            chat.title = title

        await db.commit()

        await db.refresh(chat)

        return chat

    @staticmethod
    async def delete(
        db,
        chat_id: str
    ):
        """
        Delete a chat by ID
        """
        await db.execute(
            delete(Chat)
            .where(
                Chat.id == chat_id
            )
        )

        await db.commit()