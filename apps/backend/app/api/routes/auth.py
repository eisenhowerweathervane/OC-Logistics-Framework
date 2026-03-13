from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbDep
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token_safe,
    verify_password,
)
from app.db.models.org import User, UserRole
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbDep):
    result = await db.execute(
        select(User)
        .where(User.email == body.email, User.status == "active")
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
    )
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: DbDep):
    payload = decode_token_safe(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    import uuid

    result = await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"]), User.status == "active"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(user: CurrentUser):
    # Stateless JWT — client discards token. Future: add token blocklist via Redis.
    pass


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser):
    return UserResponse(
        id=str(user.id),
        email=user.email,
        roles=[ur.role.name for ur in user.user_roles if ur.role],
    )
