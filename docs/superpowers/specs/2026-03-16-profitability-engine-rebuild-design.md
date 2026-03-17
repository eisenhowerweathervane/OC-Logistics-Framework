# Profitability Engine Modular Rebuild — Design Spec

**Date:** 2026-03-16
**Status:** Approved
**Author:** Rajan Patel + Claude

## Overview

Rebuild the existing profitability engine (`profitability_engine.py`) from a monolithic scorer into a modular, composable system. The new engine provides smarter scoring, dynamic cost modeling, adaptive multi-day planning with scenario analysis, and multiple data ingestion methods. All features are designed to work from Day 0 with zero historical data and improve automatically as load volume grows.

**Constraints:**
- Single Van operation (no equipment-type cost profiles)
- No DAT API access — internal historical data only
- Pre-revenue — no existing load history
- Planning-side only (no real-time re-optimization in v1)

## Architecture

```
ingestion/
  dat_email_parser.py       — existing email parser (preserved)
  dat_paste_parser.py       — copy-paste from DAT dashboard
  ocr_parser.py             — screenshot OCR extraction
  gap_resolver.py           — identifies missing fields, prompts user

costs/
  cost_model.py             — base costs with monthly-to-per-mile conversion
  toll_service.py           — route-specific toll estimation
  fuel_service.py           — dynamic regional fuel pricing (DOE/EIA data)
  accessorials.py           — lumpers, TONU, detention, layover line items

scoring/
  lane_scorer.py            — lane-aware scoring with historical context
  broker_scorer.py          — broker reliability tracking and grading
  strategic_scorer.py       — destination demand / repositioning value
  composite_scorer.py       — combines all scorers with configurable weights

optimizer/
  chain_optimizer.py        — multi-day optimizer with full FMCSA HOS
  scenario_engine.py        — sensitivity analysis / dwell-time scenario trees
  watchlist.py              — committed + watchlist planning model

analytics/
  lane_history.py           — lane average tracking (all loads, booked and passed)
  broker_history.py         — broker performance tracking
```

All parsers produce a unified `ParsedLoad` structure. All scorers implement a common interface and are composed by `composite_scorer.py`.

### ParsedLoad Schema

Every parser outputs this unified structure. Fields marked required must be present before a load can be scored; optional fields enhance scoring when available.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `origin_city` | str | Yes | |
| `origin_state` | str | Yes | 2-letter state code |
| `destination_city` | str | Yes | |
| `destination_state` | str | Yes | 2-letter state code |
| `mileage` | int | Yes | Loaded miles |
| `rate_total` | float | No | Null if "Call for rate" |
| `rate_per_mile` | float | No | Auto-calculated if rate_total + mileage present |
| `deadhead_miles` | int | No | Defaults to 0 |
| `weight` | int | No | Pounds |
| `equipment_type` | str | No | Defaults to "Van" |
| `commodity` | str | No | |
| `pickup_date` | str | No | ISO format (YYYY-MM-DD) |
| `pickup_time_window` | str | No | e.g., "08:00-16:00" |
| `delivery_date` | str | No | ISO format |
| `delivery_time_window` | str | No | |
| `broker_name` | str | No | Used for broker scoring |
| `broker_mc_number` | str | No | |
| `contact_phone` | str | No | |
| `contact_email` | str | No | |
| `load_number` | str | No | |
| `notes` | str | No | |
| `source` | str | Yes | "email", "paste", "ocr", "manual" |

**Field-level confidence (OCR parser only):**

When the OCR parser extracts fields, each field is wrapped with metadata:

```python
ParsedField = {
    "value": <extracted_value>,
    "confidence": float,  # 0.0 to 1.0
    "source": str          # "ocr", "email", "paste", "manual"
}
```

The gap resolver triggers for any field with `confidence < 0.7` or missing required fields.

---

## Section 1: Data Ingestion Layer

### 1.1 DAT Email Parser (existing)

Preserved from current `dat_email_parser.py`. Splits multi-load emails, handles edge cases (special characters in city names, "Call for rate", etc.). Already unit-tested.

### 1.2 DAT Paste Parser

