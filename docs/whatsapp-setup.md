# WhatsApp Driver Channel Setup — OC Logistics

## How It Works

OpenClaw connects to WhatsApp via **Baileys** (WhatsApp Web protocol). No business API needed — just scan a QR code with the phone you want to use as the dispatch number.

Drivers text the dispatch number. The AI agent identifies them by phone number, pulls their context (active load, next stop, missing docs), and handles the conversation.

## 1. Link WhatsApp Account

```bash
openclaw channels login --channel whatsapp
```

This opens a QR code. Scan it with the WhatsApp app on the phone you want to use as the dispatch line. Credentials are stored at `~/.openclaw/credentials/whatsapp/`.

## 2. Add Driver Phone Numbers

Each driver needs their phone number in the TMS:

```bash
# Via API
curl -X PATCH http://localhost:8000/api/drivers/{driver_id} \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"phone": "+15551234567"}'
```

Or via the dispatch Slack channel: "Update driver John's phone to +15551234567"

## 3. Configure Allowed Contacts

In `~/.openclaw/openclaw.json` under `channels.whatsapp`:

```json
{
  "allowFrom": ["+15551234567", "+15559876543"],
  "dmPolicy": "allowlist"
}
```

Start with `allowlist` so only known drivers can interact. Add each driver's number to `allowFrom`.

## 4. Set Up Gateway Token (for outbound messages)

The backend sends proactive WhatsApp messages (dispatch alerts, doc reminders) via the OpenClaw gateway API.

```bash
# Add to your .env
OPENCLAW_GATEWAY_TOKEN=98729cde236a75b4051b64fa1844c9cfca4d05749201073c
```

Use the same token from `gateway.auth.token` in `~/.openclaw/openclaw.json`.

## What Drivers Can Do

Drivers text naturally in their language. The AI agent handles:

- **"I'm at the pickup"** → `tms_update_load_status` to `arrived_pickup`
- **"Loaded up and rolling"** → `tms_update_load_status` to `loaded` then `in_transit`
- **"Just delivered"** → `tms_update_load_status` to `delivered`
- **"Stopped for fuel, 150 gallons at Pilot in Columbus OH"** → `tms_log_fuel`
- **"Where am I going next?"** → `tms_driver_context` → next stop details
- **"What docs do I still need?"** → `tms_driver_context` → missing_document_types

## What Dispatch Can Trigger

From the Slack channel or API:

- **Dispatch alert** → `tms_notify_driver_dispatched` sends WhatsApp message with load details
- **Docs reminder** → `tms_notify_driver_docs_needed` sends reminder about missing BOL/POD

## Agent Behavior

The WhatsApp channel system prompt (from TOOLS.md) instructs the agent to:

1. Always call `tms_driver_by_phone` first to identify who's messaging
2. Then call `tms_driver_context` to understand their current situation
3. Keep responses short — drivers are on the road
4. Use WhatsApp formatting (*bold*, _italic_), no tables
5. Ask for missing info (gallons, location) when logging fuel
6. Acknowledge status updates with the next expected action

## Security Notes

- `dmPolicy: "allowlist"` — only numbers in `allowFrom` can interact
- `groupPolicy: "disabled"` — no group chats (driver comms are 1:1)
- `sendReadReceipts: true` — blue checkmarks so drivers know the message was received
- Drivers cannot access management tools (load creation, invoicing, etc.) — those are Slack-only
- The agent uses the same JWT token for all API calls (dispatcher-level access)

## Verify

```bash
# Check WhatsApp connection status
openclaw channels status --channel whatsapp

# Test driver lookup
curl http://localhost:8000/api/drivers/by-phone/+15551234567 \
  -H "Authorization: Bearer $TOKEN"
```
