"""
Compliance automation service.

Handles:
- IFTA quarterly return calculation (aggregate fuel purchases + load miles by jurisdiction)
- Fleet-wide compliance scanning (inspections, maintenance, DOT deadlines)
- IRP distance aggregation
"""
import uuid
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.compliance import (
    AnnualInspection,
    FuelPurchase,
    IftaDistanceByJurisdiction,
    IftaFuelByJurisdiction,
    IftaReturn,
    IrpDistanceByJurisdiction,
    IrpYear,
    MaintenanceItem,
)
from app.db.models.fleet import Vehicle
from app.db.models.loads import Load, LoadStop


# ── IFTA ─────────────────────────────────────────────────────────────────────


def _quarter_date_range(year: int, quarter: int) -> tuple[date, date]:
    """Return (start_date, end_date) for a given quarter."""
    month_start = (quarter - 1) * 3 + 1
    start = date(year, month_start, 1)
    if quarter == 4:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month_start + 3, 1) - timedelta(days=1)
    return start, end


async def calculate_ifta_fuel(
    db: AsyncSession, org_id: uuid.UUID, year: int, quarter: int
) -> list[dict]:
    """Aggregate fuel purchases by jurisdiction for the quarter."""
    start, end = _quarter_date_range(year, quarter)

    result = await db.execute(
        select(
            FuelPurchase.jurisdiction,
            func.sum(FuelPurchase.gallons).label("total_gallons"),
        )
        .where(
            FuelPurchase.organization_id == org_id,
            FuelPurchase.purchased_at_local >= start,
            FuelPurchase.purchased_at_local <= end,
            FuelPurchase.jurisdiction.isnot(None),
            FuelPurchase.gallons.isnot(None),
        )
        .group_by(FuelPurchase.jurisdiction)
        .order_by(FuelPurchase.jurisdiction)
    )

    return [
        {"jurisdiction": row.jurisdiction, "gallons": float(row.total_gallons)}
        for row in result.all()
    ]


async def calculate_ifta_miles(
    db: AsyncSession, org_id: uuid.UUID, year: int, quarter: int
) -> list[dict]:
    """
    Aggregate load miles by pickup/delivery state for the quarter.

    Uses load stops to determine jurisdictions traversed. Each load's total
    miles are split proportionally across jurisdictions based on stop locations.
    For a simple one-truck carrier, this is a reasonable approximation.
    """
    start, end = _quarter_date_range(year, quarter)

    # Find delivered loads in this quarter
    result = await db.execute(
        select(Load)
        .where(
            Load.organization_id == org_id,
            Load.status.in_(["delivered", "invoice_ready", "invoiced", "paid", "closed", "archived"]),
            Load.created_at >= start,
            Load.created_at <= end,
            Load.miles_loaded.isnot(None),
        )
    )
    loads = list(result.scalars().all())

    # Gather miles by state from load stops
    miles_by_state: dict[str, float] = {}

    for load in loads:
        if not load.miles_loaded:
            continue

        stops_result = await db.execute(
            select(LoadStop)
            .where(LoadStop.load_id == load.id)
            .order_by(LoadStop.seq)
        )
        stops = list(stops_result.scalars().all())

        states = list(dict.fromkeys(s.state for s in stops if s.state))
        if not states:
            continue

        # Split miles evenly across traversed states
        per_state = float(load.miles_loaded) / len(states)
        for state in states:
            miles_by_state[state] = miles_by_state.get(state, 0) + per_state

    return [
        {"jurisdiction": st, "miles": round(miles, 2)}
        for st, miles in sorted(miles_by_state.items())
    ]