Accepts raw text copied from the DAT web dashboard. Uses pattern matching tuned for DAT's web UI format (different from email format). Requires sample pasted text to calibrate patterns during implementation.

### 1.3 OCR Parser

Accepts a screenshot image (PNG, JPG, max 10MB). Primary implementation: Tesseract (free, local, no API costs). Fallback/upgrade path: Google Cloud Vision API for higher accuracy if needed. Extracts text from the image, then runs it through the paste parser. Returns extracted fields with confidence scores (see ParsedField in Architecture section).

### 1.4 Gap Resolver

After any parser runs:
1. Checks which required fields are missing or low-confidence
2. Returns a response: `"parsed 8 of 12 fields — missing: rate, delivery_date, weight, commodity"`
3. User can: type missing values, upload a screenshot to fill gaps, or skip optional fields
4. Once complete, load moves to scoring

### 1.5 Duplicate Detection

When a load is ingested (any method), the system checks for duplicates using this key: `(origin_city, origin_state, destination_city, destination_state, pickup_date, broker_name, rate_total, mileage)`. This replaces the existing UNIQUE constraint which used a narrower key without rate or mileage.

- If match found: flags it — "This looks like a duplicate of Load #47"
- User chooses: remove, keep (e.g., rate changed), or merge (update existing record)
- Duplicates are never silently deleted — always user's call

---

## Section 2: Cost Model

### 2.1 Monthly-to-Per-Mile Conversion

Users input fixed costs as monthly amounts. System converts to per-mile using expected monthly mileage (user-provided estimate). As actual mileage data accumulates, the system recalculates using real miles run.

**Configurable fixed costs (monthly input):**
- Truck lease (e.g., $4,000/mo)
- Insurance (e.g., $1,800/mo)
- Overhead (e.g., $500/mo)

**Conversion:**
```
Per-mile cost = Monthly cost / Expected monthly miles
Example: $4,000 / 8,000 mi = $0.50/mi
```

Users can update monthly amounts anytime; per-mile costs recalculate everywhere.

### 2.2 Driver Pay Modes

Three selectable modes:

- **Mode 1: Base + Per-Mile** — e.g., $800/week base + $0.15/mi. Base converted to per-mile using expected (then actual) mileage, added to per-mile component.
- **Mode 2: Per-Mile Only** — e.g., $0.55/mi. Used as-is.
- **Mode 3: Base Pay Only** — e.g., $1,200/week salary. Converted to per-mile using expected (then actual) mileage.

### 2.3 Dynamic Fuel Pricing

Pulls regional diesel prices from the EIA API (`api.eia.gov`, free with API key). Uses PADD district regions (5 US regions) to match routes to regional fuel prices. Data refreshed weekly via scheduled fetch or on-demand.

**Storage:** `fuel_prices` table (see Section 5.4).

**Fallback:** If EIA API is unavailable, uses most recent cached price. If no cached data exists (Day 0), uses a configurable static default (initially $3.85/gal).

Still uses MPG assumption (configurable, default 6.5).

### 2.4 Route-Specific Tolls

Toll estimation based on known toll corridors. Stored in a `toll_corridors` table (see Section 5.4).

**Seed corridors (Class 5 / tractor-trailer rates):**
- Ohio Turnpike (I-80/I-90): ~$0.15/mi
- PA Turnpike (I-76): ~$0.45/mi
- NJ Turnpike: ~$0.25/mi
- NY Thruway (I-90): ~$0.12/mi
- Indiana Toll Road (I-80/I-90): ~$0.20/mi
- West Virginia Turnpike (I-77): ~$0.10/mi
- Florida Turnpike: ~$0.12/mi

**Route matching:** If origin-destination route passes through a toll corridor (based on Google Maps route or known interstate overlap), the corridor's cost is added. Multiple corridors can apply to one route.

**Learning:** After each trip, user can record actual toll paid. Over time, actual data replaces estimates per corridor. Stored in `load_feedback` table.

### 2.5 Accessorial Costs

