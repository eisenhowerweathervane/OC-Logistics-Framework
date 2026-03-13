"""
WhatsApp notification service.

Sends proactive messages to drivers via the OpenClaw gateway's WhatsApp channel.
Uses the OpenClaw API to deliver messages (OpenClaw handles Baileys/WhatsApp Web).

Degrades gracefully when OPENCLAW_BACKEND_BASE_URL is not configured or
OpenClaw is unreachable.
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _gateway_url() -> str:
    """OpenClaw gateway URL — defaults to local."""
    return "http://localhost:3117"


def _gateway_token() -> str:
    """OpenClaw gateway auth token."""
    return settings.openclaw_gateway_token


def _is_configured() -> bool:
    return bool(settings.openclaw_gateway_token)


async def send_driver_message(phone: str, text: str) -> bool:
    """
    Send a WhatsApp message to a driver via the OpenClaw gateway.

    Args:
        phone: Driver's phone in E.164 format (e.g., "+15551234567")
        text: Message text
    """
    if not _is_configured():
        logger.debug("openclaw_gateway_not_configured — skipping WhatsApp message")
        return False

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{_gateway_url()}/api/channels/whatsapp/send",
                json={"to": phone, "text": text},
                headers={"Authorization": f"Bearer {_gateway_token()}"},
            )
            if resp.status_code == 200:
                return True
            logger.warning(
                "whatsapp_send_failed",
                extra={"status": resp.status_code, "body": resp.text[:200]},
            )
            return False
    except Exception:
        logger.exception("whatsapp_send_exception")
        return False


async def notify_driver_dispatched(
    phone: str,
    driver_name: str,
    load_ref: str,
    pickup_city: Optional[str] = None,
    pickup_state: Optional[str] = None,
    appt_start: Optional[str] = None,
) -> bool:
    """Notify driver they've been dispatched to a new load."""
    location = ""
    if pickup_city and pickup_state:
        location = f" in {pickup_city}, {pickup_state}"

    appt_info = ""
    if appt_start:
        appt_info = f"\n📅 Appointment: {appt_start}"

    text = (
        f"🚛 *New dispatch — Load {load_ref}*\n\n"
        f"Hey {driver_name.split()[0]}, you've been assigned to load {load_ref}.\n"
        f"Pickup{location}.{appt_info}\n\n"
        f"Reply here when you arrive at the pickup."
    )
    return await send_driver_message(phone, text)


async def notify_driver_docs_needed(
    phone: str,
    driver_name: str,
    load_ref: str,
    missing_docs: list[str],
) -> bool:
    """Remind driver about missing documents."""
    docs_list = ", ".join(missing_docs)
    text = (
        f"📋 *Documents needed — Load {load_ref}*\n\n"
        f"Hey {driver_name.split()[0]}, we still need: {docs_list}\n\n"
        f"Please send photos of the documents here."
    )
    return await send_driver_message(phone, text)
