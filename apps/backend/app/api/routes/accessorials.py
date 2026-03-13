import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbDep, DispatcherUser
from app.db.models.loads import AccessorialCharge, Load
from app.schemas.loads import AccessorialChargeCreate, AccessorialChargeResponse, AccessorialChargeUpdate

router = APIRouter(tags=["accessorials"])


@router.post("/loads/{load_id}/accessorials", response_model=AccessorialChargeResponse, status_code=201)
async def create_accessorial(load_id: uuid.UUID, body: AccessorialChargeCreate, db: DbDep, user: DispatcherUser):
    load_result = await db.execute(
        select(Load).where(Load.id == load_id, Load.organization_id == user.organization_id)
    )
    load = load_result.scalar_one_or_none()
    if not load:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found")

    charge = AccessorialCharge(
        organization_id=user.organization_id,
        load_id=load_id,
        charge_type=body.charge_type,
        description=body.description,
        amount=body.amount,
        occurred_at=body.occurred_at,
        notes=body.notes,
    )
    db.add(charge)
    await db.commit()
    await db.refresh(charge)
    return charge


@router.get("/loads/{load_id}/accessorials", response_model=list[AccessorialChargeResponse])
async def list_accessorials(load_id: uuid.UUID, db: DbDep, user: CurrentUser):
    load_result = await db.execute(
        select(Load).where(Load.id == load_id, Load.organization_id == user.organization_id)
    )
    if not load_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found")

    result = await db.execute(
        select(AccessorialCharge)
        .where(AccessorialCharge.load_id == load_id)
        .order_by(AccessorialCharge.created_at)
    )
    return list(result.scalars().all())


@router.patch("/accessorials/{charge_id}", response_model=AccessorialChargeResponse)
async def update_accessorial(charge_id: uuid.UUID, body: AccessorialChargeUpdate, db: DbDep, user: DispatcherUser):
    result = await db.execute(
        select(AccessorialCharge).where(
            AccessorialCharge.id == charge_id,
            AccessorialCharge.organization_id == user.organization_id,
        )
    )
    charge = result.scalar_one_or_none()
    if not charge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Accessorial charge not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(charge, field, value)
    await db.commit()
    await db.refresh(charge)
    return charge


@router.delete("/accessorials/{charge_id}", status_code=204)
async def delete_accessorial(charge_id: uuid.UUID, db: DbDep, user: DispatcherUser):
    result = await db.execute(
        select(AccessorialCharge).where(
            AccessorialCharge.id == charge_id,
            AccessorialCharge.organization_id == user.organization_id,
        )
    )
    charge = result.scalar_one_or_none()
    if not charge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Accessorial charge not found")

    await db.delete(charge)
    await db.commit()


@router.get("/accessorials/summary")
async def accessorial_summary(
    db: DbDep,
    user: CurrentUser,
    load_id: Optional[uuid.UUID] = None,
):
    q = (
        select(
            AccessorialCharge.charge_type,
            func.count().label("count"),
            func.sum(AccessorialCharge.amount).label("total"),
        )
        .where(AccessorialCharge.organization_id == user.organization_id)
        .group_by(AccessorialCharge.charge_type)
    )
    if load_id:
        q = q.where(AccessorialCharge.load_id == load_id)

    result = await db.execute(q)
    rows = result.all()
    return [{"charge_type": r.charge_type, "count": r.count, "total": float(r.total or 0)} for r in rows]
