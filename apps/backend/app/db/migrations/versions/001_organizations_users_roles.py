"""organizations, users, roles, user_roles

Revision ID: 001
Revises:
Create Date: 2026-03-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("legal_name", sa.Text, nullable=False),
        sa.Column("dba_name", sa.Text, nullable=True),
        sa.Column("ein_encrypted", sa.Text, nullable=True),
        sa.Column("usdot_number", sa.String(20), nullable=True),
        sa.Column("mc_number", sa.String(20), nullable=True),
        sa.Column("address_line_1", sa.Text, nullable=True),
        sa.Column("address_line_2", sa.Text, nullable=True),
        sa.Column("city", sa.Text, nullable=True),
        sa.Column("state", sa.String(10), nullable=True),
        sa.Column("zip", sa.String(20), nullable=True),
        sa.Column("country", sa.String(10), nullable=False, server_default="US"),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_organizations_usdot_number", "organizations", ["usdot_number"])
    op.create_index("ix_organizations_mc_number", "organizations", ["mc_number"])

    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.Text, unique=True, nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("password_hash", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "role_id"),
    )

    # Seed roles
    op.execute("""
        INSERT INTO roles (id, name, created_at) VALUES
        (uuid_generate_v4(), 'owner', now()),
        (uuid_generate_v4(), 'dispatcher', now()),
        (uuid_generate_v4(), 'driver', now()),
        (uuid_generate_v4(), 'broker_viewer', now())
    """)


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("organizations")
