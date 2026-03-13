import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep, require_roles
from app.db.models.loads import Receivable
from app.schemas.invoices import InvoicePacketResponse, ReceivableResponse
from app.services import invoice_service

router = APIRouter(tags=["invoices"])

_dispatcher = Depends(require_roles(["owner", "dispatcher"]))


@router.get("/loads/{load_id}/invoice-packet", response_model=InvoicePacketResponse)
async def get_invoice_packet(load_id: uuid.UUID, db: DbDep, user: CurrentUser):
    packet = await invoice_service.get_packet(db, load_id)
    if not packet:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice packet not found")
    return packet


@router.post("/loads/{load_id}/invoice-packet/generate", response_model=InvoicePacketResponse, status_code=200)
async def generate_invoice_packet(load_id: uuid.UUID, db: DbDep, user: CurrentUser = _dispatcher):
    return await invoice_service.check_readiness(db, load_id)


@router.get("/receivables", response_model=list[ReceivableResponse])
async def list_receivables(
    db: DbDep,
    user: CurrentUser = _dispatcher,
    recv_status: Optional[str] = None,
    broker_id: Optional[uuid.UUID] = None,
    due_before: Optional[datetime] = None,
    overdue_only: bool = False,
    page: int = 1,
    page_size: int = 50,
):
    from datetime import timezone
    q = select(Receivable).join(Receivable.load).where(
        __import__("app.db.models.loads", fromlist=["Load"]).Load.organization_id == user.organization_id
    )
    if recv_status:
        q = q.where(Receivable.status == recv_status)
    if broker_id:
        q = q.where(Receivable.broker_id == broker_id)
    if due_before:
        q = q.where(Receivable.due_date <= due_before)
    if overdue_only:
        from datetime import datetime
        q = q.where(
            Receivable.status.in_(["open", "partial"]),
            Receivable.due_date < datetime.now(timezone.utc),
        )
    q = q.order_by(Receivable.due_date.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all())
