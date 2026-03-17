# Load Profitability Tool

A tool for analyzing DAT load board opportunities to determine profitability.

## Project Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Email Parser | Complete |
| 2 | Scoring Engine + Chain Optimizer | Complete |
| 3 | API + Email Ingestion | Complete |

---

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements.txt

# Copy config template
cp config.py.example config.py

# Set your Google Maps API key (recommended: use environment variable)
export GOOGLE_MAPS_API_KEY="your-api-key-here"

# Start the API server
python3 app.py
```

API runs at `http://localhost:8000`. View docs at `http://localhost:8000/docs`.

> **Security Note**: Never commit API keys to source control. Use environment variables or keep `config.py` in `.gitignore`.

---

## Phase 1: Email Parser

Parses raw DAT load board alert emails and extracts structured load data.

```python
from dat_email_parser import parse_load_email

loads = parse_load_email(raw_email_text)
# Returns list of dicts, one per load
```

---

## Phase 2: Profitability Engine

Scores loads and optimizes multi-load chains using **hours-based HOS constraints**.

### Key Features

- **Real Drive Times**: Uses Google Maps Distance Matrix API for actual drive times (not estimates)
- **Hours-Based HOS**: Enforces FMCSA hours-of-service limits (default 10 hrs/day, legal max 11)
- **Dwell Time**: Accounts for 1.5 hours load/unload time per stop
- **Smart Routing**: Ensures driver can complete load AND return home within HOS

### Usage

```python
from profitability_engine import score_load, optimize_chain

# Score a single load (with automatic deadhead calculation)
result = score_load(load, current_city="Cleveland, OH")
print(f"Score: {result['score']} → {result['action']}")
print(f"Drive time: {result['drive_hours']} hrs + {result['dwell_time']} hrs dwell")
print(f"Total hours: {result['total_hours']}")

# Optimize a chain with HOS constraint
chain = optimize_chain(
    loads,
    start_city="Cleveland, OH",
    hos_remaining=10,  # Hours remaining TODAY
    days_away=1        # Additional days (each adds 10 more hours)
)
print(f"HOS used: {chain['summary']['hos_used']} / {chain['summary']['hos_available']} hrs")
```

### Scored Load Output

| Field | Description |
|-------|-------------|
| `deadhead_miles` | Miles to pickup |
| `deadhead_drive_time` | Hours to reach pickup (from Google Maps) |
| `loaded_drive_time` | Hours for loaded portion (from Google Maps) |
| `dwell_time` | Load/unload time (default 1.5 hrs) |
| `drive_hours` | Total drive time (deadhead + loaded) |
| `total_hours` | Total time including dwell |
| `profit_per_hour` | Profit / total_hours |

### Chain Optimizer Summary

| Field | Description |
|-------|-------------|
| `hos_available` | Total hours available (hos_remaining + days_away × 10) |
| `hos_used` | Hours consumed by the chain |
| `hos_remaining` | Hours left after chain |
| `total_drive_hours` | Actual driving time |
| `total_hours` | Drive + dwell time |

### Action Tiers

| Score | Action | Meaning |
|-------|--------|---------|
| 5+ | BOOK IT | Excellent load |
| 2-4 | CONSIDER | Good load |
| 0-1 | NEGOTIATE | Marginal |
| <0 | PASS | Not profitable |

### Default Assumptions

```python
DEFAULT_ASSUMPTIONS = {
    "fuel_price": 3.85,        # $/gallon
    "mpg": 6.5,                # miles per gallon
    "driver_pay": 0.55,        # $/mile
    "truck_lease": 0.22,       # $/mile (Ryder full-service)
    "insurance": 0.08,         # $/mile
    "overhead": 0.04,          # $/mile
    "factoring_fee": 3.0,      # % of gross revenue
    "load_unload_time": 1.5,   # hours (dwell time)
    "max_drive_hours": 10,     # per day (legal max is 11)
    "home_base": "Cleveland, OH"
}
```

---

## Phase 3: API + Email Ingestion

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/loads` | GET | List all loads (sorted by score) |
| `/api/loads` | POST | Create and score a new load |
| `/api/loads/{id}` | GET | Get single load |
| `/api/parse` | POST | Parse email without saving |
| `/api/parse-and-score` | POST | Parse, score, and optionally save |
| `/api/score` | POST | Score a load without saving |
| `/api/optimize` | POST | Run chain optimizer on selected loads |
| `/api/distance` | GET | Get distance + drive time between cities |
| `/api/cities` | GET | List known cities |
| `/api/assumptions` | GET | Get default cost assumptions |
| `/api/stats` | GET | Dashboard statistics |

### Configuration (config.py)

**Google Maps API (for real distances AND drive times):**
```python
GOOGLE_MAPS_API_KEY = "your-api-key-here"
USE_GOOGLE_MAPS = True
```

You can also set via environment variable:
```bash
export GOOGLE_MAPS_API_KEY="your-api-key-here"
```

> **Note**: Google Maps provides actual road distances and drive times. Without it, the system falls back to Haversine estimates (straight-line × 1.28 road factor) at 52 mph average.

**Email / IMAP (for live email ingestion):**
```python
EMAIL_CONFIG = {
    "email": "your@email.com",
    "password": "your-app-password",
    "imap_server": "imap.gmail.com",
    "filter_subject": "DAT Load Alert",
}
```

### Email Polling

```bash
# Start polling for new emails (checks every 60 seconds)
python3 email_fetcher.py poll 60
```

---

## File Structure

```
Profitability Test/
├── README.md
├── requirements.txt
├── config.py              # Credentials (DO NOT COMMIT)
├── .gitignore
│
├── dat_email_parser.py    # Phase 1 - Email parser
├── profitability_engine.py # Phase 2 - Scoring + optimizer
│
├── app.py                 # Phase 3 - FastAPI backend
├── email_fetcher.py       # Phase 3 - IMAP email polling
├── distance_service.py    # Phase 3 - Google Maps API (distance + drive time)
└── loads.db               # SQLite database (auto-created)
```

---

## Connecting Your React Frontend

Your existing React frontend (`stratus-dispatch-intelligence`) can connect to this API:

1. Start the API: `python3 app.py`
2. Update your React app's API base URL to `http://localhost:8000`
3. Use these endpoints:
   - `GET /api/loads` → populate LoadPoolTable
   - `POST /api/optimize` → run chain optimizer
   - `GET /api/assumptions` → get default assumptions

---

## Running Tests

```bash
# Test parser (Phase 1)
python3 dat_email_parser.py

# Test scorer (Phase 2)
python3 profitability_engine.py

# Test distance service
python3 distance_service.py
```
