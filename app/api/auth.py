from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse
)
from fastapi.security import OAuth2PasswordRequestForm

from app.services.auth_service import AuthService

from app.core.dependencies import (
    get_current_user
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db)
):

    return await AuthService.register(
        db,
        payload
    )


@router.post(
    "/login",
    response_model=TokenResponse
)
async def login(
    payload: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):

    return await AuthService.login(
        db,
        payload.username,
        payload.password
    )


@router.get(
    "/me",
    response_model=UserResponse
)
async def me(
    current_user=Depends(
        get_current_user
    )
):
    return current_user


@router.post("/logout")
async def logout(
    current_user=Depends(
        get_current_user
    )
):
    """
    Logout endpoint (mainly for client-side token cleanup)
    """
    return {
        "message": "Successfully logged out",
        "status": "success"
    }


@router.put(
    "/profile",
    response_model=UserResponse
)
async def update_profile(
    username: str = None,
    email: str = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(
        get_current_user
    )
):
    """
    Update user profile (username and/or email)
    """
    return await AuthService.update_profile(
        db,
        current_user,
        username,
        email
    )


@router.delete("/account")
async def delete_account(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(
        get_current_user
    )
):
    """
    Delete user account and all associated data
    """
    return await AuthService.delete_account(
        db,
        current_user
    )