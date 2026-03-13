"""
Analytics and reporting service.

Provides:
- Dashboard summary (loads, revenue, fleet status at a glance)
- Revenue reports (by period, broker, lane)
- Fleet utilization metrics
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select, and_, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.compliance import FuelPurchase, MaintenanceItem
from app.db.models.fleet import Driver, Vehicle
from app.db.models.loads import Assignment, Load, LoadStop, Receivable


async def dashboard_summary(db: AsyncSession, org_id: uuid.UUID) -> dict:
    """
    High-level dashboard data: active loads, revenue this month,
    fleet counts, AR status.
    """
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Active loads (not closed/archived)
    active_result = await db.execute(
        select(func.count()).where(
            Load.organization_id == org_id,
            Load.status.notin_(["closed", "archived", "quoted"]),
        )
    )
    active_loads = active_result.scalar() or 0

    # Loads delivered this month
    delivered_result = await db.execute(
        select(func.count()).where(
            Load.organization_id == org_id,
            Load.status.in_(["delivered", "invoice_ready", "invoiced", "paid", "closed"]),
            Load.updated_at >= month_start,
        )
    )
    delivered_this_month = delivered_result.scalar() or 0

    # Revenue this month (from delivered+ loads)
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Load.rate_total), 0)).where(
            Load.organization_id == org_id,
            Load.status.in_(["delivered", "invoice_ready", "invoiced", "paid", "closed"]),
            Load.updated_at >= month_start,
        )
    )
    revenue_this_month = float(revenue_result.scalar() or 0)

    # Fleet counts
    drivers_result = await db.execute(
        select(func.count()).where(
            Driver.organization_id == org_id,
            Driver.status == "active",
        )
    )
    active_drivers = drivers_result.scalar() or 0

    vehicles_result = await db.execute(
        select(func.count()).where(
            Vehicle.organization_id == org_id,
            Vehicle.status == "active",
        )
    )
    active_vehicles = vehicles_result.scalar() or 0

    # AR: total outstanding
    ar_result = await db.execute(
        select(
            func.count().label("cnt"),
            func.coalesce(func.sum(Receivable.amount_due - Receivable.amount_paid), 0).label("total"),
        )
        .join(Receivable.load)
        .where(
            Load.organization_id == org_id,
            Receivable.status.in_(["open", "partial"]),
        )
    )
    ar_row = ar_result.one()

    # Overdue AR
    overdue_result = await db.execute(
        select(func.coalesce(func.sum(Receivable.amount_due - Receivable.amount_paid), 0))
        .join(Receivable.load)
        .where(
            Load.organization_id == org_id,
            Receivable.status.in_(["open", "partial"]),
            Receivable.due_date < now,
        )
    )
    overdue_amount = float(overdue_result.scalar() or 0)

    return {
        "active_loads": active_loads,
        "delivered_this_month": delivered_this_month,
        "revenue_this_month": round(revenue_this_month, 2),
        "active_drivers": active_drivers,
        "active_vehicles": active_vehicles,
        "outstanding_ar": round(float(ar_row.total), 2),
        "outstanding_ar_count": ar_row.cnt,
        "overdue_ar": round(overdue_amount, 2),
    }


async def revenue_by_period(
    db: AsyncSession,
    org_id: uuid.UUID,
    period: str = "monthly",  # "weekly" or "monthly"
    months_back: int = 6,
) -> list[dict]:
    """
    Revenue breakdown by period. Returns list of { period, load_count, total_revenue, avg_rpm }.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=months_back * 31)

    result = await db.execute(
        select(Load).where(
            Load.organization_id == org_id,
            Load.status.in_(["delivered", "invoice_ready", "invoiced", "paid", "closed", "archived"]),
            Load.updated_at >= cutoff,
            Load.rate_total.isnot(None),
        )
        .order_by(Load.updated_at)
    )
    loads = list(result.scalars().all())

    buckets: dict[str, dict] = {}

    for load in loads:
        if period == "weekly":
            key = load.updated_at.strftime("%Y-W%U")
        else:
            key = load.updated_at.strftime("%Y-%m")

        if key not in buckets:
            buckets[key] = {"period": key, "load_count": 0, "total_revenue": 0, "total_miles": 0}

        rate = float(load.rate_total) if load.rate_total else 0
        miles = float(load.miles_loaded) if load.miles_loaded else 0

        buckets[key]["load_count"] += 1
        buckets[key]["total_revenue"] += rate
        buckets[key]["total_miles"] += miles

    result_list = []
    for b in sorted(buckets.values(), key=lambda x: x["period"]):
        avg_rpm = round(b["total_revenue"] / b["total_miles"], 2) if b["total_miles"] > 0 else 0
        result_list.append({
            "period": b["period"],
            "load_count": b["load_count"],
            "total_revenue": round(b["total_revenue"], 2),
            "avg_rate_per_mile": avg_rpm,
        })

    return result_list


async def fleet_utilization(db: AsyncSession, org_id: uuid.UUID) -> list[dict]:
    """
    Fleet utilization report: for each driver, show total loads, total miles,
    total revenue, and current status (assigned/idle).
    """
    drivers_result = await db.execute(
        select(Driver).where(Driver.organization_id == org_id).order_by(Driver.last_name)
    )
    drivers = list(drivers_result.scalars().all())

    utilization = []

    for driver in drivers:
        # Total assigned loads (completed)
        loads_result = await db.execute(
            select(Load)
            .join(Assignment, Assignment.load_id == Load.id)
            .where(
                Assignment.driver_id == driver.id,
                Load.status.in_(["delivered", "invoice_ready", "invoiced", "paid", "closed", "archived"]),
            )
        )
        completed_loads = list(loads_result.scalars().all())

        total_revenue = sum(float(l.rate_total) for l in completed_loads if l.rate_total)
        total_miles = sum(float(l.miles_loaded) for l in completed_loads if l.miles_loaded)

        # Current assignment
        active_result = await db.execute(
            select(Assignment).where(
                Assignment.driver_id == driver.id,
                Assignment.unassigned_at.is_(None),
            ).limit(1)
        )
        is_assigned = active_result.scalar_one_or_none() is not None

        utilization.append({
            "driver_id": str(driver.id),
            "driver_name": f"{driver.first_name} {driver.last_name}",
            "status": driver.status,
            "currently_assigned": is_assigned,
            "completed_loads": len(completed_loads),
            "total_revenue": round(total_revenue, 2),
            "total_miles": round(total_miles, 2),
            "avg_rpm": round(total_revenue / total_miles, 2) if total_miles > 0 else 0,
        })

    return utilization


async def fuel_cost_summary(
    db: AsyncSession,
    org_id: uuid.UUID,
    months_back: int = 3,
) -> dict:
    """Fuel cost summary: total gallons, total cost, avg price per gallon."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=months_back * 31)

    result = await db.execute(
        select(
            func.count().label("purchases"),
            func.coalesce(func.sum(FuelPurchase.gallons), 0).label("total_gallons"),
            func.coalesce(func.sum(FuelPurchase.total_price), 0).label("total_cost"),
        ).where(
            FuelPurchase.organization_id == org_id,
            FuelPurchase.purchased_at_local >= cutoff,
        )
    )
    row = result.one()

    total_gallons = float(row.total_gallons) if row.total_gallons else 0
    total_cost = float(row.total_cost) if row.total_cost else 0

    return {
        "purchases": row.purchases,
        "total_gallons": round(total_gallons, 2),
        "total_cost": round(total_cost, 2),
        "avg_price_per_gallon": round(total_cost / total_gallons, 3) if total_gallons > 0 else 0,
        "period_months": months_back,
    }
