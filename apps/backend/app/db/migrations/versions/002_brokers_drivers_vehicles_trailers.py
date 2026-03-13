"""brokers, drivers, vehicles, trailers

Revision ID: 002
Revises: 001
Create Date: 2026-03-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brokers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("legal_name", sa.Text, nullable=False),
        sa.Column("dba_name", sa.Text, nullable=True),
        sa.Column("address_line_1", sa.Text, nullable=True),
        sa.Column("city", sa.Text, nullable=True),
        sa.Column("state", sa.String(10), nullable=True),
        sa.Column("zip", sa.String(20), nullable=True),
        sa.Column("billing_email", sa.Text, nullable=True),
        sa.Column("payment_terms_days", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "drivers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("first_name", sa.Text, nullable=False),
        sa.Column("last_name", sa.Text, nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("license_number_encrypted", sa.Text, nullable=True),
        sa.Column("license_state", sa.String(10), nullable=True),
        sa.Column("hire_date", sa.Date, nullable=True),
        sa.Column("termination_date", sa.Date, nullable=True),
        sa.Column("pay_type", sa.String(20), nullable=True),
        sa.Column("pay_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "vehicles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("unit_number", sa.Text, nullable=False),
        sa.Column("vin_encrypted", sa.Text, nullable=True),
        sa.Column("make", sa.Text, nullable=True),
        sa.Column("model", sa.Text, nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("plate_state", sa.String(10), nullable=True),
        sa.Column("plate_number", sa.Text, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="available"),
        sa.Column("in_service_date", sa.Date, nullable=True),
        sa.Column("out_of_service_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "trailers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("trailer_number", sa.Text, nullable=False),
        sa.Column("vin_encrypted", sa.Text, nullable=True),
        sa.Column("trailer_type", sa.String(30), nullable=False, server_default="dry_van"),
        sa.Column("status", sa.String(30), nullable=False, server_default="available"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("trailers")
    op.drop_table("vehicles")
    op.drop_table("drivers")
    op.drop_table("brokers")
