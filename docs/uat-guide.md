# OC Logistics — UAT Guide

## Prerequisites

- Docker Desktop running (whale icon in menu bar)
- `curl` and `jq` installed (`brew install jq` if needed)

## 1. Start the Stack

```bash
cd "/Users/rajanpatel/Documents/Projects/OC Logistics Framework"
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
docker compose -f infrastructure/docker-compose.yml up --build -d
```

Wait for all services to be healthy:

```bash
docker compose -f infrastructure/docker-compose.yml ps
```

You should see `backend-api`, `postgres`, `redis`, `minio`, `caddy`, and `frontend` all running.

## 2. Run Migrations + Seed

```bash
docker exec backend-api alembic upgrade head
docker exec backend-api python /app/../../scripts/seed.py
```

## 3. Get Your Auth Token

```bash
export BASE=http://localhost:8000

TOKEN=$(curl -s -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"changeme"}' | jq -r .access_token)

echo "Token: ${TOKEN:0:20}..."

# Verify — should show your email and roles
curl -s $BASE/api/auth/me -H "Authorization: Bearer $TOKEN" | jq
```

## 4. Health Check

```bash
curl -s $BASE/api/health | jq
# Expect: { "ok": true, "db": "ok", "storage": "ok", "sandbox_mode": false }

# System info — full metadata (frontend pages, API routes, services)
curl -s $BASE/api/meta/system-info | jq
# Returns: frontend pages, API route groups, running services, sandbox status
```

---

## 5. Core Workflow: Load Lifecycle

This is the money path — create a load and walk it through the full state machine.

### Create supporting entities

```bash
# Broker
BROKER=$(curl -s -X POST $BASE/api/brokers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"legal_name":"TQL","billing_email":"tql@example.com"}' | jq -r .id)
echo "Broker: $BROKER"

# Driver
DRIVER=$(curl -s -X POST $BASE/api/drivers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Mike","last_name":"Trucker","phone":"+15551234567"}' | jq -r .id)
echo "Driver: $DRIVER"

# Vehicle
VEHICLE=$(curl -s -X POST $BASE/api/vehicles \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"unit_number":"T-100","make":"Freightliner","model":"Cascadia","year":2022}' | jq -r .id)
echo "Vehicle: $VEHICLE"
```

### Create a load

```bash
LOAD=$(curl -s -X POST $BASE/api/loads \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"broker_id\": \"$BROKER\",
    \"reference_number\": \"REF-001\",
    \"commodity\": \"Palletized freight\",
    \"rate_total\": 2800,
    \"miles_loaded\": 850,
    \"miles_deadhead_est\": 45,
    \"stops\": [
      {\"seq\":1,\"stop_type\":\"pickup\",\"city\":\"Dallas\",\"state\":\"TX\",\"facility_name\":\"ABC Warehouse\"},
      {\"seq\":2,\"stop_type\":\"delivery\",\"city\":\"Memphis\",\"state\":\"TN\",\"facility_name\":\"XYZ Distribution\"}
    ]
  }" | jq -r .id)
echo "Load: $LOAD"
```

### Walk the state machine

```bash
# quoted → booked
curl -s -X POST "$BASE/api/loads/$LOAD/status-events" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"booked","occurred_at":"2026-03-12T08:00:00Z"}' | jq .status

# Assign driver + vehicle (auto-transitions booked → dispatched)
curl -s -X POST "$BASE/api/loads/$LOAD/assignments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"driver_id\":\"$DRIVER\",\"vehicle_id\":\"$VEHICLE\"}" | jq .id

# dispatched → arrived_pickup → loaded → in_transit → arrived_delivery → delivered
for STATUS in arrived_pickup loaded in_transit arrived_delivery delivered; do
  echo -n "$STATUS: "
  curl -s -X POST "$BASE/api/loads/$LOAD/status-events" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"status\":\"$STATUS\",\"occurred_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" | jq -r .status
done
```

