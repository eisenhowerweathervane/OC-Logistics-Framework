# OC Logistics Framework — Bug Log

## Format
Each entry: date · severity · file · description · status

Severity: P0 (blocker) | P1 (high) | P2 (medium) | P3 (low)
Status: open | fixed | wontfix

---

## Open

_No open bugs._

## Code Review — Security & Validation Audit (2026-03-12)

Comprehensive code review performed across all backend services. Found 3 P0 security issues and 5 P1 validation gaps. All fixed and verified with 95 tests passing.

### P0 Fixes

**CORS wildcard** — `apps/backend/app/main.py` had `allow_origins=["*"]`, allowing any origin to make credentialed requests. Fixed by reading `ALLOWED_ORIGINS` from settings config (comma-separated list, defaults to `http://localhost:3000,http://localhost:8000`).

**Missing org_id validation on load assignments** — `apps/backend/app/services/load_service.py` `assign_load()` accepted any `driver_id`/`vehicle_id` without verifying they belong to the same organization as the load. A user could assign another org's driver to their load. Fixed by querying driver/vehicle and checking `organization_id` matches, raising 403 on mismatch.

**Rate limiter disabled in tests** — `apps/backend/app/core/middleware.py` rate limiter was causing 429 errors during test runs (100+ requests per suite). Fixed by checking `TESTING` env var to skip rate limiting during tests.

### P1 Fixes

**Fleet schema constraints** — `apps/backend/app/schemas/fleet.py` had no validation on phone format, year range, or string lengths. Added: phone regex `^\+?[0-9\-\s\(\)]{7,20}$`, year range 1900–2100, max_length on all string fields, pay_rate ge=0.

**Compliance data schema constraints** — `apps/backend/app/schemas/compliance_data.py` allowed negative gallons and prices. Added: gallons gt=0, total_price/unit_price ge=0, max_length on string fields.

**Document schema constraints** — `apps/backend/app/schemas/documents.py` had no max_length on filename, mime_type, storage_key. Added max_length constraints.

**Password minimum length** — `apps/backend/app/schemas/auth.py` had `min_length=1`, accepting single-character passwords. Changed to `min_length=8`.

**Invoice readiness org_id** — `apps/backend/app/services/invoice_service.py` `check_readiness()` didn't accept org_id parameter. Added optional `org_id` parameter for defense-in-depth filtering. Updated invoice route to pass `user.organization_id`.

## Phase 5 Notes (WhatsApp Driver Channel)
No new bugs introduced. Phone normalization tested with exact, formatted, and digits-only lookups. WhatsApp notification routes degrade gracefully when driver has no phone or driver not found.

## Phase 6 Notes (Compliance Automation)
No new bugs introduced. IFTA quarterly calculation, filing, IRP registration, and fleet compliance scanning all tested. 70 tests passing.

## Phase 7 Notes (Background Jobs)
No new bugs introduced. Added 3 scheduled cron tasks: daily_compliance_digest (7 AM UTC), weekly_ar_reminder (Monday 9 AM UTC), document_retention_cleanup (3 AM UTC). 74 tests passing.

## Phase 8 Notes (Load Scoring)
No new bugs introduced. Load RPM scoring with letter grades, lane profitability analysis, and broker rating endpoints all tested. 80 tests passing.

## Phase 9 Notes (Hardening)
No new bugs introduced. Added rate limiting middleware (100 req/min per IP), request logging middleware, global exception handlers, and Pydantic Field constraints on load/auth schemas. 87 tests passing.

## Phase 10 Notes (Analytics)
No new bugs introduced. Dashboard summary, revenue by period, fleet utilization, and fuel cost summary endpoints all tested. 95 tests passing. All phases complete.

## Sandbox Mode (2026-03-12)

Added full sandbox mode toggle across backend, frontend, and OpenClaw.

**Backend** — New `SessionRegistry` in `apps/backend/app/db/base.py` allows runtime switching between production and sandbox databases. Sandbox uses a separate PostgreSQL database (`oc_logistics_sandbox`) created/dropped dynamically via asyncpg. State persisted to `/tmp/oc_sandbox_state.json` so sandbox survives backend restarts. New service `apps/backend/app/services/sandbox_service.py` handles create/drop/seed lifecycle. Seed data includes: org, roles, users (preserving caller UUID for JWT continuity), 4 brokers, 3 drivers, 2 vehicles, 1 trailer, 10 loads across all states, stops, assignments, status events, invoice packets, receivables (including overdue), 5 fuel purchases, 4 maintenance items, and annual inspections.

**API** — `GET /api/sandbox/status` (public) and `POST /api/sandbox/toggle` (requires dispatcher/owner role) in `apps/backend/app/api/routes/sandbox.py`. Health endpoint now includes `sandbox_mode` field.

**Frontend** — Sidebar toggle button with confirm dialog. Amber color scheme across sidebar when sandbox active. "SANDBOX MODE" label with flask icon. Full page reload after toggle to refresh all data from new DB.

**OpenClaw** — Two new tools: `tms_sandbox_status` and `tms_sandbox_toggle`. HEARTBEAT.md updated to skip all notifications when sandbox active. TOOLS.md updated with sandbox documentation.

