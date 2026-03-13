# Import all models so Alembic can discover them via Base.metadata
from app.db.models.org import Organization, Role, User, UserRole
from app.db.models.fleet import Broker, Driver, Trailer, Vehicle
from app.db.models.loads import (
    Assignment,
    InvoicePacket,
    Load,
    LoadStatusEvent,
    LoadStop,
    Receivable,
    VALID_TRANSITIONS,
    LOAD_STATUSES,
)
from app.db.models.documents import Document, DocumentLink, RetentionPolicy
from app.db.models.compliance import (
    AnnualInspection,
    EldDay,
    FuelPurchase,
    IftaDistanceByJurisdiction,
    IftaFuelByJurisdiction,
    IftaReturn,
    IrpDistanceByJurisdiction,
    IrpYear,
    MaintenanceItem,
    MaintenanceWorkOrder,
    RoadsideInspection,
    UcrRegistration,
)
from app.db.models.events import AuditEvent, MessageEvent
from app.db.models.exceptions import Exception_, ExceptionEvent, ExceptionResolution

__all__ = [
    "Organization", "Role", "User", "UserRole",
    "Broker", "Driver", "Trailer", "Vehicle",
    "Load", "LoadStop", "Assignment", "LoadStatusEvent",
    "InvoicePacket", "Receivable",
    "VALID_TRANSITIONS", "LOAD_STATUSES",
    "Document", "DocumentLink", "RetentionPolicy",
    "AnnualInspection", "EldDay", "FuelPurchase",
    "IftaDistanceByJurisdiction", "IftaFuelByJurisdiction", "IftaReturn",
    "IrpDistanceByJurisdiction", "IrpYear",
    "MaintenanceItem", "MaintenanceWorkOrder",
    "RoadsideInspection", "UcrRegistration",
    "AuditEvent", "MessageEvent",
    "Exception_", "ExceptionEvent", "ExceptionResolution",
]