### Verify: invalid transition should 422

```bash
curl -s -X POST "$BASE/api/loads/$LOAD/status-events" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"quoted","occurred_at":"2026-03-12T12:00:00Z"}' | jq
# Expect: 422 with "Invalid transition" message
```

---

## 6. Documents + Invoice Readiness

```bash
# Presigned upload URL (uploads to MinIO)
curl -s -X POST $BASE/api/documents/presign \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename":"ratecon.pdf","mime_type":"application/pdf"}' | jq .upload_url

# Create rate confirmation doc linked to load
curl -s -X POST $BASE/api/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"doc_type\":\"rate_confirmation\",\"filename\":\"ratecon.pdf\",\"mime_type\":\"application/pdf\",\"storage_key\":\"docs/ratecon-001.pdf\",\"links\":[{\"entity_type\":\"load\",\"entity_id\":\"$LOAD\"}]}" | jq .id

# Create POD doc linked to load
curl -s -X POST $BASE/api/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"doc_type\":\"pod\",\"filename\":\"pod.pdf\",\"mime_type\":\"application/pdf\",\"storage_key\":\"docs/pod-001.pdf\",\"links\":[{\"entity_type\":\"load\",\"entity_id\":\"$LOAD\"}]}" | jq .id

# Generate invoice packet — should flip load to invoice_ready
curl -s -X POST "$BASE/api/loads/$LOAD/invoice-packet/generate" \
  -H "Authorization: Bearer $TOKEN" | jq
# Expect: { "status": "ready", ... }

# Confirm load status changed
curl -s "$BASE/api/loads/$LOAD" \
  -H "Authorization: Bearer $TOKEN" | jq .status
# Expect: "invoice_ready"

# Record a payment against a receivable
# First get the receivable ID
RECV=$(curl -s "$BASE/api/receivables?recv_status=open" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id')
echo "Receivable: $RECV"

# Record full payment
curl -s -X PATCH "$BASE/api/receivables/$RECV" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"amount_paid\":2800,\"payment_date\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"payment_method\":\"check\",\"reference_number\":\"CHK-1234\"}" | jq
# Expect: status "paid"
```

---

## 7. Driver Context + Phone Lookup

```bash
# What the WhatsApp AI agent sees
curl -s "$BASE/api/drivers/$DRIVER/current-context" \
  -H "Authorization: Bearer $TOKEN" | jq

# Phone lookup — exact match
curl -s "$BASE/api/drivers/by-phone/+15551234567" \
  -H "Authorization: Bearer $TOKEN" | jq .id

# Phone lookup — digits only (should still match)
curl -s "$BASE/api/drivers/by-phone/5551234567" \
  -H "Authorization: Bearer $TOKEN" | jq .id

# Phone lookup — not found
curl -s "$BASE/api/drivers/by-phone/+10000000000" \
  -H "Authorization: Bearer $TOKEN" | jq
# Expect: 404
```

---

## 8. Load Scoring

```bash
# Score the load (rate per mile + grade)
curl -s "$BASE/api/scoring/loads/$LOAD" \
  -H "Authorization: Bearer $TOKEN" | jq
# Expect: rate_per_mile ~3.29, grade "A"

# Lane profitability (TX→TN corridor)
curl -s "$BASE/api/scoring/lanes" \
  -H "Authorization: Bearer $TOKEN" | jq

# Broker ratings
curl -s "$BASE/api/scoring/brokers" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 9. Compliance

```bash
# Log a fuel purchase
curl -s -X POST $BASE/api/fuel/purchases \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"vehicle_id\":\"$VEHICLE\",\"purchased_at_local\":\"2026-02-15T14:00:00\",\"seller_name\":\"Pilot Travel Center\",\"jurisdiction\":\"TX\",\"gallons\":150,\"total_price\":525}" | jq .id

