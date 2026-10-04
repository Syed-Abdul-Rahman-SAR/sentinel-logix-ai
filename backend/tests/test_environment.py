"""
SENTINEL LOGIX AI - Phase 10A Environment Intelligence Tests
Weather & Terrain Intelligence Foundation Test Suite
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.environment.data import (
    SYNTHETIC_WEATHER_DATA,
    SYNTHETIC_TERRAIN_DATA,
    KNOWN_ROUTE_IDS,
    get_weather_for_route,
    get_terrain_for_route,
)
from backend.app.environment.assessment import (
    assess_environmental_risk,
    THRESHOLD_CRITICAL,
    THRESHOLD_HIGH,
    THRESHOLD_MEDIUM,
)
from backend.app.environment.service import EnvironmentService

client = TestClient(app)


# =============================================================================
# 1. WEATHER INTELLIGENCE TESTS
# =============================================================================

def test_synthetic_weather_data_validity():
    """Verify synthetic weather data structure, required fields, and units."""
    assert len(SYNTHETIC_WEATHER_DATA) > 0
    for route_id, w in SYNTHETIC_WEATHER_DATA.items():
        assert w["route_id"] == route_id
        assert isinstance(w["temperature_celsius"], float)
        assert isinstance(w["rainfall_mm"], float)
        assert w["rainfall_mm"] >= 0.0
        assert isinstance(w["visibility_km"], float)
        assert w["visibility_km"] >= 0.0
        assert isinstance(w["wind_speed_kmh"], float)
        assert w["wind_speed_kmh"] >= 0.0
        assert isinstance(w["precipitation_type"], str)
        assert isinstance(w["weather_condition"], str)
        # Data provenance metadata
        assert w["data_source"] == "synthetic_demo"
        assert w["environment"] == "demo"


def test_get_weather_deterministic():
    """Verify get_weather_for_route returns exact deterministic data."""
    w1 = get_weather_for_route("TEZ-TWA")
    w2 = get_weather_for_route("TEZ-TWA")
    assert w1 is not None
    assert w1 == w2
    assert w1["temperature_celsius"] == -4.0
    assert w1["precipitation_type"] == "BLIZZARD"


# =============================================================================
# 2. TERRAIN INTELLIGENCE TESTS
# =============================================================================

def test_synthetic_terrain_data_validity():
    """Verify synthetic terrain data structure, categories, and ranges."""
    assert len(SYNTHETIC_TERRAIN_DATA) > 0
    supported_categories = {"PLAINS", "HILLY", "MOUNTAINOUS", "FLOOD_PRONE", "LANDSLIDE_PRONE"}
    found_categories = set()

    for route_id, t in SYNTHETIC_TERRAIN_DATA.items():
        assert t["route_id"] == route_id
        assert t["terrain_type"] in supported_categories
        found_categories.add(t["terrain_type"])
        assert t["terrain_risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert 0.0 <= t["elevation_factor"] <= 1.0
        assert 0.0 <= t["slope_factor"] <= 1.0
        assert t["road_condition"] in {"EXCELLENT", "GOOD", "FAIR", "POOR", "CRITICAL"}
        assert t["distance_km"] > 0.0
        assert isinstance(t["flood_prone"], bool)
        assert isinstance(t["landslide_prone"], bool)
        # Data provenance metadata
        assert t["data_source"] == "synthetic_demo"
        assert t["environment"] == "demo"

    # Verify all supported categories are present in the dataset
    assert supported_categories.issubset(found_categories)


def test_get_terrain_deterministic():
    """Verify get_terrain_for_route returns exact deterministic data."""
    t1 = get_terrain_for_route("SIL-IMP")
    t2 = get_terrain_for_route("SIL-IMP")
    assert t1 is not None
    assert t1 == t2
    assert t1["terrain_type"] == "LANDSLIDE_PRONE"
    assert t1["landslide_prone"] is True


# =============================================================================
# 3. ENVIRONMENTAL RISK ASSESSMENT ENGINE TESTS
# =============================================================================

def test_risk_calculation_low_risk():
    """Verify low environmental risk assessment for a clear plains route (JOR-DBR)."""
    weather = get_weather_for_route("JOR-DBR")
    terrain = get_terrain_for_route("JOR-DBR")
    assessment = assess_environmental_risk(weather, terrain)

    assert assessment["classification"] == "LOW"
    assert assessment["environmental_risk_score"] < THRESHOLD_MEDIUM
    assert assessment["weather_risk_score"] <= 5.0
    assert assessment["environmental_risk_score"] == round(assessment["weather_risk_score"] + assessment["terrain_risk_score"], 1)
    assert assessment["data_source"] == "synthetic_demo"
    assert assessment["environment"] == "demo"


def test_risk_calculation_medium_risk():
    """Verify medium environmental risk assessment for a hilly route (GHY-SHL)."""
    weather = get_weather_for_route("GHY-SHL")
    terrain = get_terrain_for_route("GHY-SHL")
    assessment = assess_environmental_risk(weather, terrain)

    assert assessment["classification"] == "MEDIUM"
    assert THRESHOLD_MEDIUM <= assessment["environmental_risk_score"] < THRESHOLD_HIGH
    assert assessment["environmental_risk_score"] == round(assessment["weather_risk_score"] + assessment["terrain_risk_score"], 1)


def test_risk_calculation_high_risk():
    """Verify high environmental risk assessment (SIL-IMP, terrain dominant)."""
    weather = get_weather_for_route("SIL-IMP")
    terrain = get_terrain_for_route("SIL-IMP")
    assessment = assess_environmental_risk(weather, terrain)

    assert assessment["classification"] in {"HIGH", "CRITICAL"}
    assert assessment["environmental_risk_score"] >= THRESHOLD_HIGH
    # Terrain risk should be dominant or major contributor
    assert assessment["terrain_risk_score"] > assessment["weather_risk_score"]
    # Check contributing factors explainability
    assert len(assessment["contributing_factors"]) > 0
    factors = [f["factor"] for f in assessment["contributing_factors"]]
    assert "precipitation_intensity" in factors or "geohazard_flags" in factors or "road_condition" in factors
    assert "SILCHAR" in assessment["explanation"].upper() or "IMP" in assessment["explanation"].upper() or "ROUTE" in assessment["explanation"].upper()


def test_risk_calculation_critical_weather_dominant():
    """Verify critical risk where weather is the dominant contributor (TEZ-TWA blizzard)."""
    weather = get_weather_for_route("TEZ-TWA")
    terrain = get_terrain_for_route("TEZ-TWA")
    assessment = assess_environmental_risk(weather, terrain)

    assert assessment["classification"] == "CRITICAL"
    assert assessment["environmental_risk_score"] >= THRESHOLD_CRITICAL
    # Weather risk should be very high due to blizzard, gale winds, zero vis, subzero temp
    assert assessment["weather_risk_score"] >= 40.0
    assert len(assessment["contributing_factors"]) >= 4
    assert assessment["data_source"] == "synthetic_demo"


def test_score_boundaries_and_classification_thresholds():
    """Verify bounds [0, 50] for sub-scores and [0, 100] for composite score."""
    for route_id in KNOWN_ROUTE_IDS:
        assessment = EnvironmentService.get_environmental_risk(route_id)
        w_score = assessment["weather_risk_score"]
        t_score = assessment["terrain_risk_score"]
        e_score = assessment["environmental_risk_score"]
        cls = assessment["classification"]

        assert 0.0 <= w_score <= 50.0
        assert 0.0 <= t_score <= 50.0
        assert 0.0 <= e_score <= 100.0
        assert e_score == round(w_score + t_score, 1)

        if e_score >= 75.0:
            assert cls == "CRITICAL"
        elif e_score >= 50.0:
            assert cls == "HIGH"
        elif e_score >= 25.0:
            assert cls == "MEDIUM"
        else:
            assert cls == "LOW"


# =============================================================================
# 4. API ENDPOINT TESTS
# =============================================================================

def test_api_list_route_environmental_risks():
    """Test GET /api/environment/routes/risk returns list sorted descending by risk."""
    response = client.get("/api/environment/routes/risk")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(KNOWN_ROUTE_IDS)

    # Check descending order
    scores = [item["environmental_risk_score"] for item in data]
    assert scores == sorted(scores, reverse=True)

    # Check synthetic provenance in all items
    for item in data:
        assert item["data_source"] == "synthetic_demo"
        assert item["environment"] == "demo"


def test_api_get_route_environmental_risk_valid():
    """Test GET /api/environment/routes/{route_id}/risk for valid route."""
    response = client.get("/api/environment/routes/TEZ-TWA/risk")
    assert response.status_code == 200
    data = response.json()

    assert data["route_id"] == "TEZ-TWA"
    assert "weather" in data
    assert "terrain" in data
    assert data["weather_risk_score"] > 0
    assert data["terrain_risk_score"] > 0
    assert data["environmental_risk_score"] == round(data["weather_risk_score"] + data["terrain_risk_score"], 1)
    assert data["classification"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert isinstance(data["contributing_factors"], list)
    assert isinstance(data["explanation"], str)
    assert data["data_source"] == "synthetic_demo"
    assert data["environment"] == "demo"


def test_api_get_route_weather_valid():
    """Test GET /api/environment/routes/{route_id}/weather for valid route."""
    response = client.get("/api/environment/routes/GHY-SHL/weather")
    assert response.status_code == 200
    data = response.json()

    assert data["route_id"] == "GHY-SHL"
    assert "temperature_celsius" in data
    assert "rainfall_mm" in data
    assert "visibility_km" in data
    assert "wind_speed_kmh" in data
    assert data["data_source"] == "synthetic_demo"
    assert data["environment"] == "demo"


def test_api_get_route_terrain_valid():
    """Test GET /api/environment/routes/{route_id}/terrain for valid route."""
    response = client.get("/api/environment/routes/GHY-SHL/terrain")
    assert response.status_code == 200
    data = response.json()

    assert data["route_id"] == "GHY-SHL"
    assert "terrain_type" in data
    assert "elevation_factor" in data
    assert "slope_factor" in data
    assert "road_condition" in data
    assert data["data_source"] == "synthetic_demo"
    assert data["environment"] == "demo"


def test_api_unknown_route_returns_404():
    """Test GET /api/environment/routes/{unknown_id}/... returns HTTP 404."""
    r1 = client.get("/api/environment/routes/NON_EXISTENT_ROUTE/risk")
    assert r1.status_code == 404

    r2 = client.get("/api/environment/routes/NON_EXISTENT_ROUTE/weather")
    assert r2.status_code == 404

    r3 = client.get("/api/environment/routes/NON_EXISTENT_ROUTE/terrain")
    assert r3.status_code == 404
