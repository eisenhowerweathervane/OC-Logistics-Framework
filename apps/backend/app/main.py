from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    analytics, auth, brokers, compliance, documents, drivers, eld, fuel, health, invoices,
    loads, meta, notifications, sandbox, scoring, trailers, vehicles,
)
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    register_exception_handlers,
)
from app.services import storage_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # Ensure MinIO bucket exists on startup
    try:
        storage_service.ensure_bucket_exists()
    except Exception:
        pass
    yield


app = FastAPI(
    title="OC Logistics Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware (order matters — outermost first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,
    window_seconds=60,
    exclude_paths=["/api/health"],
)

# Global exception handlers
register_exception_handlers(app)

# Routes
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(loads.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(invoices.router, prefix="/api")
app.include_router(drivers.router, prefix="/api")
app.include_router(vehicles.router, prefix="/api")
app.include_router(brokers.router, prefix="/api")
app.include_router(trailers.router, prefix="/api")
app.include_router(compliance.router, prefix="/api")
app.include_router(fuel.router, prefix="/api")
app.include_router(eld.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(scoring.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(sandbox.router, prefix="/api")
app.include_router(meta.router, prefix="/api")