# Calculate IFTA for Q1 2026
curl -s -X POST $BASE/api/compliance/ifta/calculate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"year":2026,"quarter":1}' | jq
# Expect: fuel_by_jurisdiction with TX entry

# Fleet compliance scan (should flag no annual inspection)
curl -s "$BASE/api/compliance/scan" \
  -H "Authorization: Bearer $TOKEN" | jq
# Expect: alert_type "no_annual_inspection" for T-100

# Add an annual inspection to clear the alert
curl -s -X POST $BASE/api/compliance/annual-inspections \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"vehicle_id\":\"$VEHICLE\",\"inspected_at\":\"2026-03-01\",\"expires_at\":\"2027-03-01\",\"inspector_name\":\"DOT Inspector\"}" | jq .id

# Re-scan — should be clean now
curl -s "$BASE/api/compliance/scan" \
  -H "Authorization: Bearer $TOKEN" | jq
# Expect: no critical alerts

# Vehicle compliance summary
curl -s "$BASE/api/vehicles/$VEHICLE/compliance-summary" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 10. Analytics Dashboard

```bash
# Dashboard overview
curl -s "$BASE/api/analytics/dashboard" \
  -H "Authorization: Bearer $TOKEN" | jq

# Revenue report (monthly)
curl -s "$BASE/api/analytics/revenue?period=monthly&months_back=3" \
  -H "Authorization: Bearer $TOKEN" | jq

# Fleet utilization
curl -s "$BASE/api/analytics/fleet-utilization" \
  -H "Authorization: Bearer $TOKEN" | jq

# Fuel cost summary
curl -s "$BASE/api/analytics/fuel-costs?months_back=3" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 11. Notifications (Slack + WhatsApp)

These degrade gracefully when tokens aren't configured — they return `sent: false`.

```bash
# Slack: overdue AR summary
curl -s -X POST $BASE/api/notifications/slack/overdue-ar-summary \
  -H "Authorization: Bearer $TOKEN" | jq

# Slack: compliance check
curl -s -X POST $BASE/api/notifications/slack/compliance-check \
  -H "Authorization: Bearer $TOKEN" | jq

# WhatsApp: dispatch alert
curl -s -X POST $BASE/api/notifications/whatsapp/dispatch-alert \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"driver_id\":\"$DRIVER\",\"load_id\":\"$LOAD\"}" | jq

# WhatsApp: docs reminder
curl -s -X POST $BASE/api/notifications/whatsapp/docs-reminder \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"driver_id\":\"$DRIVER\",\"load_id\":\"$LOAD\",\"missing_docs\":[\"bol\"]}" | jq
```

---

## 12. Edge Cases to Verify

| Test | Expected |
|------|----------|
| Login with wrong password | 401 |
| Request without token | 401 |
| Expired token (wait 60 min or set `ACCESS_TOKEN_EXPIRE_MINUTES=1`) | 401 |
| Invalid state transition (e.g. delivered→quoted) | 422 |
| Negative rate_total | 422 |
| Weight > 200,000 | 422 |
| Stop seq = 0 | 422 |
| Password under 8 chars | 422 |
| Phone lookup for unknown number | 404 |
| Load not found | 404 |

---

## 13. Interactive API Docs

FastAPI auto-generates Swagger UI:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Click "Authorize" in Swagger UI and paste your Bearer token to test any endpoint interactively.

---

## 14. MinIO Console (file storage)

- **URL**: http://localhost:9001
- **Login**: minioadmin / minioadmin

Browse uploaded documents in the `oc-logistics` bucket.

---

## Teardown

```bash
docker compose -f infrastructure/docker-compose.yml down
# Add -v to also delete data volumes:
# docker compose -f infrastructure/docker-compose.yml down -v
```

---

## 15. Sandbox Mode

Toggle between production and a demo database with sample data.

### Via Frontend

1. Open http://localhost:3000 and log in
2. Click **Sandbox Mode** in the bottom-left sidebar
3. Confirm the dialog — sidebar turns amber, "SANDBOX MODE" label appears
4. All pages now show demo data (loads, drivers, vehicles, compliance, receivables)
5. Click **Exit Sandbox** to switch back — sandbox data is deleted

### Via API

```bash
# Check current mode
curl -s $BASE/api/sandbox/status | jq
# Expect: { "sandbox_mode": false }

