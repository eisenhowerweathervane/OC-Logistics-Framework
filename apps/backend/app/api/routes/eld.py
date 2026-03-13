"""
ELD day log routes.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep, DispatcherUser
from app.db.models.compliance import EldDay
from app.db.models.fleet import Driver, Vehicle
from app.schemas.compliance_data import EldDayCreate, EldDayResponse

router = APIRouter(prefix="/eld", tags=["eld"])


@router.post("/days", response_model=EldDayResponse, status_code=201)
async def create_eld_day(body: EldDayCreate, db: DbDep, user: DispatcherUser):
    driver_result = await db.execute(
        select(Driver).where(
            Driver.id == body.driver_id, Driver.organization_id == user.organization_id
        )
    )
    if not driver_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    vehicle_result = await db.execute(
        select(Vehicle).where(
            Vehicle.id == body.vehicle_id, Vehicle.organization_id == user.organization_id
        )
    )
    if not vehicle_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    now = datetime.now(timezone.utc)
    day = EldDay(
        organization_id=user.organization_id,
        driver_id=body.driver_id,
        vehicle_id=body.vehicle_id,
        date_local=body.date_local,
        timezone_offset_minutes=body.timezone_offset_minutes,
        eld_vendor=body.eld_vendor,
        eld_device_id=body.eld_device_id,
        file_storage_key=body.file_storage_key,
        file_sha256=body.file_sha256,
        notes=body.notes,
        imported_at=now,
        created_at=now,
    )
    db.add(day)
    await db.commit()
    await db.refresh(day)
    return day


@router.get("/days", response_model=list[EldDayResponse])
async def list_eld_days(
    db: DbDep,
    user: CurrentUser,
    driver_id: Optional[uuid.UUID] = None,
    vehicle_id: Optional[uuid.UUID] = None,
    page: int = 1,
    page_size: int = 100,
):
    q = select(EldDay).where(EldDay.organization_id == user.organization_id)
    if driver_id:
        q = q.where(EldDay.driver_id == driver_id)
    if vehicle_id:
        q = q.where(EldDay.vehicle_id == vehicle_id)
    q = q.order_by(EldDay.date_local.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all())