async def build_ifta_return(
    db: AsyncSession, org_id: uuid.UUID, year: int, quarter: int
) -> IftaReturn:
    """
    Create or update an IFTA return with calculated fuel and distance data.
    Only updates draft returns — filed returns are immutable.
    """
    # Find or create
    result = await db.execute(
        select(IftaReturn).where(
            IftaReturn.organization_id == org_id,
            IftaReturn.year == year,
            IftaReturn.quarter == quarter,
        )
    )
    ifta_return = result.scalar_one_or_none()

    if ifta_return and ifta_return.status != "draft":
        return ifta_return  # Don't recalculate filed returns

    if not ifta_return:
        ifta_return = IftaReturn(
            organization_id=org_id,
            year=year,
            quarter=quarter,
            status="draft",
        )
        db.add(ifta_return)
        await db.flush()

    # Clear existing jurisdiction rows
    existing_dist = await db.execute(
        select(IftaDistanceByJurisdiction).where(
            IftaDistanceByJurisdiction.ifta_return_id == ifta_return.id
        )
    )
    for row in existing_dist.scalars().all():
        await db.delete(row)

    existing_fuel = await db.execute(
        select(IftaFuelByJurisdiction).where(
            IftaFuelByJurisdiction.ifta_return_id == ifta_return.id
        )
    )
    for row in existing_fuel.scalars().all():
        await db.delete(row)

    await db.flush()

    # Recalculate
    fuel_data = await calculate_ifta_fuel(db, org_id, year, quarter)
    miles_data = await calculate_ifta_miles(db, org_id, year, quarter)

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    for f in fuel_data:
        db.add(IftaFuelByJurisdiction(
            ifta_return_id=ifta_return.id,
            jurisdiction=f["jurisdiction"],
            gallons=f["gallons"],
            created_at=now,
        ))

    for m in miles_data:
        db.add(IftaDistanceByJurisdiction(
            ifta_return_id=ifta_return.id,
            jurisdiction=m["jurisdiction"],
            miles=m["miles"],
            created_at=now,
        ))

    await db.commit()
    await db.refresh(ifta_return)
    return ifta_return


# ── Fleet compliance scan ────────────────────────────────────────────────────


async def scan_fleet_compliance(
    db: AsyncSession, org_id: uuid.UUID
) -> list[dict]:
    """
    Scan all active vehicles for compliance issues. Returns a list of alert dicts.
    Each alert: { vehicle_id, unit_number, alert_type, detail, severity }
    """
    today = date.today()
    alerts: list[dict] = []

    vehicles_result = await db.execute(
        select(Vehicle).where(
            Vehicle.organization_id == org_id,
            Vehicle.status != "out_of_service",
        )
    )
    vehicles = list(vehicles_result.scalars().all())

    for vehicle in vehicles:
        # Annual inspection check
        insp_result = await db.execute(
            select(AnnualInspection)
            .where(AnnualInspection.vehicle_id == vehicle.id)
            .order_by(AnnualInspection.inspected_at.desc())
            .limit(1)
        )
        latest_insp = insp_result.scalar_one_or_none()

        if not latest_insp:
            alerts.append({
                "vehicle_id": str(vehicle.id),
                "unit_number": vehicle.unit_number,
                "alert_type": "no_annual_inspection",
                "detail": "No annual inspection on record",
                "severity": "critical",
            })
        elif latest_insp.expires_at:
            days_until = (latest_insp.expires_at - today).days
            if days_until < 0:
                alerts.append({
                    "vehicle_id": str(vehicle.id),
                    "unit_number": vehicle.unit_number,
                    "alert_type": "annual_inspection_expired",
                    "detail": f"Expired {abs(days_until)} days ago ({latest_insp.expires_at.isoformat()})",
                    "severity": "critical",
                })
            elif days_until <= 30:
                alerts.append({
                    "vehicle_id": str(vehicle.id),
                    "unit_number": vehicle.unit_number,
                    "alert_type": "annual_inspection_expiring",
                    "detail": f"Expires in {days_until} days ({latest_insp.expires_at.isoformat()})",
                    "severity": "warning",
                })

        # Overdue maintenance
        maint_result = await db.execute(
            select(MaintenanceItem).where(
                MaintenanceItem.vehicle_id == vehicle.id,
                MaintenanceItem.status == "open",
                MaintenanceItem.due_date < today,
            )
        )
        overdue_items = list(maint_result.scalars().all())
        if overdue_items:
            alerts.append({
                "vehicle_id": str(vehicle.id),
                "unit_number": vehicle.unit_number,
                "alert_type": "overdue_maintenance",
                "detail": f"{len(overdue_items)} overdue item(s): {', '.join(i.category for i in overdue_items)}",
                "severity": "warning",
            })

        # Upcoming maintenance (due within 7 days)
        upcoming_result = await db.execute(
            select(MaintenanceItem).where(
                MaintenanceItem.vehicle_id == vehicle.id,
                MaintenanceItem.status == "open",
                MaintenanceItem.due_date >= today,
                MaintenanceItem.due_date <= today + timedelta(days=7),
            )
        )
        upcoming_items = list(upcoming_result.scalars().all())
        if upcoming_items:
            alerts.append({
                "vehicle_id": str(vehicle.id),
                "unit_number": vehicle.unit_number,
                "alert_type": "upcoming_maintenance",
                "detail": f"{len(upcoming_items)} item(s) due within 7 days: {', '.join(i.category for i in upcoming_items)}",
                "severity": "info",
            })

    return alerts
