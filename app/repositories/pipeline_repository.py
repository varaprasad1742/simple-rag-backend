from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline_step import (
    PipelineStep
)


class PipelineRepository:

    @staticmethod
    async def create_step(
        db: AsyncSession,
        step: PipelineStep
    ):

        db.add(step)

        await db.commit()