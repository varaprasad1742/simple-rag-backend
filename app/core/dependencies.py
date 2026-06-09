from jose import jwt
from jose import JWTError

from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.core.config import settings

from app.repositories.user_repository import UserRepository

from app.core.request_context import (
    trace_id_ctx,
    user_id_ctx
)

from app.observability.collector import (
    init_steps
)

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from uuid import uuid4

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):

    try:

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user_id = payload.get("sub")

    user = await UserRepository.get_by_id(
        db,
        user_id
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    user_id_ctx.set(user.id)
    trace_id_ctx.set(
    str(uuid4())
)

  

    init_steps()
    return user