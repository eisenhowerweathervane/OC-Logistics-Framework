from fastapi import APIRouter

from app.core.config import settings
from app.db.base import registry

router = APIRouter(prefix="/meta", tags=["meta"])

# ── Frontend page registry ────────────────────────────────────────────────────
# Keep this in sync when adding/removing frontend pages.

FRONTEND_PAGES = [
    {
        "path": "/dashboard",
        "label": "Dashboard",
        "description": "KPI cards (active loads, revenue, fleet size), revenue bar chart",
    },
    {"path": "/loads", "label": "Loads", "description": "Load list with status filter, create new load"},
    {
        "path": "/loads/:id",
        "label": "Load Detail",
        "description": "Single load detail view with state machine buttons (dispatch, pickup, deliver, etc.)",
    },
    {"path": "/loads/new", "label": "New Load", "description": "Create a new load with stops, rate, commodity"},
    {"path": "/fleet/drivers", "label": "Drivers", "description": "Driver CRUD with inline forms"},
    {"path": "/fleet/vehicles", "label": "Vehicles", "description": "Vehicle CRUD with inline forms"},
    {"path": "/compliance", "label": "Compliance", "description": "Fleet scan alerts, IFTA quarterly returns table"},
    {
        "path": "/analytics",
        "label": "Analytics",
        "description": "Revenue chart, fuel costs line chart, fleet utilization table",
    },
    {"path": "/scoring", "label": "Scoring", "description": "Lane profitability analysis, broker ratings"},
    {
        "path": "/receivables",
        "label": "Receivables",
        "description": "Accounts receivable table with overdue highlighting",
    },
    {"path": "/login", "label": "Login", "description": "Email + password authentication"},
]

API_ROUTE_GROUPS = [
    {"group": "auth", "prefix": "/api/auth", "description": "Login, refresh, user management"},
    {"group": "loads", "prefix": "/api/loads", "description": "Load CRUD, status transitions, driver assignment"},
    {"group": "drivers", "prefix": "/api/drivers", "description": "Driver CRUD"},
    {"group": "vehicles", "prefix": "/api/vehicles", "description": "Vehicle CRUD"},
    {"group": "trailers", "prefix": "/api/trailers", "description": "Trailer CRUD"},
    {"group": "brokers", "prefix": "/api/brokers", "description": "Broker CRUD"},
    {"group": "documents", "prefix": "/api/documents", "description": "File upload/download (rate cons, PODs, BOLs)"},
    {"group": "invoices", "prefix": "/api/invoices", "description": "Invoice generation and retrieval"},
    {"group": "fuel", "prefix": "/api/fuel", "description": "Fuel purchase logging"},
    {
        "group": "compliance",
        "prefix": "/api/compliance",
        "description": "IFTA returns, fleet compliance scans, maintenance, inspections",
    },
    {"group": "eld", "prefix": "/api/eld", "description": "ELD log ingestion"},
    {
        "group": "analytics",
        "prefix": "/api/analytics",
        "description": "Revenue, fuel cost, fleet utilization analytics",
    },
    {"group": "scoring", "prefix": "/api/scoring", "description": "Lane profitability, broker scoring"},
    {"group": "notifications", "prefix": "/api/notifications", "description": "Slack push alerts (AR, compliance)"},
    {"group": "receivables", "prefix": "/api/receivables", "description": "Accounts receivable, payment recording"},
    {"group": "accessorials", "prefix": "/api/accessorials", "description": "Accessorial charges on loads"},
    {
        "group": "settlements",
        "prefix": "/api/settlements",
        "description": "Driver settlement generation, approval, payment",
    },
    {"group": "customers", "prefix": "/api/customers", "description": "Customer (direct shipper) CRUD"},
    {"group": "sandbox", "prefix": "/api/sandbox", "description": "Sandbox mode toggle and status"},
    {"group": "meta", "prefix": "/api/meta", "description": "System info (this endpoint)"},
]


@router.get("/system-info")
async def system_info():
    """Returns live system metadata: frontend pages, API routes, services, and current mode.

    OpenClaw calls this to stay aware of the full system without relying on static docs.
    """
    return {
        "system": "OC Logistics TMS",
        "frontend": {
            "url": settings.frontend_url,
            "pages": FRONTEND_PAGES,
        },
        "api": {
            "url": settings.api_url,
            "route_groups": API_ROUTE_GROUPS,
        },
        "services": [
            {"name": "backend-api", "port": 8000, "description": "FastAPI backend"},
            {"name": "frontend", "port": 3000, "description": "Next.js dashboard"},
            {"name": "postgres", "port": 5432, "description": "PostgreSQL 16"},
            {"name": "redis", "port": 6379, "description": "Redis (arq task queue)"},
            {"name": "minio", "port": 9000, "description": "MinIO object storage (dev S3)"},
            {"name": "caddy", "port": 443, "description": "Reverse proxy"},
        ],
        "sandbox_mode": registry.is_sandbox,
    }
