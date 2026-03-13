from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, documents, drivers, health, invoices, loads, vehicles
from app.core.logging import configure_logging
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(loads.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(invoices.router, prefix="/api")
app.include_router(drivers.router, prefix="/api")
app.include_router(vehicles.router, prefix="/api")
