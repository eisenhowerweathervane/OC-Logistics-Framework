import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep, DispatcherUser
from app.db.models.fleet import Broker
from app.schemas.fleet import BrokerCreate, BrokerResponse, BrokerUpdate

router = APIRouter(prefix="/brokers", tags=["brokers"])


@router.post("", response_model=BrokerResponse, status_code=201)
async def create_broker(body: BrokerCreate, db: DbDep, user: DispatcherUser):
    broker = Broker(
        organization_id=user.organization_id,
        legal_name=body.legal_name,
        dba_name=body.dba_name,
        address_line_1=body.address_line_1,
        city=body.city,
        state=body.state,
        zip=body.zip,
        billing_email=body.billing_email,
        payment_terms_days=body.payment_terms_days,
        notes=body.notes,
    )
    db.add(broker)
    await db.commit()
    await db.refresh(broker)
    return broker


@router.get("", response_model=list[BrokerResponse])
async def list_brokers(
    db: DbDep,
    user: CurrentUser,
    page: int = 1,
    page_size: int = 50,
):
    q = (
        select(Broker)
        .where(Broker.organization_id == user.organization_id)
        .order_by(Broker.legal_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    return list(result.scalars().all())


@router.get("/{broker_id}", response_model=BrokerResponse)
async def get_broker(broker_id: uuid.UUID, db: DbDep, user: CurrentUser):
    result = await db.execute(
        select(Broker).where(Broker.id == broker_id, Broker.organization_id == user.organization_id)
    )
    broker = result.scalar_one_or_none()
    if not broker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker not found")
    return broker


@router.patch("/{broker_id}", response_model=BrokerResponse)
async def update_broker(broker_id: uuid.UUID, body: BrokerUpdate, db: DbDep, user: DispatcherUser):
    result = await db.execute(
        select(Broker).where(Broker.id == broker_id, Broker.organization_id == user.organization_id)
    )
    broker = result.scalar_one_or_none()
    if not broker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(broker, field, value)
    await db.commit()
    await db.refresh(broker)
    return broker
