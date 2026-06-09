from fastapi import (
    APIRouter,
    Depends,
    HTTPException
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

from app.repositories.trace_repository import (
    TraceRepository
)
import json

router = APIRouter(
    prefix="/traces",
    tags=["Traces"]
)

@router.get("")
async def get_traces(
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    ),
    limit: int = 50,
    offset: int = 0
):

    traces = await (
        TraceRepository
        .get_user_traces(
            db,
            current_user.id
        )
    )

    return [
        {
            "trace_id":
            trace.trace_id,

            "pipeline_type":
            trace.pipeline_type,

            "status":
            trace.status,

            "created_at":
            trace.created_at
        }
        for trace in traces
    ]


@router.get("/search")
async def search_traces(
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    ),
    pipeline_type: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Search traces with filters
    """
    traces = await (
        TraceRepository
        .get_user_traces(
            db,
            current_user.id,
            limit=limit
        )
    )
    
    # Filter by pipeline_type if provided
    if pipeline_type:
        traces = [t for t in traces if t.pipeline_type == pipeline_type]
    
    # Filter by status if provided
    if status:
        traces = [t for t in traces if t.status == status]
    
    # Apply offset
    traces = traces[offset:]
    
    return [
        {
            "trace_id": trace.trace_id,
            "pipeline_type": trace.pipeline_type,
            "status": trace.status,
            "created_at": trace.created_at
        }
        for trace in traces
    ]


@router.get(
    "/{trace_id}"
)
async def get_trace(
    trace_id: str,
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):
    run = await (
            TraceRepository
            .get_run_by_trace_id(
                db,
                trace_id
            )
        )
    if not run:

        raise HTTPException(
            status_code=404,
            detail="Trace not found"
        )

    if run.user_id != current_user.id:

        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )
    steps = await (
        TraceRepository
        .get_trace_steps(
            db,
            run.id
        )
    )
    return {

            "trace_id":
            run.trace_id,

            "pipeline_type":
            run.pipeline_type,

            "status":
            run.status,

            "created_at":
            run.created_at,

            "steps": [

                {
                    "step_name":
                    step.step_name,

                    "duration":
                    step.duration,

                    "status":
                    step.status,

                    "trace_metadata":
                    json.loads(
                        step.trace_metadata
                    )
                    if step.trace_metadata
                    else {}
                }

                for step in steps
            ]
        }


@router.get("/latest")
async def latest_trace(
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):
    traces = await (
        TraceRepository
        .get_user_traces(
            db,
            current_user.id,
            limit=1
        )
    )
    if not traces:
        return None

    return {
        "trace_id":
        traces[0].trace_id,

        "pipeline_type":
        traces[0].pipeline_type
    }


@router.delete("/{trace_id}")
async def delete_trace(
    trace_id: str,
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):
    """
    Delete a trace and all its steps
    """
    run = await (
        TraceRepository
        .get_run_by_trace_id(
            db,
            trace_id
        )
    )
    
    if not run:
        raise HTTPException(
            status_code=404,
            detail="Trace not found"
        )

    if run.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )
    
    await TraceRepository.delete(db, run.id)
    
    return {
        "message": f"Trace {trace_id} deleted successfully",
        "status": "success"
    }


@router.get("/{trace_id}/export")
async def export_trace(
    trace_id: str,
    db: AsyncSession = Depends(
        get_db
    ),
    current_user=Depends(
        get_current_user
    )
):
    """
    Export trace as JSON
    """
    run = await (
        TraceRepository
        .get_run_by_trace_id(
            db,
            trace_id
        )
    )
    
    if not run:
        raise HTTPException(
            status_code=404,
            detail="Trace not found"
        )

    if run.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )
    
    steps = await (
        TraceRepository
        .get_trace_steps(
            db,
            run.id
        )
    )
    
    return {
        "trace_id": run.trace_id,
        "pipeline_type": run.pipeline_type,
        "status": run.status,
        "created_at": run.created_at,
        "steps": [
            {
                "step_name": step.step_name,
                "duration": step.duration,
                "status": step.status,
                "trace_metadata": json.loads(step.trace_metadata) if step.trace_metadata else {}
            }
            for step in steps
        ]
    }