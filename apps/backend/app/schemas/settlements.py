import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class SettlementGenerate(BaseModel):
    driver_id: uuid.UUID
    period_start: date
    period_end: date


class SettlementLineItemAdd(BaseModel):
    load_id: Optional[uuid.UUID] = None
    line_type: str = Field(max_length=30)
    description: Optional[str] = Field(default=None, max_length=500)
    miles: Optional[Decimal] = Field(default=None, ge=0, le=100000)
    revenue: Optional[Decimal] = Field(default=None, ge=0, le=1000000)
    amount: Decimal = Field(ge=-1000000, le=1000000)


class SettlementLineItemResponse(BaseModel):
    id: uuid.UUID
    settlement_id: uuid.UUID
    load_id: Optional[uuid.UUID] = None
    line_type: str
    description: Optional[str] = None
    miles: Optional[Decimal] = None
    revenue: Optional[Decimal] = None
    amount: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SettlementResponse(BaseModel):
    id: uuid.UUID
    driver_id: uuid.UUID
    period_start: date
    period_end: date
    status: str
    total_miles: Decimal
    total_revenue: Decimal
    total_pay: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    approved_at: Optional[datetime] = None
    approved_by: Optional[uuid.UUID] = None
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None
    line_items: list[SettlementLineItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SettlementListItem(BaseModel):
    id: uuid.UUID
    driver_id: uuid.UUID
    period_start: date
    period_end: date
    status: str
    total_revenue: Decimal
    net_pay: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class SettlementUpdate(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=5000)
