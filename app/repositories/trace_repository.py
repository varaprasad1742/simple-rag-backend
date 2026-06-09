from sqlalchemy import (
    select
)

from sqlalchemy.orm import (
    selectinload
)

from app.models.pipeline_run import (
    PipelineRun
)

from app.models.pipeline_step import (
    PipelineStep
)


class TraceRepository:

    @staticmethod
    async def create_run(
        db,
        run: PipelineRun
    ):

        db.add(run)

        await db.commit()

        await db.refresh(run)

        return run

    @staticmethod
    async def create_step(
        db,
        step: PipelineStep
    ):

        db.add(step)

        await db.commit()

        await db.refresh(step)

        return step

    @staticmethod
    async def bulk_create_steps(
        db,
        steps: list[PipelineStep]
    ):

        db.add_all(
            steps
        )

        await db.commit()

        return steps

    @staticmethod
    async def get_run_by_trace_id(
        db,
        trace_id: str
    ):

        result = await db.execute(
            select(
                PipelineRun
            )
            .where(
                PipelineRun.trace_id
                == trace_id
            )
        )

        return (
            result
            .scalar_one_or_none()
        )

    @staticmethod
    async def get_run_by_id(
        db,
        run_id: str
    ):

        result = await db.execute(
            select(
                PipelineRun
            )
            .where(
                PipelineRun.id
                == run_id
            )
        )

        return (
            result
            .scalar_one_or_none()
        )

    @staticmethod
    async def get_user_traces(
        db,
        user_id: str,
        limit: int = 50
    ):

        result = await db.execute(
            select(
                PipelineRun
            )
            .where(
                PipelineRun.user_id
                == user_id
            )
            .order_by(
                PipelineRun.created_at.desc()
            )
            .limit(limit)
        )

        return (
            result
            .scalars()
            .all()
        )

    @staticmethod
    async def get_trace_details(
        db,
        trace_id: str
    ):

        result = await db.execute(
            select(
                PipelineRun
            )
            .options(
                selectinload(
                    PipelineRun.steps
                )
            )
            .where(
                PipelineRun.trace_id
                == trace_id
            )
        )

        return (
            result
            .scalar_one_or_none()
        )

    @staticmethod
    async def get_trace_steps(
        db,
        run_id: str
    ):

        result = await db.execute(
            select(
                PipelineStep
            )
            .where(
                PipelineStep.pipeline_run_id
                == run_id
            )
            .order_by(
                PipelineStep.created_at.asc()
            )
        )

        return (
            result
            .scalars()
            .all()
        )

    @staticmethod
    async def update_run_status(
        db,
        run: PipelineRun,
        status: str
    ):

        run.status = status

        await db.commit()

        await db.refresh(run)

        return run

    @staticmethod
    async def delete_trace(
        db,
        trace_id: str
    ):

        run = await (
            TraceRepository
            .get_run_by_trace_id(
                db,
                trace_id
            )
        )

        if not run:
            return False

        await db.delete(
            run
        )

        await db.commit()

        return True