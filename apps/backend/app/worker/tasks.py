"""
Background task definitions for arq.

Each function receives `ctx` (arq worker context) as its first argument.
The db session is created fresh per task — tasks run outside the HTTP request
lifecycle, so they cannot reuse the request session.

Task types:
  - On-demand: check_invoice_readiness, notify_load_delivered (enqueued by HTTP routes)
  - Scheduled: daily_compliance_digest, weekly_ar_reminder, document_retention_cleanup (cron)
"""
import uuid
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def _get_session_factory() -> async_sessionmaker:
    global _engine, _session_factory
    if _session_factory is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def check_invoice_readiness(ctx: dict, load_id: str) -> None:
    """
    Background task: run invoice readiness check for a load.
    Triggered automatically after a load reaches 'delivered' status.
    If the packet becomes ready, sends a Slack notification.
    """
    from app.services import invoice_service, slack_service

    load_uuid = uuid.UUID(load_id)
    session_factory = _get_session_factory()

    async with session_factory() as db:
        try:
            packet = await invoice_service.check_readiness(db, load_uuid)
            logger.info(
                "invoice_readiness_check_complete",
                extra={"load_id": load_id, "packet_status": packet.status},
            )

            # Notify Slack when invoice packet becomes ready
            if packet.status == "ready":
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload
                from app.db.models.loads import Load

                load_result = await db.execute(
                    select(Load).where(Load.id == load_uuid).options(selectinload(Load.stops))
                )
                load = load_result.scalar_one_or_none()
                if load:
                    load_ref = load.reference_number or load.shipping_document_number or str(load.id)[:8]
                    await slack_service.notify_invoice_ready(
                        load_ref=load_ref,
                        load_id=load_id,
                        rate_total=str(load.rate_total) if load.rate_total else None,
                    )
        except Exception:
            logger.exception("invoice_readiness_check_failed", extra={"load_id": load_id})
            raise


async def notify_load_delivered(ctx: dict, load_id: str, driver_name: str) -> None:
    """
    Background task: send Slack notification when a load is delivered.
    """
    from app.services import slack_service
    from sqlalchemy import select
    from app.db.models.loads import Load, LoadStop

    load_uuid = uuid.UUID(load_id)
    session_factory = _get_session_factory()

    async with session_factory() as db:
        try:
            load_result = await db.execute(select(Load).where(Load.id == load_uuid))
            load = load_result.scalar_one_or_none()
            if not load:
                return

            load_ref = load.reference_number or load.shipping_document_number or str(load.id)[:8]

            # Get last delivery stop for location
            stop_result = await db.execute(
                select(LoadStop)
                .where(LoadStop.load_id == load_uuid, LoadStop.stop_type == "delivery")
                .order_by(LoadStop.seq.desc())
                .limit(1)
            )
            last_stop = stop_result.scalar_one_or_none()

            await slack_service.notify_load_delivered(
                load_ref=load_ref,
                load_id=load_id,
                driver_name=driver_name,
                delivery_city=last_stop.city if last_stop else None,
                delivery_state=last_stop.state if last_stop else None,
            )
        except Exception:
            logger.exception("notify_load_delivered_failed", extra={"load_id": load_id})


# ── Scheduled tasks ──────────────────────────────────────────────────────────


