import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep, DispatcherUser
from app.db.models.fleet import Customer
from app.schemas.fleet import CustomerCreate, CustomerResponse, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(body: CustomerCreate, db: DbDep, user: DispatcherUser):
    customer = Customer(
        organization_id=user.organization_id,
        company_name=body.company_name,
        contact_name=body.contact_name,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        address_line_1=body.address_line_1,
        city=body.city,
        state=body.state,
        zip=body.zip,
        credit_terms_days=body.credit_terms_days,
        preferred_lanes=body.preferred_lanes,
        notes=body.notes,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerResponse])
async def list_customers(
    db: DbDep,
    user: CurrentUser,
    customer_status: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    q = (
        select(Customer)
        .where(Customer.organization_id == user.organization_id)
        .order_by(Customer.company_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if customer_status:
        q = q.where(Customer.status == customer_status)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: uuid.UUID, db: DbDep, user: CurrentUser):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.organization_id == user.organization_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(customer_id: uuid.UUID, body: CustomerUpdate, db: DbDep, user: DispatcherUser):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.organization_id == user.organization_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    await db.commit()
    await db.refresh(customer)
    return customer