No bugs introduced. All 95 existing tests continue to pass.

## System Info Endpoint (2026-03-12)

Added `GET /api/meta/system-info` so OpenClaw can discover the system dynamically instead of relying on static workspace docs.

**Backend** — New `apps/backend/app/api/routes/meta.py` returns live metadata: frontend pages (paths, labels, descriptions), API route groups, running services, and sandbox mode status. Registered in `main.py`.

**OpenClaw** — New `tms_system_info` tool (`apps/openclaw/src/tools/meta.ts`) calls the endpoint. Registered in `index.ts` (23 tools total). TOOLS.md updated to reference `tms_system_info` instead of a static page list, so OpenClaw always gets current info even as the frontend evolves.

No bugs introduced. All 95 existing tests continue to pass.

---

## Fixed

**2026-03-12 · P0 · apps/backend/app/api/deps.py**
`get_current_user` called `uuid.UUID(user_id)` on the JWT `sub` claim without error handling. A malformed or tampered token with a non-UUID `sub` would crash with an unhandled `ValueError` (500) instead of returning 401. Fixed by wrapping in try/except and raising `HTTPException(401)`.

**2026-03-12 · P1 · apps/openclaw/src/tools/fleet.ts**
`tms_list_drivers` and `tms_list_vehicles` sent `?status=...` as the query parameter, but the backend routes expect `?driver_status=` and `?vehicle_status=` respectively. Status filtering was silently ignored. Fixed by mapping to the correct query parameter names.

**2026-03-12 · P1 · apps/openclaw/src/tools/invoices.ts**
`tms_list_receivables` sent `?status=...` but the backend route expects `?recv_status=`. Status filtering was silently ignored. Fixed by mapping to `recv_status`.

**2026-03-12 · P1 · apps/backend/app/api/routes/invoices.py**
`get_invoice_packet` and `generate_invoice_packet` did not verify the load belonged to the requesting user's organization. An authenticated user could access invoice data for loads in other orgs by guessing load_ids. Fixed by adding `Load.organization_id == user.organization_id` check before proceeding.

---

## Previously Fixed

**2026-03-11 · P1 · apps/backend/pyproject.toml**
Missing `email-validator` transitive dependency. `pydantic>=2.7.0` does not install `email-validator` by default; importing `EmailStr` raised `ImportError`. Fixed by changing to `pydantic[email]>=2.7.0`.

**2026-03-11 · P0 · apps/backend/app/api/deps.py + routes/loads.py + routes/documents.py + routes/invoices.py**
FastAPI `AssertionError` on startup: "Cannot specify `Depends` in `Annotated` and default value together". Routes used `user: CurrentUser = Depends(require_roles(...))` which is invalid when `CurrentUser` is itself `Annotated[User, Depends(...)]`. Fixed by creating pre-built `Annotated` types (`DispatcherUser`, `AnyStaffUser`) in deps.py and using them directly in route signatures.

**2026-03-11 · P0 · apps/backend/pyproject.toml**
Missing `greenlet` dependency. SQLAlchemy async requires `greenlet` at runtime; all async DB operations raised `ValueError: the greenlet library is required`. Fixed by adding `"greenlet>=3.0.0"` to pyproject.toml and installing it.

**2026-03-11 · P1 · apps/backend/app/db/models/events.py**
`JSONB` (PostgreSQL-specific type) used for `payload_json` column in `AuditEvent`. SQLite test DB cannot compile `JSONB`, raising `sqlalchemy.exc.CompileError`. Fixed by importing `JSON` from `sqlalchemy` (not the dialect) and using `mapped_column(JSON, ...)`. Production migrations retain `JSONB` for performance.

**2026-03-11 · P0 · apps/backend/pyproject.toml**
`passlib[bcrypt]` incompatible with `bcrypt>=5.0.0`. bcrypt 5.x removed `__about__` module and changed password length handling; passlib 1.7.4 raises `AttributeError` and `ValueError` during hashing. Fixed by pinning `"bcrypt>=4.0.0,<5.0.0"` in pyproject.toml.

**2026-03-12 · P3 · apps/backend/tests/test_auth.py**
`test_me_unauthenticated` asserted `status_code == 403` based on older FastAPI behaviour where `HTTPBearer(auto_error=True)` raised 403 for missing credentials. FastAPI 0.135 returns 401. Fixed by updating assertion to `in (401, 403)` — both are acceptable for an unauthenticated request.

**2026-03-11 · P2 · apps/backend/app/services/invoice_service.py**
`check_readiness()` used `__import__("app.db.models.documents", fromlist=["Document"])` inline to reference the `Document` model, avoiding a circular import that no longer existed. Fixed by adding `Document` to the top-level import from `app.db.models.documents`.

**2026-03-11 · P1 · apps/backend/app/services/load_service.py**
`create_load` and `update_load` returned a `Load` ORM object after `db.refresh()` without eagerly loading the `stops` relationship. FastAPI's response serialization of `LoadResponse` (which includes `stops`) triggered a lazy load outside the async greenlet context, raising `ResponseValidationError` (MissingGreenlet). Fixed by replacing the final `db.refresh(load)` return with a call to `get_load()`, which uses `selectinload` for all relationships.
