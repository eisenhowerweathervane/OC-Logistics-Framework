"""
Load Profitability API - Phase 3
FastAPI backend for the Stratus Dispatch Intelligence frontend.
"""

import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Local imports
from config import DATABASE_PATH, API_HOST, API_PORT, DEBUG
from database import init_db, get_db, seed_defaults
from models import ScorerConfig, ParsedLoad
from dat_email_parser import parse_load_email
from profitability_engine import (
    score_load, optimize_chain, greedy_chain,
    DEFAULT_ASSUMPTIONS, CITIES, is_city_known
)
from distance_service import get_distance, CITY_COORDS
from ingestion.dat_paste_parser import parse_dat_paste
from ingestion.gap_resolver import resolve_gaps
from ingestion.duplicate_detector import check_duplicate


# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="Stratus Dispatch Intelligence API",
    description="Load profitability scoring and route optimization",
    version="1.0.0"
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class LoadInput(BaseModel):
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    rate_total: Optional[float] = None
    mileage: Optional[int] = None
    deadhead_miles: Optional[int] = None
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


class AssumptionsInput(BaseModel):
    fuel_price: float = 3.85
    mpg: float = 6.5
    driver_pay: float = 0.55
    truck_lease: float = 0.22
    insurance: float = 0.08
    maint_reserve: float = 0.00
    overhead: float = 0.04
    factoring_fee: float = 3.0
    detention_rate: float = 50.0
    max_deadhead_pct: float = 15.0
    min_margin_pct: float = 15.0
    target_margin_pct: float = 25.0
    avg_speed: float = 52.0
    load_unload_time: float = 1.5
    home_base: str = "Cleveland, OH"


class EmailInput(BaseModel):
    raw_text: str


class OptimizeInput(BaseModel):
    load_ids: list[int]
    start_city: str = "Cleveland, OH"
    hos_remaining: float = 11.0
    days_away: int = 0
    assumptions: Optional[AssumptionsInput] = None


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


class PasteInput(BaseModel):
    text: str


class CompleteInput(BaseModel):
    load: dict
    fills: dict = {}
    save: bool = False


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db(DATABASE_PATH)
    seed_defaults(DATABASE_PATH)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Stratus Dispatch Intelligence API"}


@app.get("/api/loads")
async def get_loads(
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "score",
    sort_order: str = "desc",
    action: Optional[str] = None
):
    """Get all loads, sorted by score (highest first)."""
    valid_sort_fields = ["score", "profit", "margin_pct", "all_in_rpm", "created_at"]
    if sort_by not in valid_sort_fields:
        sort_by = "score"

    order = "DESC" if sort_order.lower() == "desc" else "ASC"

    query = f"SELECT * FROM loads"
    params = []

    if action:
        query += " WHERE action = ?"
        params.append(action.upper())

    query += f" ORDER BY {sort_by} {order} NULLS LAST LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db(DATABASE_PATH) as conn:
        rows = conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            load = dict(row)
            # Parse warnings from JSON string back to list
            if load.get("warnings") and isinstance(load["warnings"], str):
                try:
                    load["warnings"] = json.loads(load["warnings"])
                except json.JSONDecodeError:
                    load["warnings"] = []
            results.append(load)
        return results


