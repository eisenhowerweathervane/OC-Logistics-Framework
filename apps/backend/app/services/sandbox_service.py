"""
Sandbox mode service — creates/drops a sandbox database with demo data.

The sandbox database is a full copy of the schema (via Alembic migrations)
populated with rich demo data. Toggling off drops the sandbox database entirely.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import SANDBOX_DB_NAME, _sandbox_database_url, registry


def _admin_dsn() -> str:
    """Connection string to the `postgres` maintenance database (for CREATE/DROP)."""
    base = settings.database_url
    # asyncpg needs postgresql:// not postgresql+asyncpg://
    raw = base.replace("postgresql+asyncpg://", "postgresql://")
    parts = raw.rsplit("/", 1)
    return f"{parts[0]}/postgres"


async def _db_exists() -> bool:
    conn = await asyncpg.connect(_admin_dsn())
    try:
        row = await conn.fetchrow(
            "SELECT 1 FROM pg_database WHERE datname = $1", SANDBOX_DB_NAME
        )
        return row is not None
    finally:
        await conn.close()


async def create_sandbox_db() -> None:
    """Create the sandbox database if it doesn't exist."""
    if await _db_exists():
        return
    conn = await asyncpg.connect(_admin_dsn())
    try:
        await conn.execute(f'CREATE DATABASE "{SANDBOX_DB_NAME}"')
    finally:
        await conn.close()


