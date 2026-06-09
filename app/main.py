from fastapi import FastAPI

from app.core.config import settings
from contextlib import asynccontextmanager

from app.models.base import Base
from app.models.user import User

from app.core.database import engine
from prometheus_client import (
    generate_latest
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    Response
)
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )

    yield

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }

from app.api.auth import router as auth_router

app.include_router(
    auth_router
)



@app.get("/metrics")
async def metrics():

    return Response(
        generate_latest(),
        media_type="text/plain"
    )


from app.api.documents import (
    router as document_router
)

app.include_router(
    document_router
)

from app.api.chat import (
    router as chat_router
)

app.include_router(
    chat_router
)

from app.api import (
    traces
)

app.include_router(
    traces.router
)