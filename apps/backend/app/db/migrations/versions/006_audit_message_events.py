"""audit_events, message_events

Revision ID: 006
Revises: 005
Create Date: 2026-03-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_driver_id", UUID(as_uuid=True), nullable=True),
        sa.Column("source_channel", sa.String(30), nullable=True),
        sa.Column("source_message_id", sa.Text, nullable=True),
        sa.Column("payload_json", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "message_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("channel_type", sa.String(20), nullable=False),
        sa.Column("external_message_id", sa.Text, nullable=True),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("linked_entity_type", sa.String(50), nullable=True),
        sa.Column("linked_entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("requires_response", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("delivery_status", sa.String(20), nullable=True),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("normalized_intent", sa.String(60), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_message_events_channel_type_external_message_id",
        "message_events",
        ["channel_type", "external_message_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_message_events_channel_type_external_message_id")
    op.drop_table("message_events")
    op.drop_table("audit_events")
