import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep, DispatcherUser
from app.db.models.loads import Load, Receivable
from app.schemas.invoices import InvoicePacketResponse, ReceivableResponse
from app.services import invoice_service

router = APIRouter(tags=["invoices"])


@router.get("/loads/{load_id}/invoice-packet", response_model=InvoicePacketResponse)
async def get_invoice_packet(load_id: uuid.UUID, db: DbDep, user: CurrentUser):
    # Verify load belongs to user's org
    load_result = await db.execute(select(Load).where(Load.id == load_id, Load.organization_id == user.organization_id))
    if not load_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found")
    packet = await invoice_service.get_packet(db, load_id)
    if not packet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice packet not found")
    return packet


@router.post("/loads/{load_id}/invoice-packet/generate", response_model=InvoicePacketResponse, status_code=200)
async def generate_invoice_packet(load_id: uuid.UUID, db: DbDep, user: DispatcherUser):
    # Verify load belongs to user's org
    load_result = await db.execute(select(Load).where(Load.id == load_id, Load.organization_id == user.organization_id))
    if not load_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found")
    return await invoice_service.check_readiness(db, load_id, org_id=user.organization_id)


@router.get("/receivables", response_model=list[ReceivableResponse])
async def list_receivables(
    db: DbDep,
    user: DispatcherUser,
    recv_status: Optional[str] = None,
    broker_id: Optional[uuid.UUID] = None,
    due_before: Optional[datetime] = None,
    overdue_only: bool = False,
    page: int = 1,
    page_size: int = 50,
):
    q = select(Receivable).join(Receivable.load).where(Load.organization_id == user.organization_id)
    if recv_status:
        q = q.where(Receivable.status == recv_status)
    if broker_id:
        q = q.where(Receivable.broker_id == broker_id)
    if due_before:
        q = q.where(Receivable.due_date <= due_before)
    if overdue_only:
        q = q.where(
            Receivable.status.in_(["open", "partial"]),
            Receivable.due_date < datetime.now(timezone.utc),
        )
    q = q.order_by(Receivable.due_date.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all())
