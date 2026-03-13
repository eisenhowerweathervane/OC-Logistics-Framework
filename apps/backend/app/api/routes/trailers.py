import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep, DispatcherUser
from app.db.models.fleet import Trailer
from app.schemas.fleet import TrailerCreate, TrailerResponse, TrailerUpdate

router = APIRouter(prefix="/trailers", tags=["trailers"])


@router.post("", response_model=TrailerResponse, status_code=201)
async def create_trailer(body: TrailerCreate, db: DbDep, user: DispatcherUser):
    trailer = Trailer(
        organization_id=user.organization_id,
        trailer_number=body.trailer_number,
        trailer_type=body.trailer_type,
    )
    db.add(trailer)
    await db.commit()
    await db.refresh(trailer)
    return trailer


@router.get("", response_model=list[TrailerResponse])
async def list_trailers(
    db: DbDep,
    user: CurrentUser,
    trailer_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
):
    q = select(Trailer).where(Trailer.organization_id == user.organization_id)
    if trailer_status:
        q = q.where(Trailer.status == trailer_status)
    q = q.order_by(Trailer.trailer_number).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.get("/{trailer_id}", response_model=TrailerResponse)
async def get_trailer(trailer_id: uuid.UUID, db: DbDep, user: CurrentUser):
    result = await db.execute(
        select(Trailer).where(Trailer.id == trailer_id, Trailer.organization_id == user.organization_id)
    )
    trailer = result.scalar_one_or_none()
    if not trailer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trailer not found")
    return trailer


@router.patch("/{trailer_id}", response_model=TrailerResponse)
async def update_trailer(trailer_id: uuid.UUID, body: TrailerUpdate, db: DbDep, user: DispatcherUser):
    result = await db.execute(
        select(Trailer).where(Trailer.id == trailer_id, Trailer.organization_id == user.organization_id)
    )
    trailer = result.scalar_one_or_none()
    if not trailer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trailer not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(trailer, field, value)
    await db.commit()
    await db.refresh(trailer)
    return trailer
