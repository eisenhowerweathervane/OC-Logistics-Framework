# Profitability Engine Modular Rebuild — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the monolithic profitability engine into a modular, composable system with smarter scoring, dynamic costs, scenario-based chain optimization, and multiple data ingestion methods.

**Architecture:** New module directories (`ingestion/`, `costs/`, `scoring/`, `optimizer/`, `analytics/`) alongside existing files. Each module has focused responsibility and clear interfaces. Database migrated with new tables for config, history, and feedback. Existing email parser and API endpoints preserved.

**Tech Stack:** Python 3, FastAPI, SQLite3, Pydantic, Google Maps API, Tesseract OCR (later), EIA fuel API

**Spec:** `docs/superpowers/specs/2026-03-16-profitability-engine-rebuild-design.md`

---

## Chunk 1: Foundation — Database Migration, Shared Models, Cost Config

This chunk establishes the data layer and shared types that every other module depends on.

### File Structure (Chunk 1)

- Create: `models.py` — shared Pydantic models (`ParsedLoad`, `ParsedField`, `CostConfig`, `ScorerConfig`)
- Create: `database.py` — centralized DB init, migration, seed data, connection manager (accepts `db_path` param, defaults to `loads.db`, reads `DATABASE_PATH` env var for test overrides)
- Create: `costs/__init__.py`
- Create: `costs/cost_model.py` — base cost calculation with monthly-to-per-mile conversion + driver pay modes
- Create: `tests/__init__.py`
- Create: `tests/conftest.py` — shared test fixtures (test DB creation/teardown, test client factory)
- Create: `tests/test_models.py`
- Create: `tests/test_database.py`
- Create: `tests/test_cost_model.py`
- Modify: `app.py` — swap inline DB init for `database.py`, add cost config endpoints

---

### Task 1: Shared Models (`models.py`)

**Files:**
- Create: `models.py`
- Create: `tests/__init__.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for ParsedLoad validation**

```python
# tests/test_models.py
import pytest
from models import ParsedLoad, CostConfig, ScorerConfig


class TestParsedLoad:
    def test_valid_minimal_load(self):
        """Required fields only should produce a valid ParsedLoad."""
        load = ParsedLoad(
            origin_city="Columbus",
            origin_state="OH",
            destination_city="Pittsburgh",
            destination_state="PA",
            mileage=185,
            source="paste",
        )
        assert load.origin_city == "Columbus"
        assert load.mileage == 185
        assert load.source == "paste"
        assert load.deadhead_miles == 0
        assert load.equipment_type == "Van"

    def test_valid_full_load(self):
        """All fields populated should work."""
        load = ParsedLoad(
            origin_city="Columbus",
            origin_state="OH",
            destination_city="Pittsburgh",
            destination_state="PA",
            mileage=185,
            source="email",
            rate_total=600.00,
            rate_per_mile=3.24,
            deadhead_miles=127,
            weight=42000,
            equipment_type="Van",
            commodity="Auto Parts",
            pickup_date="2026-03-20",
            pickup_time_window="08:00-16:00",
            delivery_date="2026-03-21",
            delivery_time_window="06:00-12:00",
            broker_name="TQL",
            broker_mc_number="MC-123456",
            contact_phone="555-0100",
            contact_email="dispatch@tql.com",
            load_number="TQL-98765",
            notes="Dock appointment required",
        )
        assert load.rate_total == 600.00
        assert load.broker_name == "TQL"

    def test_missing_required_field_raises(self):
        """Missing origin_city should raise ValidationError."""
        with pytest.raises(Exception):
            ParsedLoad(
                origin_state="OH",
                destination_city="Pittsburgh",
                destination_state="PA",
                mileage=185,
                source="paste",
            )

    def test_invalid_source_raises(self):
        """Source must be one of: email, paste, ocr, manual."""
        with pytest.raises(Exception):
            ParsedLoad(
                origin_city="Columbus",
                origin_state="OH",
                destination_city="Pittsburgh",
                destination_state="PA",
                mileage=185,
                source="invalid_source",
            )

    def test_rate_per_mile_auto_calculated(self):
        """If rate_total and mileage present but rate_per_mile not, it should auto-calculate."""
        load = ParsedLoad(
            origin_city="Columbus",
            origin_state="OH",
            destination_city="Pittsburgh",
            destination_state="PA",
            mileage=200,
            rate_total=600.00,
            source="paste",
        )
        assert load.rate_per_mile == pytest.approx(3.00)

    def test_to_dict_returns_plain_dict(self):
        """to_dict() should return a plain dict compatible with existing score_load()."""
        load = ParsedLoad(
            origin_city="Columbus",
            origin_state="OH",
            destination_city="Pittsburgh",
            destination_state="PA",
            mileage=185,
            rate_total=600.00,
            source="paste",
        )
        d = load.to_dict()
        assert isinstance(d, dict)
        assert d["origin_city"] == "Columbus"
        assert d["rate_total"] == 600.00


class TestCostConfig:
    def test_defaults(self):
        """CostConfig with no args should have sensible defaults."""
        config = CostConfig()
        assert config.truck_lease_monthly == 4000.00
        assert config.driver_pay_mode == "per_mile_only"
        assert config.factoring_fee_pct == 3.0
        assert config.fuel_mpg == 6.5

    def test_per_mile_conversion(self):
        """Monthly costs should convert to per-mile correctly."""
        config = CostConfig(
            truck_lease_monthly=4000.00,
            expected_monthly_miles=8000,
        )
        assert config.truck_lease_per_mile == pytest.approx(0.50)

    def test_driver_pay_base_plus_mile(self):
        """Base + per-mile mode should combine both components."""
        config = CostConfig(
            driver_pay_mode="base_plus_mile",
            driver_base_weekly=800.00,
            driver_per_mile=0.15,
            expected_monthly_miles=8000,
        )
        # Weekly base → monthly → per mile: (800 * 52/12) / 8000 ≈ 0.433
        # Plus per_mile: 0.15
        # Total ≈ 0.583
        assert config.driver_pay_per_mile == pytest.approx(
            (800.0 * 52 / 12) / 8000 + 0.15, rel=0.01
        )

    def test_driver_pay_per_mile_only(self):
        """Per-mile only mode uses driver_per_mile directly."""
        config = CostConfig(
            driver_pay_mode="per_mile_only",
            driver_per_mile=0.55,
        )
        assert config.driver_pay_per_mile == pytest.approx(0.55)

    def test_driver_pay_base_only(self):
        """Base-only mode converts weekly salary to per-mile."""
        config = CostConfig(
            driver_pay_mode="base_only",
            driver_base_weekly=1200.00,
            expected_monthly_miles=8000,
        )
        expected = (1200.0 * 52 / 12) / 8000
        assert config.driver_pay_per_mile == pytest.approx(expected, rel=0.01)

    def test_total_base_cpm(self):
        """total_base_cpm should sum all per-mile costs."""
        config = CostConfig(
            truck_lease_monthly=4000.00,
            insurance_monthly=1800.00,
            overhead_monthly=500.00,
            maint_reserve_monthly=0.00,
            expected_monthly_miles=8000,
            driver_pay_mode="per_mile_only",
            driver_per_mile=0.55,
            fuel_mpg=6.5,
            default_fuel_price=3.85,
        )
        fuel_cpm = 3.85 / 6.5
        lease_cpm = 4000 / 8000
        insurance_cpm = 1800 / 8000
        overhead_cpm = 500 / 8000
        maint_cpm = 0 / 8000
        expected_total = fuel_cpm + 0.55 + lease_cpm + insurance_cpm + overhead_cpm + maint_cpm
        assert config.total_base_cpm(fuel_price_override=None) == pytest.approx(
            expected_total, rel=0.01
        )