Optional line items per load:
- **Detention** — tracked per broker for reliability scoring
- **Lumper fees** — added as known cost when present
- **TONU (truck ordered not used)** — tracked as risk factor by broker
- **Layover** — cost for overnight wait between loads

If unknown at scoring time, defaults to $0 and flags as assumption.

### 2.6 Total Cost Formula

```
Base CPM = (Fuel Cost per Mile) + (Driver Pay per Mile) + (Lease per Mile) + (Insurance per Mile) + (Overhead per Mile) + (Maintenance Reserve per Mile)

Total Cost = (Base CPM x Total Miles) + Tolls + Accessorials

Net Revenue = Gross Revenue - (Factoring Fee % x Gross Revenue)
Profit = Net Revenue - Total Cost
```

**Factoring fee** (carried from existing system): Configurable percentage (default 3%) deducted from gross revenue. Stored in `cost_config`.

**Maintenance reserve:** Included in the cost model as an optional monthly cost (default $0.00 — appropriate for full-service Ryder lease where maintenance is included). Converted to per-mile the same way as lease/insurance/overhead. Can be set to non-zero if the truck arrangement changes.

Cost breakdown visible per load so the user sees where money goes.

---

## Section 3: Scoring Engine

### 3.1 Lane-Aware Scoring (`lane_scorer.py`)

Tracks historical performance per lane. A "lane" is defined at **city-to-city** granularity (e.g., Columbus, OH → Pittsburgh, PA). When a city-level lane has fewer than 3 data points, the system falls back to **state-to-state** aggregation for that lane.

Stores: average rate, average margin, load count, trend direction. Scores loads relative to lane history — "this load is 15% above your average for this lane."

**Day 0 behavior:** No history = no lane adjustment. Falls back to absolute thresholds (similar to current system). Lane scoring gradually takes over as loads accumulate.

### 3.2 Broker Reliability Scoring (`broker_scorer.py`)

Tracks per broker: average detention time, TONU count, rate accuracy (quoted vs. actual), on-time pickup %, number of loads completed. Builds a broker reliability grade (A/B/C/D/F) over time.

- Brokers with history of long detentions get penalized
- Brokers with clean track records get a boost
- **Day 0 behavior:** All brokers start unrated — no penalty, no bonus. System prompts user to log broker experience after each load.

### 3.3 Strategic Value Scoring (`strategic_scorer.py`)

Evaluates where a load leaves you, not just what it pays:
- Is the destination a high-demand area?
- Are there historically good backhauls from that city?
- Does this load move you closer to or further from home base?

A break-even load that drops you in a high-demand market scores better than a marginally profitable load that strands you.

**Day 0 behavior:** Uses a static "city demand tier" list (major hubs = Tier 1, mid-markets = Tier 2, rural = Tier 3). Refines with actual data over time.

### 3.4 Composite Scorer (`composite_scorer.py`)

Combines all sub-scores with configurable weights:
- Financial: 50% (margin, RPM, profit/hour — existing metrics)
- Lane history: 15%
- Broker reliability: 15%
- Strategic value: 20%

User can tune weights as they learn what matters most. Still produces a final score and action tier: **BOOK IT / CONSIDER / NEGOTIATE / PASS**.

---

## Section 4: Chain Optimizer & Scenario Engine

### 4.1 Chain Optimizer (`chain_optimizer.py`)

**Full FMCSA HOS modeling:**
- 11-hour driving limit per duty period
- 14-hour on-duty window (driving must complete within 14 hrs of coming on duty)
- Mandatory 10-hour rest period between duty periods
- 30-minute break after 8 cumulative driving hours — modeled as 0.5 hours added to total time after 8 driving hours within a duty period
- 70-hour/8-day weekly cap — tracked via `weekly_hours_used` parameter passed to the optimizer. For multi-day planning, the optimizer deducts each day's on-duty time from the weekly budget.

**Repositioning value:** When ranking next loads, factors in what the destination opens up (uses strategic scorer). A lower-profit load that puts you in a freight-rich area can beat a higher-profit load that strands you.

**Wider search:** Increased beam width with pruning heuristics. Explores more combinations without excessive computation.

