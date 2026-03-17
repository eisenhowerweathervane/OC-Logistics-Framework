"""Centralized database initialization, migration, and seed data management.

Provides:
- get_db(db_path)    — context manager returning a sqlite3 connection
- init_db(db_path)   — idempotent table creation + migration
- seed_defaults(db_path) — idempotent seed data insertion
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DEFAULT_DB_PATH = "loads.db"


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------

@contextmanager
def get_db(db_path: str = DEFAULT_DB_PATH):
    """Context manager that yields a sqlite3 connection with Row factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Table DDL
# ---------------------------------------------------------------------------

_TABLES_SQL = """
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

    -- New columns
    outcome TEXT,
    duplicate_of INTEGER,
    source TEXT,

    -- Deduplication
    UNIQUE(origin_city, origin_state, destination_city, destination_state,
           pickup_date, broker_name, rate_total, mileage)
);

CREATE TABLE IF NOT EXISTS email_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT UNIQUE,
    subject TEXT,
    sender TEXT,
    received_at TEXT,
    processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    loads_found INTEGER,
    status TEXT
);

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
);

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
);

CREATE TABLE IF NOT EXISTS load_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    load_id INTEGER REFERENCES loads(id),
    actual_dwell_hours REAL,
    actual_rate_paid REAL,
    actual_toll_cost REAL,
    detention_hours REAL DEFAULT 0.0,
    ontime_pickup BOOLEAN,
    issues TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accessorials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    load_id INTEGER REFERENCES loads(id),
    type TEXT,
    amount REAL,
    notes TEXT
);

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
);

CREATE TABLE IF NOT EXISTS scorer_config (
    id INTEGER PRIMARY KEY,
    financial_weight REAL DEFAULT 0.50,
    lane_weight REAL DEFAULT 0.15,
    broker_weight REAL DEFAULT 0.15,
    strategic_weight REAL DEFAULT 0.20,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS toll_corridors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    corridor_name TEXT,
    interstate TEXT,
    states TEXT,
    cost_per_mile REAL,
    last_updated TEXT
);

CREATE TABLE IF NOT EXISTS fuel_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    padd_region TEXT,
    price_per_gallon REAL,
    effective_date TEXT,
    fetched_at TEXT
);

CREATE TABLE IF NOT EXISTS city_demand_tiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT,
    state TEXT,
    tier INTEGER,
    source TEXT DEFAULT 'seed',
    updated_at TEXT
);
"""


# ---------------------------------------------------------------------------
# Migration helpers
# ---------------------------------------------------------------------------

def _needs_loads_migration(conn: sqlite3.Connection) -> bool:
    """Return True if the loads table exists but lacks the 'outcome' column."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='loads'"
    ).fetchall()
    if not rows:
        return False
    cols = conn.execute("PRAGMA table_info(loads)").fetchall()
    col_names = {r["name"] for r in cols}
    return "outcome" not in col_names


def _migrate_loads(conn: sqlite3.Connection) -> None:
    """Rebuild loads table with new columns, preserving existing data."""
    conn.execute("ALTER TABLE loads RENAME TO loads_old")

    # Create new loads table (extract just the CREATE TABLE for loads)
    conn.executescript(
        _TABLES_SQL.split("CREATE TABLE IF NOT EXISTS email_log")[0]
    )

    # Copy data from old table
    old_cols = conn.execute("PRAGMA table_info(loads_old)").fetchall()
    old_col_names = [r["name"] for r in old_cols if r["name"] != "id"]

    cols_str = ", ".join(old_col_names)
    conn.execute(
        f"INSERT OR IGNORE INTO loads ({cols_str}, source) "
        f"SELECT {cols_str}, 'email' FROM loads_old"
    )
    conn.execute("DROP TABLE loads_old")
    conn.commit()


# ---------------------------------------------------------------------------
# init_db — idempotent table creation + migration
# ---------------------------------------------------------------------------

def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Create all tables. Safe to call multiple times (idempotent).

    If the loads table already exists without the 'outcome' column,
    performs a full table rebuild migrating existing data.
    """
    with get_db(db_path) as conn:
        if _needs_loads_migration(conn):
            _migrate_loads(conn)
        conn.executescript(_TABLES_SQL)
        conn.commit()