async def daily_compliance_digest(ctx: dict) -> None:
    """
    Scheduled task (daily): scan all orgs' fleets for compliance issues
    and push a digest to each org's Slack channel.
    """
    from app.db.models.org import Organization
    from app.services import compliance_service, slack_service

    session_factory = _get_session_factory()

    async with session_factory() as db:
        try:
            orgs_result = await db.execute(select(Organization))
            orgs = list(orgs_result.scalars().all())

            for org in orgs:
                alerts = await compliance_service.scan_fleet_compliance(db, org.id)
                critical = [a for a in alerts if a["severity"] == "critical"]
                warnings = [a for a in alerts if a["severity"] == "warning"]

                if not critical and not warnings:
                    continue

                # Send per-alert notifications for critical items
                for alert in critical:
                    await slack_service.notify_compliance_alert(
                        vehicle_unit=alert["unit_number"],
                        vehicle_id=alert["vehicle_id"],
                        alert_type=alert["alert_type"].replace("_", " ").title(),
                        detail=alert["detail"],
                    )

                logger.info(
                    "daily_compliance_digest_complete",
                    extra={
                        "org_id": str(org.id),
                        "critical": len(critical),
                        "warnings": len(warnings),
                    },
                )
        except Exception:
            logger.exception("daily_compliance_digest_failed")


async def weekly_ar_reminder(ctx: dict) -> None:
    """
    Scheduled task (weekly): check for overdue receivables across all orgs
    and push AR summary to Slack.
    """
    from app.db.models.org import Organization
    from app.db.models.loads import Load, Receivable
    from app.services import slack_service

    session_factory = _get_session_factory()
    now = datetime.now(timezone.utc)

    async with session_factory() as db:
        try:
            orgs_result = await db.execute(select(Organization))
            orgs = list(orgs_result.scalars().all())

            for org in orgs:
                q = (
                    select(
                        func.count().label("cnt"),
                        func.coalesce(
                            func.sum(Receivable.amount_due - Receivable.amount_paid), 0
                        ).label("total"),
                        func.min(Receivable.due_date).label("oldest_due"),
                    )
                    .join(Receivable.load)
                    .where(
                        Load.organization_id == org.id,
                        Receivable.status.in_(["open", "partial"]),
                        Receivable.due_date < now,
                    )
                )
                result = await db.execute(q)
                row = result.one()

                if row.cnt > 0:
                    oldest_days = (now - row.oldest_due).days if row.oldest_due else 0
                    await slack_service.notify_overdue_receivables(
                        overdue_count=row.cnt,
                        total_amount=f"{float(row.total):,.2f}",
                        oldest_days=oldest_days,
                    )
                    logger.info(
                        "weekly_ar_reminder_sent",
                        extra={"org_id": str(org.id), "overdue_count": row.cnt},
                    )
        except Exception:
            logger.exception("weekly_ar_reminder_failed")


async def document_retention_cleanup(ctx: dict) -> None:
    """
    Scheduled task (daily): find documents past their retention period
    and mark them for archival/deletion based on retention policy.

    Does NOT delete S3 objects — only updates document status. Actual
    storage cleanup can be handled by a separate process.
    """
    from app.db.models.documents import Document, RetentionPolicy

    session_factory = _get_session_factory()
    now = datetime.now(timezone.utc)

    async with session_factory() as db:
        try:
            # Find documents with retention policies
            policies_result = await db.execute(select(RetentionPolicy))
            policies = {p.id: p for p in policies_result.scalars().all()}

            if not policies:
                return

            docs_result = await db.execute(
                select(Document).where(
                    Document.retention_policy_id.isnot(None),
                    Document.doc_type != "archived",
                )
            )
            docs = list(docs_result.scalars().all())

            archived_count = 0
            for doc in docs:
                policy = policies.get(doc.retention_policy_id)
                if not policy:
                    continue

                # Check if past retention
                retention_cutoff = doc.created_at + timedelta(days=policy.retention_days)
                if now >= retention_cutoff and not policy.hold_enabled:
                    if policy.deletion_action == "archive":
                        doc.doc_type = f"archived_{doc.doc_type}"
                    elif policy.deletion_action == "delete":
                        doc.doc_type = f"deleted_{doc.doc_type}"
                    archived_count += 1

            if archived_count > 0:
                await db.commit()

            logger.info(
                "document_retention_cleanup_complete",
                extra={"archived_count": archived_count, "scanned_count": len(docs)},
            )
        except Exception:
            logger.exception("document_retention_cleanup_failed")
