import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str | UUID, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str | UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def decode_token_safe(token: str) -> dict[str, Any] | None:
    try:
        return decode_token(token)
    except JWTError:
        return None


# ── Token blocklist (Redis-backed) ──────────────────────────────────────────

_blocklist_redis: aioredis.Redis | None = None
_blocklist_available = True


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _get_blocklist_redis() -> aioredis.Redis | None:
    global _blocklist_redis, _blocklist_available
    if not _blocklist_available:
        return None
    if _blocklist_redis is None:
        try:
            _blocklist_redis = aioredis.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=2
            )
            await _blocklist_redis.ping()
        except Exception:
            logger.warning("Redis unavailable for token blocklist")
            _blocklist_available = False
            _blocklist_redis = None
            return None
    return _blocklist_redis


async def blocklist_token(token: str) -> None:
    """Add a token to the blocklist with TTL matching its remaining lifetime."""
    if os.environ.get("TESTING"):
        return
    payload = decode_token_safe(token)
    if not payload or "exp" not in payload:
        return
    ttl = int(payload["exp"] - datetime.now(timezone.utc).timestamp())
    if ttl <= 0:
        return
    r = await _get_blocklist_redis()
    if r is None:
        return
    try:
        await r.setex(f"blocklist:{_token_hash(token)}", ttl, "1")
    except Exception:
        logger.warning("Failed to blocklist token in Redis")


async def is_token_blocklisted(token: str) -> bool:
    """Check if a token has been blocklisted."""
    if os.environ.get("TESTING"):
        return False
    r = await _get_blocklist_redis()
    if r is None:
        return False
    try:
        return await r.exists(f"blocklist:{_token_hash(token)}") > 0
    except Exception:
        return False