# Toggle on (requires auth)
curl -s -X POST $BASE/api/sandbox/toggle \
  -H "Authorization: Bearer $TOKEN" | jq
# Expect: { "sandbox_mode": true, "message": "Sandbox activated ..." }

# Toggle off
curl -s -X POST $BASE/api/sandbox/toggle \
  -H "Authorization: Bearer $TOKEN" | jq
# Expect: { "sandbox_mode": false, "message": "Sandbox deactivated ..." }
```

### What sandbox seeds

| Entity | Count | Notes |
|--------|-------|-------|
| Organization | 1 | Demo carrier |
| Users | 3 | Owner (your JWT identity), dispatcher, driver |
| Brokers | 4 | TQL, CH Robinson, Echo, Coyote |
| Drivers | 3 | Active drivers with phones |
| Vehicles | 2 | Freightliner Cascadia units |
| Trailer | 1 | 53' dry van |
| Loads | 10 | Spread across all states (quoted through archived) |
| Fuel purchases | 5 | Across TX, OK, TN jurisdictions |
| Maintenance items | 4 | Oil change, tires, brakes, DOT inspection |
| Annual inspections | 1 | Current, on primary vehicle |
| Receivables | 3 | Including 1 overdue |

### OpenClaw awareness

OpenClaw checks `tms_sandbox_status` before heartbeat notifications. In sandbox mode it skips all Slack/WhatsApp alerts and prefixes any sandbox data mentions with `[SANDBOX]`.

### System discovery

OpenClaw can call `tms_system_info` to get live metadata about the entire system — frontend pages, API routes, running services, and sandbox status. This keeps OpenClaw aware of new features without manually updating workspace docs.

---

## 16. Frontend Dashboard

The web dashboard is at **http://localhost:3000**.

### Login

- **Email**: `owner@example.com`
- **Password**: `changeme`

### Pages

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/dashboard` | KPI cards, charts |
| Loads | `/loads` | Load list with filters, create/detail views |
| Drivers | `/fleet/drivers` | Driver list and management |
| Vehicles | `/fleet/vehicles` | Vehicle list and management |
| Compliance | `/compliance` | Alerts, IFTA, inspections |
| Analytics | `/analytics` | Revenue, utilization, fuel charts |
| Scoring | `/scoring` | Lane profitability, broker ratings |
| Receivables | `/receivables` | AR tracking with overdue highlighting |

---

## 17. CI/CD

GitHub Actions runs automatically on every push and PR to `main`.

### CI Pipeline

Two parallel jobs:
- **backend-test** — Python 3.12, `ruff check`, 111 pytest tests (SQLite in-memory, no Docker)
- **frontend-build** — Node 20, `eslint`, `next build`

Check status at: https://github.com/eisenhowerweathervane/OC-Logistics-Framework/actions

### Auto-Deploy

After CI passes on `main`, the deploy workflow SSHs into the VPS and:
1. `git pull origin main`
2. `docker compose up --build -d`
3. `alembic upgrade head`

Requires GitHub secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`. Deploy skips gracefully until these are configured.

---

## 18. Accessorial Charges

Track extra charges on top of the base rate per load.

```bash
# Add detention charge to a load
curl -s -X POST "$BASE/api/loads/$LOAD/accessorials" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"charge_type":"detention","amount":"150.00","description":"2 hours waiting at shipper"}' | jq

# Add lumper fee
curl -s -X POST "$BASE/api/loads/$LOAD/accessorials" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"charge_type":"lumper","amount":"75.00"}' | jq

