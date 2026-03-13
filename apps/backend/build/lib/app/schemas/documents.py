import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class DocumentLinkItem(BaseModel):
    entity_type: str
    entity_id: uuid.UUID


class PresignRequest(BaseModel):
    filename: str
    mime_type: str
    target_folder: str = "documents"


class PresignResponse(BaseModel):
    upload_url: str
    storage_key: str


class DocumentCreate(BaseModel):
    doc_type: str
    filename: str
    mime_type: str
    storage_key: str
    sha256: Optional[str] = None
    upload_source: Optional[str] = None
    doc_date: Optional[date] = None
    doc_time: Optional[time] = None
    nearest_city: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "USD"
    vendor_name: Optional[str] = None
    retention_policy_id: Optional[uuid.UUID] = None
    links: list[DocumentLinkItem] = []


class DocumentResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    doc_type: str
    filename: str
    mime_type: str
    storage_key: str
    sha256: Optional[str] = None
    upload_source: Optional[str] = None
    doc_date: Optional[date] = None
    nearest_city: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str
    vendor_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DownloadUrlResponse(BaseModel):
    download_url: str
    expires_in_seconds: int
