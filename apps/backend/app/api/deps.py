import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decode_token_safe
from app.db.base import get_db
from app.db.models.org import User, UserRole

bearer_scheme = HTTPBearer()

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: DbDep,
) -> User:
    payload = decode_token_safe(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id_raw = payload.get("sub")
    try:
        user_id = uuid.UUID(user_id_raw)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    result = await db.execute(
        select(User)
        .where(User.id == user_id, User.status == "active")
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(allowed: list[str]):
    async def _check(user: CurrentUser) -> User:
        user_roles = {ur.role.name for ur in user.user_roles if ur.role}
        if not user_roles.intersection(allowed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _check


# Pre-built role-gated user deps — use these directly in route signatures
# e.g.  async def create_load(user: DispatcherUser, ...)
DispatcherUser = Annotated[User, Depends(require_roles(["owner", "dispatcher"]))]
AnyStaffUser = Annotated[User, Depends(require_roles(["owner", "dispatcher", "driver"]))]