# List accessorials for a load
curl -s "$BASE/api/loads/$LOAD/accessorials" \
  -H "Authorization: Bearer $TOKEN" | jq

# Summary by type (counts + totals)
curl -s "$BASE/api/accessorials/summary" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 19. Driver Settlements

Generate, review, and pay driver settlements.

```bash
# Generate a settlement for the driver covering a date range
SETTLEMENT=$(curl -s -X POST "$BASE/api/settlements/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"driver_id\":\"$DRIVER\",\"period_start\":\"2026-03-01\",\"period_end\":\"2026-03-15\"}" | jq -r .id)
echo "Settlement: $SETTLEMENT"

# View settlement detail with line items
curl -s "$BASE/api/settlements/$SETTLEMENT" \
  -H "Authorization: Bearer $TOKEN" | jq

# Add a fuel advance deduction
curl -s -X POST "$BASE/api/settlements/$SETTLEMENT/lines" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"line_type":"fuel_advance","amount":"200.00","description":"Fuel advance 3/10"}' | jq

# Approve the settlement
curl -s -X POST "$BASE/api/settlements/$SETTLEMENT/approve" \
  -H "Authorization: Bearer $TOKEN" | jq .status
# Expect: "approved"

# Mark as paid
curl -s -X POST "$BASE/api/settlements/$SETTLEMENT/pay" \
  -H "Authorization: Bearer $TOKEN" | jq .status
# Expect: "paid"

# List all settlements
curl -s "$BASE/api/settlements" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 20. Customers / Shippers

CRUD for direct shipper relationships (separate from brokers).

```bash
# Create a customer
CUSTOMER=$(curl -s -X POST "$BASE/api/customers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Acme Manufacturing","contact_name":"Jane Smith","contact_email":"jane@acme.com","contact_phone":"555-0200","city":"Columbus","state":"OH","credit_terms_days":30,"preferred_lanes":"OH to PA, OH to MI"}' | jq -r .id)
echo "Customer: $CUSTOMER"

# List customers
curl -s "$BASE/api/customers" \
  -H "Authorization: Bearer $TOKEN" | jq

# Filter by status
curl -s "$BASE/api/customers?customer_status=active" \
  -H "Authorization: Bearer $TOKEN" | jq

# Get a single customer
curl -s "$BASE/api/customers/$CUSTOMER" \
  -H "Authorization: Bearer $TOKEN" | jq

# Update customer
curl -s -X PATCH "$BASE/api/customers/$CUSTOMER" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"credit_terms_days":45}' | jq
```

---

## 21. OpenClaw Tools (68 total)

OpenClaw has 68 tools across 16 files covering all TMS operations:

| Group | Tools | Description |
|-------|-------|-------------|
| Loads | 5 | create, list, get, update status, assign driver |
| Fleet | 4 | list drivers, list vehicles, driver context, vehicle compliance |
| Brokers | 4 | list, get, create, update |
| Trailers | 4 | list, get, create, update |
| Customers | 4 | list, get, create, update |
| Invoices | 4 | list receivables, generate invoice, get packet, record payment |
| Documents | 4 | presign upload, create, list, download |
| Compliance | 5 | log fuel, list fuel, log maintenance, list maintenance, scan |
| IFTA | 3 | calculate, list returns, file return |
| Inspections | 4 | annual (create/list), roadside (create/list) |
| ELD | 2 | create day log, list day logs |
| Accessorials | 4 | add, list, update, summary |
| Settlements | 6 | generate, list, get, approve, pay, add line item |
| Analytics | 4 | dashboard, revenue, fleet utilization, fuel costs |
| Scoring | 3 | score load, lane profitability, broker ratings |
| Notifications | 2 | Slack overdue AR, Slack compliance |
| WhatsApp | 3 | driver by phone, dispatch alert, docs reminder |
| Sandbox | 2 | status, toggle |
| Meta | 1 | system info |
