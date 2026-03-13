import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbDep
from app.db.models.fleet import Driver, Trailer
from app.db.models.loads import Assignment, Load, LoadStop
from app.db.models.documents import DocumentLink, Document
from app.schemas.compliance import DriverContextResponse

router = APIRouter(prefix="/drivers", tags=["drivers"])

REQUIRED_DOC_TYPES_BY_STATUS = {
    "loaded": ["bol"],
    "delivered": ["bol", "pod"],
    "arrived_delivery": ["bol"],
}


@router.get("/{driver_id}/current-context", response_model=DriverContextResponse)
async def get_driver_context(driver_id: uuid.UUID, db: DbDep, user: CurrentUser):
    result = await db.execute(
        select(Driver).where(
            Driver.id == driver_id, Driver.organization_id == user.organization_id
        )
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    # Find active assignment
    assign_result = await db.execute(
        select(Assignment)
        .where(Assignment.driver_id == driver_id, Assignment.unassigned_at.is_(None))
        .order_by(Assignment.assigned_at.desc())
        .limit(1)
        .options(selectinload(Assignment.load))
    )
    assignment = assign_result.scalar_one_or_none()

    if not assignment:
        return DriverContextResponse(
            driver_id=driver_id,
            driver_name=driver.full_name,
        )

    load = assignment.load

    # Next stop = earliest stop without a departed_at
    stops_result = await db.execute(
        select(LoadStop)
        .where(LoadStop.load_id == load.id, LoadStop.departed_at.is_(None))
        .order_by(LoadStop.seq)
        .limit(1)
    )
    next_stop = stops_result.scalar_one_or_none()

    # Trailer number
    trailer_number = None
    if assignment.trailer_id:
        trailer_result = await db.execute(
            select(Trailer).where(Trailer.id == assignment.trailer_id)
        )
        trailer = trailer_result.scalar_one_or_none()
        if trailer:
            trailer_number = trailer.trailer_number

    # Missing documents
    required = REQUIRED_DOC_TYPES_BY_STATUS.get(load.status, [])
    missing = []
    for doc_type in required:
        exists_result = await db.execute(
            select(DocumentLink)
            .where(
                DocumentLink.entity_type == "load",
                DocumentLink.entity_id == load.id,
            )
            .join(DocumentLink.document)
            .where(Document.doc_type == doc_type)
            .limit(1)
        )
        if not exists_result.scalar_one_or_none():
            missing.append(doc_type)

    next_stop_dict = None
    if next_stop:
        next_stop_dict = {
            "seq": next_stop.seq,
            "stop_type": next_stop.stop_type,
            "facility_name": next_stop.facility_name,
            "city": next_stop.city,
            "state": next_stop.state,
            "appt_start": next_stop.appt_start.isoformat() if next_stop.appt_start else None,
        }

    return DriverContextResponse(
        driver_id=driver_id,
        driver_name=driver.full_name,
        active_load_id=load.id,
        active_load_status=load.status,
        next_stop=next_stop_dict,
        missing_document_types=missing,
        trailer_number=trailer_number,
    )
