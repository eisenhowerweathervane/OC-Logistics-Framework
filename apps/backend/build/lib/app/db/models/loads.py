import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# Load lifecycle state machine — enforced by load_service.py
VALID_TRANSITIONS: dict[str, list[str]] = {
    "quoted": ["booked"],
    "booked": ["dispatched"],
    "dispatched": ["arrived_pickup"],
    "arrived_pickup": ["loaded"],
    "loaded": ["in_transit"],
    "in_transit": ["arrived_delivery"],
    "arrived_delivery": ["delivered"],
    "delivered": ["invoice_ready"],
    "invoice_ready": ["invoiced"],
    "invoiced": ["paid"],
    "paid": ["closed"],
    "closed": ["archived"],
    "archived": [],
}

LOAD_STATUSES = list(VALID_TRANSITIONS.keys())


class Load(Base, TimestampMixin):
    __tablename__ = "loads"
    __table_args__ = (
        Index("ix_loads_status", "status"),
        Index("ix_loads_broker_id", "broker_id"),
        Index("ix_loads_shipping_document_number", "shipping_document_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    broker_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brokers.id"), nullable=True
    )
    shipping_document_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    commodity: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight_lbs: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    pieces: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rate_total: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    rate_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    miles_loaded: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    miles_deadhead_est: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="quoted")

    stops: Mapped[list["LoadStop"]] = relationship(
        "LoadStop", back_populates="load", order_by="LoadStop.seq"
    )
    assignments: Mapped[list["Assignment"]] = relationship("Assignment", back_populates="load")
    status_events: Mapped[list["LoadStatusEvent"]] = relationship(
        "LoadStatusEvent", back_populates="load"
    )
    invoice_packet: Mapped["InvoicePacket | None"] = relationship(
        "InvoicePacket", back_populates="load", uselist=False
    )
    receivable: Mapped["Receivable | None"] = relationship(
        "Receivable", back_populates="load", uselist=False
    )


class LoadStop(Base, TimestampMixin):
    __tablename__ = "load_stops"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    load_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loads.id"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    stop_type: Mapped[str] = mapped_column(String(20), nullable=False, default="pickup")
    facility_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    appt_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    appt_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    departed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    load: Mapped["Load"] = relationship("Load", back_populates="stops")


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    load_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loads.id"), nullable=False
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False
    )
    trailer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trailers.id"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatcher_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    load: Mapped["Load"] = relationship("Load", back_populates="assignments")


class LoadStatusEvent(Base):
    __tablename__ = "load_status_events"
    __table_args__ = (
        Index("ix_load_status_events_load_id_occurred_at", "load_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    load_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loads.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    actor_driver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=True
    )
    location_city: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_channel: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    load: Mapped["Load"] = relationship("Load", back_populates="status_events")


class InvoicePacket(Base, TimestampMixin):
    __tablename__ = "invoice_packets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    load_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loads.id"), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_ready")
    rate_con_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    pod_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    packet_storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    load: Mapped["Load"] = relationship("Load", back_populates="invoice_packet")


class Receivable(Base, TimestampMixin):
    __tablename__ = "receivables"
    __table_args__ = (
        Index("ix_receivables_status_due_date", "status", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    load_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loads.id"), unique=True, nullable=False
    )
    broker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brokers.id"), nullable=False
    )
    invoice_packet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoice_packets.id"), nullable=True
    )
    invoice_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    amount_due: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    last_reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    load: Mapped["Load"] = relationship("Load", back_populates="receivable")
