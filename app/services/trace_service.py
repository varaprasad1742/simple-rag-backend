import json

from app.core.request_context import (
    trace_id_ctx,
    user_id_ctx
)

from app.observability.collector import (
    get_steps
)

from app.models.pipeline_run import (
    PipelineRun
)

from app.models.pipeline_step import (
    PipelineStep
)

from app.repositories.trace_repository import (
    TraceRepository
)


class TraceService:

    @staticmethod
    async def save_current_trace(
        db,
        pipeline_type: str
    ):

        trace_id = trace_id_ctx.get()

        user_id = user_id_ctx.get()

        steps = get_steps()

        if not steps:
            return None

        run = await (
            TraceRepository.create_run(
                db,
                PipelineRun(
                    trace_id=trace_id,
                    user_id=user_id,
                    pipeline_type=pipeline_type,
                    status="success"
                )
            )
        )

        entities = []

        for step in steps:

            entities.append(
                PipelineStep(
                    pipeline_run_id=run.id,

                    step_name=
                    step["name"],

                    duration=
                    step["duration"],

                    status=
                    step["status"],

                    trace_metadata=
                    json.dumps(
                        step.get(
                            "trace_metadata",
                            {}
                        )
                    )
                )
            )

        await (
            TraceRepository
            .bulk_create_steps(
                db,
                entities
            )
        )

        return run