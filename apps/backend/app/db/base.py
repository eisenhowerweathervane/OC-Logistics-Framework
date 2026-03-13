import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings

# ── Declarative base & mixins ─────────────────────────────────────────────────


class Base(AsyncAttrs, DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ── Session registry (supports sandbox mode) ─────────────────────────────────

SANDBOX_STATE_FILE = Path("/tmp/oc_sandbox_state.json")
SANDBOX_DB_NAME = "oc_logistics_sandbox"


def _sandbox_database_url() -> str:
    """Derive sandbox DB URL from the production URL by swapping the database name."""
    base = settings.database_url
    # Replace the last path segment (database name) with the sandbox name
    parts = base.rsplit("/", 1)
    return f"{parts[0]}/{SANDBOX_DB_NAME}"


class SessionRegistry:
    """Manages production and sandbox database engines.

    Reads persisted sandbox state from disk on init so the mode
    survives backend restarts.
    """

    def __init__(self) -> None:
        self.prod_engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
        self.prod_session = async_sessionmaker(self.prod_engine, class_=AsyncSession, expire_on_commit=False)

        self.sandbox_engine = None
        self.sandbox_session = None
        self._sandbox_active = False

        # Restore persisted sandbox state
        if SANDBOX_STATE_FILE.exists():
            try:
                state = json.loads(SANDBOX_STATE_FILE.read_text())
                if state.get("active"):
                    self._init_sandbox_engine()
                    self._sandbox_active = True
            except Exception:
                pass

    def _init_sandbox_engine(self) -> None:
        url = _sandbox_database_url()
        self.sandbox_engine = create_async_engine(url, echo=False, pool_pre_ping=True)
        self.sandbox_session = async_sessionmaker(self.sandbox_engine, class_=AsyncSession, expire_on_commit=False)

    @property
    def is_sandbox(self) -> bool:
        return self._sandbox_active

    def get_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if self._sandbox_active and self.sandbox_session:
            return self.sandbox_session
        return self.prod_session

    async def activate_sandbox(self) -> None:
        """Switch to sandbox database."""
        if not self.sandbox_engine:
            self._init_sandbox_engine()
        self._sandbox_active = True
        self._persist_state()

    async def deactivate_sandbox(self) -> None:
        """Switch back to production database and dispose sandbox engine."""
        self._sandbox_active = False
        if self.sandbox_engine:
            await self.sandbox_engine.dispose()
            self.sandbox_engine = None
            self.sandbox_session = None
        self._persist_state()

    def _persist_state(self) -> None:
        SANDBOX_STATE_FILE.write_text(json.dumps({"active": self._sandbox_active}))


# Global registry instance
registry = SessionRegistry()

# Backwards-compatible aliases used throughout the codebase
engine = registry.prod_engine
AsyncSessionLocal = registry.prod_session


async def get_db():
    sessionmaker = registry.get_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
        finally:
            await session.close()
