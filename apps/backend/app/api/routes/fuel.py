"""
Fuel purchase data entry routes.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep, DispatcherUser
from app.db.models.compliance import FuelPurchase
from app.db.models.fleet import Vehicle
from app.schemas.compliance_data import FuelPurchaseCreate, FuelPurchaseResponse

router = APIRouter(prefix="/fuel", tags=["fuel"])


@router.post("/purchases", response_model=FuelPurchaseResponse, status_code=201)
async def create_fuel_purchase(body: FuelPurchaseCreate, db: DbDep, user: DispatcherUser):
    vehicle_result = await db.execute(
        select(Vehicle).where(
            Vehicle.id == body.vehicle_id, Vehicle.organization_id == user.organization_id
        )
    )
    if not vehicle_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    purchase = FuelPurchase(
        organization_id=user.organization_id,
        vehicle_id=body.vehicle_id,
        purchased_at_local=body.purchased_at_local,
        seller_name=body.seller_name,
        seller_address=body.seller_address,
        jurisdiction=body.jurisdiction,
        fuel_type=body.fuel_type,
        gallons=body.gallons,
        unit_price=body.unit_price,
        total_price=body.total_price,
        purchaser_name=body.purchaser_name,
        receipt_document_id=body.receipt_document_id,
    )
    db.add(purchase)
    await db.commit()
    await db.refresh(purchase)
    return purchase


@router.get("/purchases", response_model=list[FuelPurchaseResponse])
async def list_fuel_purchases(
    db: DbDep,
    user: CurrentUser,
    vehicle_id: Optional[uuid.UUID] = None,
    jurisdiction: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
):
    q = select(FuelPurchase).where(FuelPurchase.organization_id == user.organization_id)
    if vehicle_id:
        q = q.where(FuelPurchase.vehicle_id == vehicle_id)
    if jurisdiction:
        q = q.where(FuelPurchase.jurisdiction == jurisdiction)
    q = q.order_by(FuelPurchase.purchased_at_local.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all())
