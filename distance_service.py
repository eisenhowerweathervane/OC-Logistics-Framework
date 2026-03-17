"""
Distance Service - Phase 3 (Updated)

Provides REAL driving distance and drive time using Google Maps Distance Matrix API.
Falls back to Haversine estimates if API fails.
"""

import math
import os
import ssl
import urllib.request
import urllib.parse
import json
from typing import Optional, Tuple, Dict

# Use certifi for proper SSL certificate verification
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    # Fallback to system certificates if certifi not installed
    SSL_CONTEXT = ssl.create_default_context()

# Get API key from environment variable first, then fall back to config
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

# If not in env, try to get from config
if not GOOGLE_MAPS_API_KEY:
    try:
        from config import GOOGLE_MAPS_API_KEY as CONFIG_KEY
        GOOGLE_MAPS_API_KEY = CONFIG_KEY
    except ImportError:
        pass

# Check if we should use Google Maps
USE_GOOGLE_MAPS = bool(GOOGLE_MAPS_API_KEY)


# =============================================================================
# CITY COORDINATES (fallback for Haversine)
# =============================================================================

CITY_COORDS = {
    "Cleveland, OH": (41.4993, -81.6944),
    "Pittsburgh, PA": (40.4406, -79.9959),
    "Columbus, OH": (39.9612, -82.9988),
    "Cincinnati, OH": (39.1031, -84.5120),
    "Indianapolis, IN": (39.7684, -86.1581),
    "Buffalo, NY": (42.8864, -78.8784),
    "Detroit, MI": (42.3314, -83.0458),
    "Louisville, KY": (38.2527, -85.7585),
    "Chicago, IL": (41.8781, -87.6298),
    "Toledo, OH": (41.6528, -83.5379),
    "Akron, OH": (41.0814, -81.5190),
    "Dayton, OH": (39.7589, -84.1916),
    "Erie, PA": (42.1292, -80.0851),
    "Fort Wayne, IN": (41.0793, -85.1394),
    "Lexington, KY": (38.0406, -84.5037),
    "Nashville, TN": (36.1627, -86.7816),
    "St. Louis, MO": (38.6270, -90.1994),
    "Philadelphia, PA": (39.9526, -75.1652),
    "Charlotte, NC": (35.2271, -80.8431),
    "Atlanta, GA": (33.7490, -84.3880),
    "Memphis, TN": (35.1495, -90.0490),
    "Newark, NJ": (40.7357, -74.1724),
    "Boston, MA": (42.3601, -71.0589),
    "New York, NY": (40.7128, -74.0060),
    "Baltimore, MD": (39.2904, -76.6122),
    "Washington, DC": (38.9072, -77.0369),
    "Raleigh, NC": (35.7796, -78.6382),
    "Jacksonville, FL": (30.3322, -81.6557),
    "Miami, FL": (25.7617, -80.1918),
    "Tampa, FL": (27.9506, -82.4572),
    "Orlando, FL": (28.5383, -81.3792),
    "New Orleans, LA": (29.9511, -90.0715),
    "Houston, TX": (29.7604, -95.3698),
    "Dallas, TX": (32.7767, -96.7970),
    "San Antonio, TX": (29.4241, -98.4936),
    "Kansas City, MO": (39.0997, -94.5786),
    "Denver, CO": (39.7392, -104.9903),
    "Minneapolis, MN": (44.9778, -93.2650),
    "Milwaukee, WI": (43.0389, -87.9065),
    "Grand Rapids, MI": (42.9634, -85.6681),
    "Knoxville, TN": (35.9606, -83.9207),
    "Birmingham, AL": (33.5207, -86.8025),
    "Mobile, AL": (30.6954, -88.0399),
    "Little Rock, AR": (34.7465, -92.2896),
    "Oklahoma City, OK": (35.4676, -97.5164),
}

# Cache for API results: (origin, destination) -> {distance_miles, drive_time_hours, source}
_drive_cache: Dict[Tuple[str, str], Dict] = {}


def get_drive_info(origin: str, destination: str, avg_speed: float = 52.0) -> Dict:
    """
    Get REAL driving distance and time between two cities.

    Uses Google Maps Distance Matrix API if available, falls back to Haversine.

    Args:
        origin: Origin city (e.g., "Cleveland, OH")
        destination: Destination city (e.g., "Columbus, OH")
        avg_speed: Average speed for Haversine fallback (mph)

    Returns:
        Dict with keys:
            - distance_miles: float (actual road miles)
            - drive_time_hours: float (actual drive time)
            - source: str ("google" or "haversine")
    """
    if origin == destination:
        return {
            "distance_miles": 0,
            "drive_time_hours": 0,
            "source": "same"
        }

    # Check cache first
    cache_key = (origin, destination)
    if cache_key in _drive_cache:
        return _drive_cache[cache_key]

    # Try Google Maps if API key is set
    if USE_GOOGLE_MAPS and GOOGLE_MAPS_API_KEY:
        result = google_maps_drive_info(origin, destination)
        if result:
            _drive_cache[cache_key] = result
            return result

    # Fall back to Haversine
    result = haversine_drive_info(origin, destination, avg_speed)
    _drive_cache[cache_key] = result
    return result


