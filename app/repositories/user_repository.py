from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        user: User
    ) -> User:

        db.add(user)

        await db.commit()

        await db.refresh(user)

        return user

    @staticmethod
    async def get_by_email(
        db: AsyncSession,
        email: str
    ) -> User | None:

        stmt = select(User).where(
            User.email == email
        )

        result = await db.execute(stmt)

        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        user_id: str
    ) -> User | None:

        stmt = select(User).where(
            User.id == user_id
        )

        result = await db.execute(stmt)

        return result.scalar_one_or_none()