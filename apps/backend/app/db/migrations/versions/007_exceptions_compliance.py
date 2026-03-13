"""exceptions, exception_events, exception_resolution, eld_days, fuel_purchases, ifta, irp, ucr, maintenance

Revision ID: 007
Revises: 006
Create Date: 2026-03-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Exceptions
    op.create_table(
        "exceptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("load_id", UUID(as_uuid=True), sa.ForeignKey("loads.id"), nullable=True),
        sa.Column("driver_id", UUID(as_uuid=True), sa.ForeignKey("drivers.id"), nullable=True),
        sa.Column("vehicle_id", UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=True),
        sa.Column("exception_type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "exception_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("exception_id", UUID(as_uuid=True), sa.ForeignKey("exceptions.id"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_driver_id", UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "exception_resolution",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("exception_id", UUID(as_uuid=True), sa.ForeignKey("exceptions.id"), unique=True, nullable=False),
        sa.Column("resolution_type", sa.String(40), nullable=False),
        sa.Column("financial_impact", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ELD
    op.create_table(
        "eld_days",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("driver_id", UUID(as_uuid=True), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("vehicle_id", UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("date_local", sa.Date, nullable=False),
        sa.Column("timezone_offset_minutes", sa.Integer, nullable=True),
        sa.Column("eld_vendor", sa.Text, nullable=True),
        sa.Column("eld_device_id", sa.Text, nullable=True),
        sa.Column("file_storage_key", sa.Text, nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_eld_days_driver_id_date_local", "eld_days", ["driver_id", "date_local"])

    # Fuel
    op.create_table(
        "fuel_purchases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("vehicle_id", UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("purchased_at_local", sa.DateTime(timezone=True), nullable=False),
        sa.Column("seller_name", sa.Text, nullable=False),
        sa.Column("seller_address", sa.Text, nullable=True),
        sa.Column("jurisdiction", sa.String(10), nullable=True),
        sa.Column("fuel_type", sa.String(20), nullable=True),
        sa.Column("gallons", sa.Numeric(10, 3), nullable=True),
        sa.Column("unit_price", sa.Numeric(10, 4), nullable=True),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("purchaser_name", sa.Text, nullable=True),
        sa.Column("receipt_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_fuel_purchases_vehicle_id_purchased_at_local",
        "fuel_purchases",
        ["vehicle_id", "purchased_at_local"],
    )

    # IFTA
    op.create_table(
        "ifta_returns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("quarter", sa.Integer, nullable=False),
        sa.Column("filed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("pdf_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "ifta_distance_by_jurisdiction",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("ifta_return_id", UUID(as_uuid=True), sa.ForeignKey("ifta_returns.id"), nullable=False),
        sa.Column("jurisdiction", sa.String(10), nullable=False),
        sa.Column("miles", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "ifta_fuel_by_jurisdiction",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("ifta_return_id", UUID(as_uuid=True), sa.ForeignKey("ifta_returns.id"), nullable=False),
        sa.Column("jurisdiction", sa.String(10), nullable=False),
        sa.Column("gallons", sa.Numeric(12, 3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # IRP
    op.create_table(
        "irp_years",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("registration_year", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("cab_card_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "irp_distance_by_jurisdiction",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("irp_year_id", UUID(as_uuid=True), sa.ForeignKey("irp_years.id"), nullable=False),
        sa.Column("jurisdiction", sa.String(10), nullable=False),
        sa.Column("miles", sa.Numeric(12, 2), nullable=False),
        sa.Column("source", sa.String(20), nullable=True),
        sa.Column("supporting_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # UCR
    op.create_table(
        "ucr_registrations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("usdot_number", sa.String(20), nullable=True),
        sa.Column("bracket", sa.String(20), nullable=True),
        sa.Column("receipt_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Maintenance
    op.create_table(
        "maintenance_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("vehicle_id", UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("due_odometer", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_maintenance_items_vehicle_id_due_date", "maintenance_items", ["vehicle_id", "due_date"])

    op.create_table(
        "maintenance_work_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("vehicle_id", UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("odometer", sa.Numeric(12, 2), nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("vendor", sa.Text, nullable=True),
        sa.Column("total_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("invoice_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "annual_inspections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("vehicle_id", UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("inspected_at", sa.Date, nullable=False),
        sa.Column("inspector_name", sa.Text, nullable=True),
        sa.Column("report_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("expires_at", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_annual_inspections_vehicle_id_expires_at",
        "annual_inspections",
        ["vehicle_id", "expires_at"],
    )

    op.create_table(
        "roadside_inspections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("vehicle_id", UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("inspected_at", sa.Date, nullable=False),
        sa.Column("report_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("corrections_certified_at", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("roadside_inspections")
    op.drop_index("ix_annual_inspections_vehicle_id_expires_at")
    op.drop_table("annual_inspections")
    op.drop_table("maintenance_work_orders")
    op.drop_index("ix_maintenance_items_vehicle_id_due_date")
    op.drop_table("maintenance_items")
    op.drop_table("ucr_registrations")
    op.drop_table("irp_distance_by_jurisdiction")
    op.drop_table("irp_years")
    op.drop_table("ifta_fuel_by_jurisdiction")
    op.drop_table("ifta_distance_by_jurisdiction")
    op.drop_table("ifta_returns")
    op.drop_index("ix_fuel_purchases_vehicle_id_purchased_at_local")
    op.drop_table("fuel_purchases")
    op.drop_index("ix_eld_days_driver_id_date_local")
    op.drop_table("eld_days")
    op.drop_table("exception_resolution")
    op.drop_table("exception_events")
    op.drop_table("exceptions")