def google_maps_drive_info(origin: str, destination: str) -> Optional[Dict]:
    """
    Get driving info from Google Maps Distance Matrix API.

    Returns dict with distance_miles and drive_time_hours, or None if fails.
    """
    if not GOOGLE_MAPS_API_KEY:
        return None

    try:
        base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": origin,
            "destinations": destination,
            "units": "imperial",
            "key": GOOGLE_MAPS_API_KEY,
        }

        url = f"{base_url}?{urllib.parse.urlencode(params)}"

        # Use proper SSL certificate verification
        with urllib.request.urlopen(url, timeout=10, context=SSL_CONTEXT) as response:
            data = json.loads(response.read().decode())

        if data.get("status") != "OK":
            print(f"Google Maps API error: {data.get('status')}")
            return None

        rows = data.get("rows", [])
        if not rows:
            return None

        elements = rows[0].get("elements", [])
        if not elements:
            return None

        element = elements[0]
        if element.get("status") != "OK":
            return None

        # Distance is returned in meters, convert to miles
        distance_meters = element.get("distance", {}).get("value", 0)
        distance_miles = distance_meters / 1609.34

        # Duration is returned in seconds, convert to hours
        duration_seconds = element.get("duration", {}).get("value", 0)
        drive_time_hours = duration_seconds / 3600

        return {
            "distance_miles": round(distance_miles, 1),
            "drive_time_hours": round(drive_time_hours, 2),
            "source": "google"
        }

    except Exception as e:
        print(f"Google Maps API error for {origin} → {destination}: {e}")
        return None


def haversine_drive_info(origin: str, destination: str, avg_speed: float = 52.0) -> Dict:
    """
    Estimate driving info using Haversine formula with 1.28x road factor.

    Returns dict with estimated distance_miles and drive_time_hours.
    """
    if origin not in CITY_COORDS or destination not in CITY_COORDS:
        print(f"WARNING: Unknown city in route {origin} → {destination}, using 0")
        return {
            "distance_miles": 0,
            "drive_time_hours": 0,
            "source": "unknown"
        }

    lat1, lon1 = CITY_COORDS[origin]
    lat2, lon2 = CITY_COORDS[destination]

    # Haversine formula
    R = 3959  # Earth's radius in miles

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    straight_line = R * c

    # Apply 1.28x road factor
    distance_miles = straight_line * 1.28
    drive_time_hours = distance_miles / avg_speed

    return {
        "distance_miles": round(distance_miles, 1),
        "drive_time_hours": round(drive_time_hours, 2),
        "source": "haversine"
    }


# Legacy function for backwards compatibility
def get_distance(origin: str, destination: str) -> Tuple[int, str]:
    """
    Legacy function - returns (distance_miles, source).
    Use get_drive_info() for new code.
    """
    info = get_drive_info(origin, destination)
    return (int(round(info["distance_miles"])), info["source"])


def calculate_distance(city1: str, city2: str) -> int:
    """
    Legacy function - returns just the distance in miles.
    Use get_drive_info() for new code.
    """
    info = get_drive_info(city1, city2)
    return int(round(info["distance_miles"]))


def is_city_known(city: str) -> bool:
    """Check if a city is in the coordinate lookup table."""
    return city in CITY_COORDS


def clear_cache():
    """Clear the distance/drive time cache."""
    global _drive_cache
    _drive_cache = {}


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("Distance Service Test")
    print("=" * 60)
    print(f"Google Maps API key set: {'Yes' if GOOGLE_MAPS_API_KEY else 'No'}")
    print(f"Using Google Maps: {USE_GOOGLE_MAPS}")
    print()

    test_routes = [
        ("Cleveland, OH", "Columbus, OH"),
        ("Cleveland, OH", "Pittsburgh, PA"),
        ("Cleveland, OH", "Charlotte, NC"),
        ("Cleveland, OH", "Chicago, IL"),
    ]

    for origin, dest in test_routes:
        info = get_drive_info(origin, dest)
        print(f"{origin} → {dest}:")
        print(f"  Distance: {info['distance_miles']} miles")
        print(f"  Drive time: {info['drive_time_hours']} hours")
        print(f"  Source: {info['source']}")
        print()
