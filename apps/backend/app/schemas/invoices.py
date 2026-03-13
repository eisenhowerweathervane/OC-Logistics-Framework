import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class RecordPaymentRequest(BaseModel):
    amount_paid: Decimal = Field(gt=0, description="Payment amount received")
    payment_date: datetime
    payment_method: Optional[str] = Field(default=None, max_length=50)
    reference_number: Optional[str] = Field(default=None, max_length=100)


class InvoicePacketResponse(BaseModel):
    id: uuid.UUID
    load_id: uuid.UUID
    status: str
    rate_con_document_id: Optional[uuid.UUID] = None
    pod_document_id: Optional[uuid.UUID] = None
    generated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReceivableResponse(BaseModel):
    id: uuid.UUID
    load_id: uuid.UUID
    broker_id: uuid.UUID
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    amount_due: Decimal
    amount_paid: Decimal
    status: str
    last_reminder_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