class TestScorerConfig:
    def test_defaults_sum_to_one(self):
        config = ScorerConfig()
        total = (
            config.financial_weight
            + config.lane_weight
            + config.broker_weight
            + config.strategic_weight
        )
        assert total == pytest.approx(1.0)

    def test_custom_weights_validated(self):
        """Weights must sum to 1.0."""
        with pytest.raises(Exception):
            ScorerConfig(
                financial_weight=0.50,
                lane_weight=0.50,
                broker_weight=0.50,
                strategic_weight=0.50,
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: Implement models.py**

```python
# models.py
"""Shared data models for the profitability engine."""

from typing import Optional, Literal
from pydantic import BaseModel, field_validator, model_validator


class ParsedLoad(BaseModel):
    """Unified load structure produced by all parsers."""

    # Required
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    mileage: int
    source: Literal["email", "paste", "ocr", "manual"]

    # Optional
    rate_total: Optional[float] = None
    rate_per_mile: Optional[float] = None
    deadhead_miles: int = 0
    weight: Optional[int] = None
    equipment_type: str = "Van"
    commodity: str = ""
    pickup_date: str = ""
    pickup_time_window: str = ""
    delivery_date: str = ""
    delivery_time_window: str = ""
    broker_name: str = ""
    broker_mc_number: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    load_number: str = ""
    notes: str = ""

    @model_validator(mode="after")
    def auto_calculate_rate_per_mile(self):
        if self.rate_total and self.mileage and not self.rate_per_mile:
            self.rate_per_mile = round(self.rate_total / self.mileage, 2)
        return self

    def to_dict(self) -> dict:
        """Convert to plain dict compatible with existing score_load()."""
        return self.model_dump()


class ParsedField(BaseModel):
    """Wrapper for OCR-extracted fields with confidence metadata."""

    value: Optional[str | int | float] = None
    confidence: float = 1.0
    source: Literal["email", "paste", "ocr", "manual"] = "manual"


class CostConfig(BaseModel):
    """Cost configuration with monthly-to-per-mile conversion."""

    # Monthly fixed costs
    truck_lease_monthly: float = 4000.00
    insurance_monthly: float = 1800.00
    overhead_monthly: float = 500.00
    maint_reserve_monthly: float = 0.00
    expected_monthly_miles: int = 8000

    # Driver pay
    driver_pay_mode: Literal["base_plus_mile", "per_mile_only", "base_only"] = "per_mile_only"
    driver_base_weekly: float = 0.00
    driver_per_mile: float = 0.55

    # Other
    factoring_fee_pct: float = 3.0
    fuel_mpg: float = 6.5
    default_fuel_price: float = 3.85

    @property
    def truck_lease_per_mile(self) -> float:
        return self.truck_lease_monthly / self.expected_monthly_miles

    @property
    def insurance_per_mile(self) -> float:
        return self.insurance_monthly / self.expected_monthly_miles

    @property
    def overhead_per_mile(self) -> float:
        return self.overhead_monthly / self.expected_monthly_miles

    @property
    def maint_reserve_per_mile(self) -> float:
        return self.maint_reserve_monthly / self.expected_monthly_miles

    @property
    def driver_pay_per_mile(self) -> float:
        if self.driver_pay_mode == "per_mile_only":
            return self.driver_per_mile
        elif self.driver_pay_mode == "base_only":
            monthly_base = self.driver_base_weekly * 52 / 12
            return monthly_base / self.expected_monthly_miles
        else:  # base_plus_mile
            monthly_base = self.driver_base_weekly * 52 / 12
            return (monthly_base / self.expected_monthly_miles) + self.driver_per_mile

    def total_base_cpm(self, fuel_price_override: Optional[float] = None) -> float:
        """Calculate total base cost per mile."""
        fuel_price = fuel_price_override or self.default_fuel_price
        fuel_cpm = fuel_price / self.fuel_mpg
        return (
            fuel_cpm
            + self.driver_pay_per_mile
            + self.truck_lease_per_mile
            + self.insurance_per_mile
            + self.overhead_per_mile
            + self.maint_reserve_per_mile
        )


class ScorerConfig(BaseModel):
    """Composite scorer weight configuration."""

    financial_weight: float = 0.50
    lane_weight: float = 0.15
    broker_weight: float = 0.15
    strategic_weight: float = 0.20

    @model_validator(mode="after")
    def weights_must_sum_to_one(self):
        total = (
            self.financial_weight
            + self.lane_weight
            + self.broker_weight
            + self.strategic_weight
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Scorer weights must sum to 1.0, got {total}")
        return self
```

- [ ] **Step 4: Create empty `__init__.py` files**

```python
# tests/__init__.py
# (empty)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_models.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test"
git add models.py tests/__init__.py tests/test_models.py
git commit -m "feat: add shared models (ParsedLoad, CostConfig, ScorerConfig)"
```

---

### Task 2: Database Migration (`database.py`)

**Files:**
- Create: `database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write failing tests for database migration**

```python
# tests/test_database.py
import os
import sqlite3
import pytest
from database import init_db, get_db, seed_defaults


TEST_DB = "test_loads.db"


@pytest.fixture(autouse=True)
def clean_db():
    """Remove test DB before and after each test."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestInitDb:
    def test_creates_all_tables(self):
        init_db(TEST_DB)
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = sorted([row[0] for row in cursor.fetchall()])
        conn.close()

        expected = sorted([
            "loads", "email_log", "lane_history", "broker_history",
            "load_feedback", "accessorials", "cost_config", "scorer_config",
            "toll_corridors", "fuel_prices", "city_demand_tiers",
        ])
        assert tables == expected

    def test_loads_table_has_new_columns(self):
        init_db(TEST_DB)
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.execute("PRAGMA table_info(loads)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        assert "outcome" in columns
        assert "duplicate_of" in columns
        assert "source" in columns

    def test_idempotent_init(self):
        """Calling init_db twice should not error."""
        init_db(TEST_DB)
        init_db(TEST_DB)  # Should not raise


class TestSeedDefaults:
    def test_seeds_cost_config(self):
        init_db(TEST_DB)
        seed_defaults(TEST_DB)
        conn = sqlite3.connect(TEST_DB)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM cost_config WHERE id = 1").fetchone()
        conn.close()

        assert row is not None
        assert row["truck_lease_monthly"] == 4000.00
        assert row["driver_pay_mode"] == "per_mile_only"

    def test_seeds_scorer_config(self):
        init_db(TEST_DB)
        seed_defaults(TEST_DB)
        conn = sqlite3.connect(TEST_DB)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM scorer_config WHERE id = 1").fetchone()
        conn.close()

        assert row is not None
        assert row["financial_weight"] == 0.50

    def test_seeds_toll_corridors(self):
        init_db(TEST_DB)
        seed_defaults(TEST_DB)
        conn = sqlite3.connect(TEST_DB)
        count = conn.execute("SELECT COUNT(*) FROM toll_corridors").fetchone()[0]
        conn.close()

        assert count == 7

    def test_seeds_city_demand_tiers(self):
        init_db(TEST_DB)
        seed_defaults(TEST_DB)
        conn = sqlite3.connect(TEST_DB)
        count = conn.execute("SELECT COUNT(*) FROM city_demand_tiers").fetchone()[0]
        conn.close()

        assert count > 0

    def test_seed_idempotent(self):
        """Running seed twice should not duplicate data."""
        init_db(TEST_DB)
        seed_defaults(TEST_DB)
        seed_defaults(TEST_DB)
        conn = sqlite3.connect(TEST_DB)
        count = conn.execute("SELECT COUNT(*) FROM cost_config").fetchone()[0]
        conn.close()
        assert count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_database.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'database'`

- [ ] **Step 3: Implement database.py**

```python
# database.py
"""Centralized database initialization, migration, and seed data."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


DEFAULT_DB_PATH = "loads.db"


@contextmanager
def get_db(db_path: str = DEFAULT_DB_PATH):
    """Database connection context manager."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: str = DEFAULT_DB_PATH):
    """Initialize all database tables. Safe to call multiple times."""
    conn = sqlite3.connect(db_path)

    # Original tables (preserved)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS loads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            -- From parser
            origin_city TEXT,
            origin_state TEXT,
            destination_city TEXT,
            destination_state TEXT,
            rate_total REAL,
            rate_per_mile REAL,
            mileage INTEGER,
            deadhead_miles INTEGER,
            weight INTEGER,
            equipment_type TEXT,
            commodity TEXT,
            pickup_date TEXT,
            pickup_time_window TEXT,
            delivery_date TEXT,
            delivery_time_window TEXT,
            broker_name TEXT,
            broker_mc_number TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            load_number TEXT,
            notes TEXT,

            -- From scorer
            total_miles INTEGER,
            total_cost REAL,
            net_revenue REAL,
            profit REAL,
            margin_pct REAL,
            rpm REAL,
            all_in_rpm REAL,
            drive_hours REAL,
            total_hours REAL,
            profit_per_hour REAL,
            score INTEGER,
            action TEXT,
            floor_rpm REAL,
            warnings TEXT,

            -- New columns (v2)
            outcome TEXT,
            duplicate_of INTEGER,
            source TEXT,

            UNIQUE(origin_city, origin_state, destination_city, destination_state,
                   pickup_date, broker_name, rate_total, mileage)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id TEXT UNIQUE,
            subject TEXT,
            sender TEXT,
            received_at TEXT,
            processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            loads_found INTEGER,
            status TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS lane_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin_city TEXT,
            origin_state TEXT,
            destination_city TEXT,
            destination_state TEXT,
            avg_rate REAL,
            avg_margin_pct REAL,
            load_count INTEGER DEFAULT 0,
            booked_count INTEGER DEFAULT 0,
            trend_direction TEXT DEFAULT 'stable',
            last_seen TEXT,
            updated_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS broker_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            broker_name TEXT UNIQUE,
            broker_mc_number TEXT,
            avg_detention_hours REAL DEFAULT 0.0,
            tonu_count INTEGER DEFAULT 0,
            loads_completed INTEGER DEFAULT 0,
            loads_seen INTEGER DEFAULT 0,
            rate_accuracy_pct REAL DEFAULT 100.0,
            ontime_pickup_pct REAL DEFAULT 100.0,
            reliability_grade TEXT DEFAULT 'U',
            updated_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS load_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            load_id INTEGER,
            actual_dwell_hours REAL,
            actual_rate_paid REAL,
            actual_toll_cost REAL,
            detention_hours REAL DEFAULT 0.0,
            ontime_pickup BOOLEAN,
            issues TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (load_id) REFERENCES loads(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS accessorials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            load_id INTEGER,
            type TEXT,
            amount REAL,
            notes TEXT,
            FOREIGN KEY (load_id) REFERENCES loads(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cost_config (
            id INTEGER PRIMARY KEY,
            truck_lease_monthly REAL DEFAULT 4000.00,
            insurance_monthly REAL DEFAULT 1800.00,
            overhead_monthly REAL DEFAULT 500.00,
            maint_reserve_monthly REAL DEFAULT 0.00,
            expected_monthly_miles INTEGER DEFAULT 8000,
            driver_pay_mode TEXT DEFAULT 'per_mile_only',
            driver_base_weekly REAL DEFAULT 0.00,
            driver_per_mile REAL DEFAULT 0.55,
            factoring_fee_pct REAL DEFAULT 3.0,
            fuel_mpg REAL DEFAULT 6.5,
            default_fuel_price REAL DEFAULT 3.85,
            updated_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS scorer_config (
            id INTEGER PRIMARY KEY,
            financial_weight REAL DEFAULT 0.50,
            lane_weight REAL DEFAULT 0.15,
            broker_weight REAL DEFAULT 0.15,
            strategic_weight REAL DEFAULT 0.20,
            updated_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS toll_corridors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corridor_name TEXT,
            interstate TEXT,
            states TEXT,
            cost_per_mile REAL,
            last_updated TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS fuel_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            padd_region TEXT,
            price_per_gallon REAL,
            effective_date TEXT,
            fetched_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS city_demand_tiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT,
            state TEXT,
            tier INTEGER,
            source TEXT DEFAULT 'seed',
            updated_at TEXT
        )
    """)

    # Migrate existing loads table if needed
    try:
        conn.execute("SELECT outcome FROM loads LIMIT 1")
    except sqlite3.OperationalError:
        # Old table exists without new columns — full migration needed
        # SQLite cannot ALTER UNIQUE constraints, so we rebuild the table
        conn.execute("ALTER TABLE loads RENAME TO loads_old")
        # The CREATE TABLE above already created the new schema
        conn.execute("""
            INSERT INTO loads (
                id, email_id, created_at, origin_city, origin_state,
                destination_city, destination_state, rate_total, rate_per_mile,
                mileage, deadhead_miles, weight, equipment_type, commodity,
                pickup_date, pickup_time_window, delivery_date, delivery_time_window,
                broker_name, broker_mc_number, contact_phone, contact_email,
                load_number, notes, total_miles, total_cost, net_revenue, profit,
                margin_pct, rpm, all_in_rpm, drive_hours, total_hours,
                profit_per_hour, score, action, floor_rpm, warnings, source
            )
            SELECT
                id, email_id, created_at, origin_city, origin_state,
                destination_city, destination_state, rate_total, rate_per_mile,
                mileage, deadhead_miles, weight, equipment_type, commodity,
                pickup_date, pickup_time_window, delivery_date, delivery_time_window,
                broker_name, broker_mc_number, contact_phone, contact_email,
                load_number, notes, total_miles, total_cost, net_revenue, profit,
                margin_pct, rpm, all_in_rpm, drive_hours, total_hours,
                profit_per_hour, score, action, floor_rpm, warnings, 'email'
            FROM loads_old
        """)
        conn.execute("DROP TABLE loads_old")

    conn.commit()
    conn.close()


