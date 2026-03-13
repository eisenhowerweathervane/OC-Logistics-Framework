import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.documents import Document, DocumentLink
from app.schemas.documents import DocumentCreate
from app.services import storage_service


async def create_document(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: DocumentCreate,
    actor_user_id: Optional[uuid.UUID] = None,
    actor_driver_id: Optional[uuid.UUID] = None,
) -> Document:
    doc = Document(
        organization_id=org_id,
        doc_type=data.doc_type,
        filename=data.filename,
        mime_type=data.mime_type,
        storage_key=data.storage_key,
        sha256=data.sha256,
        upload_source=data.upload_source,
        uploaded_by_user_id=actor_user_id,
        uploaded_by_driver_id=actor_driver_id,
        doc_date=data.doc_date,
        doc_time=data.doc_time,
        nearest_city=data.nearest_city,
        amount=data.amount,
        currency=data.currency,
        vendor_name=data.vendor_name,
        retention_policy_id=data.retention_policy_id,
    )
    db.add(doc)
    await db.flush()

    now = datetime.now(timezone.utc)
    for link_item in data.links:
        link = DocumentLink(
            document_id=doc.id,
            entity_type=link_item.entity_type,
            entity_id=link_item.entity_id,
            created_at=now,
        )
        db.add(link)

    await db.commit()
    await db.refresh(doc)
    return doc


async def get_document(
    db: AsyncSession, document_id: uuid.UUID, org_id: uuid.UUID
) -> Document:
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id, Document.organization_id == org_id)
        .options(selectinload(Document.links))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


async def list_documents(
    db: AsyncSession,
    org_id: uuid.UUID,
    doc_type: Optional[str] = None,
    load_id: Optional[uuid.UUID] = None,
    driver_id: Optional[uuid.UUID] = None,
    vehicle_id: Optional[uuid.UUID] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> list[Document]:
    q = select(Document).where(Document.organization_id == org_id)
    if doc_type:
        q = q.where(Document.doc_type == doc_type)
    if load_id or driver_id or vehicle_id:
        entity_type = "load" if load_id else ("driver" if driver_id else "vehicle")
        entity_id = load_id or driver_id or vehicle_id
        q = q.join(DocumentLink, DocumentLink.document_id == Document.id).where(
            DocumentLink.entity_type == entity_type,
            DocumentLink.entity_id == entity_id,
        )
    q = q.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().unique().all())


def get_presign_upload(org_id: str, target_folder: str, filename: str, mime_type: str) -> tuple[str, str]:
    storage_key = storage_service.generate_storage_key(org_id, target_folder, filename)
    upload_url = storage_service.presign_upload(storage_key, mime_type)
    return upload_url, storage_key


def get_presign_download(storage_key: str) -> str:
    return storage_service.presign_download(storage_key)
