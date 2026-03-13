import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class EldDay(Base):
    __tablename__ = "eld_days"
    __table_args__ = (
        Index("ix_eld_days_driver_id_date_local", "driver_id", "date_local"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False
    )
    date_local: Mapped[date] = mapped_column(Date, nullable=False)
    timezone_offset_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eld_vendor: Mapped[str | None] = mapped_column(Text, nullable=True)
    eld_device_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FuelPurchase(Base, TimestampMixin):
    __tablename__ = "fuel_purchases"
    __table_args__ = (
        Index("ix_fuel_purchases_vehicle_id_purchased_at_local", "vehicle_id", "purchased_at_local"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False
    )
    purchased_at_local: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    seller_name: Mapped[str] = mapped_column(Text, nullable=False)
    seller_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fuel_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gallons: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    total_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    purchaser_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )


class IftaReturn(Base, TimestampMixin):
    __tablename__ = "ifta_returns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    filed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    pdf_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )

    distance_by_jurisdiction: Mapped[list["IftaDistanceByJurisdiction"]] = relationship(
        "IftaDistanceByJurisdiction", back_populates="ifta_return"
    )
    fuel_by_jurisdiction: Mapped[list["IftaFuelByJurisdiction"]] = relationship(
        "IftaFuelByJurisdiction", back_populates="ifta_return"
    )


class IftaDistanceByJurisdiction(Base):
    __tablename__ = "ifta_distance_by_jurisdiction"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ifta_return_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ifta_returns.id"), nullable=False
    )
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)
    miles: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    ifta_return: Mapped["IftaReturn"] = relationship(
        "IftaReturn", back_populates="distance_by_jurisdiction"
    )


class IftaFuelByJurisdiction(Base):
    __tablename__ = "ifta_fuel_by_jurisdiction"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ifta_return_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ifta_returns.id"), nullable=False
    )
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)
    gallons: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    ifta_return: Mapped["IftaReturn"] = relationship(
        "IftaReturn", back_populates="fuel_by_jurisdiction"
    )


class IrpYear(Base, TimestampMixin):
    __tablename__ = "irp_years"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    registration_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    cab_card_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )


class IrpDistanceByJurisdiction(Base):
    __tablename__ = "irp_distance_by_jurisdiction"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    irp_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("irp_years.id"), nullable=False
    )
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)
    miles: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    supporting_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UcrRegistration(Base, TimestampMixin):
    __tablename__ = "ucr_registrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    usdot_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bracket: Mapped[str | None] = mapped_column(String(20), nullable=True)
    receipt_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )


class MaintenanceItem(Base, TimestampMixin):
    __tablename__ = "maintenance_items"
    __table_args__ = (
        Index("ix_maintenance_items_vehicle_id_due_date", "vehicle_id", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_odometer: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class MaintenanceWorkOrder(Base, TimestampMixin):
    __tablename__ = "maintenance_work_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    odometer: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    vendor: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    invoice_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")


class AnnualInspection(Base, TimestampMixin):
    __tablename__ = "annual_inspections"
    __table_args__ = (
        Index("ix_annual_inspections_vehicle_id_expires_at", "vehicle_id", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False
    )
    inspected_at: Mapped[date] = mapped_column(Date, nullable=False)
    inspector_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)


class RoadsideInspection(Base, TimestampMixin):
    __tablename__ = "roadside_inspections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False
    )
    inspected_at: Mapped[date] = mapped_column(Date, nullable=False)
    report_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    corrections_certified_at: Mapped[date | None] = mapped_column(Date, nullable=True)
