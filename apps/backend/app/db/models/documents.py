import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class RetentionPolicy(Base, TimestampMixin):
    __tablename__ = "retention_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    legal_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    deletion_action: Mapped[str] = mapped_column(String(20), nullable=False, default="archive")
    hold_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_doc_type", "doc_type"),
        Index("ix_documents_doc_date", "doc_date"),
        Index("ix_documents_storage_key", "storage_key", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    upload_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    uploaded_by_driver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=True
    )
    doc_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    doc_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    nearest_city: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    vendor_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retention_policies.id"), nullable=True
    )

    links: Mapped[list["DocumentLink"]] = relationship("DocumentLink", back_populates="document")


class DocumentLink(Base):
    __tablename__ = "document_links"
    __table_args__ = (Index("ix_document_links_entity_type_entity_id", "entity_type", "entity_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    document: Mapped["Document"] = relationship("Document", back_populates="links")
