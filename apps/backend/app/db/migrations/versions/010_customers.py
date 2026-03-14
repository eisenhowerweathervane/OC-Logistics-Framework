"""Add customers table and customer_id FK on loads.

Revision ID: 010
Revises: 009
Create Date: 2026-03-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("company_name", sa.Text, nullable=False),
        sa.Column("contact_name", sa.Text, nullable=True),
        sa.Column("contact_email", sa.Text, nullable=True),
        sa.Column("contact_phone", sa.String(30), nullable=True),
        sa.Column("address_line_1", sa.Text, nullable=True),
        sa.Column("city", sa.Text, nullable=True),
        sa.Column("state", sa.String(10), nullable=True),
        sa.Column("zip", sa.String(20), nullable=True),
        sa.Column("credit_terms_days", sa.Integer, nullable=True),
        sa.Column("preferred_lanes", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_customers_org_id", "customers", ["organization_id"])

    op.add_column("loads", sa.Column("customer_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_loads_customer_id", "loads", "customers", ["customer_id"], ["id"])
    op.create_index("ix_loads_customer_id", "loads", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_loads_customer_id", table_name="loads")
    op.drop_constraint("fk_loads_customer_id", "loads", type_="foreignkey")
    op.drop_column("loads", "customer_id")
    op.drop_index("ix_customers_org_id", table_name="customers")
    op.drop_table("customers")
