"""
Unit & Integration tests for SENTINEL LOGIX AI Intelligence Dashboard API.
Verifies aggregation of operational overview, inventory, risk, readiness, demand,
supply movement, Digital Twin status, and metadata without database mutations.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db, get_db
from backend.app.db.seed import seed_database
from backend.app.intelligence import IntelligenceService
from backend.app.digital_twin import DigitalTwinScenarioRequest, DigitalTwinService

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Fixture initializing isolated test SQLite database populated with seed data."""
    test_db_file = str(tmp_path / "test_sentinel_intelligence.db")
    import backend.app.config as config
    config.DB_PATH = test_db_file
    init_db(test_db_file)
    seed_database(test_db_file)
    yield test_db_file

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# 1. GET /api/intelligence/dashboard returns HTTP 200
def test_dashboard_endpoint_returns_200(client):
    resp = client.get("/api/intelligence/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "metadata" in data
    assert "operational_overview" in data

# 2. Response follows explicit schema structure
def test_dashboard_response_schema(client):
    resp = client.get("/api/intelligence/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metadata"]["data_source"] == "synthetic_demo"
    assert data["metadata"]["environment"] == "demo"
    assert "generated_at" in data["metadata"]
    assert "operational_overview" in data
    assert "inventory_intelligence" in data
    assert "risk_intelligence" in data
    assert "readiness_intelligence" in data
    assert "demand_intelligence" in data
    assert "supply_movement" in data
    assert "digital_twin" in data
    assert "intelligence_status" in data

# 3. Inventory information aggregates existing inventory records
def test_dashboard_inventory_intelligence(setup_test_db):
    intel = IntelligenceService.get_dashboard_intelligence(db_path=setup_test_db)
    inv = intel["inventory_intelligence"]
    assert inv["total_tracked_inventory_quantity"] > 0
    assert inv["critical_inventory_items_count"] >= 1
    assert len(inv["items_summary"]) >= 5

# 4. Stock-out information incorporates existing stock-out predictions
def test_dashboard_stockout_predictions(setup_test_db):
    intel = IntelligenceService.get_dashboard_intelligence(db_path=setup_test_db)
    inv = intel["inventory_intelligence"]
    assert "stockout_projected_count" in inv
    assert inv["stockout_projected_count"] >= 1

# 5. Risk information aggregates existing risk service assessments
def test_dashboard_risk_intelligence(setup_test_db):
    intel = IntelligenceService.get_dashboard_intelligence(db_path=setup_test_db)
    risk = intel["risk_intelligence"]
    assert risk["overall_risk_level"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
    assert "risk_classification_counts" in risk
    assert risk["highest_risk_score"] >= 0.0

# 6. Readiness information aggregates existing readiness service assessments
def test_dashboard_readiness_intelligence(setup_test_db):
    intel = IntelligenceService.get_dashboard_intelligence(db_path=setup_test_db)
    readiness = intel["readiness_intelligence"]
    assert readiness["overall_readiness_status"] in ("READY", "CAUTION", "DEGRADED", "CRITICAL")
    assert "readiness_status_counts" in readiness
    assert 0.0 <= readiness["average_readiness_score"] <= 100.0

# 7. Demand information incorporates forecasting logic
def test_dashboard_demand_intelligence(setup_test_db):
    intel = IntelligenceService.get_dashboard_intelligence(db_path=setup_test_db)
    demand = intel["demand_intelligence"]
    assert demand["forecast_horizon_days"] == 14
    assert demand["forecast_model_status"] == "ACTIVE"
    assert isinstance(demand["high_pressure_items"], list)

# 8. Supply movement information includes shipment statistics
def test_dashboard_supply_movement(setup_test_db):
    intel = IntelligenceService.get_dashboard_intelligence(db_path=setup_test_db)
    supply = intel["supply_movement"]
    assert supply["total_shipments_count"] >= 4
    assert supply["in_transit_shipments_count"] >= 1
    assert supply["shipment_routes_count"] >= 2

# 9. Synthetic data metadata is present and explicitly labeled
def test_dashboard_synthetic_metadata(client):
    resp = client.get("/api/intelligence/dashboard")
    assert resp.status_code == 200
    meta = resp.json()["metadata"]
    assert meta["data_source"] == "synthetic_demo"
    assert meta["environment"] == "demo"

# 10. Digital Twin scenario integration when active scenario result is supplied
def test_dashboard_digital_twin_scenario_integration(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=2,
        severity="HIGH"
    )
    sim_result = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)

    intel = IntelligenceService.get_dashboard_intelligence(
        db_path=setup_test_db,
        active_simulation_result=sim_result
    )

    dt = intel["digital_twin"]
    assert dt["scenario_available"] is True
    assert dt["scenario_type"] == "ROUTE_DISRUPTION"
    assert dt["affected_depot_id"] == "DEPOT-IMP-SUP"
    assert dt["risk_delta"] is not None
    assert dt["readiness_delta"] is not None
    assert dt["human_summary"] is not None

# 11. Partial module status flags modules as AVAILABLE or NO_ACTIVE_SCENARIO
def test_dashboard_module_status(client):
    resp = client.get("/api/intelligence/dashboard")
    assert resp.status_code == 200
    status = resp.json()["intelligence_status"]
    assert status["operational_data"] == "AVAILABLE"
    assert status["inventory"] == "AVAILABLE"
    assert status["digital_twin"] == "NO_ACTIVE_SCENARIO"

# 12. Database remains completely unchanged after calling dashboard API
def test_dashboard_zero_database_mutations(setup_test_db):
    with get_db(setup_test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, current_quantity FROM inventory_items ORDER BY id")
        before_inv = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT id, status FROM depots ORDER BY id")
        before_depots = [dict(r) for r in cursor.fetchall()]

    _ = IntelligenceService.get_dashboard_intelligence(db_path=setup_test_db)

    with get_db(setup_test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, current_quantity FROM inventory_items ORDER BY id")
        after_inv = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT id, status FROM depots ORDER BY id")
        after_depots = [dict(r) for r in cursor.fetchall()]

    assert before_inv == after_inv
    assert before_depots == after_depots

# 13. Environmental Intelligence section exists and aggregates metrics correctly
def test_dashboard_environmental_intelligence(setup_test_db):
    intel = IntelligenceService.get_dashboard_intelligence(db_path=setup_test_db)
    assert "environmental_intelligence" in intel
    env = intel["environmental_intelligence"]

    assert env["total_routes_assessed"] > 0
    assert (
        env["low_risk_routes"]
        + env["medium_risk_routes"]
        + env["high_risk_routes"]
        + env["critical_risk_routes"]
    ) == env["total_routes_assessed"]

    assert env["highest_risk_route"] == "TEZ-TWA"
    assert env["highest_risk_score"] >= 75.0
    assert (
        env["weather_dominant_routes"] + env["terrain_dominant_routes"]
    ) == env["total_routes_assessed"]

    assert len(env["routes"]) == env["total_routes_assessed"]
    sample_route = env["routes"][0]
    assert "route_id" in sample_route
    assert "route_name" in sample_route
    assert "weather_risk_score" in sample_route
    assert "terrain_risk_score" in sample_route
    assert "environmental_risk_score" in sample_route
    assert sample_route["classification"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert sample_route["dominant_dimension"] in {"WEATHER", "TERRAIN"}
    assert isinstance(sample_route["explanation"], str)

    assert env["data_source"] == "synthetic_demo"
    assert env["environment"] == "demo"

# 14. Module status reports environmental intelligence as AVAILABLE
def test_dashboard_environmental_status(client):
    resp = client.get("/api/intelligence/dashboard")
    assert resp.status_code == 200
    status = resp.json()["intelligence_status"]
    assert status["environmental_intelligence"] == "AVAILABLE"

# 15. Regression: Verify existing operational risk, readiness, and all existing sections remain intact
def test_dashboard_regression_integrity(client):
    resp = client.get("/api/intelligence/dashboard")
    assert resp.status_code == 200
    data = resp.json()

    # All required dashboard keys present
    expected_keys = {
        "metadata",
        "operational_overview",
        "inventory_intelligence",
        "risk_intelligence",
        "readiness_intelligence",
        "demand_intelligence",
        "supply_movement",
        "environmental_intelligence",
        "digital_twin",
        "intelligence_status",
    }
    assert expected_keys.issubset(data.keys())

    # Operational risk calculation remains untouched
    assert "overall_risk_level" in data["risk_intelligence"]
    assert "highest_risk_score" in data["risk_intelligence"]

    # Readiness calculation remains untouched
    assert "overall_readiness_status" in data["readiness_intelligence"]
    assert "average_readiness_score" in data["readiness_intelligence"]

