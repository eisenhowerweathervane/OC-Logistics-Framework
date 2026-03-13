#!/usr/bin/env python3
"""
Run the backend locally with SQLite — no Docker, no Postgres, no Redis, no MinIO.

Usage (from project root):
    cd apps/backend && ../.venv/bin/python ../../scripts/run_local.py

Or:
    cd apps/backend && SKIP_TASK_QUEUE=true .venv/bin/python ../../scripts/run_local.py

What it does:
  1. Points DATABASE_URL at a local SQLite file (oc_logistics_dev.db)
  2. Disables Redis (SKIP_TASK_QUEUE=true)
  3. Creates all tables via SQLAlchemy metadata
  4. Runs the seed script if not already seeded
  5. Starts uvicorn on http://localhost:8000
"""
import asyncio
import os
import sys
from pathlib import Path

# Must set env vars BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///oc_logistics_dev.db"
os.environ["SKIP_TASK_QUEUE"] = "true"
os.environ.setdefault("JWT_SECRET", "local-dev-secret-change-in-prod")
os.environ.setdefault("S3_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("S3_BUCKET", "oc-logistics")
os.environ.setdefault("S3_ACCESS_KEY", "minioadmin")
os.environ.setdefault("S3_SECRET_KEY", "minioadmin")
os.environ.setdefault("SEED_OWNER_EMAIL", "owner@example.com")
os.environ.setdefault("SEED_OWNER_PASSWORD", "changeme")

# Ensure app is importable
backend_dir = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from app.db.base import Base, engine, AsyncSessionLocal
from app.core.security import hash_password


async def init_db():
    """Create all tables and seed if empty."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[run_local] SQLite tables created.")

    # Seed
    from sqlalchemy import select
    from app.db.models.org import Organization, Role, User, UserRole
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Organization).limit(1))
        if result.scalar_one_or_none():
            print("[run_local] Already seeded.")
            return

        now = datetime.now(timezone.utc)
        org = Organization(legal_name="My Trucking Co LLC", dba_name="My Trucking", country="US")
        db.add(org)
        await db.flush()

        roles = {}
        for name in ["owner", "dispatcher", "driver", "broker_viewer"]:
            role = Role(name=name, created_at=now)
            db.add(role)
            await db.flush()
            roles[name] = role

        owner = User(
            organization_id=org.id,
            email=os.environ["SEED_OWNER_EMAIL"],
            password_hash=hash_password(os.environ["SEED_OWNER_PASSWORD"]),
            status="active",
        )
        db.add(owner)
        await db.flush()
        db.add(UserRole(user_id=owner.id, role_id=roles["owner"].id, created_at=now))
        await db.commit()

        print(f"[run_local] Seeded org: {org.legal_name}")
        print(f"[run_local] Seeded user: {os.environ['SEED_OWNER_EMAIL']} / {os.environ['SEED_OWNER_PASSWORD']}")


def main():
    asyncio.run(init_db())
    print("\n[run_local] Starting uvicorn on http://localhost:8000")
    print("[run_local] API docs: http://localhost:8000/docs")
    print("[run_local] Login: owner@example.com / changeme")
    print("[run_local] DB: oc_logistics_dev.db (SQLite)")
    print("[run_local] Storage: S3/MinIO calls will fail (no MinIO running) — that's OK for UAT\n")

    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
