import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbDep, DispatcherUser
from app.schemas.loads import (
    AssignmentCreate,
    AssignmentResponse,
    LoadCreate,
    LoadResponse,
    LoadUpdate,
    LoadListItem,
    StatusEventCreate,
    StatusEventResponse,
)
from app.services import load_service

router = APIRouter(prefix="/loads", tags=["loads"])


@router.post("", response_model=LoadResponse, status_code=201)
async def create_load(body: LoadCreate, db: DbDep, user: DispatcherUser):
    return await load_service.create_load(db, user.organization_id, body, actor_user_id=user.id)


@router.get("", response_model=list[LoadListItem])
async def list_loads(
    db: DbDep,
    user: CurrentUser,
    load_status: Optional[str] = Query(None, alias="status"),
    broker_id: Optional[uuid.UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50,
):
    return await load_service.list_loads(
        db, user.organization_id, load_status, broker_id, date_from, date_to, page, page_size
    )


@router.get("/{load_id}", response_model=LoadResponse)
async def get_load(load_id: uuid.UUID, db: DbDep, user: CurrentUser):
    return await load_service.get_load(db, load_id, user.organization_id)


@router.patch("/{load_id}", response_model=LoadResponse)
async def update_load(load_id: uuid.UUID, body: LoadUpdate, db: DbDep, user: DispatcherUser):
    return await load_service.update_load(db, load_id, user.organization_id, body)


@router.post("/{load_id}/assignments", response_model=AssignmentResponse, status_code=201)
async def assign_load(load_id: uuid.UUID, body: AssignmentCreate, db: DbDep, user: DispatcherUser):
    return await load_service.assign_load(db, load_id, user.organization_id, body, dispatcher_user_id=user.id)


@router.post("/{load_id}/status-events", response_model=StatusEventResponse, status_code=201)
async def append_status_event(load_id: uuid.UUID, body: StatusEventCreate, db: DbDep, user: CurrentUser):
    return await load_service.append_status_event(
        db, load_id, user.organization_id, body, actor_user_id=user.id
    )