def seed_defaults(db_path: str = DEFAULT_DB_PATH):
    """Insert default config rows and seed data. Idempotent."""
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)

    # Cost config (single row, id=1)
    existing = conn.execute("SELECT id FROM cost_config WHERE id = 1").fetchone()
    if not existing:
        conn.execute("""
            INSERT INTO cost_config (id, truck_lease_monthly, insurance_monthly,
                overhead_monthly, maint_reserve_monthly, expected_monthly_miles,
                driver_pay_mode, driver_base_weekly, driver_per_mile,
                factoring_fee_pct, fuel_mpg, default_fuel_price, updated_at)
            VALUES (1, 4000.00, 1800.00, 500.00, 0.00, 8000,
                    'per_mile_only', 0.00, 0.55, 3.0, 6.5, 3.85, ?)
        """, (now,))

    # Scorer config (single row, id=1)
    existing = conn.execute("SELECT id FROM scorer_config WHERE id = 1").fetchone()
    if not existing:
        conn.execute("""
            INSERT INTO scorer_config (id, financial_weight, lane_weight,
                broker_weight, strategic_weight, updated_at)
            VALUES (1, 0.50, 0.15, 0.15, 0.20, ?)
        """, (now,))

    # Toll corridors (7 seed corridors)
    existing_count = conn.execute("SELECT COUNT(*) FROM toll_corridors").fetchone()[0]
    if existing_count == 0:
        corridors = [
            ("Ohio Turnpike (I-80/I-90)", "I-80,I-90", "OH", 0.15),
            ("PA Turnpike (I-76)", "I-76", "PA", 0.45),
            ("NJ Turnpike", "I-95", "NJ", 0.25),
            ("NY Thruway (I-90)", "I-90", "NY", 0.12),
            ("Indiana Toll Road (I-80/I-90)", "I-80,I-90", "IN", 0.20),
            ("West Virginia Turnpike (I-77)", "I-77", "WV", 0.10),
            ("Florida Turnpike", "FL-91", "FL", 0.12),
        ]
        for name, interstate, states, cpm in corridors:
            conn.execute("""
                INSERT INTO toll_corridors (corridor_name, interstate, states, cost_per_mile, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (name, interstate, states, cpm, now))

    # City demand tiers
    existing_count = conn.execute("SELECT COUNT(*) FROM city_demand_tiers").fetchone()[0]
    if existing_count == 0:
        # Tier 1: Major freight hubs
        tier1 = [
            ("Atlanta", "GA"), ("Chicago", "IL"), ("Dallas", "TX"),
            ("Houston", "TX"), ("Memphis", "TN"), ("Nashville", "TN"),
            ("Columbus", "OH"), ("Indianapolis", "IN"), ("Charlotte", "NC"),
            ("Jacksonville", "FL"), ("Louisville", "KY"),
        ]
        # Tier 2: Mid-market cities
        tier2 = [
            ("Cleveland", "OH"), ("Pittsburgh", "PA"), ("Cincinnati", "OH"),
            ("Detroit", "MI"), ("Buffalo", "NY"), ("Philadelphia", "PA"),
            ("Baltimore", "MD"), ("Raleigh", "NC"), ("Tampa", "FL"),
            ("St. Louis", "MO"), ("Kansas City", "MO"), ("Milwaukee", "WI"),
            ("Minneapolis", "MN"), ("Denver", "CO"), ("New Orleans", "LA"),
            ("Birmingham", "AL"), ("Knoxville", "TN"), ("Grand Rapids", "MI"),
        ]
        # Tier 3: Smaller / low-demand
        tier3 = [
            ("Erie", "PA"), ("Toledo", "OH"), ("Akron", "OH"),
            ("Dayton", "OH"), ("Fort Wayne", "IN"), ("Lexington", "KY"),
            ("Mobile", "AL"), ("Little Rock", "AR"), ("Oklahoma City", "OK"),
        ]

        for city, state in tier1:
            conn.execute(
                "INSERT INTO city_demand_tiers (city, state, tier, source, updated_at) VALUES (?, ?, 1, 'seed', ?)",
                (city, state, now),
            )
        for city, state in tier2:
            conn.execute(
                "INSERT INTO city_demand_tiers (city, state, tier, source, updated_at) VALUES (?, ?, 2, 'seed', ?)",
                (city, state, now),
            )
        for city, state in tier3:
            conn.execute(
                "INSERT INTO city_demand_tiers (city, state, tier, source, updated_at) VALUES (?, ?, 3, 'seed', ?)",
                (city, state, now),
            )

    conn.commit()
    conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_database.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test"
git add database.py tests/test_database.py
git commit -m "feat: add centralized database with migration and seed data"
```

---

### Task 3: Cost Model (`costs/cost_model.py`)

**Files:**
- Create: `costs/__init__.py`
- Create: `costs/cost_model.py`
- Create: `tests/test_cost_model.py`

- [ ] **Step 1: Write failing tests for cost calculations**

```python
# tests/test_cost_model.py
import pytest
from models import CostConfig
from costs.cost_model import calculate_load_cost, CostBreakdown


class TestCalculateLoadCost:
    def test_basic_cost_calculation(self):
        """Calculate cost for a simple load with defaults."""
        config = CostConfig(
            truck_lease_monthly=4000.00,
            insurance_monthly=1800.00,
            overhead_monthly=500.00,
            maint_reserve_monthly=0.00,
            expected_monthly_miles=8000,
            driver_pay_mode="per_mile_only",
            driver_per_mile=0.55,
            fuel_mpg=6.5,
            default_fuel_price=3.85,
            factoring_fee_pct=3.0,
        )
        result = calculate_load_cost(
            loaded_miles=200,
            deadhead_miles=50,
            rate_total=600.00,
            config=config,
        )
        assert isinstance(result, CostBreakdown)
        assert result.total_miles == 250
        assert result.total_cost > 0
        assert result.net_revenue > 0
        assert result.profit == result.net_revenue - result.total_cost
        assert result.factoring_amount == pytest.approx(600.00 * 0.03)

    def test_cost_breakdown_components(self):
        """Verify individual cost components are tracked."""
        config = CostConfig(expected_monthly_miles=10000)
        result = calculate_load_cost(
            loaded_miles=500,
            deadhead_miles=100,
            rate_total=2000.00,
            config=config,
        )
        assert result.fuel_cost > 0
        assert result.driver_cost > 0
        assert result.lease_cost > 0
        assert result.insurance_cost > 0

    def test_with_tolls_and_accessorials(self):
        """Tolls and accessorials should add to total cost."""
        config = CostConfig()
        result_no_extras = calculate_load_cost(
            loaded_miles=200,
            deadhead_miles=50,
            rate_total=600.00,
            config=config,
        )
        result_with_extras = calculate_load_cost(
            loaded_miles=200,
            deadhead_miles=50,
            rate_total=600.00,
            config=config,
            toll_cost=45.00,
            accessorial_costs={"lumper": 75.00, "detention": 100.00},
        )
        assert result_with_extras.total_cost == pytest.approx(
            result_no_extras.total_cost + 45.00 + 75.00 + 100.00
        )
        assert result_with_extras.toll_cost == 45.00
        assert result_with_extras.accessorial_total == 175.00

    def test_null_rate_returns_partial(self):
        """If rate is None, revenue/profit fields should be None."""
        config = CostConfig()
        result = calculate_load_cost(
            loaded_miles=200,
            deadhead_miles=50,
            rate_total=None,
            config=config,
        )
        assert result.total_cost > 0
        assert result.net_revenue is None
        assert result.profit is None

    def test_fuel_price_override(self):
        """Regional fuel price should override default."""
        config = CostConfig(default_fuel_price=3.85)
        result_default = calculate_load_cost(
            loaded_miles=200, deadhead_miles=0, rate_total=600.00, config=config,
        )
        result_override = calculate_load_cost(
            loaded_miles=200, deadhead_miles=0, rate_total=600.00, config=config,
            fuel_price_override=4.50,
        )
        assert result_override.fuel_cost > result_default.fuel_cost

    def test_margin_and_rpm(self):
        """Verify margin and RPM calculations."""
        config = CostConfig(expected_monthly_miles=10000)
        result = calculate_load_cost(
            loaded_miles=200, deadhead_miles=0, rate_total=600.00, config=config,
        )
        assert result.margin_pct is not None
        assert result.rpm == pytest.approx(600.00 / 200)
        assert result.all_in_rpm == pytest.approx(result.net_revenue / 200)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_cost_model.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement costs/cost_model.py**

```python
# costs/__init__.py
# (empty)
```

```python
# costs/cost_model.py
"""Cost calculation with itemized breakdown."""

from dataclasses import dataclass
from typing import Optional
from models import CostConfig


@dataclass
class CostBreakdown:
    """Itemized cost breakdown for a load."""

    # Miles
    loaded_miles: float
    deadhead_miles: float
    total_miles: float

    # Cost components
    fuel_cost: float
    driver_cost: float
    lease_cost: float
    insurance_cost: float
    overhead_cost: float
    maint_reserve_cost: float
    toll_cost: float
    accessorial_total: float
    accessorial_detail: dict  # {"lumper": 75.00, ...}
    base_cpm: float
    total_cost: float

    # Revenue (None if rate unknown)
    gross_revenue: Optional[float]
    factoring_amount: Optional[float]
    net_revenue: Optional[float]
    profit: Optional[float]
    margin_pct: Optional[float]
    rpm: Optional[float]
    all_in_rpm: Optional[float]


def calculate_load_cost(
    loaded_miles: float,
    deadhead_miles: float,
    rate_total: Optional[float],
    config: CostConfig,
    fuel_price_override: Optional[float] = None,
    toll_cost: float = 0.0,
    accessorial_costs: Optional[dict] = None,
    detention_hours: float = 0.0,
    detention_rate: float = 50.0,
) -> CostBreakdown:
    """Calculate full cost breakdown for a load.

    Args:
        loaded_miles: Miles from pickup to delivery.
        deadhead_miles: Miles from current location to pickup.
        rate_total: Quoted rate (None if "Call for rate").
        config: CostConfig with monthly costs and driver pay settings.
        fuel_price_override: Regional fuel price (overrides config default).
        toll_cost: Estimated toll cost for this route.
        accessorial_costs: Dict of accessorial name → amount.
        detention_hours: Expected detention hours.
        detention_rate: $/hour for detention.

    Returns:
        CostBreakdown with all cost components and revenue metrics.
    """
    if accessorial_costs is None:
        accessorial_costs = {}

    total_miles = loaded_miles + deadhead_miles
    fuel_price = fuel_price_override or config.default_fuel_price

    # Per-mile costs
    fuel_cpm = fuel_price / config.fuel_mpg
    fuel_cost = fuel_cpm * total_miles
    driver_cost = config.driver_pay_per_mile * total_miles
    lease_cost = config.truck_lease_per_mile * total_miles
    insurance_cost = config.insurance_per_mile * total_miles
    overhead_cost = config.overhead_per_mile * total_miles
    maint_cost = config.maint_reserve_per_mile * total_miles

    base_cpm = config.total_base_cpm(fuel_price_override=fuel_price)
    accessorial_total = sum(accessorial_costs.values())

    total_cost = (base_cpm * total_miles) + toll_cost + accessorial_total

    # Revenue
    if rate_total is not None:
        gross_revenue = rate_total + (detention_hours * detention_rate)
        factoring_amount = gross_revenue * (config.factoring_fee_pct / 100)
        net_revenue = gross_revenue - factoring_amount
        profit = net_revenue - total_cost
        margin_pct = (profit / net_revenue * 100) if net_revenue > 0 else 0.0
        rpm = rate_total / loaded_miles if loaded_miles > 0 else 0.0
        all_in_rpm = net_revenue / total_miles if total_miles > 0 else 0.0
    else:
        gross_revenue = None
        factoring_amount = None
        net_revenue = None
        profit = None
        margin_pct = None
        rpm = None
        all_in_rpm = None

    return CostBreakdown(
        loaded_miles=loaded_miles,
        deadhead_miles=deadhead_miles,
        total_miles=total_miles,
        fuel_cost=round(fuel_cost, 2),
        driver_cost=round(driver_cost, 2),
        lease_cost=round(lease_cost, 2),
        insurance_cost=round(insurance_cost, 2),
        overhead_cost=round(overhead_cost, 2),
        maint_reserve_cost=round(maint_cost, 2),
        toll_cost=round(toll_cost, 2),
        accessorial_total=round(accessorial_total, 2),
        accessorial_detail=accessorial_costs,
        base_cpm=round(base_cpm, 4),
        total_cost=round(total_cost, 2),
        gross_revenue=round(gross_revenue, 2) if gross_revenue is not None else None,
        factoring_amount=round(factoring_amount, 2) if factoring_amount is not None else None,
        net_revenue=round(net_revenue, 2) if net_revenue is not None else None,
        profit=round(profit, 2) if profit is not None else None,
        margin_pct=round(margin_pct, 2) if margin_pct is not None else None,
        rpm=round(rpm, 2) if rpm is not None else None,
        all_in_rpm=round(all_in_rpm, 2) if all_in_rpm is not None else None,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_cost_model.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test"
git add costs/__init__.py costs/cost_model.py tests/test_cost_model.py
git commit -m "feat: add cost model with itemized breakdown and driver pay modes"
```

---

### Task 4: Wire Database + Cost Config API into app.py

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Write failing test for cost config endpoints**

```python
# tests/test_api_config.py
import os
import pytest
from fastapi.testclient import TestClient


TEST_DB = "test_api_loads.db"


@pytest.fixture(autouse=True)
def setup_app():
    """Set up test database and app."""
    os.environ["DATABASE_PATH"] = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    from database import init_db, seed_defaults
    init_db(TEST_DB)
    seed_defaults(TEST_DB)

    from app import app
    yield app

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.fixture
def client(setup_app):
    return TestClient(setup_app)


class TestCostConfigEndpoints:
    def test_get_cost_config(self, client):
        response = client.get("/api/config/costs")
        assert response.status_code == 200
        data = response.json()
        assert data["truck_lease_monthly"] == 4000.00
        assert data["driver_pay_mode"] == "per_mile_only"

    def test_update_cost_config(self, client):
        response = client.put("/api/config/costs", json={
            "truck_lease_monthly": 5000.00,
            "driver_pay_mode": "base_plus_mile",
            "driver_base_weekly": 800.00,
            "driver_per_mile": 0.15,
        })
        assert response.status_code == 200

        # Verify update persisted
        response = client.get("/api/config/costs")
        data = response.json()
        assert data["truck_lease_monthly"] == 5000.00
        assert data["driver_pay_mode"] == "base_plus_mile"


class TestScorerConfigEndpoints:
    def test_get_scorer_config(self, client):
        response = client.get("/api/config/scorer")
        assert response.status_code == 200
        data = response.json()
        assert data["financial_weight"] == 0.50

    def test_update_scorer_config(self, client):
        response = client.put("/api/config/scorer", json={
            "financial_weight": 0.40,
            "lane_weight": 0.20,
            "broker_weight": 0.20,
            "strategic_weight": 0.20,
        })
        assert response.status_code == 200

    def test_reject_weights_not_summing_to_one(self, client):
        response = client.put("/api/config/scorer", json={
            "financial_weight": 0.50,
            "lane_weight": 0.50,
            "broker_weight": 0.50,
            "strategic_weight": 0.50,
        })
        assert response.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_api_config.py -v`
Expected: FAIL — endpoints don't exist yet

- [ ] **Step 3: Update app.py — swap DB init, add config endpoints**

Changes to `app.py`:
1. Replace inline `init_db()` and `get_db()` with imports from `database.py`
2. Add `GET /api/config/costs` and `PUT /api/config/costs`
3. Add `GET /api/config/scorer` and `PUT /api/config/scorer`
4. Call `seed_defaults()` in startup

Key additions (add after existing endpoints in `app.py`):

```python
# In app.py, update imports at top:
from database import init_db, get_db, seed_defaults, DEFAULT_DB_PATH
from models import ScorerConfig

# Update startup:
@app.on_event("startup")
async def startup():
    init_db()
    seed_defaults()

# Add new Pydantic models:
class CostConfigInput(BaseModel):
    truck_lease_monthly: Optional[float] = None
    insurance_monthly: Optional[float] = None
    overhead_monthly: Optional[float] = None
    maint_reserve_monthly: Optional[float] = None
    expected_monthly_miles: Optional[int] = None
    driver_pay_mode: Optional[str] = None
    driver_base_weekly: Optional[float] = None
    driver_per_mile: Optional[float] = None
    factoring_fee_pct: Optional[float] = None
    fuel_mpg: Optional[float] = None
    default_fuel_price: Optional[float] = None

class ScorerConfigInput(BaseModel):
    financial_weight: float
    lane_weight: float
    broker_weight: float
    strategic_weight: float

# Add new endpoints:
@app.get("/api/config/costs")
async def get_cost_config():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM cost_config WHERE id = 1").fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Cost config not found")
        return dict(row)

@app.put("/api/config/costs")
async def update_cost_config(config: CostConfigInput):
    updates = {k: v for k, v in config.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values())
    values.append(datetime.now(timezone.utc).isoformat())

    with get_db() as conn:
        conn.execute(
            f"UPDATE cost_config SET {set_clause}, updated_at = ? WHERE id = 1",
            values,
        )
        conn.commit()
        row = conn.execute("SELECT * FROM cost_config WHERE id = 1").fetchone()
        return dict(row)

@app.get("/api/config/scorer")
async def get_scorer_config():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM scorer_config WHERE id = 1").fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Scorer config not found")
        return dict(row)

@app.put("/api/config/scorer")
async def update_scorer_config(config: ScorerConfigInput):
    # Validate weights sum to 1.0
    ScorerConfig(**config.dict())  # Raises if invalid

    with get_db() as conn:
        conn.execute("""
            UPDATE scorer_config
            SET financial_weight = ?, lane_weight = ?, broker_weight = ?,
                strategic_weight = ?, updated_at = ?
            WHERE id = 1
        """, (config.financial_weight, config.lane_weight, config.broker_weight,
              config.strategic_weight, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        row = conn.execute("SELECT * FROM scorer_config WHERE id = 1").fetchone()
        return dict(row)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_api_config.py -v`
Expected: All PASS

- [ ] **Step 5: Run existing tests to confirm nothing broke**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test"
git add app.py tests/test_api_config.py
git commit -m "feat: wire database.py into app, add cost/scorer config endpoints"
```

---

## Chunk 2: Data Ingestion — Paste Parser, Gap Resolver, Duplicate Detection

### File Structure (Chunk 2)

- Create: `ingestion/__init__.py`
- Create: `ingestion/dat_paste_parser.py` — parse copy-pasted DAT dashboard text
- Create: `ingestion/gap_resolver.py` — identify missing fields, manage completion flow
- Create: `ingestion/duplicate_detector.py` — check for duplicate loads
- Create: `tests/test_paste_parser.py`
- Create: `tests/test_gap_resolver.py`
- Create: `tests/test_duplicate_detector.py`
- Modify: `app.py` — add ingestion endpoints

**NOTE:** The paste parser requires sample pasted text from the DAT dashboard to calibrate patterns. During implementation, the developer should ask the user for 2-3 sample pastes. The tests below use placeholder patterns that will need adjustment once real samples are available.

---

### Task 5: DAT Paste Parser (`ingestion/dat_paste_parser.py`)

**Files:**
- Create: `ingestion/__init__.py`
- Create: `ingestion/dat_paste_parser.py`
- Create: `tests/test_paste_parser.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_paste_parser.py
import pytest
from ingestion.dat_paste_parser import parse_dat_paste
from models import ParsedLoad


class TestParseDatPaste:
    def test_parses_basic_load(self):
        """Parse a standard DAT paste with all key fields."""
        # NOTE: This sample format is a best guess. Update once real
        # DAT dashboard paste samples are provided by the user.
        text = """
        Columbus, OH → Pittsburgh, PA
        185 mi | Van | 42,000 lbs
        Rate: $600.00 ($3.24/mi)
        Pickup: 03/20/2026 08:00-16:00
        Delivery: 03/21/2026
        Company: TQL | MC# 123456
        Contact: 555-0100 | dispatch@tql.com
        """
        loads = parse_dat_paste(text)
        assert len(loads) == 1
        load = loads[0]
        assert isinstance(load, ParsedLoad)
        assert load.origin_city == "Columbus"
        assert load.origin_state == "OH"
        assert load.destination_city == "Pittsburgh"
        assert load.destination_state == "PA"
        assert load.mileage == 185
        assert load.rate_total == 600.00
        assert load.source == "paste"

    def test_parses_call_for_rate(self):
        """Load with 'Call' or missing rate should have rate_total=None."""
        text = """
        Columbus, OH → Charlotte, NC
        456 mi | Van | 38,000 lbs
        Rate: Call
        Pickup: 03/22/2026
        Company: Echo Global
        """
        loads = parse_dat_paste(text)
        assert len(loads) == 1
        assert loads[0].rate_total is None

    def test_parses_multiple_loads(self):
        """Multiple loads in one paste should all be extracted."""
        text = """
        Columbus, OH → Pittsburgh, PA
        185 mi | Van | 42,000 lbs
        Rate: $600.00
        Pickup: 03/20/2026
        Company: TQL

        Cincinnati, OH → Indianapolis, IN
        112 mi | Van | 35,000 lbs
        Rate: $400.00
        Pickup: 03/20/2026
        Company: CH Robinson
        """
        loads = parse_dat_paste(text)
        assert len(loads) == 2

    def test_empty_text_returns_empty(self):
        loads = parse_dat_paste("")
        assert loads == []

    def test_partial_data_returns_what_it_can(self):
        """Even if some fields are missing, return what was parsed."""
        text = """
        Columbus, OH → Pittsburgh, PA
        185 mi
        """
        loads = parse_dat_paste(text)
        assert len(loads) == 1
        assert loads[0].origin_city == "Columbus"
        assert loads[0].mileage == 185
        assert loads[0].rate_total is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_paste_parser.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ingestion/dat_paste_parser.py**

```python
# ingestion/__init__.py
# (empty)
```

```python
# ingestion/dat_paste_parser.py
"""Parse load data from text copy-pasted from the DAT dashboard.

NOTE: The regex patterns here are based on common DAT formatting.
These should be refined once real paste samples from the user are available.
"""

import re
from typing import Optional
from models import ParsedLoad


def parse_dat_paste(text: str) -> list[ParsedLoad]:
    """Parse pasted DAT dashboard text into ParsedLoad objects.

    Handles single or multiple loads separated by blank lines.

    Args:
        text: Raw text copied from DAT dashboard.

    Returns:
        List of ParsedLoad objects (one per load found).
    """
    if not text or not text.strip():
        return []

    # Split into load blocks (separated by double newlines or horizontal rules)
    blocks = re.split(r"\n\s*\n", text.strip())
    blocks = [b.strip() for b in blocks if b.strip()]

    loads = []
    for block in blocks:
        load = _parse_single_block(block)
        if load:
            loads.append(load)

    return loads


def _parse_single_block(block: str) -> Optional[ParsedLoad]:
    """Parse a single load block into a ParsedLoad."""
    lines = block.strip()

    origin_city, origin_state = _extract_origin(lines)
    dest_city, dest_state = _extract_destination(lines)
    mileage = _extract_mileage(lines)

    # Must have at least origin, destination, and mileage
    if not all([origin_city, origin_state, dest_city, dest_state, mileage]):
        # Try looser parsing — if we have origin/dest but no mileage, still return
        if origin_city and origin_state and dest_city and dest_state:
            mileage = mileage or 0
        else:
            return None

    return ParsedLoad(
        origin_city=origin_city,
        origin_state=origin_state,
        destination_city=dest_city,
        destination_state=dest_state,
        mileage=mileage if mileage else 0,
        source="paste",
        rate_total=_extract_rate(lines),
        rate_per_mile=_extract_rate_per_mile(lines),
        weight=_extract_weight(lines),
        equipment_type=_extract_equipment(lines) or "Van",
        commodity=_extract_commodity(lines) or "",
        pickup_date=_extract_date(lines, "pickup") or "",
        pickup_time_window=_extract_time_window(lines, "pickup") or "",
        delivery_date=_extract_date(lines, "delivery") or "",
        delivery_time_window=_extract_time_window(lines, "delivery") or "",
        broker_name=_extract_company(lines) or "",
        broker_mc_number=_extract_mc(lines) or "",
        contact_phone=_extract_phone(lines) or "",
        contact_email=_extract_email(lines) or "",
    )


def _extract_origin(text: str) -> tuple[str, str]:
    """Extract origin city and state from route line."""
    # Pattern: "City, ST → City, ST" or "City, ST to City, ST"
    match = re.search(
        r"([A-Za-z\s.''-]+),\s*([A-Z]{2})\s*(?:→|->|to|―)\s*",
        text
    )
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "", ""


def _extract_destination(text: str) -> tuple[str, str]:
    """Extract destination city and state from route line."""
    match = re.search(
        r"(?:→|->|to|―)\s*([A-Za-z\s.''-]+),\s*([A-Z]{2})",
        text
    )
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "", ""


def _extract_mileage(text: str) -> Optional[int]:
    """Extract mileage from text."""
    match = re.search(r"(\d{1,4})\s*mi", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _extract_rate(text: str) -> Optional[float]:
    """Extract total rate. Returns None if 'Call' or not found."""
    # Check for "Call for rate" or just "Call"
    if re.search(r"rate\s*:\s*call", text, re.IGNORECASE):
        return None

    match = re.search(r"rate\s*:\s*\$?([\d,]+\.?\d*)", text, re.IGNORECASE)
    if match:
        return float(match.group(1).replace(",", ""))

    # Also try standalone dollar amount pattern
    match = re.search(r"\$([\d,]+\.?\d*)\s*(?:\(|$|\s)", text)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


def _extract_rate_per_mile(text: str) -> Optional[float]:
    """Extract rate per mile if shown."""
    match = re.search(r"\$([\d.]+)\s*/\s*mi", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _extract_weight(text: str) -> Optional[int]:
    """Extract weight in lbs."""
    match = re.search(r"([\d,]+)\s*(?:lbs?|pounds?)", text, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def _extract_equipment(text: str) -> Optional[str]:
    """Extract equipment type."""
    for equip in ["Reefer", "Flatbed", "Van", "Step Deck", "Power Only"]:
        if re.search(equip, text, re.IGNORECASE):
            return equip
    return None


def _extract_commodity(text: str) -> Optional[str]:
    """Extract commodity if present."""
    match = re.search(r"commodity\s*:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_date(text: str, label: str) -> Optional[str]:
    """Extract date for pickup or delivery."""
    match = re.search(
        rf"{label}\s*:\s*(\d{{1,2}}/\d{{1,2}}/\d{{4}})",
        text, re.IGNORECASE
    )
    if match:
        parts = match.group(1).split("/")
        return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
    return None


def _extract_time_window(text: str, label: str) -> Optional[str]:
    """Extract time window for pickup or delivery."""
    match = re.search(
        rf"{label}\s*:\s*\d{{1,2}}/\d{{1,2}}/\d{{4}}\s+(\d{{1,2}}:\d{{2}}\s*-\s*\d{{1,2}}:\d{{2}})",
        text, re.IGNORECASE
    )
    if match:
        return match.group(1).strip()
    return None


def _extract_company(text: str) -> Optional[str]:
    """Extract broker/company name."""
    match = re.search(r"company\s*:\s*(.+?)(?:\||$|\n)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_mc(text: str) -> Optional[str]:
    """Extract MC number."""
    match = re.search(r"MC#?\s*(\d+)", text, re.IGNORECASE)
    if match:
        return f"MC-{match.group(1)}"
    return None


def _extract_phone(text: str) -> Optional[str]:
    """Extract phone number."""
    match = re.search(r"(?:contact|phone)\s*:\s*([\d\s()-]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Also try standalone phone patterns
    match = re.search(r"(\d{3}[-.\s]\d{3}[-.\s]\d{4})", text)
    if match:
        return match.group(1)
    return None


def _extract_email(text: str) -> Optional[str]:
    """Extract email address."""
    match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if match:
        return match.group(0)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_paste_parser.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test"
git add ingestion/__init__.py ingestion/dat_paste_parser.py tests/test_paste_parser.py
git commit -m "feat: add DAT paste parser for copy-paste ingestion"
```

---

### Task 6: Gap Resolver (`ingestion/gap_resolver.py`)

**Files:**
- Create: `ingestion/gap_resolver.py`
- Create: `tests/test_gap_resolver.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_gap_resolver.py
import pytest
from models import ParsedLoad, ParsedField
from ingestion.gap_resolver import resolve_gaps, GapReport


class TestResolveGaps:
    def test_complete_load_has_no_gaps(self):
        load = ParsedLoad(
            origin_city="Columbus", origin_state="OH",
            destination_city="Pittsburgh", destination_state="PA",
            mileage=185, rate_total=600.00, source="paste",
            broker_name="TQL", pickup_date="2026-03-20",
        )
        report = resolve_gaps(load)
        assert report.is_complete
        assert len(report.missing_required) == 0

    def test_missing_rate_flagged_as_optional_gap(self):
        load = ParsedLoad(
            origin_city="Columbus", origin_state="OH",
            destination_city="Pittsburgh", destination_state="PA",
            mileage=185, source="paste",
        )
        report = resolve_gaps(load)
        assert report.is_complete  # Rate is optional
        assert "rate_total" in report.missing_optional

    def test_low_confidence_fields_flagged(self):
        """Fields with confidence < 0.7 should be flagged."""
        load = ParsedLoad(
            origin_city="Columbus", origin_state="OH",
            destination_city="Pittsburgh", destination_state="PA",
            mileage=185, rate_total=600.00, source="ocr",
        )
        confidence = {
            "rate_total": ParsedField(value=600.00, confidence=0.5, source="ocr"),
            "mileage": ParsedField(value=185, confidence=0.9, source="ocr"),
        }
        report = resolve_gaps(load, field_confidence=confidence)
        assert "rate_total" in report.low_confidence

    def test_apply_fills_merges_fields(self):
        load = ParsedLoad(
            origin_city="Columbus", origin_state="OH",
            destination_city="Pittsburgh", destination_state="PA",
            mileage=185, source="paste",
        )
        fills = {"rate_total": 600.00, "broker_name": "TQL"}
        updated = resolve_gaps(load).apply_fills(load, fills)
        assert updated.rate_total == 600.00
        assert updated.broker_name == "TQL"

    def test_summary_message(self):
        load = ParsedLoad(
            origin_city="Columbus", origin_state="OH",
            destination_city="Pittsburgh", destination_state="PA",
            mileage=185, source="paste",
        )
        report = resolve_gaps(load)
        assert isinstance(report.summary, str)
        assert "parsed" in report.summary.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_gap_resolver.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ingestion/gap_resolver.py**

```python
# ingestion/gap_resolver.py
"""Identifies missing or low-confidence fields in parsed loads."""

from dataclasses import dataclass, field
from typing import Optional
from models import ParsedLoad, ParsedField


# Fields that enhance scoring when present
SCORING_FIELDS = [
    "rate_total", "deadhead_miles", "weight", "pickup_date",
    "delivery_date", "broker_name",
]

CONFIDENCE_THRESHOLD = 0.7


@dataclass
class GapReport:
    """Report of missing/low-confidence fields for a parsed load."""

    missing_required: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    low_confidence: list[str] = field(default_factory=list)
    fields_parsed: int = 0
    fields_total: int = len(SCORING_FIELDS) + 5  # required + scoring

    @property
    def is_complete(self) -> bool:
        """True if all required fields are present."""
        return len(self.missing_required) == 0

    @property
    def summary(self) -> str:
        msg = f"Parsed {self.fields_parsed} of {self.fields_total} fields"
        gaps = self.missing_required + self.missing_optional + self.low_confidence
        if gaps:
            msg += f" — gaps: {', '.join(gaps)}"
        return msg

    def apply_fills(self, load: ParsedLoad, fills: dict) -> ParsedLoad:
        """Return a new ParsedLoad with filled-in values."""
        data = load.to_dict()
        data.update(fills)
        return ParsedLoad(**data)


def resolve_gaps(
    load: ParsedLoad,
    field_confidence: Optional[dict[str, ParsedField]] = None,
) -> GapReport:
    """Analyze a ParsedLoad for missing or low-confidence fields.

    Args:
        load: The parsed load to analyze.
        field_confidence: Optional dict of field_name → ParsedField with
            confidence scores (typically from OCR parser).

    Returns:
        GapReport with lists of missing/low-confidence fields.
    """
    if field_confidence is None:
        field_confidence = {}

    report = GapReport()
    parsed_count = 0

    # Check required fields (should always be present if ParsedLoad was created,
    # but the model allows mileage=0 which might indicate unparsed)
    required = ["origin_city", "origin_state", "destination_city", "destination_state", "mileage"]
    for f in required:
        val = getattr(load, f, None)
        if val is None or val == "" or val == 0:
            if f == "mileage" and load.mileage == 0:
                report.missing_required.append(f)
            elif not val:
                report.missing_required.append(f)
        else:
            parsed_count += 1

    # Check optional scoring fields
    for f in SCORING_FIELDS:
        val = getattr(load, f, None)
        if val is None or val == "" or val == 0:
            report.missing_optional.append(f)
        else:
            parsed_count += 1

    # Check confidence
    for field_name, pf in field_confidence.items():
        if pf.confidence < CONFIDENCE_THRESHOLD:
            report.low_confidence.append(field_name)

    report.fields_parsed = parsed_count
    return report
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_gap_resolver.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test"
git add ingestion/gap_resolver.py tests/test_gap_resolver.py
git commit -m "feat: add gap resolver for identifying missing load fields"
```

---

### Task 7: Duplicate Detector (`ingestion/duplicate_detector.py`)

**Files:**
- Create: `ingestion/duplicate_detector.py`
- Create: `tests/test_duplicate_detector.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_duplicate_detector.py
import os
import pytest
from database import init_db, get_db
from models import ParsedLoad
from ingestion.duplicate_detector import check_duplicate, DuplicateResult

TEST_DB = "test_dedup.db"


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    # Insert a test load
    with get_db(TEST_DB) as conn:
        conn.execute("""
            INSERT INTO loads (origin_city, origin_state, destination_city,
                destination_state, pickup_date, broker_name, rate_total, mileage, source)
            VALUES ('Columbus', 'OH', 'Pittsburgh', 'PA', '2026-03-20', 'TQL', 600.00, 185, 'paste')
        """)
        conn.commit()
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestCheckDuplicate:
    def test_exact_duplicate_detected(self):
        load = ParsedLoad(
            origin_city="Columbus", origin_state="OH",
            destination_city="Pittsburgh", destination_state="PA",
            mileage=185, rate_total=600.00, source="paste",
            pickup_date="2026-03-20", broker_name="TQL",
        )
        result = check_duplicate(load, db_path=TEST_DB)
        assert result.is_duplicate
        assert result.matching_load_id is not None

    def test_different_rate_not_duplicate(self):
        load = ParsedLoad(
            origin_city="Columbus", origin_state="OH",
            destination_city="Pittsburgh", destination_state="PA",
            mileage=185, rate_total=650.00, source="paste",
            pickup_date="2026-03-20", broker_name="TQL",
        )
        result = check_duplicate(load, db_path=TEST_DB)
        assert not result.is_duplicate

    def test_different_route_not_duplicate(self):
        load = ParsedLoad(
            origin_city="Cincinnati", origin_state="OH",
            destination_city="Pittsburgh", destination_state="PA",
            mileage=285, rate_total=600.00, source="paste",
        )
        result = check_duplicate(load, db_path=TEST_DB)
        assert not result.is_duplicate

    def test_no_loads_in_db(self):
        os.remove(TEST_DB)
        init_db(TEST_DB)
        load = ParsedLoad(
            origin_city="Columbus", origin_state="OH",
            destination_city="Pittsburgh", destination_state="PA",
            mileage=185, rate_total=600.00, source="paste",
        )
        result = check_duplicate(load, db_path=TEST_DB)
        assert not result.is_duplicate
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_duplicate_detector.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ingestion/duplicate_detector.py**

```python
# ingestion/duplicate_detector.py
"""Check incoming loads against existing database for duplicates."""

from dataclasses import dataclass
from typing import Optional
from models import ParsedLoad
from database import get_db, DEFAULT_DB_PATH


@dataclass
class DuplicateResult:
    is_duplicate: bool
    matching_load_id: Optional[int] = None
    message: str = ""


def check_duplicate(load: ParsedLoad, db_path: str = DEFAULT_DB_PATH) -> DuplicateResult:
    """Check if a load already exists in the database.

    Duplicate key: (origin_city, origin_state, destination_city,
    destination_state, pickup_date, broker_name, rate_total, mileage)
    """
    with get_db(db_path) as conn:
        row = conn.execute("""
            SELECT id FROM loads
            WHERE origin_city = ? AND origin_state = ?
              AND destination_city = ? AND destination_state = ?
              AND COALESCE(pickup_date, '') = COALESCE(?, '')
              AND COALESCE(broker_name, '') = COALESCE(?, '')
              AND COALESCE(rate_total, 0) = COALESCE(?, 0)
              AND COALESCE(mileage, 0) = COALESCE(?, 0)
            LIMIT 1
        """, (
            load.origin_city, load.origin_state,
            load.destination_city, load.destination_state,
            load.pickup_date or "", load.broker_name or "",
            load.rate_total or 0, load.mileage or 0,
        )).fetchone()

    if row:
        return DuplicateResult(
            is_duplicate=True,
            matching_load_id=row[0],
            message=f"This looks like a duplicate of Load #{row[0]}",
        )

    return DuplicateResult(is_duplicate=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_duplicate_detector.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test"
git add ingestion/duplicate_detector.py tests/test_duplicate_detector.py
git commit -m "feat: add duplicate detection for incoming loads"
```

---

### Task 8: Ingestion API Endpoints

**Files:**
- Modify: `app.py`
- Create: `tests/test_api_ingestion.py`

- [ ] **Step 1: Write failing tests for ingestion endpoints**

```python
# tests/test_api_ingestion.py
import os
import pytest
from fastapi.testclient import TestClient

TEST_DB = "test_ingest_api.db"


@pytest.fixture(autouse=True)
def setup_app():
    os.environ["DATABASE_PATH"] = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    from database import init_db, seed_defaults
    init_db(TEST_DB)
    seed_defaults(TEST_DB)
    from app import app
    yield app
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.fixture
def client(setup_app):
    return TestClient(setup_app)


class TestPasteEndpoint:
    def test_parse_paste_returns_loads(self, client):
        response = client.post("/api/ingest/paste", json={
            "text": """
            Columbus, OH → Pittsburgh, PA
            185 mi | Van | 42,000 lbs
            Rate: $600.00 ($3.24/mi)
            Pickup: 03/20/2026 08:00-16:00
            Company: TQL | MC# 123456
            """
        })
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        assert "gaps" in data

    def test_parse_paste_empty_text(self, client):
        response = client.post("/api/ingest/paste", json={"text": ""})
        assert response.status_code == 200
        assert response.json()["count"] == 0


class TestCompleteEndpoint:
    def test_complete_and_save_load(self, client):
        # First parse
        parse_response = client.post("/api/ingest/paste", json={
            "text": """
            Columbus, OH → Pittsburgh, PA
            185 mi | Van
            Rate: $600.00
            Pickup: 03/20/2026
            Company: TQL
            """
        })
        load_data = parse_response.json()["loads"][0]

        # Complete and save
        response = client.post("/api/ingest/complete", json={
            "load": load_data,
            "fills": {"weight": 42000},
            "save": True,
        })
        assert response.status_code == 200
        assert response.json()["saved"] is True
        assert "id" in response.json()


class TestDuplicateEndpoint:
    def test_duplicate_flagged(self, client):
        # Save a load
        client.post("/api/ingest/complete", json={
            "load": {
                "origin_city": "Columbus", "origin_state": "OH",
                "destination_city": "Pittsburgh", "destination_state": "PA",
                "mileage": 185, "rate_total": 600.00, "source": "paste",
                "pickup_date": "2026-03-20", "broker_name": "TQL",
            },
            "fills": {},
            "save": True,
        })
        # Try same load again
        response = client.post("/api/ingest/paste", json={
            "text": """
            Columbus, OH → Pittsburgh, PA
            185 mi | Van
            Rate: $600.00
            Pickup: 03/20/2026
            Company: TQL
            """
        })
        data = response.json()
        # Should flag as duplicate
        assert any(
            l.get("duplicate_of") is not None
            for l in data.get("loads", [])
        ) or data.get("duplicates", 0) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_api_ingestion.py -v`
Expected: FAIL — endpoints don't exist

- [ ] **Step 3: Add ingestion endpoints to app.py**

Add to `app.py`:

```python
# New imports at top:
from ingestion.dat_paste_parser import parse_dat_paste
from ingestion.gap_resolver import resolve_gaps
from ingestion.duplicate_detector import check_duplicate
from models import ParsedLoad

# New Pydantic models:
class PasteInput(BaseModel):
    text: str

class CompleteInput(BaseModel):
    load: dict
    fills: dict = {}
    save: bool = False

# New endpoints:
@app.post("/api/ingest/paste")
async def ingest_paste(input: PasteInput):
    loads = parse_dat_paste(input.text)
    results = []
    for load in loads:
        gap_report = resolve_gaps(load)
        dup = check_duplicate(load)
        load_dict = load.to_dict()
        load_dict["gaps"] = gap_report.summary
        load_dict["missing_optional"] = gap_report.missing_optional
        load_dict["is_complete"] = gap_report.is_complete
        if dup.is_duplicate:
            load_dict["duplicate_of"] = dup.matching_load_id
            load_dict["duplicate_message"] = dup.message
        results.append(load_dict)
    return {
        "loads": results,
        "count": len(results),
        "gaps": [r["gaps"] for r in results],
        "duplicates": sum(1 for r in results if r.get("duplicate_of")),
    }

@app.post("/api/ingest/complete")
async def ingest_complete(input: CompleteInput):
    load_data = {**input.load, **input.fills}
    # Ensure source is set
    if "source" not in load_data:
        load_data["source"] = "manual"

    parsed = ParsedLoad(**load_data)
    scored = score_load(parsed.to_dict())

    if input.save:
        with get_db() as conn:
            try:
                cursor = conn.execute("""
                    INSERT INTO loads (
                        origin_city, origin_state, destination_city, destination_state,
                        rate_total, rate_per_mile, mileage, deadhead_miles, weight,
                        equipment_type, commodity, pickup_date, pickup_time_window,
                        delivery_date, delivery_time_window, broker_name, broker_mc_number,
                        contact_phone, contact_email, load_number, notes,
                        total_miles, total_cost, net_revenue, profit, margin_pct,
                        rpm, all_in_rpm, drive_hours, total_hours, profit_per_hour,
                        score, action, floor_rpm, warnings, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                              ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    scored["origin_city"], scored["origin_state"],
                    scored["destination_city"], scored["destination_state"],
                    scored["rate_total"], scored.get("rpm"), scored["mileage"],
                    scored["deadhead_miles"], scored.get("weight"),
                    scored.get("equipment_type", "Van"), scored.get("commodity", ""),
                    scored.get("pickup_date", ""), scored.get("pickup_time_window", ""),
                    scored.get("delivery_date", ""), scored.get("delivery_time_window", ""),
                    scored.get("broker_name", ""), scored.get("broker_mc_number", ""),
                    scored.get("contact_phone", ""), scored.get("contact_email", ""),
                    scored.get("load_number", ""), scored.get("notes", ""),
                    scored["total_miles"], scored["total_cost"],
                    scored.get("net_revenue"), scored.get("profit"), scored.get("margin_pct"),
                    scored.get("rpm"), scored.get("all_in_rpm"),
                    scored.get("drive_hours"), scored.get("total_hours"),
                    scored.get("profit_per_hour"),
                    scored.get("score"), scored.get("action"), scored.get("floor_rpm"),
                    json.dumps(scored.get("warnings", [])),
                    parsed.source,
                ))
                conn.commit()
                scored["id"] = cursor.lastrowid
                return {"saved": True, "id": cursor.lastrowid, "scored": scored}
            except sqlite3.IntegrityError:
                return {"saved": False, "error": "Duplicate load", "scored": scored}

    return {"saved": False, "scored": scored}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/test_api_ingestion.py -v`
Expected: All PASS

- [ ] **Step 5: Run full test suite**

Run: `cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test" && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
cd "/Users/rajanpatel/Documents/Stratus LLc/Stratus Intelligence/Profitability Test"
git add app.py tests/test_api_ingestion.py
git commit -m "feat: add paste ingestion, gap resolution, and duplicate detection endpoints"
```

---

## Chunk 3: Scoring Engine — Lane, Broker, Strategic, Composite Scorers

### File Structure (Chunk 3)

- Create: `scoring/__init__.py`
- Create: `scoring/financial_scorer.py` — extracted from existing `profitability_engine.py`
- Create: `scoring/lane_scorer.py` — lane-aware scoring with history
- Create: `scoring/broker_scorer.py` — broker reliability grading
- Create: `scoring/strategic_scorer.py` — destination demand scoring
- Create: `scoring/composite_scorer.py` — combines all scorers
- Create: `tests/test_financial_scorer.py`
- Create: `tests/test_lane_scorer.py`
- Create: `tests/test_broker_scorer.py`
- Create: `tests/test_strategic_scorer.py`
- Create: `tests/test_composite_scorer.py`

---

### Task 9: Financial Scorer (extract from existing engine)

**Files:**
- Create: `scoring/__init__.py`
- Create: `scoring/financial_scorer.py`
- Create: `tests/test_financial_scorer.py`

Extract the scoring rubric from `profitability_engine.py:220-280` into a standalone scorer that takes a `CostBreakdown` and returns a normalized score (0.0 to 1.0).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_financial_scorer.py
import pytest
from scoring.financial_scorer import score_financial


class TestScoreFinancial:
    def test_excellent_load(self):
        """High margin, high RPM, low deadhead → high score."""
        result = score_financial(
            margin_pct=30.0, all_in_rpm=3.50,
            deadhead_pct=3.0, loaded_miles=200, detention_hours=0,
        )
        assert 0.0 <= result.score <= 1.0
        assert result.score >= 0.7

    def test_terrible_load(self):
        """Negative margin → low score."""
        result = score_financial(
            margin_pct=-5.0, all_in_rpm=1.50,
            deadhead_pct=40.0, loaded_miles=50, detention_hours=3,
        )
        assert result.score <= 0.3

    def test_null_rate_returns_none(self):
        """If margin is None (no rate), score should be None."""
        result = score_financial(
            margin_pct=None, all_in_rpm=None,
            deadhead_pct=10.0, loaded_miles=200, detention_hours=0,
        )
        assert result.score is None

    def test_action_tier_book_it(self):
        result = score_financial(
            margin_pct=30.0, all_in_rpm=3.50,
            deadhead_pct=3.0, loaded_miles=200, detention_hours=0,
        )
        assert result.action == "BOOK IT"

    def test_action_tier_pass(self):
        result = score_financial(
            margin_pct=-5.0, all_in_rpm=1.50,
            deadhead_pct=40.0, loaded_miles=50, detention_hours=3,
        )
        assert result.action == "PASS"

    def test_score_normalized_to_zero_one(self):
        """Score should always be between 0 and 1."""
        for margin in [-10, 0, 5, 15, 25, 40]:
            for rpm in [1.0, 2.0, 3.0, 4.0]:
                result = score_financial(
                    margin_pct=margin, all_in_rpm=rpm,
                    deadhead_pct=10.0, loaded_miles=200, detention_hours=0,
                )
                assert 0.0 <= result.score <= 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement scoring/financial_scorer.py**

```python
# scoring/__init__.py
# (empty)
```

```python
# scoring/financial_scorer.py
"""Financial scoring — extracted from the existing profitability engine rubric.

Normalizes the -10 to +10 score to 0.0 to 1.0 for composite scoring.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FinancialScore:
    score: Optional[float]  # 0.0 to 1.0 (None if no rate)
    raw_score: Optional[int]  # -10 to +10 (original rubric)
    action: str  # BOOK IT / CONSIDER / NEGOTIATE / PASS
    components: dict  # Breakdown of score components


def score_financial(
    margin_pct: Optional[float],
    all_in_rpm: Optional[float],
    deadhead_pct: float,
    loaded_miles: float,
    detention_hours: float,
    target_margin: float = 25.0,
    min_margin: float = 15.0,
    max_deadhead: float = 15.0,
) -> FinancialScore:
    """Score a load on financial metrics.

    Uses the same rubric as the existing profitability_engine.py
    but normalizes output to 0.0-1.0 range.
    """
    if margin_pct is None or all_in_rpm is None:
        return FinancialScore(score=None, raw_score=None, action="NEGOTIATE", components={})

    raw = 0
    components = {}

    # Margin scoring
    if margin_pct >= target_margin:
        raw += 4
        components["margin"] = 4
    elif margin_pct >= min_margin:
        raw += 2
        components["margin"] = 2
    elif margin_pct >= 5:
        components["margin"] = 0
    elif margin_pct >= 0:
        raw -= 2
        components["margin"] = -2
    else:
        raw -= 5
        components["margin"] = -5

    # RPM scoring
    if all_in_rpm >= 3.00:
        raw += 2
        components["rpm"] = 2
    elif all_in_rpm >= 2.50:
        raw += 1
        components["rpm"] = 1
    elif all_in_rpm >= 2.00:
        components["rpm"] = 0
    else:
        raw -= 2
        components["rpm"] = -2

    # Deadhead
    if deadhead_pct <= 5:
        raw += 2
        components["deadhead"] = 2
    elif deadhead_pct <= max_deadhead:
        raw += 1
        components["deadhead"] = 1
    elif deadhead_pct <= 25:
        raw -= 1
        components["deadhead"] = -1
    else:
        raw -= 3
        components["deadhead"] = -3

    # Mileage sweet spot
    if 150 <= loaded_miles <= 300:
        raw += 1
        components["mileage"] = 1
    elif loaded_miles < 80:
        raw -= 1
        components["mileage"] = -1
    else:
        components["mileage"] = 0

    # Detention
    if detention_hours > 2:
        raw -= 1
        components["detention"] = -1
    else:
        components["detention"] = 0

    raw = max(-10, min(10, raw))

    # Normalize to 0-1: (-10 maps to 0, +10 maps to 1)
    normalized = (raw + 10) / 20

    # Action tier
    if raw >= 5:
        action = "BOOK IT"
    elif raw >= 2:
        action = "CONSIDER"
    elif raw >= 0:
        action = "NEGOTIATE"
    else:
        action = "PASS"

    return FinancialScore(
        score=round(normalized, 3),
        raw_score=raw,
        action=action,
        components=components,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add scoring/__init__.py scoring/financial_scorer.py tests/test_financial_scorer.py
git commit -m "feat: extract financial scorer from existing engine"
```

---

### Task 10: Lane Scorer

**Files:**
- Create: `scoring/lane_scorer.py`
- Create: `tests/test_lane_scorer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_lane_scorer.py
import os
import pytest
from database import init_db, get_db
from scoring.lane_scorer import score_lane, LaneScore

TEST_DB = "test_lane_scorer.db"


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestScoreLane:
    def test_no_history_returns_neutral(self):
        """Day 0: no lane data → neutral score (0.5)."""
        result = score_lane("Columbus", "OH", "Pittsburgh", "PA", 600.0, db_path=TEST_DB)
        assert isinstance(result, LaneScore)
        assert result.score == 0.5
        assert result.data_points == 0

    def test_above_average_rate_scores_high(self):
        """Rate above lane average → score > 0.5."""
        with get_db(TEST_DB) as conn:
            conn.execute("""
                INSERT INTO lane_history (origin_city, origin_state, destination_city,
                    destination_state, avg_rate, load_count, updated_at)
                VALUES ('Columbus', 'OH', 'Pittsburgh', 'PA', 500.0, 10, '2026-03-16')
            """)
            conn.commit()

        result = score_lane("Columbus", "OH", "Pittsburgh", "PA", 600.0, db_path=TEST_DB)
        assert result.score > 0.5
        assert result.vs_average_pct > 0

    def test_below_average_rate_scores_low(self):
        """Rate below lane average → score < 0.5."""
        with get_db(TEST_DB) as conn:
            conn.execute("""
                INSERT INTO lane_history (origin_city, origin_state, destination_city,
                    destination_state, avg_rate, load_count, updated_at)
                VALUES ('Columbus', 'OH', 'Pittsburgh', 'PA', 700.0, 10, '2026-03-16')
            """)
            conn.commit()

        result = score_lane("Columbus", "OH", "Pittsburgh", "PA", 500.0, db_path=TEST_DB)
        assert result.score < 0.5

    def test_falls_back_to_state_level(self):
        """< 3 city-level data points → use state-to-state."""
        with get_db(TEST_DB) as conn:
            # Only 2 city-level loads
            conn.execute("""
                INSERT INTO lane_history (origin_city, origin_state, destination_city,
                    destination_state, avg_rate, load_count, updated_at)
                VALUES ('Columbus', 'OH', 'Pittsburgh', 'PA', 500.0, 2, '2026-03-16')
            """)
            # State-level has more
            conn.execute("""
                INSERT INTO lane_history (origin_city, origin_state, destination_city,
                    destination_state, avg_rate, load_count, updated_at)
                VALUES ('Cincinnati', 'OH', 'Philadelphia', 'PA', 550.0, 15, '2026-03-16')
            """)
            conn.commit()

        result = score_lane("Columbus", "OH", "Pittsburgh", "PA", 600.0, db_path=TEST_DB)
        # Should use state-level aggregation since city-level < 3
        assert result.level == "state"
        assert result.data_points >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement scoring/lane_scorer.py**

```python
# scoring/lane_scorer.py
"""Lane-aware scoring based on historical rate/margin data."""

from dataclasses import dataclass
from typing import Optional
from database import get_db, DEFAULT_DB_PATH

MIN_CITY_DATA_POINTS = 3


@dataclass
class LaneScore:
    score: float  # 0.0 to 1.0
    data_points: int
    avg_rate: Optional[float]
    vs_average_pct: Optional[float]  # % above/below average
    level: str  # "city", "state", or "none"


def score_lane(
    origin_city: str,
    origin_state: str,
    dest_city: str,
    dest_state: str,
    rate_total: Optional[float],
    db_path: str = DEFAULT_DB_PATH,
) -> LaneScore:
    """Score a load based on lane history.

    Falls back from city-to-city → state-to-state → neutral.
    """
    if rate_total is None:
        return LaneScore(score=0.5, data_points=0, avg_rate=None, vs_average_pct=None, level="none")

    # Try city-to-city first
    avg, count = _get_lane_avg(origin_city, origin_state, dest_city, dest_state, db_path)

    if count >= MIN_CITY_DATA_POINTS:
        vs_avg = ((rate_total - avg) / avg * 100) if avg > 0 else 0
        score = _pct_to_score(vs_avg)
        return LaneScore(score=score, data_points=count, avg_rate=avg, vs_average_pct=round(vs_avg, 1), level="city")

    # Fall back to state-to-state aggregation
    avg, count = _get_state_avg(origin_state, dest_state, db_path)

    if count >= MIN_CITY_DATA_POINTS:
        vs_avg = ((rate_total - avg) / avg * 100) if avg > 0 else 0
        score = _pct_to_score(vs_avg)
        return LaneScore(score=score, data_points=count, avg_rate=avg, vs_average_pct=round(vs_avg, 1), level="state")

    # No data — neutral
    return LaneScore(score=0.5, data_points=count, avg_rate=avg, vs_average_pct=None, level="none")


def _get_lane_avg(o_city, o_state, d_city, d_state, db_path):
    with get_db(db_path) as conn:
        row = conn.execute("""
            SELECT avg_rate, load_count FROM lane_history
            WHERE origin_city = ? AND origin_state = ?
              AND destination_city = ? AND destination_state = ?
        """, (o_city, o_state, d_city, d_state)).fetchone()
    if row:
        return row[0] or 0, row[1] or 0
    return 0, 0


def _get_state_avg(o_state, d_state, db_path):
    with get_db(db_path) as conn:
        row = conn.execute("""
            SELECT AVG(avg_rate), SUM(load_count) FROM lane_history
            WHERE origin_state = ? AND destination_state = ?
        """, (o_state, d_state)).fetchone()
    if row and row[0]:
        return row[0], int(row[1] or 0)
    return 0, 0


def _pct_to_score(vs_average_pct: float) -> float:
    """Convert % above/below average to 0-1 score.

    +20% above avg → 0.8
    +10% → 0.7
    0% (at avg) → 0.5
    -10% → 0.3
    -20% → 0.2
    """
    score = 0.5 + (vs_average_pct / 100) * 1.5
    return round(max(0.0, min(1.0, score)), 3)
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add scoring/lane_scorer.py tests/test_lane_scorer.py
git commit -m "feat: add lane scorer with city/state fallback"
```

---

### Task 11: Broker Scorer

**Files:**
- Create: `scoring/broker_scorer.py`
- Create: `tests/test_broker_scorer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_broker_scorer.py
import os
import pytest
from database import init_db, get_db
from scoring.broker_scorer import score_broker, BrokerScore

TEST_DB = "test_broker_scorer.db"


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestScoreBroker:
    def test_unknown_broker_returns_neutral(self):
        result = score_broker("Unknown Co", db_path=TEST_DB)
        assert result.score == 0.5
        assert result.grade == "U"

    def test_reliable_broker_scores_high(self):
        with get_db(TEST_DB) as conn:
            conn.execute("""
                INSERT INTO broker_history (broker_name, avg_detention_hours,
                    tonu_count, loads_completed, loads_seen, rate_accuracy_pct,
                    ontime_pickup_pct, reliability_grade, updated_at)
                VALUES ('TQL', 0.5, 0, 20, 25, 98.0, 95.0, 'A', '2026-03-16')
            """)
            conn.commit()

        result = score_broker("TQL", db_path=TEST_DB)
        assert result.score > 0.6
        assert result.grade == "A"

    def test_unreliable_broker_scores_low(self):
        with get_db(TEST_DB) as conn:
            conn.execute("""
                INSERT INTO broker_history (broker_name, avg_detention_hours,
                    tonu_count, loads_completed, loads_seen, rate_accuracy_pct,
                    ontime_pickup_pct, reliability_grade, updated_at)
                VALUES ('Bad Broker', 4.5, 5, 3, 10, 75.0, 50.0, 'F', '2026-03-16')
            """)
            conn.commit()

        result = score_broker("Bad Broker", db_path=TEST_DB)
        assert result.score < 0.4
        assert result.grade == "F"

    def test_empty_broker_name_returns_neutral(self):
        result = score_broker("", db_path=TEST_DB)
        assert result.score == 0.5
```

- [ ] **Step 2-5: Implement, test, commit** (same pattern as above)

Implementation: `scoring/broker_scorer.py` — looks up broker in `broker_history` table, maps grade to score (A=0.9, B=0.7, C=0.5, D=0.3, F=0.1, U=0.5).

---

### Task 12: Strategic Scorer

**Files:**
- Create: `scoring/strategic_scorer.py`
- Create: `tests/test_strategic_scorer.py`

Uses `city_demand_tiers` table. Tier 1 destination = 0.8, Tier 2 = 0.5, Tier 3 = 0.3. Adjusts for proximity to home base (closer to home after delivery = small bonus).

---

### Task 13: Composite Scorer

**Files:**
- Create: `scoring/composite_scorer.py`
- Create: `tests/test_composite_scorer.py`

Loads `scorer_config` from DB, calls all four sub-scorers, computes weighted sum, returns final score and action tier.

---

### Task 13.5: Wire New Scoring + Cost Model into app.py

**Files:**
- Modify: `app.py`

This is a critical integration task. After the composite scorer is built, replace all calls to the old `score_load()` in `app.py` with the new pipeline:

1. Load `CostConfig` from `cost_config` table (not hardcoded `DEFAULT_ASSUMPTIONS`)
2. Call `calculate_load_cost()` from `costs/cost_model.py` for financial metrics
3. Call `composite_scorer.score()` which internally calls all four sub-scorers
4. Return the combined result

Also extract the repeated 35-field INSERT statement into a `database.py` helper: `save_scored_load(conn, scored_dict) -> int`

Update `ingest_complete`, `create_load`, and `parse_and_score` endpoints to all use this new pipeline.

---

## Chunk 4: Chain Optimizer, Scenario Engine, Watchlist

### File Structure (Chunk 4)

- Create: `optimizer/__init__.py`
- Create: `optimizer/hos_model.py` — FMCSA HOS state tracking
- Create: `optimizer/chain_optimizer.py` — improved beam search
- Create: `optimizer/scenario_engine.py` — dwell-time scenario branches
- Create: `optimizer/watchlist.py` — committed + watchlist model
- Create: `tests/test_hos_model.py`
- Create: `tests/test_chain_optimizer.py`
- Create: `tests/test_scenario_engine.py`
- Create: `tests/test_watchlist.py`

---

### Task 14: HOS Model (`optimizer/hos_model.py`)

Full FMCSA HOS state machine: 11-hr drive, 14-hr on-duty window, 10-hr rest, 30-min break after 8 driving hours, 70-hr/8-day weekly cap. Used by the chain optimizer to check feasibility.

---

### Task 15: Chain Optimizer (`optimizer/chain_optimizer.py`)

Rebuild beam search with:
- HOS model integration (Task 14)
- Repositioning value from strategic scorer
- Wider beam width (configurable, default 5)
- Composite scorer for ranking

---

### Task 16: Scenario Engine (`optimizer/scenario_engine.py`)

For each leg, generates 4 dwell-time branches (quick/normal/slow/detention). Each branch re-runs the optimizer with updated HOS and time. Returns a scenario tree dict.

---

### Task 17: Watchlist Model (`optimizer/watchlist.py`)

Manages committed vs. watchlist loads. Endpoint `POST /api/watchlist/resolve` takes actual dwell time, returns matching scenario recommendations.

---

### Task 18: Wire Optimizer + Watchlist API Endpoints

Update `app.py` with:
- Updated `POST /api/optimize` using new chain optimizer + scenario engine
- `GET /api/watchlist` and `POST /api/watchlist`
- `POST /api/watchlist/resolve`

---

## Chunk 5: Analytics, Feedback, and Remaining Endpoints

### Task 19: Lane History (`analytics/lane_history.py`)

Rebuild `lane_history` table from loads. Exponential decay (90-day half-life). Called after each load save and on a rebuild endpoint.

---

### Task 20: Broker History (`analytics/broker_history.py`)

Rebuild `broker_history` from `load_feedback`. Calculate grades. Called after feedback submission.

---

### Task 21: Load Feedback + Outcome Endpoints

- `POST /api/loads/{id}/feedback` — submit post-load actuals
- `PATCH /api/loads/{id}/outcome` — set booked/passed/expired/watchlist_skipped
- `GET /api/analytics/lanes` — lane stats
- `GET /api/analytics/brokers` — broker grades
- `GET /api/duplicates` and `POST /api/duplicates` — manage duplicates
- `GET/PUT /api/config/demand-tiers` — city demand tiers

---

### Task 22: Fuel Service (`costs/fuel_service.py`)

Fetch diesel prices from EIA API by PADD region. Cache in `fuel_prices` table. Fallback to static default.

---

### Task 23: Toll Service (`costs/toll_service.py`)

Look up toll corridors for a route. Match route interstates against `toll_corridors` table. Return estimated toll cost.

---

## Chunk 6: OCR Parser (Lower Priority)

### Task 24: OCR Parser (`ingestion/ocr_parser.py`)

Tesseract-based screenshot parsing. Extracts text, runs through paste parser, wraps fields with confidence scores via ParsedField.

### Task 25: Screenshot Ingestion Endpoint

`POST /api/ingest/screenshot` — accepts image upload, runs OCR, returns parsed fields + gaps.

---

## Chunk 7: Integration Testing + Cleanup

### Task 26: End-to-End Integration Tests

Full flow tests: paste load → score → optimize with scenarios → submit feedback → verify analytics updated.

### Task 27: Remove Old Code

- Remove `greedy_chain()` from `profitability_engine.py`
- Remove inline `init_db()` and `get_db()` from `app.py` (replaced by `database.py`)
- Update `app.py` imports to use new modules
- Verify all existing tests still pass

### Task 28: Final Test Suite Run + Cleanup

Run full test suite, fix any failures, verify all endpoints work via manual testing with `http://localhost:8000/docs`.
