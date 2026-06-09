from sqlalchemy import (
    select,
    delete
)

from app.models.message import (
    Message
)


class MessageRepository:

    @staticmethod
    async def create(
        db,
        message: Message
    ):

        db.add(message)

        await db.commit()

        await db.refresh(message)

        return message

    @staticmethod
    async def get_by_id(
        db,
        message_id: str
    ):
        """
        Get a message by ID
        """
        result = await db.execute(
            select(Message)
            .where(
                Message.id == message_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_chat_messages(
        db,
        chat_id: str
    ):

        result = await db.execute(
            select(Message)
            .where(
                Message.chat_id
                == chat_id
            )
            .order_by(
                Message.created_at.asc()
            )
        )

        return result.scalars().all()

    @staticmethod
    async def get_recent_messages(
        db,
        chat_id: str,
        limit: int = 10
    ):

        result = await db.execute(
            select(Message)
            .where(
                Message.chat_id
                == chat_id
            )
            .order_by(
                Message.created_at.desc()
            )
            .limit(limit)
        )

        return list(
            reversed(
                result.scalars().all()
            )
        )

    @staticmethod
    async def delete(
        db,
        message_id: str
    ):
        """
        Delete a message by ID
        """
        await db.execute(
            delete(Message)
            .where(
                Message.id == message_id
            )
        )

        await db.commit()