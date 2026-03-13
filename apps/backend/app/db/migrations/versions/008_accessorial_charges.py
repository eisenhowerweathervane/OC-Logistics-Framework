"""accessorial_charges

Revision ID: 008
Revises: 007
Create Date: 2026-03-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accessorial_charges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("load_id", UUID(as_uuid=True), sa.ForeignKey("loads.id"), nullable=False),
        sa.Column("charge_type", sa.String(30), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_accessorial_charges_load_id", "accessorial_charges", ["load_id"])


def downgrade() -> None:
    op.drop_index("ix_accessorial_charges_load_id")
    op.drop_table("accessorial_charges")