@app.get("/api/loads/{load_id}")
async def get_load(load_id: int):
    """Get a single load by ID."""
    with get_db(DATABASE_PATH) as conn:
        row = conn.execute("SELECT * FROM loads WHERE id = ?", (load_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Load not found")
        load = dict(row)
        # Parse warnings from JSON string back to list
        if load.get("warnings") and isinstance(load["warnings"], str):
            try:
                load["warnings"] = json.loads(load["warnings"])
            except json.JSONDecodeError:
                load["warnings"] = []
        return load


@app.post("/api/loads")
async def create_load(load: LoadInput, assumptions: Optional[AssumptionsInput] = None):
    """Create a new load and score it."""
    load_dict = load.dict()

    # Convert assumptions to the format expected by score_load
    config = None
    if assumptions:
        config = {
            "fuel_price": assumptions.fuel_price,
            "mpg": assumptions.mpg,
            "driver_pay": assumptions.driver_pay,
            "truck_lease": assumptions.truck_lease,
            "insurance": assumptions.insurance,
            "maint_reserve": assumptions.maint_reserve,
            "overhead": assumptions.overhead,
            "factoring_fee": assumptions.factoring_fee,
            "detention_rate": assumptions.detention_rate,
            "max_deadhead_pct": assumptions.max_deadhead_pct,
            "min_margin_pct": assumptions.min_margin_pct,
            "target_margin_pct": assumptions.target_margin_pct,
            "avg_speed": assumptions.avg_speed,
            "load_unload_time": assumptions.load_unload_time,
            "home_base": assumptions.home_base,
        }

    # Score the load
    scored = score_load(load_dict, assumptions=config)

    # Insert into database
    with get_db(DATABASE_PATH) as conn:
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
                    score, action, floor_rpm, warnings
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scored["origin_city"], scored["origin_state"],
                scored["destination_city"], scored["destination_state"],
                scored["rate_total"], scored.get("rpm"), scored["mileage"],
                scored["deadhead_miles"], scored["weight"],
                scored["equipment_type"], scored["commodity"],
                scored["pickup_date"], scored["pickup_time_window"],
                scored["delivery_date"], scored["delivery_time_window"],
                scored["broker_name"], scored["broker_mc_number"],
                scored["contact_phone"], scored["contact_email"],
                scored["load_number"], scored.get("notes", ""),
                scored["total_miles"], scored["total_cost"],
                scored["net_revenue"], scored["profit"], scored["margin_pct"],
                scored["rpm"], scored["all_in_rpm"],
                scored["drive_hours"], scored["total_hours"], scored["profit_per_hour"],
                scored["score"], scored["action"], scored["floor_rpm"],
                json.dumps(scored["warnings"])
            ))
            conn.commit()
            scored["id"] = cursor.lastrowid
        except sqlite3.IntegrityError:
            # Return existing load instead of error
            existing = conn.execute(
                """SELECT * FROM loads WHERE origin_city = ? AND origin_state = ?
                   AND destination_city = ? AND destination_state = ?
                   AND COALESCE(pickup_date, '') = COALESCE(?, '')
                   AND COALESCE(broker_name, '') = COALESCE(?, '')""",
                (scored["origin_city"], scored["origin_state"],
                 scored["destination_city"], scored["destination_state"],
                 scored["pickup_date"], scored["broker_name"])
            ).fetchone()
            if existing:
                scored["id"] = existing["id"]
            else:
                raise HTTPException(status_code=409, detail="Duplicate load (same route/date/broker)")

    return scored


@app.delete("/api/loads/{load_id}")
async def delete_load(load_id: int):
    """Delete a load by ID."""
    with get_db(DATABASE_PATH) as conn:
        result = conn.execute("DELETE FROM loads WHERE id = ?", (load_id,))
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Load not found")
    return {"status": "deleted", "id": load_id}


@app.post("/api/parse")
async def parse_email(email: EmailInput):
    """Parse a raw DAT email and return extracted loads (without saving)."""
    loads = parse_load_email(email.raw_text)
    return {"loads": loads, "count": len(loads)}


@app.post("/api/parse-and-score")
async def parse_and_score(
    email: EmailInput,
    assumptions: Optional[AssumptionsInput] = None,
    save: bool = False
):
    """Parse a raw DAT email, score all loads, and optionally save to database."""
    loads = parse_load_email(email.raw_text)

    config = None
    if assumptions:
        config = assumptions.dict()

    scored_loads = []
    for load in loads:
        scored = score_load(load, assumptions=config)
        scored_loads.append(scored)

    if save:
        saved_count = 0
        with get_db(DATABASE_PATH) as conn:
            for scored in scored_loads:
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
                            score, action, floor_rpm, warnings
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        scored["origin_city"], scored["origin_state"],
                        scored["destination_city"], scored["destination_state"],
                        scored["rate_total"], scored.get("rpm"),
                        scored["mileage"], scored["deadhead_miles"], scored["weight"],
                        scored["equipment_type"], scored["commodity"],
                        scored["pickup_date"], scored["pickup_time_window"],
                        scored["delivery_date"], scored["delivery_time_window"],
                        scored["broker_name"], scored["broker_mc_number"],
                        scored["contact_phone"], scored["contact_email"],
                        scored["load_number"], scored.get("notes", ""),
                        scored["total_miles"], scored["total_cost"],
                        scored["net_revenue"], scored["profit"], scored["margin_pct"],
                        scored["rpm"], scored["all_in_rpm"],
                        scored["drive_hours"], scored["total_hours"], scored["profit_per_hour"],
                        scored["score"], scored["action"], scored["floor_rpm"],
                        json.dumps(scored["warnings"])
                    ))
                    scored["id"] = cursor.lastrowid
                    saved_count += 1
                except sqlite3.IntegrityError:
                    # Duplicate, skip
                    pass
            conn.commit()

        return {
            "loads": scored_loads,
            "count": len(scored_loads),
            "saved": saved_count,
            "duplicates": len(scored_loads) - saved_count
        }

    return {"loads": scored_loads, "count": len(scored_loads)}


