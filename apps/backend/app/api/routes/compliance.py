"""
Compliance data entry routes: maintenance items, annual inspections, roadside inspections,
IFTA quarterly returns, IRP registration, fleet compliance scanning.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbDep, DispatcherUser
from app.db.models.compliance import (
    AnnualInspection,
    IftaDistanceByJurisdiction,
    IftaFuelByJurisdiction,
    IftaReturn,
    IrpYear,
    MaintenanceItem,
    RoadsideInspection,
)
from app.db.models.fleet import Vehicle
from app.schemas.compliance import (
    ComplianceAlert,
    IftaCalculateRequest,
    IftaReturnResponse,
    IftaReturnSummary,
    IrpYearCreate,
    IrpYearResponse,
)
from app.schemas.compliance_data import (
    AnnualInspectionCreate,
    AnnualInspectionResponse,
    MaintenanceItemCreate,
    MaintenanceItemResponse,
    MaintenanceItemUpdate,
    RoadsideInspectionCreate,
    RoadsideInspectionResponse,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])


# ── Maintenance items ─────────────────────────────────────────────────────────


@router.post("/maintenance", response_model=MaintenanceItemResponse, status_code=201)
async def create_maintenance_item(body: MaintenanceItemCreate, db: DbDep, user: DispatcherUser):
    vehicle_result = await db.execute(
        select(Vehicle).where(Vehicle.id == body.vehicle_id, Vehicle.organization_id == user.organization_id)
    )
    if not vehicle_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    item = MaintenanceItem(
        organization_id=user.organization_id,
        vehicle_id=body.vehicle_id,
        category=body.category,
        due_date=body.due_date,
        due_odometer=body.due_odometer,
        notes=body.notes,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/maintenance", response_model=list[MaintenanceItemResponse])
async def list_maintenance_items(
    db: DbDep,
    user: CurrentUser,
    vehicle_id: Optional[uuid.UUID] = None,
    item_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
):
    q = select(MaintenanceItem).where(MaintenanceItem.organization_id == user.organization_id)
    if vehicle_id:
        q = q.where(MaintenanceItem.vehicle_id == vehicle_id)
    if item_status:
        q = q.where(MaintenanceItem.status == item_status)
    q = q.order_by(MaintenanceItem.due_date.asc().nulls_last()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.patch("/maintenance/{item_id}", response_model=MaintenanceItemResponse)
async def update_maintenance_item(item_id: uuid.UUID, body: MaintenanceItemUpdate, db: DbDep, user: DispatcherUser):
    result = await db.execute(
        select(MaintenanceItem).where(
            MaintenanceItem.id == item_id,
            MaintenanceItem.organization_id == user.organization_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance item not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


# ── Annual inspections ────────────────────────────────────────────────────────


@router.post("/annual-inspections", response_model=AnnualInspectionResponse, status_code=201)
async def create_annual_inspection(body: AnnualInspectionCreate, db: DbDep, user: DispatcherUser):
    vehicle_result = await db.execute(
        select(Vehicle).where(Vehicle.id == body.vehicle_id, Vehicle.organization_id == user.organization_id)
    )
    if not vehicle_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    inspection = AnnualInspection(
        organization_id=user.organization_id,
        vehicle_id=body.vehicle_id,
        inspected_at=body.inspected_at,
        inspector_name=body.inspector_name,
        expires_at=body.expires_at,
        report_document_id=body.report_document_id,
    )
    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)
    return inspection


@router.get("/annual-inspections", response_model=list[AnnualInspectionResponse])
async def list_annual_inspections(
    db: DbDep,
    user: CurrentUser,
    vehicle_id: Optional[uuid.UUID] = None,
    page: int = 1,
    page_size: int = 50,
):
    q = select(AnnualInspection).where(AnnualInspection.organization_id == user.organization_id)
    if vehicle_id:
        q = q.where(AnnualInspection.vehicle_id == vehicle_id)
    q = q.order_by(AnnualInspection.inspected_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all())


# ── Roadside inspections ──────────────────────────────────────────────────────


@router.post("/roadside-inspections", response_model=RoadsideInspectionResponse, status_code=201)
async def create_roadside_inspection(body: RoadsideInspectionCreate, db: DbDep, user: DispatcherUser):
    vehicle_result = await db.execute(
        select(Vehicle).where(Vehicle.id == body.vehicle_id, Vehicle.organization_id == user.organization_id)
    )
    if not vehicle_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    inspection = RoadsideInspection(
        organization_id=user.organization_id,
        vehicle_id=body.vehicle_id,
        inspected_at=body.inspected_at,
        report_document_id=body.report_document_id,
        corrections_certified_at=body.corrections_certified_at,
    )
    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)
    return inspection


@router.get("/roadside-inspections", response_model=list[RoadsideInspectionResponse])
async def list_roadside_inspections(
    db: DbDep,
    user: CurrentUser,
    vehicle_id: Optional[uuid.UUID] = None,
    page: int = 1,
    page_size: int = 50,
):
    q = select(RoadsideInspection).where(RoadsideInspection.organization_id == user.organization_id)
    if vehicle_id:
        q = q.where(RoadsideInspection.vehicle_id == vehicle_id)
    q = q.order_by(RoadsideInspection.inspected_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all())


# ── IFTA quarterly returns ───────────────────────────────────────────────────


@router.post("/ifta/calculate", response_model=IftaReturnResponse)
async def calculate_ifta_return(body: IftaCalculateRequest, db: DbDep, user: DispatcherUser):
    """Calculate (or recalculate) an IFTA quarterly return from fuel purchases and load miles."""
    if body.quarter not in (1, 2, 3, 4):
        raise HTTPException(status_code=422, detail="Quarter must be 1-4")

    from app.services import compliance_service

    ifta_return = await compliance_service.build_ifta_return(db, user.organization_id, body.year, body.quarter)

    # Reload with relationships
    result = await db.execute(
        select(IftaReturn)
        .where(IftaReturn.id == ifta_return.id)
        .options(
            selectinload(IftaReturn.fuel_by_jurisdiction),
            selectinload(IftaReturn.distance_by_jurisdiction),
        )
    )
    loaded = result.scalar_one()

    return IftaReturnResponse(
        id=loaded.id,
        organization_id=loaded.organization_id,
        year=loaded.year,
        quarter=loaded.quarter,
        status=loaded.status,
        filed_at=loaded.filed_at,
        fuel_by_jurisdiction=[
            {"jurisdiction": f.jurisdiction, "gallons": f.gallons} for f in loaded.fuel_by_jurisdiction
        ],
        distance_by_jurisdiction=[
            {"jurisdiction": d.jurisdiction, "miles": d.miles} for d in loaded.distance_by_jurisdiction
        ],
        created_at=loaded.created_at,
        updated_at=loaded.updated_at,
    )


@router.get("/ifta", response_model=list[IftaReturnSummary])
async def list_ifta_returns(
    db: DbDep,
    user: CurrentUser,
    year: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
):
    """List IFTA quarterly returns with totals."""
    q = select(IftaReturn).where(IftaReturn.organization_id == user.organization_id)
    if year:
        q = q.where(IftaReturn.year == year)
    q = q.order_by(IftaReturn.year.desc(), IftaReturn.quarter.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(q)
    returns = list(result.scalars().all())

    summaries = []
    for r in returns:
        # Get totals
        fuel_result = await db.execute(
            select(func.sum(IftaFuelByJurisdiction.gallons)).where(IftaFuelByJurisdiction.ifta_return_id == r.id)
        )
        total_gallons = fuel_result.scalar()

        dist_result = await db.execute(
            select(func.sum(IftaDistanceByJurisdiction.miles)).where(IftaDistanceByJurisdiction.ifta_return_id == r.id)
        )
        total_miles = dist_result.scalar()

        summaries.append(
            IftaReturnSummary(
                id=r.id,
                year=r.year,
                quarter=r.quarter,
                status=r.status,
                total_gallons=total_gallons,
                total_miles=total_miles,
                filed_at=r.filed_at,
            )
        )

    return summaries


@router.post("/ifta/{ifta_id}/file", response_model=IftaReturnSummary)
async def file_ifta_return(ifta_id: uuid.UUID, db: DbDep, user: DispatcherUser):
    """Mark an IFTA return as filed. Locks it from further recalculation."""
    result = await db.execute(
        select(IftaReturn).where(
            IftaReturn.id == ifta_id,
            IftaReturn.organization_id == user.organization_id,
        )
    )
    ifta_return = result.scalar_one_or_none()
    if not ifta_return:
        raise HTTPException(status_code=404, detail="IFTA return not found")
    if ifta_return.status == "filed":
        raise HTTPException(status_code=422, detail="Already filed")

    ifta_return.status = "filed"
    ifta_return.filed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ifta_return)

    return IftaReturnSummary(
        id=ifta_return.id,
        year=ifta_return.year,
        quarter=ifta_return.quarter,
        status=ifta_return.status,
        filed_at=ifta_return.filed_at,
    )


# ── IRP registration ────────────────────────────────────────────────────────


@router.post("/irp", response_model=IrpYearResponse, status_code=201)
async def create_irp_year(body: IrpYearCreate, db: DbDep, user: DispatcherUser):
    """Create an IRP registration year record."""
    irp = IrpYear(
        organization_id=user.organization_id,
        registration_year=body.registration_year,
        cab_card_document_id=body.cab_card_document_id,
    )
    db.add(irp)
    await db.commit()
    await db.refresh(irp)
    return irp


@router.get("/irp", response_model=list[IrpYearResponse])
async def list_irp_years(db: DbDep, user: CurrentUser):
    """List IRP registration years."""
    result = await db.execute(
        select(IrpYear)
        .where(IrpYear.organization_id == user.organization_id)
        .order_by(IrpYear.registration_year.desc())
    )
    return list(result.scalars().all())


# ── Fleet compliance scan ────────────────────────────────────────────────────


@router.get("/scan", response_model=list[ComplianceAlert])
async def scan_compliance(db: DbDep, user: CurrentUser):
    """Scan all active vehicles and return compliance alerts."""
    from app.services import compliance_service

    alerts = await compliance_service.scan_fleet_compliance(db, user.organization_id)
    return alerts
