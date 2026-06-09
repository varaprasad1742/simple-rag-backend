from sqlalchemy.ext.asyncio import (
    AsyncSession
)

from sqlalchemy import select, delete

from app.models.document import (
    Document
)


class DocumentRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        document: Document
    ):

        db.add(document)

        await db.commit()

        await db.refresh(document)

        return document

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        document_id: str
    ):

        result = await db.execute(
            select(Document)
            .where(
                Document.id == document_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_user(
        db: AsyncSession,
        user_id: str
    ):

        result = await db.execute(
            select(Document)
            .where(
                Document.user_id == user_id
            )
        )

        return result.scalars().all()

    @staticmethod
    async def get_user_documents(
        db: AsyncSession,
        user_id: str
    ):
        """
        Get all documents for a user
        """
        result = await db.execute(
            select(Document)
            .where(
                Document.user_id == user_id
            )
        )

        return result.scalars().all()
    
    @staticmethod
    async def update_text(
        db: AsyncSession,
        document: Document,
        text: str
    ):

        document.text_content = text

        await db.commit()

        await db.refresh(
            document
        )

        return document

    @staticmethod
    async def delete(
        db: AsyncSession,
        document_id: str
    ):
        """
        Delete a document by ID
        """
        await db.execute(
            delete(Document)
            .where(
                Document.id == document_id
            )
        )

        await db.commit()