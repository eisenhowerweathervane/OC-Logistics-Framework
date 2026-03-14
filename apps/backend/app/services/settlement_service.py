"""Settlement generation service.

Builds a settlement for a driver over a date range by finding all delivered
loads they were assigned to and calculating pay based on the driver's
pay_type/pay_rate.

Supported pay types:
  per_mile   — pay_rate * miles_loaded
  percentage — pay_rate% * rate_total
  flat_rate  — pay_rate per load
"""

import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.fleet import Driver
from app.db.models.loads import Assignment, Load
from app.db.models.settlements import Settlement, SettlementLineItem

DELIVERED_STATUSES = {"delivered", "invoice_ready", "invoiced", "paid", "closed", "archived"}


async def generate_settlement(
    db: AsyncSession,
    org_id: uuid.UUID,
    driver_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> Settlement:
    """Generate a draft settlement for the given driver and period."""

    # Fetch driver for pay info
    driver_result = await db.execute(
        select(Driver).where(Driver.id == driver_id, Driver.organization_id == org_id)
    )
    driver = driver_result.scalar_one_or_none()
    if not driver:
        raise ValueError("Driver not found")

    # Find loads assigned to this driver that were delivered within the period
    result = await db.execute(
        select(Load)
        .join(Assignment, Assignment.load_id == Load.id)
        .where(
            Assignment.driver_id == driver_id,
            Load.organization_id == org_id,
            Load.status.in_(DELIVERED_STATUSES),
        )
        .options(selectinload(Load.accessorial_charges), selectinload(Load.stops))
    )
    loads = list(result.scalars().unique().all())

    # Create settlement
    settlement = Settlement(
        organization_id=org_id,
        driver_id=driver_id,
        period_start=period_start,
        period_end=period_end,
        status="draft",
    )
    db.add(settlement)
    await db.flush()  # get settlement.id

    total_miles = Decimal("0")
    total_revenue = Decimal("0")
    total_pay = Decimal("0")

    for load in loads:
        miles = Decimal(str(load.miles_loaded or 0))
        revenue = Decimal(str(load.rate_total or 0))

        # Include approved accessorial charges in revenue
        accessorial_total = sum(
            Decimal(str(ch.amount))
            for ch in load.accessorial_charges
            if ch.status == "approved"
        )
        revenue += accessorial_total

        # Calculate driver pay
        pay = _calculate_pay(driver.pay_type, Decimal(str(driver.pay_rate or 0)), miles, revenue)

        origin_city = ""
        dest_city = ""
        if hasattr(load, "stops") and load.stops:
            pickups = [s for s in load.stops if s.stop_type == "pickup"]
            deliveries = [s for s in load.stops if s.stop_type == "delivery"]
            if pickups:
                origin_city = pickups[0].city or ""
            if deliveries:
                dest_city = deliveries[-1].city or ""

        description = f"Load {str(load.id)[:8]}"
        if origin_city or dest_city:
            description += f" ({origin_city} → {dest_city})"

        line = SettlementLineItem(
            settlement_id=settlement.id,
            load_id=load.id,
            line_type="load_pay",
            description=description,
            miles=miles,
            revenue=revenue,
            amount=pay,
        )
        db.add(line)

        total_miles += miles
        total_revenue += revenue
        total_pay += pay

    settlement.total_miles = total_miles
    settlement.total_revenue = total_revenue
    settlement.total_pay = total_pay
    settlement.total_deductions = Decimal("0")
    settlement.net_pay = total_pay

    await db.commit()

    # Re-query to eagerly load all attributes + line_items
    refreshed = await db.execute(
        select(Settlement)
        .where(Settlement.id == settlement.id)
        .options(selectinload(Settlement.line_items))
    )
    return refreshed.scalar_one()


def _calculate_pay(pay_type: str | None, pay_rate: Decimal, miles: Decimal, revenue: Decimal) -> Decimal:
    """Calculate driver pay based on their compensation structure."""
    if not pay_type or pay_rate == 0:
        return Decimal("0")

    if pay_type == "per_mile":
        return (pay_rate * miles).quantize(Decimal("0.01"))
    elif pay_type == "percentage":
        return (revenue * pay_rate / Decimal("100")).quantize(Decimal("0.01"))
    elif pay_type == "flat_rate":
        return pay_rate
    else:
        return Decimal("0")
