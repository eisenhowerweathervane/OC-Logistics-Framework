import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbDep, DispatcherUser
from app.db.models.fleet import Driver, Trailer
from app.db.models.loads import Assignment, Load, LoadStop
from app.db.models.documents import DocumentLink, Document
from app.schemas.compliance import DriverContextResponse
from app.schemas.fleet import DriverCreate, DriverResponse, DriverUpdate

router = APIRouter(prefix="/drivers", tags=["drivers"])

REQUIRED_DOC_TYPES_BY_STATUS = {
    "loaded": ["bol"],
    "delivered": ["bol", "pod"],
    "arrived_delivery": ["bol"],
}


@router.post("", response_model=DriverResponse, status_code=201)
async def create_driver(body: DriverCreate, db: DbDep, user: DispatcherUser):
    driver = Driver(
        organization_id=user.organization_id,
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
        license_state=body.license_state,
        hire_date=body.hire_date,
        pay_type=body.pay_type,
        pay_rate=body.pay_rate,
    )
    db.add(driver)
    await db.commit()
    await db.refresh(driver)
    return driver


@router.get("", response_model=list[DriverResponse])
async def list_drivers(
    db: DbDep,
    user: CurrentUser,
    driver_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
):
    q = select(Driver).where(Driver.organization_id == user.organization_id)
    if driver_status:
        q = q.where(Driver.status == driver_status)
    q = q.order_by(Driver.last_name, Driver.first_name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.get("/{driver_id}", response_model=DriverResponse)
async def get_driver(driver_id: uuid.UUID, db: DbDep, user: CurrentUser):
    result = await db.execute(
        select(Driver).where(Driver.id == driver_id, Driver.organization_id == user.organization_id)
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    return driver


@router.patch("/{driver_id}", response_model=DriverResponse)
async def update_driver(driver_id: uuid.UUID, body: DriverUpdate, db: DbDep, user: DispatcherUser):
    result = await db.execute(
        select(Driver).where(Driver.id == driver_id, Driver.organization_id == user.organization_id)
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(driver, field, value)
    await db.commit()
    await db.refresh(driver)
    return driver


@router.get("/by-phone/{phone}", response_model=DriverResponse)
async def get_driver_by_phone(phone: str, db: DbDep, user: CurrentUser):
    """Look up a driver by phone number. Normalizes input by stripping non-digit chars."""
    # Normalize: strip everything except digits and leading +
    normalized = phone.lstrip("+")
    digits_only = "".join(c for c in normalized if c.isdigit())

    # Try matching with and without country code prefix
    result = await db.execute(
        select(Driver).where(
            Driver.organization_id == user.organization_id,
            Driver.phone.isnot(None),
        )
    )
    drivers = list(result.scalars().all())
    for driver in drivers:
        if not driver.phone:
            continue
        driver_digits = "".join(c for c in driver.phone if c.isdigit())
        # Match last 10 digits (US number without country code)
        if driver_digits[-10:] == digits_only[-10:] and len(digits_only) >= 10:
            return driver
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No driver found with that phone number")


@router.get("/{driver_id}/current-context", response_model=DriverContextResponse)
async def get_driver_context(driver_id: uuid.UUID, db: DbDep, user: CurrentUser):
    result = await db.execute(
        select(Driver).where(
            Driver.id == driver_id, Driver.organization_id == user.organization_id
        )
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    # Find active assignment
    assign_result = await db.execute(
        select(Assignment)
        .where(Assignment.driver_id == driver_id, Assignment.unassigned_at.is_(None))
        .order_by(Assignment.assigned_at.desc())
        .limit(1)
        .options(selectinload(Assignment.load))
    )
    assignment = assign_result.scalar_one_or_none()

    if not assignment:
        return DriverContextResponse(
            driver_id=driver_id,
            driver_name=driver.full_name,
        )

    load = assignment.load

    # Next stop = earliest stop without a departed_at
    stops_result = await db.execute(
        select(LoadStop)
        .where(LoadStop.load_id == load.id, LoadStop.departed_at.is_(None))
        .order_by(LoadStop.seq)
        .limit(1)
    )
    next_stop = stops_result.scalar_one_or_none()

    # Trailer number
    trailer_number = None
    if assignment.trailer_id:
        trailer_result = await db.execute(
            select(Trailer).where(Trailer.id == assignment.trailer_id)
        )
        trailer = trailer_result.scalar_one_or_none()
        if trailer:
            trailer_number = trailer.trailer_number

    # Missing documents
    required = REQUIRED_DOC_TYPES_BY_STATUS.get(load.status, [])
    missing = []
    for doc_type in required:
        exists_result = await db.execute(
            select(DocumentLink)
            .where(
                DocumentLink.entity_type == "load",
                DocumentLink.entity_id == load.id,
            )
            .join(DocumentLink.document)
            .where(Document.doc_type == doc_type)
            .limit(1)
        )
        if not exists_result.scalar_one_or_none():
            missing.append(doc_type)

    next_stop_dict = None
    if next_stop:
        next_stop_dict = {
            "seq": next_stop.seq,
            "stop_type": next_stop.stop_type,
            "facility_name": next_stop.facility_name,
            "city": next_stop.city,
            "state": next_stop.state,
            "appt_start": next_stop.appt_start.isoformat() if next_stop.appt_start else None,
        }

    return DriverContextResponse(
        driver_id=driver_id,
        driver_name=driver.full_name,
        active_load_id=load.id,
        active_load_status=load.status,
        next_stop=next_stop_dict,
        missing_document_types=missing,
        trailer_number=trailer_number,
    )
