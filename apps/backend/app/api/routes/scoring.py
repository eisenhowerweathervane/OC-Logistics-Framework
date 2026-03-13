"""
Load scoring and profitability analysis routes.

Provides rate-per-mile scoring, lane profitability analysis, and broker ratings.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbDep
from app.services import scoring_service

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.get("/loads/{load_id}")
async def score_load(load_id: uuid.UUID, db: DbDep, user: CurrentUser):
    """Get rate-per-mile score and grade for a single load."""
    result = await scoring_service.score_load(db, load_id, user.organization_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found")
    return result


@router.get("/lanes")
async def get_lane_profitability(
    db: DbDep,
    user: CurrentUser,
    origin_state: Optional[str] = None,
    dest_state: Optional[str] = None,
    limit: int = 20,
):
    """Analyze lane profitability by origin→destination state."""
    return await scoring_service.lane_profitability(db, user.organization_id, origin_state, dest_state, limit)


@router.get("/brokers")
async def get_broker_ratings(
    db: DbDep,
    user: CurrentUser,
    limit: int = 20,
):
    """Rate brokers by RPM, payment speed, and volume."""
    return await scoring_service.broker_ratings(db, user.organization_id, limit)
