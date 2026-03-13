"""
Notification routes — trigger on-demand Slack and WhatsApp alerts.

These are internal-facing endpoints (dispatcher/owner only) for sending
notifications to the dispatch Slack channel and driver WhatsApp.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbDep, DispatcherUser
from app.db.models.compliance import AnnualInspection, MaintenanceItem
from app.db.models.fleet import Driver, Vehicle
from app.db.models.loads import Load, Receivable
from app.services import slack_service, whatsapp_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/slack/overdue-ar-summary", status_code=200)
async def send_overdue_ar_summary(db: DbDep, user: DispatcherUser):
    """Send a summary of overdue receivables to the dispatch Slack channel."""
    now = datetime.now(timezone.utc)

    q = (
        select(
            func.count().label("cnt"),
            func.coalesce(func.sum(Receivable.amount_due - Receivable.amount_paid), 0).label("total"),
            func.min(Receivable.due_date).label("oldest_due"),
        )
        .join(Receivable.load)
        .where(
            Load.organization_id == user.organization_id,
            Receivable.status.in_(["open", "partial"]),
            Receivable.due_date < now,
        )
    )
    result = await db.execute(q)
    row = result.one()

    if row.cnt == 0:
        return {"sent": False, "reason": "no_overdue_receivables"}

    oldest_days = (now - row.oldest_due).days if row.oldest_due else 0

    sent = await slack_service.notify_overdue_receivables(
        overdue_count=row.cnt,
        total_amount=f"{float(row.total):,.2f}",
        oldest_days=oldest_days,
    )
    return {"sent": sent, "overdue_count": row.cnt, "total_amount": float(row.total)}


@router.post("/slack/compliance-check", status_code=200)
async def send_compliance_alerts(db: DbDep, user: DispatcherUser):
    """Check fleet compliance and send alerts for expiring/expired items."""
    from datetime import date, timedelta

    today = date.today()
    alerts_sent = 0

    # Check annual inspections expiring within 30 days or already expired
    vehicles_result = await db.execute(
        select(Vehicle).where(
            Vehicle.organization_id == user.organization_id,
            Vehicle.status != "out_of_service",
        )
    )
    vehicles = list(vehicles_result.scalars().all())

    for vehicle in vehicles:
        # Latest annual inspection
        insp_result = await db.execute(
            select(AnnualInspection)
            .where(AnnualInspection.vehicle_id == vehicle.id)
            .order_by(AnnualInspection.inspected_at.desc())
            .limit(1)
        )
        latest = insp_result.scalar_one_or_none()

        if latest and latest.expires_at:
            if latest.expires_at < today:
                await slack_service.notify_compliance_alert(
                    vehicle_unit=vehicle.unit_number,
                    vehicle_id=str(vehicle.id),
                    alert_type="Annual Inspection Expired",
                    detail=f"Expired {(today - latest.expires_at).days} days ago",
                )
                alerts_sent += 1
            elif latest.expires_at < today + timedelta(days=30):
                await slack_service.notify_compliance_alert(
                    vehicle_unit=vehicle.unit_number,
                    vehicle_id=str(vehicle.id),
                    alert_type="Annual Inspection Expiring Soon",
                    detail=f"Expires {latest.expires_at.isoformat()}",
                )
                alerts_sent += 1

        # Overdue maintenance
        maint_result = await db.execute(
            select(func.count()).where(
                MaintenanceItem.vehicle_id == vehicle.id,
                MaintenanceItem.status == "open",
                MaintenanceItem.due_date < today,
            )
        )
        overdue_count = maint_result.scalar() or 0
        if overdue_count > 0:
            await slack_service.notify_compliance_alert(
                vehicle_unit=vehicle.unit_number,
                vehicle_id=str(vehicle.id),
                alert_type="Overdue Maintenance",
                detail=f"{overdue_count} overdue maintenance item{'s' if overdue_count != 1 else ''}",
            )
            alerts_sent += 1

    return {"alerts_sent": alerts_sent}


# ── WhatsApp driver notifications ────────────────────────────────────────────


class DispatchAlertRequest(BaseModel):
    driver_id: uuid.UUID
    load_id: uuid.UUID


class DocsReminderRequest(BaseModel):
    driver_id: uuid.UUID
    load_id: uuid.UUID
    missing_docs: list[str]


@router.post("/whatsapp/dispatch-alert", status_code=200)
async def send_dispatch_alert(body: DispatchAlertRequest, db: DbDep, user: DispatcherUser):
    """Send a WhatsApp dispatch notification to a driver about a load assignment."""
    # Get driver
    driver_result = await db.execute(
        select(Driver).where(Driver.id == body.driver_id, Driver.organization_id == user.organization_id)
    )
    driver = driver_result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    if not driver.phone:
        return {"sent": False, "reason": "driver_has_no_phone"}

    # Get load with stops
    load_result = await db.execute(
        select(Load)
        .where(Load.id == body.load_id, Load.organization_id == user.organization_id)
        .options(selectinload(Load.stops))
    )
    load = load_result.scalar_one_or_none()
    if not load:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found")

    load_ref = load.reference_number or load.shipping_document_number or str(load.id)[:8]

    # Find first pickup stop
    pickup = next((s for s in sorted(load.stops, key=lambda s: s.seq) if s.stop_type == "pickup"), None)

    sent = await whatsapp_service.notify_driver_dispatched(
        phone=driver.phone,
        driver_name=f"{driver.first_name} {driver.last_name}",
        load_ref=load_ref,
        pickup_city=pickup.city if pickup else None,
        pickup_state=pickup.state if pickup else None,
        appt_start=pickup.appt_start.isoformat() if pickup and pickup.appt_start else None,
    )
    return {"sent": sent}


@router.post("/whatsapp/docs-reminder", status_code=200)
async def send_docs_reminder(body: DocsReminderRequest, db: DbDep, user: DispatcherUser):
    """Send a WhatsApp reminder to a driver about missing documents."""
    driver_result = await db.execute(
        select(Driver).where(Driver.id == body.driver_id, Driver.organization_id == user.organization_id)
    )
    driver = driver_result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    if not driver.phone:
        return {"sent": False, "reason": "driver_has_no_phone"}

    load_result = await db.execute(
        select(Load).where(Load.id == body.load_id, Load.organization_id == user.organization_id)
    )
    load = load_result.scalar_one_or_none()
    if not load:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found")

    load_ref = load.reference_number or load.shipping_document_number or str(load.id)[:8]

    sent = await whatsapp_service.notify_driver_docs_needed(
        phone=driver.phone,
        driver_name=f"{driver.first_name} {driver.last_name}",
        load_ref=load_ref,
        missing_docs=body.missing_docs,
    )
    return {"sent": sent}
