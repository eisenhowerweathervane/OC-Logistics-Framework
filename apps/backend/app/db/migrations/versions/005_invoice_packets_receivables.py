"""invoice_packets, receivables

Revision ID: 005
Revises: 004
Create Date: 2026-03-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoice_packets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("load_id", UUID(as_uuid=True), sa.ForeignKey("loads.id"), unique=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="not_ready"),
        sa.Column("rate_con_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("pod_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("packet_storage_key", sa.Text, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "receivables",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("load_id", UUID(as_uuid=True), sa.ForeignKey("loads.id"), unique=True, nullable=False),
        sa.Column("broker_id", UUID(as_uuid=True), sa.ForeignKey("brokers.id"), nullable=False),
        sa.Column("invoice_packet_id", UUID(as_uuid=True), sa.ForeignKey("invoice_packets.id"), nullable=True),
        sa.Column("invoice_number", sa.Text, nullable=True),
        sa.Column("invoice_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount_due", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("last_reminder_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_receivables_status_due_date", "receivables", ["status", "due_date"])


def downgrade() -> None:
    op.drop_index("ix_receivables_status_due_date")
    op.drop_table("receivables")
    op.drop_table("invoice_packets")
