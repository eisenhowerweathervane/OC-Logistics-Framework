"""retention_policies, documents, document_links

Revision ID: 004
Revises: 003
Create Date: 2026-03-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "retention_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("policy_name", sa.Text, unique=True, nullable=False),
        sa.Column("retention_days", sa.Integer, nullable=False),
        sa.Column("legal_basis", sa.Text, nullable=True),
        sa.Column("deletion_action", sa.String(20), nullable=False, server_default="archive"),
        sa.Column("hold_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Seed default retention policies
    op.execute("""
        INSERT INTO retention_policies
        (id, policy_name, retention_days, legal_basis, deletion_action, hold_enabled) VALUES
        (uuid_generate_v4(), 'eld_supporting_docs', 210, 'FMCSA 49 CFR 395.8', 'archive', false),
        (uuid_generate_v4(), 'ifta_docs', 1460, 'IFTA 4-year requirement', 'archive', false),
        (uuid_generate_v4(), 'irp_docs', 1095, 'IRP 3-year requirement', 'archive', false),
        (uuid_generate_v4(), 'annual_inspection_reports', 425, 'FMCSA 49 CFR 396.21', 'archive', false),
        (uuid_generate_v4(), 'roadside_inspection_reports', 365, 'FMCSA 49 CFR 396.11', 'archive', false),
        (uuid_generate_v4(), 'maintenance_records', 365, 'FMCSA 49 CFR 396.3', 'archive', false),
        (uuid_generate_v4(), 'dq_files', 365, 'FMCSA 49 CFR 391 - review on termination', 'manual_review', true)
    """)

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("storage_key", sa.Text, unique=True, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("upload_source", sa.String(30), nullable=True),
        sa.Column("uploaded_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("uploaded_by_driver_id", UUID(as_uuid=True), sa.ForeignKey("drivers.id"), nullable=True),
        sa.Column("doc_date", sa.Date, nullable=True),
        sa.Column("doc_time", sa.Time, nullable=True),
        sa.Column("nearest_city", sa.Text, nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("vendor_name", sa.Text, nullable=True),
        sa.Column("retention_policy_id", UUID(as_uuid=True), sa.ForeignKey("retention_policies.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_documents_doc_type", "documents", ["doc_type"])
    op.create_index("ix_documents_doc_date", "documents", ["doc_date"])
    op.create_index("ix_documents_storage_key", "documents", ["storage_key"], unique=True)

    op.create_table(
        "document_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_document_links_entity_type_entity_id",
        "document_links",
        ["entity_type", "entity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_links_entity_type_entity_id")
    op.drop_table("document_links")
    op.drop_index("ix_documents_storage_key")
    op.drop_index("ix_documents_doc_date")
    op.drop_index("ix_documents_doc_type")
    op.drop_table("documents")
    op.drop_table("retention_policies")
