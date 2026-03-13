import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class LoadStopCreate(BaseModel):
    seq: int = Field(ge=1, le=100)
    stop_type: str = Field(default="pickup", max_length=20)
    facility_name: Optional[str] = None
    address_line_1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    appt_start: Optional[datetime] = None
    appt_end: Optional[datetime] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None


class LoadStopResponse(LoadStopCreate):
    id: uuid.UUID
    load_id: uuid.UUID
    arrived_at: Optional[datetime] = None
    departed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LoadCreate(BaseModel):
    broker_id: Optional[uuid.UUID] = None
    shipping_document_number: Optional[str] = Field(default=None, max_length=200)
    reference_number: Optional[str] = Field(default=None, max_length=200)
    commodity: Optional[str] = Field(default=None, max_length=500)
    weight_lbs: Optional[Decimal] = Field(default=None, ge=0, le=200000)
    pieces: Optional[int] = Field(default=None, ge=0, le=100000)
    rate_total: Optional[Decimal] = Field(default=None, ge=0, le=1000000)
    rate_type: Optional[str] = Field(default=None, max_length=20)
    miles_loaded: Optional[Decimal] = Field(default=None, ge=0, le=100000)
    miles_deadhead_est: Optional[Decimal] = Field(default=None, ge=0, le=100000)
    notes: Optional[str] = Field(default=None, max_length=5000)
    stops: list[LoadStopCreate] = Field(default=[], max_length=50)


class LoadUpdate(BaseModel):
    commodity: Optional[str] = None
    weight_lbs: Optional[Decimal] = None
    rate_total: Optional[Decimal] = None
    rate_type: Optional[str] = None
    miles_loaded: Optional[Decimal] = None
    miles_deadhead_est: Optional[Decimal] = None
    notes: Optional[str] = None


class LoadResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    broker_id: Optional[uuid.UUID] = None
    shipping_document_number: Optional[str] = None
    reference_number: Optional[str] = None
    commodity: Optional[str] = None
    weight_lbs: Optional[Decimal] = None
    pieces: Optional[int] = None
    rate_total: Optional[Decimal] = None
    rate_type: Optional[str] = None
    miles_loaded: Optional[Decimal] = None
    miles_deadhead_est: Optional[Decimal] = None
    notes: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    stops: list[LoadStopResponse] = []

    model_config = {"from_attributes": True}


class AssignmentCreate(BaseModel):
    driver_id: uuid.UUID
    vehicle_id: uuid.UUID
    trailer_id: Optional[uuid.UUID] = None


class AssignmentResponse(BaseModel):
    id: uuid.UUID
    load_id: uuid.UUID
    driver_id: uuid.UUID
    vehicle_id: uuid.UUID
    trailer_id: Optional[uuid.UUID] = None
    assigned_at: datetime
    unassigned_at: Optional[datetime] = None
    dispatcher_user_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class StatusEventCreate(BaseModel):
    status: str = Field(max_length=30)
    occurred_at: datetime
    location_city: Optional[str] = Field(default=None, max_length=200)
    note: Optional[str] = Field(default=None, max_length=2000)
    source_channel: Optional[str] = Field(default=None, max_length=30)
    source_message_id: Optional[str] = Field(default=None, max_length=200)


class StatusEventResponse(BaseModel):
    id: uuid.UUID
    load_id: uuid.UUID
    status: str
    occurred_at: datetime
    actor_user_id: Optional[uuid.UUID] = None
    actor_driver_id: Optional[uuid.UUID] = None
    location_city: Optional[str] = None
    note: Optional[str] = None
    source_channel: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LoadListItem(BaseModel):
    id: uuid.UUID
    status: str
    broker_id: Optional[uuid.UUID] = None
    shipping_document_number: Optional[str] = None
    rate_total: Optional[Decimal] = None
    commodity: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
