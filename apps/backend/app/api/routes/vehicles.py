import uuid
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbDep, DispatcherUser
from app.db.models.compliance import AnnualInspection, MaintenanceItem, RoadsideInspection
from app.db.models.fleet import Vehicle
from app.schemas.compliance import VehicleComplianceSummary
from app.schemas.fleet import VehicleCreate, VehicleResponse, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.post("", response_model=VehicleResponse, status_code=201)
async def create_vehicle(body: VehicleCreate, db: DbDep, user: DispatcherUser):
    vehicle = Vehicle(
        organization_id=user.organization_id,
        unit_number=body.unit_number,
        make=body.make,
        model=body.model,
        year=body.year,
        plate_state=body.plate_state,
        plate_number=body.plate_number,
        in_service_date=body.in_service_date,
    )
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.get("", response_model=list[VehicleResponse])
async def list_vehicles(
    db: DbDep,
    user: CurrentUser,
    vehicle_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
):
    q = select(Vehicle).where(Vehicle.organization_id == user.organization_id)
    if vehicle_status:
        q = q.where(Vehicle.status == vehicle_status)
    q = q.order_by(Vehicle.unit_number).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(vehicle_id: uuid.UUID, db: DbDep, user: CurrentUser):
    result = await db.execute(
        select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.organization_id == user.organization_id)
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(vehicle_id: uuid.UUID, body: VehicleUpdate, db: DbDep, user: DispatcherUser):
    result = await db.execute(
        select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.organization_id == user.organization_id)
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.get("/{vehicle_id}/compliance-summary", response_model=VehicleComplianceSummary)
async def get_vehicle_compliance(vehicle_id: uuid.UUID, db: DbDep, user: CurrentUser):
    vehicle_result = await db.execute(
        select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.organization_id == user.organization_id)
    )
    vehicle = vehicle_result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    # Latest annual inspection
    insp_result = await db.execute(
        select(AnnualInspection)
        .where(AnnualInspection.vehicle_id == vehicle_id)
        .order_by(AnnualInspection.inspected_at.desc())
        .limit(1)
    )
    latest_inspection = insp_result.scalar_one_or_none()

    annual_expires_at = None
    annual_status = "unknown"
    if latest_inspection:
        annual_expires_at = latest_inspection.expires_at
        if latest_inspection.expires_at:
            today = date.today()
            if latest_inspection.expires_at < today:
                annual_status = "expired"
            elif latest_inspection.expires_at < today + timedelta(days=30):
                annual_status = "expiring_soon"
            else:
                annual_status = "valid"

    # Open maintenance count
    maint_result = await db.execute(
        select(func.count()).where(
            MaintenanceItem.vehicle_id == vehicle_id,
            MaintenanceItem.status.in_(["open", "overdue", "due_soon"]),
        )
    )
    open_maint_count = maint_result.scalar() or 0

    # Latest roadside inspection
    roadside_result = await db.execute(
        select(RoadsideInspection)
        .where(RoadsideInspection.vehicle_id == vehicle_id)
        .order_by(RoadsideInspection.inspected_at.desc())
        .limit(1)
    )
    latest_roadside = roadside_result.scalar_one_or_none()

    return VehicleComplianceSummary(
        vehicle_id=vehicle_id,
        unit_number=vehicle.unit_number,
        status=vehicle.status,
        annual_inspection_expires_at=annual_expires_at,
        annual_inspection_status=annual_status,
        open_maintenance_count=open_maint_count,
        latest_roadside_inspection_at=latest_roadside.inspected_at if latest_roadside else None,
        out_of_service=vehicle.status == "out_of_service",
    )
