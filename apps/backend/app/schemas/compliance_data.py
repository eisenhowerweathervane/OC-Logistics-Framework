import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ── Maintenance ───────────────────────────────────────────────────────────────

class MaintenanceItemCreate(BaseModel):
    vehicle_id: uuid.UUID
    category: str = Field(max_length=100)
    due_date: Optional[date] = None
    due_odometer: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)


class MaintenanceItemUpdate(BaseModel):
    category: Optional[str] = None
    due_date: Optional[date] = None
    due_odometer: Optional[Decimal] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class MaintenanceItemResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    vehicle_id: uuid.UUID
    category: str
    due_date: Optional[date] = None
    due_odometer: Optional[Decimal] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Annual Inspection ─────────────────────────────────────────────────────────

class AnnualInspectionCreate(BaseModel):
    vehicle_id: uuid.UUID
    inspected_at: date
    inspector_name: Optional[str] = None
    expires_at: Optional[date] = None
    report_document_id: Optional[uuid.UUID] = None


class AnnualInspectionResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    vehicle_id: uuid.UUID
    inspected_at: date
    inspector_name: Optional[str] = None
    expires_at: Optional[date] = None
    report_document_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Roadside Inspection ───────────────────────────────────────────────────────

class RoadsideInspectionCreate(BaseModel):
    vehicle_id: uuid.UUID
    inspected_at: date
    report_document_id: Optional[uuid.UUID] = None
    corrections_certified_at: Optional[date] = None


class RoadsideInspectionResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    vehicle_id: uuid.UUID
    inspected_at: date
    report_document_id: Optional[uuid.UUID] = None
    corrections_certified_at: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Fuel ──────────────────────────────────────────────────────────────────────

class FuelPurchaseCreate(BaseModel):
    vehicle_id: uuid.UUID
    purchased_at_local: datetime
    seller_name: str = Field(max_length=200)
    seller_address: Optional[str] = Field(default=None, max_length=300)
    jurisdiction: Optional[str] = Field(default=None, max_length=2)
    fuel_type: Optional[str] = Field(default=None, max_length=30)
    gallons: Optional[Decimal] = Field(default=None, gt=0)
    unit_price: Optional[Decimal] = Field(default=None, ge=0)
    total_price: Optional[Decimal] = Field(default=None, ge=0)
    purchaser_name: Optional[str] = Field(default=None, max_length=100)
    receipt_document_id: Optional[uuid.UUID] = None


class FuelPurchaseResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    vehicle_id: uuid.UUID
    purchased_at_local: datetime
    seller_name: str
    seller_address: Optional[str] = None
    jurisdiction: Optional[str] = None
    fuel_type: Optional[str] = None
    gallons: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None
    purchaser_name: Optional[str] = None
    receipt_document_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── ELD ───────────────────────────────────────────────────────────────────────

class EldDayCreate(BaseModel):
    driver_id: uuid.UUID
    vehicle_id: uuid.UUID
    date_local: date
    timezone_offset_minutes: Optional[int] = Field(default=None, ge=-720, le=840)
    eld_vendor: Optional[str] = Field(default=None, max_length=100)
    eld_device_id: Optional[str] = Field(default=None, max_length=100)
    file_storage_key: str = Field(max_length=500)
    file_sha256: Optional[str] = Field(default=None, max_length=64)
    notes: Optional[str] = Field(default=None, max_length=2000)


class EldDayResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    driver_id: uuid.UUID
    vehicle_id: uuid.UUID
    date_local: date
    timezone_offset_minutes: Optional[int] = None
    eld_vendor: Optional[str] = None
    eld_device_id: Optional[str] = None
    file_storage_key: str
    file_sha256: Optional[str] = None
    notes: Optional[str] = None
    imported_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
