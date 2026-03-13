# Slack App Setup — OC Logistics Dispatch Channel

## 1. Create the Slack App

1. Go to https://api.slack.com/apps → **Create New App** → **From scratch**
2. Name: `OC Logistics Dispatch`
3. Pick your workspace

## 2. Enable Socket Mode

1. **Settings → Socket Mode** → Toggle on
2. Generate an **App-Level Token** with `connections:write` scope
3. Copy the `xapp-...` token → this is your `SLACK_APP_TOKEN`

## 3. Set Bot Token Scopes

**Features → OAuth & Permissions → Scopes → Bot Token Scopes:**

| Scope | Purpose |
|---|---|
| `chat:write` | Post notifications to dispatch channel |
| `chat:write.customize` | Custom bot name/icon per message |
| `channels:history` | Read messages in channels the bot is in |
| `channels:read` | List channels |
| `groups:history` | Read messages in private channels |
| `groups:read` | List private channels |
| `im:history` | Read DMs with the bot |
| `im:write` | Send DMs |
| `reactions:write` | Add emoji reactions |
| `users:read` | Resolve user names |

## 4. Enable Events (for OpenClaw)

**Features → Event Subscriptions** → Toggle on

Subscribe to bot events:
- `message.channels`
- `message.groups`
- `message.im`
- `app_mention`

## 5. Install to Workspace

**Settings → Install App** → Install → Copy the `xoxb-...` Bot Token

## 6. Create the Dispatch Channel

1. Create a channel (e.g., `#dispatch`) in Slack
2. Invite the bot: `/invite @OC Logistics Dispatch`
3. Copy the Channel ID (right-click channel name → "Copy link" → the `C...` segment)

## 7. Configure Environment

### Backend `.env`
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_DISPATCH=C0123456789
```

### OpenClaw
Tokens are already configured in `~/.openclaw/openclaw.json` under `channels.slack`.
Set the actual values via environment variables:
```bash
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_APP_TOKEN=xapp-...
```

## 8. Verify

```bash
# Test backend can post to Slack
curl -X POST http://localhost:8000/api/notifications/slack/compliance-check \
  -H "Authorization: Bearer $TOKEN"

# Check OpenClaw connects
openclaw status
```

## What Happens Automatically

- **Load delivered** → Slack notification with driver name + location
- **Invoice packet ready** → Slack notification with load ref + rate
- **Heartbeat checks** (via OpenClaw) → overdue AR summary, compliance alerts, unassigned loads

## What You Can Ask in Slack

The AI dispatcher responds to natural language in the `#dispatch` channel:
- "Show me all active loads"
- "What's the status of load 12345?"
- "Assign driver John to the Detroit load"
- "Any overdue invoices?"
- "Run a compliance check"
- "What does Raj need to deliver next?" (uses driver context)
