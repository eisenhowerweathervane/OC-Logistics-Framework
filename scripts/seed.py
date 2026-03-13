"""
Seed script — run once against a fresh database.

Usage (from apps/backend directory):
    python -m scripts.seed
or from project root:
    python scripts/seed.py
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from project root or apps/backend
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import AsyncSessionLocal
from app.db.models.org import Organization, Role, User, UserRole


async def seed():
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        result = await db.execute(select(Organization).limit(1))
        if result.scalar_one_or_none():
            print("Already seeded — skipping.")
            return

        now = datetime.now(timezone.utc)

        # Organization
        org = Organization(
            legal_name="My Trucking Co LLC",
            dba_name="My Trucking",
            country="US",
        )
        db.add(org)
        await db.flush()

        # Roles (may already exist from migration 001, but upsert safely)
        role_names = ["owner", "dispatcher", "driver", "broker_viewer"]
        roles: dict[str, Role] = {}
        for name in role_names:
            result = await db.execute(select(Role).where(Role.name == name))
            role = result.scalar_one_or_none()
            if not role:
                role = Role(name=name, created_at=now)
                db.add(role)
                await db.flush()
            roles[name] = role

        # Owner user
        owner_email = settings.seed_owner_email
        owner_password = settings.seed_owner_password
        owner = User(
            organization_id=org.id,
            email=owner_email,
            password_hash=hash_password(owner_password),
            status="active",
        )
        db.add(owner)
        await db.flush()

        owner_role = UserRole(user_id=owner.id, role_id=roles["owner"].id, created_at=now)
        db.add(owner_role)

        await db.commit()

        print(f"Seeded organization: {org.legal_name} ({org.id})")
        print(f"Seeded owner user: {owner_email}")
        print("Retention policies were seeded in migration 004.")


if __name__ == "__main__":
    asyncio.run(seed())