# ---------------------------------------------------------------------------
# seed_defaults — idempotent seed data
# ---------------------------------------------------------------------------

def seed_defaults(db_path: str = DEFAULT_DB_PATH) -> None:
    """Insert default seed data. Safe to call multiple times (idempotent)."""
    now = datetime.now(timezone.utc).isoformat()

    with get_db(db_path) as conn:
        # -- cost_config defaults (id=1) ------------------------------------
        conn.execute(
            """INSERT OR IGNORE INTO cost_config (id, updated_at)
               VALUES (1, ?)""",
            (now,),
        )

        # -- scorer_config defaults (id=1) ----------------------------------
        conn.execute(
            """INSERT OR IGNORE INTO scorer_config (id, updated_at)
               VALUES (1, ?)""",
            (now,),
        )

        # -- toll corridors -------------------------------------------------
        toll_data = [
            ("Ohio Turnpike", "I-80/I-90", "OH", 0.15),
            ("PA Turnpike", "I-76", "PA", 0.45),
            ("NJ Turnpike", "I-95", "NJ", 0.25),
            ("NY Thruway", "I-90", "NY", 0.12),
            ("Indiana Toll Road", "I-80/I-90", "IN", 0.20),
            ("WV Turnpike", "I-77", "WV", 0.10),
            ("Florida Turnpike", "FL Turnpike", "FL", 0.12),
        ]
        for name, interstate, states, cpm in toll_data:
            conn.execute(
                """INSERT INTO toll_corridors (corridor_name, interstate, states, cost_per_mile, last_updated)
                   SELECT ?, ?, ?, ?, ?
                   WHERE NOT EXISTS (
                       SELECT 1 FROM toll_corridors WHERE corridor_name = ?
                   )""",
                (name, interstate, states, cpm, now, name),
            )

        # -- city demand tiers ----------------------------------------------
        tier_data = {
            1: [
                ("Atlanta", "GA"), ("Chicago", "IL"), ("Dallas", "TX"),
                ("Houston", "TX"), ("Memphis", "TN"), ("Nashville", "TN"),
                ("Columbus", "OH"), ("Indianapolis", "IN"), ("Charlotte", "NC"),
                ("Jacksonville", "FL"), ("Louisville", "KY"),
            ],
            2: [
                ("Cleveland", "OH"), ("Pittsburgh", "PA"), ("Cincinnati", "OH"),
                ("Detroit", "MI"), ("Buffalo", "NY"), ("Philadelphia", "PA"),
                ("Baltimore", "MD"), ("Raleigh", "NC"), ("Tampa", "FL"),
                ("St. Louis", "MO"), ("Kansas City", "MO"), ("Milwaukee", "WI"),
                ("Minneapolis", "MN"), ("Denver", "CO"), ("New Orleans", "LA"),
                ("Birmingham", "AL"), ("Knoxville", "TN"), ("Grand Rapids", "MI"),
            ],
            3: [
                ("Erie", "PA"), ("Toledo", "OH"), ("Akron", "OH"),
                ("Dayton", "OH"), ("Fort Wayne", "IN"), ("Lexington", "KY"),
                ("Mobile", "AL"), ("Little Rock", "AR"), ("Oklahoma City", "OK"),
            ],
        }
        for tier, cities in tier_data.items():
            for city, state in cities:
                conn.execute(
                    """INSERT INTO city_demand_tiers (city, state, tier, source, updated_at)
                       SELECT ?, ?, ?, 'seed', ?
                       WHERE NOT EXISTS (
                           SELECT 1 FROM city_demand_tiers WHERE city = ? AND state = ?
                       )""",
                    (city, state, tier, now, city, state),
                )

        conn.commit()
