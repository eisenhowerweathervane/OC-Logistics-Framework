"""loads, load_stops, assignments, load_status_events

Revision ID: 003
Revises: 002
Create Date: 2026-03-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "loads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("broker_id", UUID(as_uuid=True), sa.ForeignKey("brokers.id"), nullable=True),
        sa.Column("shipping_document_number", sa.Text, nullable=True),
        sa.Column("reference_number", sa.Text, nullable=True),
        sa.Column("commodity", sa.Text, nullable=True),
        sa.Column("weight_lbs", sa.Numeric(12, 2), nullable=True),
        sa.Column("pieces", sa.Integer, nullable=True),
        sa.Column("rate_total", sa.Numeric(12, 2), nullable=True),
        sa.Column("rate_type", sa.String(20), nullable=True),
        sa.Column("miles_loaded", sa.Numeric(10, 2), nullable=True),
        sa.Column("miles_deadhead_est", sa.Numeric(10, 2), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="quoted"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_loads_status", "loads", ["status"])
    op.create_index("ix_loads_broker_id", "loads", ["broker_id"])
    op.create_index("ix_loads_shipping_document_number", "loads", ["shipping_document_number"])

    op.create_table(
        "load_stops",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("load_id", UUID(as_uuid=True), sa.ForeignKey("loads.id"), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("stop_type", sa.String(20), nullable=False, server_default="pickup"),
        sa.Column("facility_name", sa.Text, nullable=True),
        sa.Column("address_line_1", sa.Text, nullable=True),
        sa.Column("city", sa.Text, nullable=True),
        sa.Column("state", sa.String(10), nullable=True),
        sa.Column("zip", sa.String(20), nullable=True),
        sa.Column("appt_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("appt_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("departed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contact_name", sa.Text, nullable=True),
        sa.Column("contact_phone", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("load_id", UUID(as_uuid=True), sa.ForeignKey("loads.id"), nullable=False),
        sa.Column("driver_id", UUID(as_uuid=True), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("vehicle_id", UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("trailer_id", UUID(as_uuid=True), sa.ForeignKey("trailers.id"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unassigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatcher_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "load_status_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("load_id", UUID(as_uuid=True), sa.ForeignKey("loads.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_driver_id", UUID(as_uuid=True), sa.ForeignKey("drivers.id"), nullable=True),
        sa.Column("location_city", sa.Text, nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("source_channel", sa.String(30), nullable=True),
        sa.Column("source_message_id", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_load_status_events_load_id_occurred_at",
        "load_status_events",
        ["load_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_load_status_events_load_id_occurred_at")
    op.drop_table("load_status_events")
    op.drop_table("assignments")
    op.drop_table("load_stops")
    op.drop_index("ix_loads_shipping_document_number")
    op.drop_index("ix_loads_broker_id")
    op.drop_index("ix_loads_status")
    op.drop_table("loads")
