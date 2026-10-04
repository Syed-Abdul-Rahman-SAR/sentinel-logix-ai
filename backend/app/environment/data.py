"""
SENTINEL LOGIX AI - Environment Intelligence Synthetic Data Store
Phase 10A: Weather & Terrain Intelligence Foundation

Provides deterministic synthetic weather snapshots and terrain characteristics
for the project's existing logistics corridors (derived from SEGMENTS_SEED).

ROUTES COVERED
--------------
  GHY-SHL  — Guwahati → Shillong        (hilly, good road, moderate weather)
  GHY-TEZ  — Guwahati → Tezpur          (plains, good road, low env risk)
  TEZ-TWA  — Tezpur → Tawang            (extreme mountain, POOR road, HIGH risk)
  SIL-IMP  — Silchar → Imphal           (hilly/landslide prone, POOR road)
  GHY-SHL  already covered above
  KHM-IMP  — Kohima → Imphal            (hilly, FAIR road)
  SIL-AIZ  — Silchar → Aizawl           (hilly, FAIR road)
  TEZ-ITN  — Tezpur → Itanagar          (hilly, GOOD road)

DESIGN NOTES
------------
* Every record contains data_source="synthetic_demo" and environment="demo".
* No real-world military, operational, or live weather data is represented.
* Values are chosen to demonstrate LOW / MEDIUM / HIGH / CRITICAL environmental
  risk profiles so downstream tests and UI can show meaningful contrast.
* Dominant weather-driven route:  TEZ-TWA  (blizzard conditions)
* Dominant terrain-driven route:  SIL-IMP  (landslide-prone + POOR road)
"""

from typing import Dict, Any, Optional, List

