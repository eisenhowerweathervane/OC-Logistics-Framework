import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Broker(Base, TimestampMixin):
    __tablename__ = "brokers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    legal_name: Mapped[str] = mapped_column(Text, nullable=False)
    dba_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    billing_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_terms_days: Mapped[int | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Driver(Base, TimestampMixin):
    __tablename__ = "drivers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    license_number_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    pay_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pay_rate: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    unit_number: Mapped[str] = mapped_column(Text, nullable=False)
    vin_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    make: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(nullable=True)
    plate_state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    plate_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="available")
    in_service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    out_of_service_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class Trailer(Base, TimestampMixin):
    __tablename__ = "trailers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    trailer_number: Mapped[str] = mapped_column(Text, nullable=False)
    vin_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    trailer_type: Mapped[str] = mapped_column(String(30), nullable=False, default="dry_van")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="available")
