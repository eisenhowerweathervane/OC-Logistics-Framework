"""settlements

Revision ID: 009
Revises: 008
Create Date: 2026-03-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "settlements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("driver_id", UUID(as_uuid=True), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("total_miles", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_revenue", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_pay", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_deductions", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("net_pay", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_settlements_driver_id", "settlements", ["driver_id"])
    op.create_index("ix_settlements_status", "settlements", ["status"])

    op.create_table(
        "settlement_line_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("settlement_id", UUID(as_uuid=True), sa.ForeignKey("settlements.id"), nullable=False),
        sa.Column("load_id", UUID(as_uuid=True), sa.ForeignKey("loads.id"), nullable=True),
        sa.Column("line_type", sa.String(30), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("miles", sa.Numeric(10, 2), nullable=True),
        sa.Column("revenue", sa.Numeric(12, 2), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_settlement_line_items_settlement_id", "settlement_line_items", ["settlement_id"])


def downgrade() -> None:
    op.drop_index("ix_settlement_line_items_settlement_id")
    op.drop_table("settlement_line_items")
    op.drop_index("ix_settlements_status")
    op.drop_index("ix_settlements_driver_id")
    op.drop_table("settlements")
