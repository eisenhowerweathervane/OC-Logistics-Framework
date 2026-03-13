import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

# ── Broker ────────────────────────────────────────────────────────────────────


class BrokerCreate(BaseModel):
    legal_name: str = Field(max_length=200)
    dba_name: Optional[str] = Field(default=None, max_length=200)
    address_line_1: Optional[str] = Field(default=None, max_length=300)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=2)
    zip: Optional[str] = Field(default=None, max_length=10)
    billing_email: Optional[str] = Field(default=None, max_length=200)
    payment_terms_days: Optional[int] = Field(default=None, ge=0, le=365)
    notes: Optional[str] = Field(default=None, max_length=2000)


class BrokerUpdate(BaseModel):
    dba_name: Optional[str] = None
    billing_email: Optional[str] = None
    payment_terms_days: Optional[int] = None
    notes: Optional[str] = None


class BrokerResponse(BrokerCreate):
    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Driver ────────────────────────────────────────────────────────────────────


class DriverCreate(BaseModel):
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20, pattern=r"^\+?[0-9\-\s\(\)]{7,20}$")
    license_state: Optional[str] = Field(default=None, max_length=2)
    hire_date: Optional[date] = None
    pay_type: Optional[str] = Field(default=None, max_length=20)
    pay_rate: Optional[Decimal] = Field(default=None, ge=0)


class DriverUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    license_state: Optional[str] = None
    pay_type: Optional[str] = None
    pay_rate: Optional[Decimal] = None
    status: Optional[str] = None


class DriverResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    first_name: str
    last_name: str
    phone: Optional[str] = None
    license_state: Optional[str] = None
    hire_date: Optional[date] = None
    pay_type: Optional[str] = None
    pay_rate: Optional[Decimal] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Vehicle ───────────────────────────────────────────────────────────────────


class VehicleCreate(BaseModel):
    unit_number: str = Field(max_length=20)
    make: Optional[str] = Field(default=None, max_length=50)
    model: Optional[str] = Field(default=None, max_length=50)
    year: Optional[int] = Field(default=None, ge=1900, le=2100)
    plate_state: Optional[str] = Field(default=None, max_length=2)
    plate_number: Optional[str] = Field(default=None, max_length=20)
    in_service_date: Optional[date] = None


class VehicleUpdate(BaseModel):
    unit_number: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    plate_state: Optional[str] = None
    plate_number: Optional[str] = None
    status: Optional[str] = None
    out_of_service_date: Optional[date] = None


class VehicleResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    unit_number: str
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    plate_state: Optional[str] = None
    plate_number: Optional[str] = None
    status: str
    in_service_date: Optional[date] = None
    out_of_service_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Trailer ───────────────────────────────────────────────────────────────────


class TrailerCreate(BaseModel):
    trailer_number: str = Field(max_length=20)
    trailer_type: str = Field(default="dry_van", max_length=30)


class TrailerUpdate(BaseModel):
    trailer_number: Optional[str] = None
    trailer_type: Optional[str] = None
    status: Optional[str] = None


class TrailerResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    trailer_number: str
    trailer_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
