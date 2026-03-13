import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.documents import Document, DocumentLink
from app.db.models.loads import InvoicePacket, Load


async def check_readiness(
    db: AsyncSession, load_id: uuid.UUID, org_id: Optional[uuid.UUID] = None
) -> InvoicePacket:
    q = select(Load).where(Load.id == load_id)
    if org_id:
        q = q.where(Load.organization_id == org_id)
    load_result = await db.execute(q)
    load = load_result.scalar_one_or_none()

    packet_result = await db.execute(
        select(InvoicePacket).where(InvoicePacket.load_id == load_id)
    )
    packet = packet_result.scalar_one_or_none()

    if not packet:
        packet = InvoicePacket(load_id=load_id, status="not_ready")
        db.add(packet)
        await db.flush()

    if not load or load.status not in ("delivered", "invoice_ready", "invoiced", "paid", "closed"):
        await db.commit()
        return packet

    rate_con_result = await db.execute(
        select(DocumentLink)
        .where(
            DocumentLink.entity_type == "load",
            DocumentLink.entity_id == load_id,
        )
        .join(DocumentLink.document)
        .where(Document.doc_type == "rate_confirmation")
        .limit(1)
    )
    has_rate_con = rate_con_result.scalar_one_or_none() is not None

    pod_result = await db.execute(
        select(DocumentLink)
        .where(
            DocumentLink.entity_type == "load",
            DocumentLink.entity_id == load_id,
        )
        .join(DocumentLink.document)
        .where(Document.doc_type == "pod")
        .limit(1)
    )
    has_pod = pod_result.scalar_one_or_none() is not None

    if has_rate_con and has_pod and packet.status == "not_ready":
        packet.status = "ready"
        packet.generated_at = datetime.now(timezone.utc)
        if load.status == "delivered":
            load.status = "invoice_ready"

    await db.commit()
    await db.refresh(packet)
    return packet


async def get_packet(db: AsyncSession, load_id: uuid.UUID) -> Optional[InvoicePacket]:
    result = await db.execute(
        select(InvoicePacket).where(InvoicePacket.load_id == load_id)
    )
    return result.scalar_one_or_none()
