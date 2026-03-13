from fastapi import APIRouter
from sqlalchemy import text

from app.db.base import AsyncSessionLocal
from app.services import storage_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    # DB check
    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    # Storage check
    storage_ok = storage_service.check_health()

    all_ok = db_ok and storage_ok
    return {
        "ok": all_ok,
        "db": "ok" if db_ok else "error",
        "storage": "ok" if storage_ok else "error",
    }