**Multiple loads per day:** The optimizer chains loads based on available hours, not day boundaries. A driver can run 2-3 short loads in a single day as long as HOS allows.

### 4.2 Scenario Engine (`scenario_engine.py`)

For each leg in a chain, generates scenario branches based on dwell time:
- **Quick (30 min):** Unload fast, maximum options available
- **Normal (1.5 hr):** Expected case
- **Slow (3 hr):** Delays, fewer options
- **Detention (6+ hr):** Significant pivot, different load set

Each branch re-runs the optimizer from that point forward with updated HOS remaining and time of day. Output is a scenario tree — a map of "if this happens, here are your best moves."

**Scenarios are computed on-the-fly** (not persisted). Each call to `/api/optimize` or `/api/watchlist/resolve` generates fresh scenarios based on current available loads and constraints. This avoids stale scenario data and simplifies the system — no scenario lifecycle/expiry management needed.

Scenario branches generate after every leg completion, not just end-of-day.

### 4.3 Watchlist Model (`watchlist.py`)

- **Committed loads:** Current leg — booked, locked in
- **Watchlist loads:** Upcoming legs — scored, ranked, grouped by scenario. Not booked yet.

Each watchlist entry shows: load details, which scenario(s) it fits, score, and time sensitivity (pickup window closing).

**Workflow:**
1. Complete a leg
2. Report actual dwell time to the system
3. System surfaces matching scenario's recommendations
4. Pick next load — it becomes committed
5. Watchlist refreshes for the leg after that

**Example output:**
```
COMMITTED:
  Cleveland -> Columbus (185 mi, $600, Score: 7)

WATCHLIST (after Columbus delivery):
  If quick unload (< 1hr):
    1. Columbus -> Pittsburgh ($550, Score: 6)
    2. Columbus -> Dayton ($280, Score: 4) + Dayton -> Cincinnati ($320, Score: 5)
    3. Columbus -> Indianapolis ($700, Score: 5)
  If normal unload (1-2hr):
    1. Columbus -> Pittsburgh ($550, Score: 6)
    2. Columbus -> Cincinnati ($400, Score: 4)
  If detention (3+ hr):
    1. Columbus -> Dayton ($280, Score: 3) — short haul, gets you moving
    2. Stay overnight, reassess next morning
```

---

## Section 5: Analytics & History

### 5.1 Lane History (`lane_history.py`)

- Records every load that enters the system — booked, passed, expired, or watchlist-skipped
- Queries: average rate/margin for a lane, trend over 30/60/90 days, load volume per lane
- Identifies most profitable lanes and lanes to avoid
- **Decay:** Exponential decay with a 90-day half-life (configurable). A load from 90 days ago counts at 50% weight, 180 days at 25%, etc. Keeps averages current without discarding old data entirely.

### 5.2 Broker History (`broker_history.py`)

- Records per broker: detention times, TONUs, rate accuracy, pickup punctuality, loads completed
- Calculates reliability grade (A through F) with configurable thresholds
- Post-load feedback loop: after completing a load, system asks "How did it go?" — rate detention, on-time, any issues. Takes 10 seconds.

### 5.3 Non-Executed Load History

Every load that enters the system is stored with an outcome tag:
- `booked` — load was taken
- `passed` — load was reviewed and declined
- `expired` — pickup window passed without action
- `watchlist_skipped` — was on watchlist but not selected

This data feeds lane averages (all loads seen, not just booked) and helps analyze selectivity patterns.

### 5.4 Database Schema Changes

**Existing `loads` table — new columns:**

| Column | Type | Notes |
|--------|------|-------|
| `outcome` | TEXT | `booked`, `passed`, `expired`, `watchlist_skipped`. Default: NULL (legacy/unset) |
| `duplicate_of` | INTEGER | FK to loads.id if flagged as duplicate |
| `source` | TEXT | `email`, `paste`, `ocr`, `manual` |