async def drop_sandbox_db() -> None:
    """Drop the sandbox database."""
    if not await _db_exists():
        return
    conn = await asyncpg.connect(_admin_dsn())
    try:
        # Terminate active connections first
        await conn.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{SANDBOX_DB_NAME}' AND pid <> pg_backend_pid()
        """)
        await conn.execute(f'DROP DATABASE IF EXISTS "{SANDBOX_DB_NAME}"')
    finally:
        await conn.close()


async def create_sandbox_tables() -> None:
    """Create all tables in the sandbox database using SQLAlchemy metadata.

    Uses Base.metadata.create_all instead of Alembic to avoid env.py
    overriding the database URL. For a throwaway sandbox this is fine.
    """
    from app.db.base import Base
    import app.db.models  # noqa: F401 — ensure all models are registered

    sandbox_engine = registry.sandbox_engine
    if not sandbox_engine:
        return

    async with sandbox_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_sandbox_data(
    caller_id: uuid.UUID | None = None,
    caller_email: str | None = None,
    caller_org_id: uuid.UUID | None = None,
) -> None:
    """Populate the sandbox database with rich demo data."""
    from app.db.models.org import Organization, Role, User, UserRole
    from app.db.models.fleet import Broker, Driver, Vehicle, Trailer
    from app.db.models.loads import (
        Load, LoadStop, Assignment, LoadStatusEvent, InvoicePacket, Receivable,
    )
    from app.db.models.compliance import FuelPurchase, MaintenanceItem, AnnualInspection

    # Use sandbox session
    sessionmaker = registry.get_sessionmaker()
    async with sessionmaker() as db:
        # Check if already seeded
        result = await db.execute(text("SELECT count(*) FROM organizations"))
        count = result.scalar()
        if count and count > 0:
            return

        now = datetime.now(timezone.utc)

        # ── Organization ──────────────────────────────────────────────────
        org = Organization(
            legal_name="OC Logistics LLC",
            dba_name="OC Logistics",
            usdot_number="3456789",
            mc_number="MC-987654",
            address_line_1="1234 Trucking Way",
            city="Charlotte",
            state="NC",
            zip="28202",
            country="US",
            phone="+17045551234",
            email="dispatch@oclogistics.com",
        )
        db.add(org)
        await db.flush()

        # ── Roles ─────────────────────────────────────────────────────────
        role_names = ["owner", "dispatcher", "driver", "broker_viewer"]
        roles: dict[str, Role] = {}
        for name in role_names:
            role = Role(name=name, created_at=now)
            db.add(role)
            await db.flush()
            roles[name] = role

        # ── Users (use caller's UUID so the JWT token works across the switch) ─
        owner_kwargs: dict = {
            "organization_id": org.id,
            "email": caller_email or settings.seed_owner_email,
            "password_hash": hash_password(settings.seed_owner_password),
            "status": "active",
        }
        if caller_id:
            owner_kwargs["id"] = caller_id
        owner = User(**owner_kwargs)
        db.add(owner)
        await db.flush()

        owner_role = UserRole(user_id=owner.id, role_id=roles["owner"].id, created_at=now)
        db.add(owner_role)

        # Also create a dispatcher user
        dispatcher = User(
            organization_id=org.id,
            email="dispatcher@oclogistics.com",
            password_hash=hash_password("sandbox123"),
            status="active",
        )
        db.add(dispatcher)
        await db.flush()
        db.add(UserRole(user_id=dispatcher.id, role_id=roles["dispatcher"].id, created_at=now))

        # ── Brokers ───────────────────────────────────────────────────────
        broker_data = [
            {"legal_name": "CH Robinson Worldwide", "dba_name": "CH Robinson", "billing_email": "billing@chrobinson.example.com", "payment_terms_days": 30, "city": "Eden Prairie", "state": "MN"},
            {"legal_name": "TQL Logistics Inc", "dba_name": "TQL", "billing_email": "ap@tql.example.com", "payment_terms_days": 21, "city": "Cincinnati", "state": "OH"},
            {"legal_name": "XPO Logistics LLC", "dba_name": "XPO", "billing_email": "invoices@xpo.example.com", "payment_terms_days": 30, "city": "Greenwich", "state": "CT"},
            {"legal_name": "Echo Global Logistics", "dba_name": "Echo", "billing_email": "payments@echo.example.com", "payment_terms_days": 45, "city": "Chicago", "state": "IL"},
        ]
        brokers: list[Broker] = []
        for bd in broker_data:
            b = Broker(organization_id=org.id, **bd)
            db.add(b)
            await db.flush()
            brokers.append(b)

        # ── Drivers ───────────────────────────────────────────────────────
        driver_data = [
            {"first_name": "Marcus", "last_name": "Johnson", "phone": "+17045559001", "license_state": "NC", "pay_type": "per_mile", "pay_rate": 0.55, "hire_date": date(2023, 3, 15)},
            {"first_name": "David", "last_name": "Rodriguez", "phone": "+17045559002", "license_state": "SC", "pay_type": "per_mile", "pay_rate": 0.52, "hire_date": date(2024, 1, 8)},
            {"first_name": "James", "last_name": "Williams", "phone": "+17045559003", "license_state": "GA", "pay_type": "percentage", "pay_rate": 25.0, "hire_date": date(2024, 6, 20)},
        ]
        drivers: list[Driver] = []
        for dd in driver_data:
            d = Driver(organization_id=org.id, status="active", **dd)
            db.add(d)
            await db.flush()
            drivers.append(d)

        # ── Vehicles ──────────────────────────────────────────────────────
        vehicle_data = [
            {"unit_number": "T-101", "make": "Freightliner", "model": "Cascadia", "year": 2022, "plate_state": "NC", "plate_number": "TRK-4521", "status": "available"},
            {"unit_number": "T-102", "make": "Peterbilt", "model": "579", "year": 2023, "plate_state": "NC", "plate_number": "TRK-4522", "status": "available"},
        ]
        vehicles: list[Vehicle] = []
        for vd in vehicle_data:
            v = Vehicle(organization_id=org.id, **vd)
            db.add(v)
            await db.flush()
            vehicles.append(v)

        # ── Trailer ───────────────────────────────────────────────────────
        trailer = Trailer(
            organization_id=org.id,
            trailer_number="DV-201",
            trailer_type="dry_van",
            status="available",
        )
        db.add(trailer)
        await db.flush()

        # ── Loads (spread across the state machine) ───────────────────────
        loads_spec = [
            # (status, broker_idx, commodity, rate, miles, ref, days_ago, driver_idx, vehicle_idx)
            ("quoted", 0, "Electronics", 2200.00, 680, "CHR-88401", 0, None, None),
            ("booked", 1, "Furniture", 1450.00, 420, "TQL-55102", 1, None, None),
            ("dispatched", 2, "Building Materials", 1875.00, 550, "XPO-77203", 2, 0, 0),
            ("in_transit", 0, "Auto Parts", 1650.00, 485, "CHR-88404", 3, 0, 0),
            ("arrived_delivery", 1, "Paper Products", 1320.00, 380, "TQL-55105", 4, 1, 1),
            ("delivered", 3, "Food Grade - Dry", 2100.00, 620, "ECH-33206", 6, 1, 1),
            ("invoice_ready", 2, "Medical Supplies", 2450.00, 710, "XPO-77207", 10, 0, 0),
            ("invoiced", 0, "Textiles", 1580.00, 460, "CHR-88408", 18, 0, 0),
            ("paid", 1, "Machinery Parts", 1950.00, 570, "TQL-55109", 35, 1, 1),
            ("closed", 3, "Consumer Goods", 1750.00, 510, "ECH-33210", 45, 0, 0),
        ]

        stops_data = [
            # (pickup_city, pickup_state, delivery_city, delivery_state)
            ("Charlotte", "NC", "Atlanta", "GA"),
            ("Greenville", "SC", "Nashville", "TN"),
            ("Raleigh", "NC", "Jacksonville", "FL"),
            ("Charlotte", "NC", "Richmond", "VA"),
            ("Columbia", "SC", "Savannah", "GA"),
            ("Atlanta", "GA", "Charlotte", "NC"),
            ("Charlotte", "NC", "Philadelphia", "PA"),
            ("Greensboro", "NC", "Washington", "DC"),
            ("Charlotte", "NC", "Memphis", "TN"),
            ("Charleston", "SC", "Charlotte", "NC"),
        ]

        created_loads: list[Load] = []
        for i, (status, broker_idx, commodity, rate, miles, ref, days_ago, drv_idx, veh_idx) in enumerate(loads_spec):
            created_at = now - timedelta(days=days_ago, hours=i)
            load = Load(
                organization_id=org.id,
                broker_id=brokers[broker_idx].id,
                reference_number=ref,
                commodity=commodity,
                rate_total=rate,
                rate_type="flat",
                miles_loaded=miles,
                status=status,
            )
            db.add(load)
            await db.flush()
            created_loads.append(load)

            # Stops
            pu_city, pu_state, del_city, del_state = stops_data[i]
            pu_stop = LoadStop(
                load_id=load.id, seq=1, stop_type="pickup",
                facility_name=f"{pu_city} Warehouse",
                city=pu_city, state=pu_state,
                appt_start=created_at + timedelta(hours=4),
                appt_end=created_at + timedelta(hours=6),
            )
            del_stop = LoadStop(
                load_id=load.id, seq=2, stop_type="delivery",
                facility_name=f"{del_city} Distribution Center",
                city=del_city, state=del_state,
                appt_start=created_at + timedelta(hours=12),
                appt_end=created_at + timedelta(hours=14),
            )
            db.add_all([pu_stop, del_stop])

            # Assignment (for dispatched+ loads)
            if drv_idx is not None and veh_idx is not None:
                assignment = Assignment(
                    load_id=load.id,
                    driver_id=drivers[drv_idx].id,
                    vehicle_id=vehicles[veh_idx].id,
                    trailer_id=trailer.id,
                    assigned_at=created_at + timedelta(hours=1),
                    dispatcher_user_id=owner.id,
                    created_at=created_at + timedelta(hours=1),
                )
                db.add(assignment)

            # Status events
            event = LoadStatusEvent(
                load_id=load.id,
                status=status,
                occurred_at=created_at,
                actor_user_id=owner.id,
                location_city=pu_city,
                note=f"Sandbox demo: set to {status}",
                created_at=created_at,
            )
            db.add(event)

        # ── Invoice packets + receivables for invoiced/paid/closed loads ──
        for load in created_loads:
            if load.status in ("invoice_ready", "invoiced", "paid", "closed"):
                packet = InvoicePacket(
                    load_id=load.id,
                    status="ready" if load.status == "invoice_ready" else "sent",
                    generated_at=now - timedelta(days=5),
                )
                db.add(packet)
                await db.flush()

            if load.status in ("invoiced", "paid", "closed"):
                is_paid = load.status in ("paid", "closed")
                days_offset = 30 if load.status == "invoiced" else 0
                recv = Receivable(
                    load_id=load.id,
                    broker_id=load.broker_id,
                    invoice_number=f"INV-2026-{str(load.id)[:4].upper()}",
                    invoice_date=now - timedelta(days=20),
                    due_date=now - timedelta(days=days_offset) if load.status == "invoiced" else now - timedelta(days=10),
                    amount_due=float(load.rate_total),
                    amount_paid=float(load.rate_total) if is_paid else 0,
                    status="paid" if is_paid else "open",
                )
                db.add(recv)

        # Add an overdue receivable for the "delivered" load (simulates aging AR)
        delivered_load = created_loads[5]  # "delivered" status
        overdue_recv = Receivable(
            load_id=delivered_load.id,
            broker_id=delivered_load.broker_id,
            invoice_number=f"INV-2026-{str(delivered_load.id)[:4].upper()}",
            invoice_date=now - timedelta(days=50),
            due_date=now - timedelta(days=20),
            amount_due=float(delivered_load.rate_total),
            amount_paid=0,
            status="overdue",
        )
        db.add(overdue_recv)

        # ── Fuel purchases ────────────────────────────────────────────────
        fuel_entries = [
            {"vehicle_id": vehicles[0].id, "seller_name": "Pilot Travel Center", "jurisdiction": "NC", "gallons": 120.5, "unit_price": 3.45, "total_price": 415.73, "purchased_at_local": now - timedelta(days=2)},
            {"vehicle_id": vehicles[0].id, "seller_name": "Love's Travel Stop", "jurisdiction": "GA", "gallons": 95.2, "unit_price": 3.52, "total_price": 335.10, "purchased_at_local": now - timedelta(days=5)},
            {"vehicle_id": vehicles[1].id, "seller_name": "Flying J", "jurisdiction": "SC", "gallons": 110.8, "unit_price": 3.39, "total_price": 375.61, "purchased_at_local": now - timedelta(days=3)},
            {"vehicle_id": vehicles[0].id, "seller_name": "TA Petro", "jurisdiction": "TN", "gallons": 88.3, "unit_price": 3.48, "total_price": 307.28, "purchased_at_local": now - timedelta(days=8)},
            {"vehicle_id": vehicles[1].id, "seller_name": "Pilot Travel Center", "jurisdiction": "VA", "gallons": 105.0, "unit_price": 3.55, "total_price": 372.75, "purchased_at_local": now - timedelta(days=12)},
        ]
        for fe in fuel_entries:
            fp = FuelPurchase(organization_id=org.id, fuel_type="diesel", **fe)
            db.add(fp)

        # ── Maintenance items ─────────────────────────────────────────────
        maint_items = [
            {"vehicle_id": vehicles[0].id, "category": "Oil Change", "due_date": date.today() + timedelta(days=15), "status": "open"},
            {"vehicle_id": vehicles[0].id, "category": "Tire Rotation", "due_date": date.today() - timedelta(days=5), "status": "overdue"},
            {"vehicle_id": vehicles[1].id, "category": "Brake Inspection", "due_date": date.today() + timedelta(days=30), "status": "open"},
            {"vehicle_id": vehicles[1].id, "category": "DOT Annual Inspection", "due_date": date.today() + timedelta(days=60), "status": "open"},
        ]
        for mi in maint_items:
            m = MaintenanceItem(organization_id=org.id, **mi)
            db.add(m)

        # ── Annual inspections ────────────────────────────────────────────
        for v in vehicles:
            insp = AnnualInspection(
                organization_id=org.id,
                vehicle_id=v.id,
                inspected_at=date.today() - timedelta(days=200),
                inspector_name="SafeFleet Inspections LLC",
                expires_at=date.today() + timedelta(days=165),
            )
            db.add(insp)

        await db.commit()


async def toggle_sandbox(
    activate: bool,
    caller_id: uuid.UUID | None = None,
    caller_email: str | None = None,
    caller_org_id: uuid.UUID | None = None,
) -> dict:
    """Toggle sandbox mode on or off. Returns status dict."""
    if activate:
        # Create DB, init engine, create tables, seed, then mark active
        await create_sandbox_db()
        await registry.activate_sandbox()
        await create_sandbox_tables()
        await seed_sandbox_data(
            caller_id=caller_id,
            caller_email=caller_email,
            caller_org_id=caller_org_id,
        )
        return {"sandbox_mode": True, "message": "Sandbox activated with demo data"}
    else:
        # Deactivate first (releases connections), then drop
        await registry.deactivate_sandbox()
        await drop_sandbox_db()
        return {"sandbox_mode": False, "message": "Sandbox deactivated, data removed"}


def get_sandbox_status() -> dict:
    """Return current sandbox status."""
    return {"sandbox_mode": registry.is_sandbox}
