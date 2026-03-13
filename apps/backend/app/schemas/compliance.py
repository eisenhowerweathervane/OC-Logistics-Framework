import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class DriverContextResponse(BaseModel):
    driver_id: uuid.UUID
    driver_name: str
    active_load_id: Optional[uuid.UUID] = None
    active_load_status: Optional[str] = None
    next_stop: Optional[dict] = None
    missing_document_types: list[str] = []
    trailer_number: Optional[str] = None

    model_config = {"from_attributes": True}


class VehicleComplianceSummary(BaseModel):
    vehicle_id: uuid.UUID
    unit_number: str
    status: str
    annual_inspection_expires_at: Optional[date] = None
    annual_inspection_status: str = "unknown"
    open_maintenance_count: int = 0
    latest_roadside_inspection_at: Optional[date] = None
    out_of_service: bool = False

    model_config = {"from_attributes": True}


# ── IFTA ─────────────────────────────────────────────────────────────────────


class IftaJurisdictionEntry(BaseModel):
    jurisdiction: str
    gallons: Optional[Decimal] = None
    miles: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class IftaReturnResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    year: int
    quarter: int
    status: str
    filed_at: Optional[datetime] = None
    fuel_by_jurisdiction: list[IftaJurisdictionEntry] = []
    distance_by_jurisdiction: list[IftaJurisdictionEntry] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IftaReturnSummary(BaseModel):
    id: uuid.UUID
    year: int
    quarter: int
    status: str
    total_gallons: Optional[Decimal] = None
    total_miles: Optional[Decimal] = None
    filed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class IftaCalculateRequest(BaseModel):
    year: int
    quarter: int


# ── IRP ──────────────────────────────────────────────────────────────────────


class IrpYearResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    registration_year: int
    status: str
    cab_card_document_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IrpYearCreate(BaseModel):
    registration_year: int
    cab_card_document_id: Optional[uuid.UUID] = None


class IrpDistanceEntry(BaseModel):
    jurisdiction: str
    miles: Decimal
    source: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Fleet compliance scan ────────────────────────────────────────────────────


class ComplianceAlert(BaseModel):
    vehicle_id: str
    unit_number: str
    alert_type: str
    detail: str
    severity: str