# ---------------------------------------------------------------------------
# SYNTHETIC WEATHER DATA
# Indexed by route_id.  Units are explicit in key names.
# ---------------------------------------------------------------------------
SYNTHETIC_WEATHER_DATA: Dict[str, Dict[str, Any]] = {
    "GHY-SHL": {
        "route_id": "GHY-SHL",
        "route_name": "Guwahati – Shillong (NH-6)",
        "temperature_celsius": 18.0,
        "rainfall_mm": 8.0,           # light–moderate rain; Shillong is wetter
        "visibility_km": 6.0,          # slightly reduced by hill fog
        "wind_speed_kmh": 20.0,
        "precipitation_type": "RAIN",
        "weather_condition": "Partly cloudy with light rain and occasional hill fog",
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "GHY-TEZ": {
        "route_id": "GHY-TEZ",
        "route_name": "Guwahati – Tezpur (NH-15)",
        "temperature_celsius": 26.0,
        "rainfall_mm": 1.5,            # dry season / low rainfall
        "visibility_km": 12.0,         # good visibility
        "wind_speed_kmh": 12.0,
        "precipitation_type": "DRIZZLE",
        "weather_condition": "Mostly clear with light drizzle; good visibility",
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "TEZ-TWA": {
        "route_id": "TEZ-TWA",
        "route_name": "Tezpur – Tawang (Sela Pass Route)",
        "temperature_celsius": -4.0,   # sub-zero at high altitude
        "rainfall_mm": 0.0,
        "visibility_km": 0.8,          # near-whiteout blizzard conditions
        "wind_speed_kmh": 75.0,        # severe gale-force winds
        "precipitation_type": "BLIZZARD",
        "weather_condition": "Severe blizzard with near-whiteout visibility and gale-force winds",
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "SIL-IMP": {
        "route_id": "SIL-IMP",
        "route_name": "Silchar – Imphal (NH-37 / NH-102)",
        "temperature_celsius": 22.0,
        "rainfall_mm": 28.0,           # heavy monsoon rainfall
        "visibility_km": 3.0,          # reduced by rain and valley fog
        "wind_speed_kmh": 35.0,
        "precipitation_type": "HEAVY_RAIN",
        "weather_condition": "Heavy monsoon rainfall with reduced visibility and gusty winds",
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "KHM-IMP": {
        "route_id": "KHM-IMP",
        "route_name": "Kohima – Imphal (NH-2)",
        "temperature_celsius": 20.0,
        "rainfall_mm": 12.0,
        "visibility_km": 5.5,
        "wind_speed_kmh": 25.0,
        "precipitation_type": "RAIN",
        "weather_condition": "Moderate rain with patchy mist; reduced but manageable visibility",
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "SIL-AIZ": {
        "route_id": "SIL-AIZ",
        "route_name": "Silchar – Aizawl (NH-54)",
        "temperature_celsius": 21.0,
        "rainfall_mm": 5.0,
        "visibility_km": 8.0,
        "wind_speed_kmh": 18.0,
        "precipitation_type": "DRIZZLE",
        "weather_condition": "Light drizzle with good visibility; moderate humidity",
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "TEZ-ITN": {
        "route_id": "TEZ-ITN",
        "route_name": "Tezpur – Itanagar (NH-415)",
        "temperature_celsius": 24.0,
        "rainfall_mm": 3.0,
        "visibility_km": 10.0,
        "wind_speed_kmh": 15.0,
        "precipitation_type": "DRIZZLE",
        "weather_condition": "Partly cloudy with light drizzle; good driving conditions",
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "JOR-DBR": {
        "route_id": "JOR-DBR",
        "route_name": "Jorhat – Dibrugarh (NH-37)",
        "temperature_celsius": 25.0,
        "rainfall_mm": 2.0,
        "visibility_km": 14.0,
        "wind_speed_kmh": 10.0,
        "precipitation_type": "NONE",
        "weather_condition": "Clear and dry; excellent logistics conditions",
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
}


# ---------------------------------------------------------------------------
# SYNTHETIC TERRAIN DATA
# Indexed by route_id. Derived from SEGMENTS_SEED data.
# elevation_factor and slope_factor are normalised 0.0–1.0.
# ---------------------------------------------------------------------------
SYNTHETIC_TERRAIN_DATA: Dict[str, Dict[str, Any]] = {
    "GHY-SHL": {
        "route_id": "GHY-SHL",
        "route_name": "Guwahati – Shillong (NH-6)",
        "terrain_type": "HILLY",
        "terrain_risk_level": "MEDIUM",
        "elevation_factor": 0.45,       # 1400m gain → moderate
        "slope_factor": 0.50,           # winding ghat sections
        "road_condition": "EXCELLENT",
        "distance_km": 100.0,
        "max_elevation_gain_m": 1400.0,
        "flood_prone": False,
        "landslide_prone": True,        # hill sections known for slides
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "GHY-TEZ": {
        "route_id": "GHY-TEZ",
        "route_name": "Guwahati – Tezpur (NH-15)",
        "terrain_type": "FLOOD_PRONE",
        "terrain_risk_level": "LOW",
        "elevation_factor": 0.05,       # flat Brahmaputra valley
        "slope_factor": 0.08,
        "road_condition": "GOOD",
        "distance_km": 175.0,
        "max_elevation_gain_m": 50.0,
        "flood_prone": True,            # Brahmaputra flood plain
        "landslide_prone": False,
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "TEZ-TWA": {
        "route_id": "TEZ-TWA",
        "route_name": "Tezpur – Tawang (Sela Pass Route)",
        "terrain_type": "MOUNTAINOUS",
        "terrain_risk_level": "CRITICAL",
        "elevation_factor": 0.95,       # +2800m gain; >4000m at Sela Pass
        "slope_factor": 0.90,           # extreme hairpin sections
        "road_condition": "POOR",
        "distance_km": 320.0,
        "max_elevation_gain_m": 2800.0,
        "flood_prone": False,
        "landslide_prone": True,
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "SIL-IMP": {
        "route_id": "SIL-IMP",
        "route_name": "Silchar – Imphal (NH-37 / NH-102)",
        "terrain_type": "LANDSLIDE_PRONE",
        "terrain_risk_level": "HIGH",
        "elevation_factor": 0.60,       # +700m through Barak valley hills
        "slope_factor": 0.65,
        "road_condition": "POOR",
        "distance_km": 255.0,
        "max_elevation_gain_m": 700.0,
        "flood_prone": True,
        "landslide_prone": True,
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "KHM-IMP": {
        "route_id": "KHM-IMP",
        "route_name": "Kohima – Imphal (NH-2)",
        "terrain_type": "HILLY",
        "terrain_risk_level": "MEDIUM",
        "elevation_factor": 0.40,
        "slope_factor": 0.45,
        "road_condition": "FAIR",
        "distance_km": 140.0,
        "max_elevation_gain_m": 600.0,
        "flood_prone": False,
        "landslide_prone": True,
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "SIL-AIZ": {
        "route_id": "SIL-AIZ",
        "route_name": "Silchar – Aizawl (NH-54)",
        "terrain_type": "HILLY",
        "terrain_risk_level": "MEDIUM",
        "elevation_factor": 0.38,
        "slope_factor": 0.40,
        "road_condition": "FAIR",
        "distance_km": 180.0,
        "max_elevation_gain_m": 950.0,
        "flood_prone": False,
        "landslide_prone": True,
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "TEZ-ITN": {
        "route_id": "TEZ-ITN",
        "route_name": "Tezpur – Itanagar (NH-415)",
        "terrain_type": "HILLY",
        "terrain_risk_level": "LOW",
        "elevation_factor": 0.25,
        "slope_factor": 0.28,
        "road_condition": "GOOD",
        "distance_km": 155.0,
        "max_elevation_gain_m": 350.0,
        "flood_prone": False,
        "landslide_prone": False,
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
    "JOR-DBR": {
        "route_id": "JOR-DBR",
        "route_name": "Jorhat – Dibrugarh (NH-37)",
        "terrain_type": "PLAINS",
        "terrain_risk_level": "LOW",
        "elevation_factor": 0.04,
        "slope_factor": 0.05,
        "road_condition": "EXCELLENT",
        "distance_km": 135.0,
        "max_elevation_gain_m": 20.0,
        "flood_prone": True,
        "landslide_prone": False,
        "data_source": "synthetic_demo",
        "environment": "demo",
    },
}

# Canonical set of known route IDs
KNOWN_ROUTE_IDS: List[str] = sorted(SYNTHETIC_WEATHER_DATA.keys())


def get_weather_for_route(route_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns the synthetic weather snapshot for the given route_id, or None if unknown.
    Callers should handle None as a 404 — do NOT generate fallback data for unknown routes.
    """
    return SYNTHETIC_WEATHER_DATA.get(route_id.upper().replace(" ", "-"))


def get_terrain_for_route(route_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns the synthetic terrain characteristics for the given route_id, or None if unknown.
    Callers should handle None as a 404 — do NOT generate fallback data for unknown routes.
    """
    return SYNTHETIC_TERRAIN_DATA.get(route_id.upper().replace(" ", "-"))
