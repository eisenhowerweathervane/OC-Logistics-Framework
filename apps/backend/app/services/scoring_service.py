"""
Load scoring and profitability analysis service.

Provides:
- Rate-per-mile calculation for individual loads
- Lane profitability analysis (origin→destination corridor stats)
- Broker performance rating (average RPM, payment speed, volume)
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.fleet import Broker
from app.db.models.loads import Load, LoadStop, Receivable


async def score_load(db: AsyncSession, load_id: uuid.UUID, org_id: uuid.UUID) -> dict:
    """
    Calculate scoring metrics for a single load.
    Returns rate_per_mile, rate_per_mile_all_in (includes deadhead),
    and a simple profitability grade.
    """
    result = await db.execute(
        select(Load)
        .where(Load.id == load_id, Load.organization_id == org_id)
        .options(selectinload(Load.stops))
    )
    load = result.scalar_one_or_none()
    if not load:
        return {}

    rate = float(load.rate_total) if load.rate_total else 0
    loaded_miles = float(load.miles_loaded) if load.miles_loaded else 0
    deadhead = float(load.miles_deadhead_est) if load.miles_deadhead_est else 0
    total_miles = loaded_miles + deadhead

    rpm = round(rate / loaded_miles, 2) if loaded_miles > 0 else None
    rpm_all_in = round(rate / total_miles, 2) if total_miles > 0 else None

    # Simple grading: A >= $3/mi, B >= $2.50, C >= $2, D >= $1.50, F < $1.50
    grade = "N/A"
    if rpm is not None:
        if rpm >= 3.0:
            grade = "A"
        elif rpm >= 2.5:
            grade = "B"
        elif rpm >= 2.0:
            grade = "C"
        elif rpm >= 1.5:
            grade = "D"
        else:
            grade = "F"

    # Get origin/destination from stops
    pickup = next((s for s in sorted(load.stops, key=lambda s: s.seq) if s.stop_type == "pickup"), None)
    delivery = next((s for s in sorted(load.stops, key=lambda s: s.seq, reverse=True) if s.stop_type == "delivery"), None)

    return {
        "load_id": str(load.id),
        "reference": load.reference_number or load.shipping_document_number,
        "rate_total": rate,
        "miles_loaded": loaded_miles,
        "miles_deadhead": deadhead,
        "rate_per_mile": rpm,
        "rate_per_mile_all_in": rpm_all_in,
        "grade": grade,
        "origin": f"{pickup.city}, {pickup.state}" if pickup and pickup.city else None,
        "destination": f"{delivery.city}, {delivery.state}" if delivery and delivery.city else None,
    }


async def lane_profitability(
    db: AsyncSession,
    org_id: uuid.UUID,
    origin_state: Optional[str] = None,
    dest_state: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """
    Analyze lane profitability by grouping completed loads by origin→destination state.
    Returns average RPM, total loads, total revenue per lane.
    """
    # Get completed loads with rate and miles
    q = select(Load).where(
        Load.organization_id == org_id,
        Load.status.in_(["delivered", "invoice_ready", "invoiced", "paid", "closed", "archived"]),
        Load.rate_total.isnot(None),
        Load.miles_loaded.isnot(None),
        Load.miles_loaded > 0,
    )
    result = await db.execute(q)
    loads = list(result.scalars().all())

    # Build lane data
    lanes: dict[str, dict] = {}

    for load in loads:
        stops_result = await db.execute(
            select(LoadStop).where(LoadStop.load_id == load.id).order_by(LoadStop.seq)
        )
        stops = list(stops_result.scalars().all())

        pickups = [s for s in stops if s.stop_type == "pickup"]
        deliveries = [s for s in stops if s.stop_type == "delivery"]

        o_state = pickups[0].state if pickups and pickups[0].state else "??"
        d_state = deliveries[-1].state if deliveries and deliveries[-1].state else "??"

        if origin_state and o_state != origin_state:
            continue
        if dest_state and d_state != dest_state:
            continue

        lane_key = f"{o_state}→{d_state}"
        if lane_key not in lanes:
            lanes[lane_key] = {
                "lane": lane_key,
                "origin_state": o_state,
                "dest_state": d_state,
                "load_count": 0,
                "total_revenue": 0,
                "total_miles": 0,
            }

        rate = float(load.rate_total) if load.rate_total else 0
        miles = float(load.miles_loaded) if load.miles_loaded else 0

        lanes[lane_key]["load_count"] += 1
        lanes[lane_key]["total_revenue"] += rate
        lanes[lane_key]["total_miles"] += miles

    # Calculate averages and sort by volume
    result_list = []
    for lane in lanes.values():
        avg_rpm = round(lane["total_revenue"] / lane["total_miles"], 2) if lane["total_miles"] > 0 else 0
        result_list.append({
            **lane,
            "avg_rate_per_mile": avg_rpm,
            "total_revenue": round(lane["total_revenue"], 2),
        })

    result_list.sort(key=lambda x: x["load_count"], reverse=True)
    return result_list[:limit]


async def broker_ratings(
    db: AsyncSession,
    org_id: uuid.UUID,
    limit: int = 20,
) -> list[dict]:
    """
    Rate brokers based on:
    - Average rate per mile they pay
    - Payment speed (avg days from invoice to payment)
    - Load volume
    """
    # Get brokers for this org
    brokers_result = await db.execute(
        select(Broker).where(Broker.organization_id == org_id)
    )
    brokers = list(brokers_result.scalars().all())

    ratings = []
    for broker in brokers:
        # Load stats for this broker
        loads_result = await db.execute(
            select(Load).where(
                Load.organization_id == org_id,
                Load.broker_id == broker.id,
                Load.status.in_(["delivered", "invoice_ready", "invoiced", "paid", "closed", "archived"]),
            )
        )
        loads = list(loads_result.scalars().all())

        if not loads:
            continue

        total_rate = sum(float(l.rate_total) for l in loads if l.rate_total)
        total_miles = sum(float(l.miles_loaded) for l in loads if l.miles_loaded)
        avg_rpm = round(total_rate / total_miles, 2) if total_miles > 0 else 0

        # Payment speed from receivables
        recv_result = await db.execute(
            select(Receivable).where(
                Receivable.broker_id == broker.id,
                Receivable.status == "paid",
            )
        )
        paid_receivables = list(recv_result.scalars().all())

        avg_payment_days = None
        if paid_receivables:
            payment_days = []
            for r in paid_receivables:
                if r.invoice_date and r.updated_at:
                    days = (r.updated_at - r.invoice_date).days
                    if days >= 0:
                        payment_days.append(days)
            if payment_days:
                avg_payment_days = round(sum(payment_days) / len(payment_days), 1)

        # Simple broker score: weighted combo of RPM and payment speed
        score = avg_rpm * 20  # Base from RPM
        if avg_payment_days is not None and avg_payment_days <= 30:
            score += 10  # Bonus for fast payers
        elif avg_payment_days is not None and avg_payment_days > 45:
            score -= 10  # Penalty for slow payers

        ratings.append({
            "broker_id": str(broker.id),
            "broker_name": broker.name,
            "load_count": len(loads),
            "total_revenue": round(total_rate, 2),
            "avg_rate_per_mile": avg_rpm,
            "avg_payment_days": avg_payment_days,
            "score": round(score, 1),
        })

    ratings.sort(key=lambda x: x["score"], reverse=True)
    return ratings[:limit]
