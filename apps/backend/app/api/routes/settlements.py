import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbDep, DispatcherUser
from app.db.models.settlements import Settlement, SettlementLineItem
from app.schemas.settlements import (
    SettlementGenerate,
    SettlementLineItemAdd,
    SettlementLineItemResponse,
    SettlementListItem,
    SettlementResponse,
    SettlementUpdate,
)
from app.services import settlement_service

router = APIRouter(tags=["settlements"])


@router.post("/settlements/generate", response_model=SettlementResponse, status_code=201)
async def generate_settlement(body: SettlementGenerate, db: DbDep, user: DispatcherUser):
    try:
        settlement = await settlement_service.generate_settlement(
            db=db,
            org_id=user.organization_id,
            driver_id=body.driver_id,
            period_start=body.period_start,
            period_end=body.period_end,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return settlement


@router.get("/settlements", response_model=list[SettlementListItem])
async def list_settlements(
    db: DbDep,
    user: CurrentUser,
    driver_id: Optional[uuid.UUID] = None,
    settlement_status: Optional[str] = None,
):
    q = select(Settlement).where(Settlement.organization_id == user.organization_id)
    if driver_id:
        q = q.where(Settlement.driver_id == driver_id)
    if settlement_status:
        q = q.where(Settlement.status == settlement_status)
    q = q.order_by(Settlement.created_at.desc())

    result = await db.execute(q)
    return list(result.scalars().all())


@router.get("/settlements/{settlement_id}", response_model=SettlementResponse)
async def get_settlement(settlement_id: uuid.UUID, db: DbDep, user: CurrentUser):
    result = await db.execute(
        select(Settlement)
        .where(Settlement.id == settlement_id, Settlement.organization_id == user.organization_id)
        .options(selectinload(Settlement.line_items))
    )
    settlement = result.scalar_one_or_none()
    if not settlement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settlement not found")
    return settlement


@router.patch("/settlements/{settlement_id}", response_model=SettlementResponse)
async def update_settlement(settlement_id: uuid.UUID, body: SettlementUpdate, db: DbDep, user: DispatcherUser):
    result = await db.execute(
        select(Settlement)
        .where(Settlement.id == settlement_id, Settlement.organization_id == user.organization_id)
        .options(selectinload(Settlement.line_items))
    )
    settlement = result.scalar_one_or_none()
    if not settlement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settlement not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(settlement, field, value)
    await db.commit()
    result2 = await db.execute(
        select(Settlement).where(Settlement.id == settlement_id).options(selectinload(Settlement.line_items))
    )
    return result2.scalar_one()


@router.post("/settlements/{settlement_id}/approve", response_model=SettlementResponse)
async def approve_settlement(settlement_id: uuid.UUID, db: DbDep, user: DispatcherUser):
    result = await db.execute(
        select(Settlement)
        .where(Settlement.id == settlement_id, Settlement.organization_id == user.organization_id)
        .options(selectinload(Settlement.line_items))
    )
    settlement = result.scalar_one_or_none()
    if not settlement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settlement not found")

    if settlement.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only draft settlements can be approved")

    settlement.status = "approved"
    settlement.approved_at = datetime.now(timezone.utc)
    settlement.approved_by = user.id
    await db.commit()
    result2 = await db.execute(
        select(Settlement).where(Settlement.id == settlement_id).options(selectinload(Settlement.line_items))
    )
    return result2.scalar_one()


@router.post("/settlements/{settlement_id}/pay", response_model=SettlementResponse)
async def mark_settlement_paid(settlement_id: uuid.UUID, db: DbDep, user: DispatcherUser):
    result = await db.execute(
        select(Settlement)
        .where(Settlement.id == settlement_id, Settlement.organization_id == user.organization_id)
        .options(selectinload(Settlement.line_items))
    )
    settlement = result.scalar_one_or_none()
    if not settlement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settlement not found")

    if settlement.status != "approved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only approved settlements can be marked paid")

    settlement.status = "paid"
    settlement.paid_at = datetime.now(timezone.utc)
    await db.commit()
    result2 = await db.execute(
        select(Settlement).where(Settlement.id == settlement_id).options(selectinload(Settlement.line_items))
    )
    return result2.scalar_one()


@router.post(
    "/settlements/{settlement_id}/lines",
    response_model=SettlementLineItemResponse,
    status_code=201,
)
async def add_line_item(settlement_id: uuid.UUID, body: SettlementLineItemAdd, db: DbDep, user: DispatcherUser):
    result = await db.execute(
        select(Settlement).where(
            Settlement.id == settlement_id, Settlement.organization_id == user.organization_id
        )
    )
    settlement = result.scalar_one_or_none()
    if not settlement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settlement not found")

    if settlement.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Can only add lines to draft settlements")

    line = SettlementLineItem(
        settlement_id=settlement_id,
        load_id=body.load_id,
        line_type=body.line_type,
        description=body.description,
        miles=body.miles,
        revenue=body.revenue,
        amount=body.amount,
    )
    db.add(line)

    # Recalculate totals
    from decimal import Decimal

    amount = Decimal(str(body.amount))
    if body.line_type == "load_pay" or body.line_type == "bonus" or body.line_type == "reimbursement":
        settlement.total_pay = Decimal(str(settlement.total_pay)) + amount
    elif body.line_type in ("deduction", "fuel_advance"):
        settlement.total_deductions = Decimal(str(settlement.total_deductions)) + abs(amount)

    settlement.net_pay = Decimal(str(settlement.total_pay)) - Decimal(str(settlement.total_deductions))

    await db.commit()
    await db.refresh(line)
    return line
