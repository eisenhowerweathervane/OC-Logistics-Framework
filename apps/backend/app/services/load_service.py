import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.fleet import Driver, Vehicle
from app.db.models.loads import (
    Assignment,
    Load,
    LoadStatusEvent,
    LoadStop,
    VALID_TRANSITIONS,
)
from app.schemas.loads import (
    AssignmentCreate,
    LoadCreate,
    LoadUpdate,
    StatusEventCreate,
)


async def create_load(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: LoadCreate,
    actor_user_id: Optional[uuid.UUID] = None,
) -> Load:
    load = Load(
        organization_id=org_id,
        broker_id=data.broker_id,
        shipping_document_number=data.shipping_document_number,
        reference_number=data.reference_number,
        commodity=data.commodity,
        weight_lbs=data.weight_lbs,
        pieces=data.pieces,
        rate_total=data.rate_total,
        rate_type=data.rate_type,
        miles_loaded=data.miles_loaded,
        miles_deadhead_est=data.miles_deadhead_est,
        notes=data.notes,
        status="quoted",
    )
    db.add(load)
    await db.flush()

    for stop_data in sorted(data.stops, key=lambda s: s.seq):
        stop = LoadStop(
            load_id=load.id,
            seq=stop_data.seq,
            stop_type=stop_data.stop_type,
            facility_name=stop_data.facility_name,
            address_line_1=stop_data.address_line_1,
            city=stop_data.city,
            state=stop_data.state,
            zip=stop_data.zip,
            appt_start=stop_data.appt_start,
            appt_end=stop_data.appt_end,
            contact_name=stop_data.contact_name,
            contact_phone=stop_data.contact_phone,
        )
        db.add(stop)

    await db.commit()
    return await get_load(db, load.id, org_id)


async def get_load(db: AsyncSession, load_id: uuid.UUID, org_id: uuid.UUID) -> Load:
    result = await db.execute(
        select(Load)
        .where(Load.id == load_id, Load.organization_id == org_id)
        .options(
            selectinload(Load.stops),
            selectinload(Load.assignments),
            selectinload(Load.status_events),
            selectinload(Load.invoice_packet),
        )
    )
    load = result.scalar_one_or_none()
    if not load:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found")
    return load


async def list_loads(
    db: AsyncSession,
    org_id: uuid.UUID,
    load_status: Optional[str] = None,
    broker_id: Optional[uuid.UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50,
) -> list[Load]:
    q = select(Load).where(Load.organization_id == org_id)
    if load_status:
        q = q.where(Load.status == load_status)
    if broker_id:
        q = q.where(Load.broker_id == broker_id)
    if date_from:
        q = q.where(Load.created_at >= date_from)
    if date_to:
        q = q.where(Load.created_at <= date_to)
    q = q.order_by(Load.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all())


async def update_load(
    db: AsyncSession, load_id: uuid.UUID, org_id: uuid.UUID, data: LoadUpdate
) -> Load:
    load = await get_load(db, load_id, org_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(load, field, value)
    await db.commit()
    return await get_load(db, load_id, org_id)


async def assign_load(
    db: AsyncSession,
    load_id: uuid.UUID,
    org_id: uuid.UUID,
    data: AssignmentCreate,
    dispatcher_user_id: Optional[uuid.UUID] = None,
) -> Assignment:
    load = await get_load(db, load_id, org_id)

    # Validate driver belongs to same org
    if data.driver_id:
        driver_result = await db.execute(
            select(Driver).where(Driver.id == data.driver_id)
        )
        driver = driver_result.scalar_one_or_none()
        if not driver or driver.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Driver does not belong to this organization",
            )

    # Validate vehicle belongs to same org
    if data.vehicle_id:
        vehicle_result = await db.execute(
            select(Vehicle).where(Vehicle.id == data.vehicle_id)
        )
        vehicle = vehicle_result.scalar_one_or_none()
        if not vehicle or vehicle.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vehicle does not belong to this organization",
            )

    now = datetime.now(timezone.utc)
    assignment = Assignment(
        load_id=load.id,
        driver_id=data.driver_id,
        vehicle_id=data.vehicle_id,
        trailer_id=data.trailer_id,
        assigned_at=now,
        dispatcher_user_id=dispatcher_user_id,
        created_at=now,
    )
    db.add(assignment)

    # Transition load to dispatched if it's booked
    if load.status == "booked":
        load.status = "dispatched"

    await db.commit()
    await db.refresh(assignment)
    return assignment


async def append_status_event(
    db: AsyncSession,
    load_id: uuid.UUID,
    org_id: uuid.UUID,
    data: StatusEventCreate,
    actor_user_id: Optional[uuid.UUID] = None,
    actor_driver_id: Optional[uuid.UUID] = None,
) -> LoadStatusEvent:
    load = await get_load(db, load_id, org_id)

    allowed = VALID_TRANSITIONS.get(load.status, [])
    if data.status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid transition: {load.status!r} → {data.status!r}. Allowed: {allowed}",
        )

    now = datetime.now(timezone.utc)
    event = LoadStatusEvent(
        load_id=load.id,
        status=data.status,
        occurred_at=data.occurred_at,
        actor_user_id=actor_user_id,
        actor_driver_id=actor_driver_id,
        location_city=data.location_city,
        note=data.note,
        source_channel=data.source_channel,
        source_message_id=data.source_message_id,
        created_at=now,
    )
    db.add(event)
    load.status = data.status

    await db.commit()
    await db.refresh(event)

    # Enqueue background tasks when load reaches delivered
    if data.status == "delivered":
        from app.worker.queue import enqueue
        await enqueue("check_invoice_readiness", str(load_id))

        # Get driver name for Slack notification
        driver_name = "Unknown driver"
        active_assignments = [a for a in load.assignments if a.unassigned_at is None]
        if active_assignments:
            from app.db.models.fleet import Driver
            driver_result = await db.execute(
                select(Driver).where(Driver.id == active_assignments[0].driver_id)
            )
            driver = driver_result.scalar_one_or_none()
            if driver:
                driver_name = f"{driver.first_name} {driver.last_name}"
        await enqueue("notify_load_delivered", str(load_id), driver_name)

    return event
