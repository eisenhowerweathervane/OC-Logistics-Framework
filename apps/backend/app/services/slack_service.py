"""
Slack notification service.

Sends proactive alerts to the dispatch Slack channel when key TMS events occur:
- Load delivered
- Invoice packet ready
- Overdue receivables detected

Uses Slack Web API directly via httpx. Degrades gracefully (logs + skips)
when SLACK_BOT_TOKEN or SLACK_CHANNEL_DISPATCH are not configured.
"""
import logging
from datetime import datetime
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SLACK_API_BASE = "https://slack.com/api"


def _is_configured() -> bool:
    return bool(settings.slack_bot_token and settings.slack_channel_dispatch)


async def _post_message(channel: str, text: str, blocks: Optional[list] = None) -> bool:
    """Post a message to a Slack channel. Returns True on success."""
    if not _is_configured():
        logger.debug("slack_not_configured — skipping notification")
        return False

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            payload: dict = {
                "channel": channel,
                "text": text,
            }
            if blocks:
                payload["blocks"] = blocks

            resp = await client.post(
                f"{SLACK_API_BASE}/chat.postMessage",
                json=payload,
                headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
            )
            data = resp.json()
            if not data.get("ok"):
                logger.warning("slack_post_failed", extra={"error": data.get("error")})
                return False
            return True
    except Exception:
        logger.exception("slack_post_exception")
        return False


async def notify_load_delivered(
    load_ref: str,
    load_id: str,
    driver_name: str,
    delivery_city: Optional[str] = None,
    delivery_state: Optional[str] = None,
) -> bool:
    """Alert dispatch channel that a load has been delivered."""
    location = ""
    if delivery_city and delivery_state:
        location = f" in {delivery_city}, {delivery_state}"
    elif delivery_city:
        location = f" in {delivery_city}"

    text = f":white_check_mark: *Load {load_ref} delivered*{location} by {driver_name}"
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Load ID: `{load_id}` | Next: upload POD + rate con for invoicing"},
            ],
        },
    ]
    return await _post_message(settings.slack_channel_dispatch, text, blocks)


async def notify_invoice_ready(
    load_ref: str,
    load_id: str,
    broker_name: Optional[str] = None,
    rate_total: Optional[str] = None,
) -> bool:
    """Alert dispatch channel that an invoice packet is ready to send."""
    broker_info = f" — {broker_name}" if broker_name else ""
    rate_info = f" (${rate_total})" if rate_total else ""

    text = f":invoice: *Invoice ready for Load {load_ref}*{broker_info}{rate_info}"
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Load ID: `{load_id}` | Rate con + POD verified"},
            ],
        },
    ]
    return await _post_message(settings.slack_channel_dispatch, text, blocks)


async def notify_overdue_receivables(
    overdue_count: int,
    total_amount: str,
    oldest_days: int,
) -> bool:
    """Alert dispatch channel about overdue receivables."""
    text = (
        f":warning: *{overdue_count} overdue receivable{'s' if overdue_count != 1 else ''}* "
        f"totaling ${total_amount} — oldest is {oldest_days} days past due"
    )
    return await _post_message(settings.slack_channel_dispatch, text)


async def notify_compliance_alert(
    vehicle_unit: str,
    vehicle_id: str,
    alert_type: str,
    detail: str,
) -> bool:
    """Alert dispatch channel about compliance issues (expiring inspection, overdue maintenance)."""
    emoji = ":rotating_light:" if "expired" in alert_type.lower() else ":warning:"
    text = f"{emoji} *{alert_type}* — Unit {vehicle_unit}: {detail}"
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Vehicle ID: `{vehicle_id}`"},
            ],
        },
    ]
    return await _post_message(settings.slack_channel_dispatch, text, blocks)
