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
