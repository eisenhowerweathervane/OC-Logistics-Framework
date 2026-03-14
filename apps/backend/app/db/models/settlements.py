import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

SETTLEMENT_STATUSES = ["draft", "approved", "paid"]


class Settlement(Base, TimestampMixin):
    __tablename__ = "settlements"
    __table_args__ = (
        Index("ix_settlements_driver_id", "driver_id"),
        Index("ix_settlements_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    total_miles: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_revenue: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_pay: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_deductions: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_pay: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    line_items: Mapped[list["SettlementLineItem"]] = relationship(
        "SettlementLineItem", back_populates="settlement", order_by="SettlementLineItem.created_at"
    )


LINE_ITEM_TYPES = ["load_pay", "fuel_advance", "deduction", "bonus", "reimbursement"]


class SettlementLineItem(Base, TimestampMixin):
    __tablename__ = "settlement_line_items"
    __table_args__ = (Index("ix_settlement_line_items_settlement_id", "settlement_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    settlement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("settlements.id"), nullable=False
    )
    load_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("loads.id"), nullable=True)
    line_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    miles: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    revenue: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    settlement: Mapped["Settlement"] = relationship("Settlement", back_populates="line_items")