**New table: `lane_history`** (aggregated stats, rebuilt from loads table periodically)

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | PK |
| `origin_city` | TEXT | |
| `origin_state` | TEXT | |
| `destination_city` | TEXT | |
| `destination_state` | TEXT | |
| `avg_rate` | REAL | Decay-weighted average |
| `avg_margin_pct` | REAL | Decay-weighted average |
| `load_count` | INTEGER | Total loads seen on this lane |
| `booked_count` | INTEGER | Loads actually taken |
| `trend_direction` | TEXT | `up`, `down`, `stable` |
| `last_seen` | TEXT | ISO date of most recent load |
| `updated_at` | TEXT | Last recalculation timestamp |

**New table: `broker_history`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | PK |
| `broker_name` | TEXT | UNIQUE |
| `broker_mc_number` | TEXT | |
| `avg_detention_hours` | REAL | Average from feedback |
| `tonu_count` | INTEGER | Total TONUs recorded |
| `loads_completed` | INTEGER | |
| `loads_seen` | INTEGER | |
| `rate_accuracy_pct` | REAL | Avg (actual_rate / quoted_rate) * 100 |
| `ontime_pickup_pct` | REAL | % of loads picked up on time |
| `reliability_grade` | TEXT | A/B/C/D/F |
| `updated_at` | TEXT | |

**New table: `load_feedback`** (post-load actuals)

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | PK |
| `load_id` | INTEGER | FK to loads.id |
| `actual_dwell_hours` | REAL | Real load/unload time |
| `actual_rate_paid` | REAL | Final rate (may differ from quoted) |
| `actual_toll_cost` | REAL | Actual tolls paid |
| `detention_hours` | REAL | Actual detention |
| `ontime_pickup` | BOOLEAN | Was pickup on time? |
| `issues` | TEXT | Free-text notes on problems |
| `created_at` | TEXT | |

**New table: `accessorials`** (line-item costs per load)

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | PK |
| `load_id` | INTEGER | FK to loads.id |
| `type` | TEXT | `detention`, `lumper`, `tonu`, `layover`, `toll`, `other` |
| `amount` | REAL | Dollar amount |
| `notes` | TEXT | Optional description |

**New table: `cost_config`** (single-row configuration)

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | PK (always 1) |
| `truck_lease_monthly` | REAL | e.g., 4000.00 |
| `insurance_monthly` | REAL | |
| `overhead_monthly` | REAL | |
| `maint_reserve_monthly` | REAL | Default 0.00 |
| `expected_monthly_miles` | INTEGER | User estimate |
| `driver_pay_mode` | TEXT | `base_plus_mile`, `per_mile_only`, `base_only` |
| `driver_base_weekly` | REAL | Used in modes 1 and 3 |
| `driver_per_mile` | REAL | Used in modes 1 and 2 |
| `factoring_fee_pct` | REAL | Default 3.0 |
| `fuel_mpg` | REAL | Default 6.5 |
| `default_fuel_price` | REAL | Fallback, default 3.85 |
| `updated_at` | TEXT | |

**New table: `scorer_config`** (composite scorer weights)

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | PK (always 1) |
| `financial_weight` | REAL | Default 0.50 |
| `lane_weight` | REAL | Default 0.15 |
| `broker_weight` | REAL | Default 0.15 |
| `strategic_weight` | REAL | Default 0.20 |
| `updated_at` | TEXT | |

**New table: `toll_corridors`** (seed data for toll estimation)

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | PK |
| `corridor_name` | TEXT | e.g., "PA Turnpike (I-76)" |
| `interstate` | TEXT | e.g., "I-76" |
| `states` | TEXT | Comma-separated, e.g., "PA" |
| `cost_per_mile` | REAL | Estimated $/mi for trucks |
| `last_updated` | TEXT | |

**New table: `fuel_prices`** (cached EIA regional prices)

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | PK |
| `padd_region` | TEXT | e.g., "PADD 1" (East Coast) |
| `price_per_gallon` | REAL | |
| `effective_date` | TEXT | Week of price data |
| `fetched_at` | TEXT | When we pulled this data |

**New table: `city_demand_tiers`** (strategic scorer seed data)

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | PK |
| `city` | TEXT | |
| `state` | TEXT | |
| `tier` | INTEGER | 1 (high demand), 2 (mid), 3 (low) |
| `source` | TEXT | `seed` or `learned` |
| `updated_at` | TEXT | |