@app.post("/api/score")
async def score_single_load(load: LoadInput, assumptions: Optional[AssumptionsInput] = None):
    """Score a single load without saving."""
    config = None
    if assumptions:
        config = assumptions.dict()

    scored = score_load(load.dict(), assumptions=config)
    return scored


@app.post("/api/optimize")
async def optimize_loads(request: OptimizeInput):
    """Run chain optimizer on selected loads."""
    # Fetch loads from database
    with get_db(DATABASE_PATH) as conn:
        placeholders = ",".join("?" * len(request.load_ids))
        rows = conn.execute(
            f"SELECT * FROM loads WHERE id IN ({placeholders})",
            request.load_ids
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No loads found")

    # Convert to dicts
    loads = [dict(row) for row in rows]

    # Get assumptions
    config = None
    if request.assumptions:
        config = request.assumptions.dict()

    # Run optimizer
    optimized = optimize_chain(
        loads,
        start_city=request.start_city,
        hos_remaining=request.hos_remaining,
        days_away=request.days_away,
        assumptions=config
    )

    # Run greedy baseline for comparison
    greedy = greedy_chain(
        loads,
        start_city=request.start_city,
        hos_remaining=request.hos_remaining,
        days_away=request.days_away,
        assumptions=config
    )

    return {
        "optimized": optimized,
        "greedy": greedy,
        "profit_difference": optimized["summary"]["total_profit"] - greedy["summary"]["total_profit"]
    }


@app.get("/api/distance")
async def get_city_distance(origin: str, destination: str):
    """Get distance between two cities."""
    distance, source = get_distance(origin, destination)
    return {
        "origin": origin,
        "destination": destination,
        "distance_miles": distance,
        "source": source,
        "origin_known": is_city_known(origin),
        "destination_known": is_city_known(destination)
    }


@app.get("/api/cities")
async def get_cities():
    """Get list of known cities."""
    return {"cities": list(CITY_COORDS.keys())}


@app.get("/api/assumptions")
async def get_default_assumptions():
    """Get default cost assumptions."""
    return DEFAULT_ASSUMPTIONS


@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics."""
    with get_db(DATABASE_PATH) as conn:
        total = conn.execute("SELECT COUNT(*) FROM loads").fetchone()[0]
        by_action = conn.execute("""
            SELECT action, COUNT(*) as count
            FROM loads
            GROUP BY action
        """).fetchall()

        avg_profit = conn.execute(
            "SELECT AVG(profit) FROM loads WHERE profit IS NOT NULL"
        ).fetchone()[0] or 0

        avg_margin = conn.execute(
            "SELECT AVG(margin_pct) FROM loads WHERE margin_pct IS NOT NULL"
        ).fetchone()[0] or 0

    return {
        "total_loads": total,
        "by_action": {row["action"]: row["count"] for row in by_action},
        "avg_profit": round(avg_profit, 2),
        "avg_margin": round(avg_margin, 2)
    }


# =============================================================================
# INGESTION ENDPOINTS
# =============================================================================

@app.post("/api/ingest/paste")
async def ingest_paste(input: PasteInput):
    """Parse pasted DAT text, resolve gaps, and check for duplicates."""
    loads = parse_dat_paste(input.text)

    results = []
    all_gaps = []
    duplicate_count = 0

    for load in loads:
        gap_report = resolve_gaps(load)
        dup_result = check_duplicate(load, DATABASE_PATH)

        load_data = load.to_dict()
        load_data["gaps"] = {
            "missing_required": gap_report.missing_required,
            "missing_optional": gap_report.missing_optional,
            "is_complete": gap_report.is_complete,
            "summary": gap_report.summary,
        }
        load_data["duplicate"] = {
            "is_duplicate": dup_result.is_duplicate,
            "matching_load_id": dup_result.matching_load_id,
            "message": dup_result.message,
        }

        if not gap_report.is_complete:
            all_gaps.extend(gap_report.missing_required)
        if dup_result.is_duplicate:
            duplicate_count += 1

        results.append(load_data)

    return {
        "loads": results,
        "count": len(results),
        "gaps": all_gaps,
        "duplicates": duplicate_count,
    }


@app.post("/api/ingest/complete")
async def ingest_complete(input: CompleteInput):
    """Complete and optionally save a load."""
    merged = {**input.load, **input.fills}

    if "source" not in merged or not merged["source"]:
        merged["source"] = "manual"

    parsed = ParsedLoad(**merged)
    scored = score_load(parsed.to_dict())

    if input.save:
        with get_db(DATABASE_PATH) as conn:
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
                    scored["rate_total"], scored.get("rpm"),
                    scored["mileage"], scored["deadhead_miles"], scored["weight"],
                    scored["equipment_type"], scored["commodity"],
                    scored["pickup_date"], scored["pickup_time_window"],
                    scored["delivery_date"], scored["delivery_time_window"],
                    scored["broker_name"], scored["broker_mc_number"],
                    scored["contact_phone"], scored["contact_email"],
                    scored["load_number"], scored.get("notes", ""),
                    scored["total_miles"], scored["total_cost"],
                    scored["net_revenue"], scored["profit"], scored["margin_pct"],
                    scored["rpm"], scored["all_in_rpm"],
                    scored["drive_hours"], scored["total_hours"], scored["profit_per_hour"],
                    scored["score"], scored["action"], scored["floor_rpm"],
                    json.dumps(scored["warnings"]),
                    merged.get("source", "manual"),
                ))
                conn.commit()
                return {"saved": True, "id": cursor.lastrowid, "scored": scored}
            except sqlite3.IntegrityError:
                return {"saved": False, "error": "Duplicate load", "scored": scored}

    return {"saved": False, "id": None, "scored": scored}


# =============================================================================
# COST / SCORER CONFIG ENDPOINTS
# =============================================================================

@app.get("/api/config/costs")
async def get_cost_config():
    """Read cost configuration from database."""
    with get_db(DATABASE_PATH) as conn:
        row = conn.execute("SELECT * FROM cost_config WHERE id = 1").fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Cost config not found")
        return dict(row)


@app.put("/api/config/costs")
async def update_cost_config(config: CostConfigInput):
    """Update cost configuration (partial update — only non-None fields)."""
    updates = {k: v for k, v in config.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values())

    with get_db(DATABASE_PATH) as conn:
        conn.execute(
            f"UPDATE cost_config SET {set_clause} WHERE id = 1",
            values,
        )
        conn.commit()
        row = conn.execute("SELECT * FROM cost_config WHERE id = 1").fetchone()
        return dict(row)


@app.get("/api/config/scorer")
async def get_scorer_config():
    """Read scorer configuration from database."""
    with get_db(DATABASE_PATH) as conn:
        row = conn.execute("SELECT * FROM scorer_config WHERE id = 1").fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Scorer config not found")
        return dict(row)


@app.put("/api/config/scorer")
async def update_scorer_config(config: ScorerConfigInput):
    """Update scorer configuration. Weights must sum to 1.0."""
    # Validate weights sum to 1.0 using the ScorerConfig model
    try:
        ScorerConfig(**config.model_dump())
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    updates = config.model_dump()
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values())

    with get_db(DATABASE_PATH) as conn:
        conn.execute(
            f"UPDATE scorer_config SET {set_clause} WHERE id = 1",
            values,
        )
        conn.commit()
        row = conn.execute("SELECT * FROM scorer_config WHERE id = 1").fetchone()
        return dict(row)


# =============================================================================
# RUN SERVER
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    print(f"Starting Stratus Dispatch Intelligence API on http://{API_HOST}:{API_PORT}")
    uvicorn.run(app, host=API_HOST, port=API_PORT, reload=DEBUG)
