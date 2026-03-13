import uuid
from typing import Optional

from fastapi import APIRouter

from app.api.deps import AnyStaffUser, CurrentUser, DbDep
from app.core.config import settings
from app.schemas.documents import (
    DocumentCreate,
    DocumentResponse,
    DownloadUrlResponse,
    PresignRequest,
    PresignResponse,
)
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/presign", response_model=PresignResponse)
async def presign_upload(body: PresignRequest, user: AnyStaffUser):
    upload_url, storage_key = document_service.get_presign_upload(
        str(user.organization_id), body.target_folder, body.filename, body.mime_type
    )
    return PresignResponse(upload_url=upload_url, storage_key=storage_key)


@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(body: DocumentCreate, db: DbDep, user: AnyStaffUser):
    return await document_service.create_document(
        db, user.organization_id, body, actor_user_id=user.id
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    db: DbDep,
    user: CurrentUser,
    doc_type: Optional[str] = None,
    load_id: Optional[uuid.UUID] = None,
    driver_id: Optional[uuid.UUID] = None,
    vehicle_id: Optional[uuid.UUID] = None,
    page: int = 1,
    page_size: int = 50,
):
    return await document_service.list_documents(
        db, user.organization_id, doc_type, load_id, driver_id, vehicle_id, page=page, page_size=page_size
    )


@router.get("/{document_id}/download", response_model=DownloadUrlResponse)
async def download_document(document_id: uuid.UUID, db: DbDep, user: CurrentUser):
    doc = await document_service.get_document(db, document_id, user.organization_id)
    download_url = document_service.get_presign_download(doc.storage_key)
    return DownloadUrlResponse(
        download_url=download_url,
        expires_in_seconds=settings.presign_expiry_seconds,
    )
