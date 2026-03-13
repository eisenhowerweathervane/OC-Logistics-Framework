import uuid

from fastapi import APIRouter

from app.api.deps import DispatcherUser
from app.services.sandbox_service import get_sandbox_status, toggle_sandbox

router = APIRouter(prefix="/sandbox", tags=["sandbox"])


@router.get("/status")
async def sandbox_status():
    """Check whether sandbox mode is active."""
    return get_sandbox_status()


@router.post("/toggle")
async def sandbox_toggle(user: DispatcherUser):
    """Toggle sandbox mode on/off. Requires owner or dispatcher role.

    Passes the current user's identity so the sandbox seed can create
    a matching user, keeping the JWT valid across the switch.
    """
    current = get_sandbox_status()
    activate = not current["sandbox_mode"]
    return await toggle_sandbox(
        activate,
        caller_id=user.id,
        caller_email=user.email,
        caller_org_id=user.organization_id,
    )