---

## Section 6: API Endpoints

### New Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ingest/paste` | POST | Parse pasted DAT text, return parsed fields + gaps |
| `/api/ingest/screenshot` | POST | Upload screenshot, OCR extract, return parsed fields + gaps |
| `/api/ingest/complete` | POST | Submit missing fields, finalize load ingestion |
| `/api/score` | POST | Score load using composite scorer (replaces current) |
| `/api/optimize` | POST | Run chain optimizer with scenario engine |
| `/api/watchlist` | GET | Get current watchlist |
| `/api/watchlist` | POST | Update watchlist after leg completion |
| `/api/watchlist/resolve` | POST | Report actual dwell time, get matching scenario recommendations |
| `/api/loads/{id}/feedback` | POST | Post-load feedback (actual dwell, issues, rate accuracy) |
| `/api/analytics/lanes` | GET | Lane history stats, trends, averages |
| `/api/analytics/brokers` | GET | Broker reliability grades and history |
| `/api/config/costs` | GET | View current cost configuration |
| `/api/config/costs` | PUT | Update monthly costs, driver pay mode, expected mileage |
| `/api/duplicates` | GET | View flagged duplicates |
| `/api/duplicates` | POST | Resolve duplicates (keep/remove/merge) |
| `/api/loads/{id}/outcome` | PATCH | Set load outcome (booked/passed/expired/watchlist_skipped) |
| `/api/config/scorer` | GET | View composite scorer weights |
| `/api/config/scorer` | PUT | Update scorer weights |
| `/api/config/demand-tiers` | GET | View city demand tier list |
| `/api/config/demand-tiers` | PUT | Update city demand tiers |

### Preserved Endpoints

All existing endpoints (`/api/loads`, `/api/parse`, `/api/distance`, `/api/cities`, `/api/stats`) continue working but return richer data from the new scoring and cost models.

---

## Day 0 Strategy

Every feature degrades gracefully with no data:

| Feature | Day 0 Behavior | With Data |
|---------|----------------|-----------|
| Lane scoring | No adjustment, absolute thresholds | Scores relative to lane history |
| Broker scoring | All unrated, no penalty/bonus | Grades A-F based on track record |
| Strategic scoring | Static city demand tiers | Refined by actual backhaul/demand data |
| Cost per mile | Based on expected mileage estimate | Recalculates from actual miles run |
| Lane averages | No data shown | Rolling averages with decay weighting |

---

## Migration Plan

Since the system is pre-revenue with no production data, migration is low-risk:

1. **ALTER existing `loads` table:** Add `outcome`, `duplicate_of`, and `source` columns (all nullable)
2. **CREATE all new tables** (`lane_history`, `broker_history`, `load_feedback`, `accessorials`, `cost_config`, `scorer_config`, `toll_corridors`, `fuel_prices`, `city_demand_tiers`)
3. **Seed data:** Insert default `cost_config` row, default `scorer_config` row, seed `toll_corridors` with the 7 corridors listed in Section 2.4, seed `city_demand_tiers` with initial tier assignments
4. **Backfill:** Any existing loads in the database get `outcome = NULL` and `source = 'email'` (since all existing loads came from the email parser)
5. **Update UNIQUE constraint** on `loads` table to match new dedup key (Section 1.5)

The existing `greedy_chain()` function is superseded by the new chain optimizer and will be removed. The beam search logic is rebuilt in the new `chain_optimizer.py` with wider search and full HOS.

---

## Implementation Priority (Suggested)

1. **Ingestion** — paste parser + gap resolver (unblocks data collection)
2. **Cost model** — monthly-to-per-mile conversion, driver pay modes, accessorials
3. **Scoring** — composite scorer with financial + strategic (lane/broker build over time)
4. **Optimizer** — full HOS, scenario engine, watchlist model
5. **Analytics** — lane/broker history, feedback loop, non-executed load tracking
6. **OCR** — screenshot parser (can be added anytime, lower priority than paste)
