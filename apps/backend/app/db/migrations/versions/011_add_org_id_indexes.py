"""add org_id indexes

Revision ID: 011
Revises: 010
Create Date: 2026-03-14

"""

from typing import Sequence, Union

from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # organization_id indexes for multi-tenant query performance
    op.create_index("ix_drivers_organization_id", "drivers", ["organization_id"])
    op.create_index("ix_vehicles_organization_id", "vehicles", ["organization_id"])
    op.create_index("ix_loads_organization_id", "loads", ["organization_id"])
    op.create_index("ix_brokers_organization_id", "brokers", ["organization_id"])
    op.create_index("ix_trailers_organization_id", "trailers", ["organization_id"])
    op.create_index("ix_settlements_organization_id", "settlements", ["organization_id"])
    op.create_index("ix_customers_organization_id", "customers", ["organization_id"])

    # frequently-joined columns on assignments
    op.create_index("ix_assignments_driver_id", "assignments", ["driver_id"])
    op.create_index("ix_assignments_vehicle_id", "assignments", ["vehicle_id"])


def downgrade() -> None:
    op.drop_index("ix_assignments_vehicle_id")
    op.drop_index("ix_assignments_driver_id")
    op.drop_index("ix_customers_organization_id")
    op.drop_index("ix_settlements_organization_id")
    op.drop_index("ix_trailers_organization_id")
    op.drop_index("ix_brokers_organization_id")
    op.drop_index("ix_loads_organization_id")
    op.drop_index("ix_vehicles_organization_id")
    op.drop_index("ix_drivers_organization_id")
