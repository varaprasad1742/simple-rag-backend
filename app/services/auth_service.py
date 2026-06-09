from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

from app.schemas.user import UserCreate

from app.repositories.user_repository import UserRepository

from app.core.security import (
    hash_password,
    verify_password,
)

from app.core.jwt import create_access_token


class AuthService:

    @staticmethod
    async def register(
        db: AsyncSession,
        payload: UserCreate
    ):

        existing = await UserRepository.get_by_email(
            db,
            payload.email
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Email already exists"
            )
        
        user = User(
            email=payload.email,
            hashed_password=hash_password(
                payload.password
            )
        )

        user = await UserRepository.create(
            db,
            user
        )

        return user

    @staticmethod
    async def login(
        db: AsyncSession,
        email: str,
        password: str
    ):

        user = await UserRepository.get_by_email(
            db,
            email
        )

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        if not verify_password(
            password,
            user.hashed_password
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        token = create_access_token(
            {
                "sub": user.id
            }
        )

        return {
            "access_token": token,
            "token_type": "bearer"
        }