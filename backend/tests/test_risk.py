"""
Unit tests for SENTINEL LOGIX AI Risk Intelligence Engine & API.
Verifies signal aggregation, deterministic 0-100 risk scoring, explainability narrative generation,
and GET /api/risk API endpoints and filters.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db
from backend.app.db.seed import seed_database
from backend.app.risk import assess_logistics_risk, RiskService

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Fixture initializing isolated test SQLite database populated with seed data."""
    test_db_file = str(tmp_path / "test_sentinel_risk.db")
    import backend.app.config as config
    config.DB_PATH = test_db_file
    init_db(test_db_file)
    seed_database(test_db_file)
    yield test_db_file

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# 1. Risk assessment is generated successfully & score is bounded between 0 and 100
def test_risk_assessment_generation_and_score_bounds(setup_test_db):
    results = RiskService.get_risk_assessments(db_path=setup_test_db)
    assert len(results) > 0
    for r in results:
        assert 0.0 <= r["risk_score"] <= 100.0
        assert r["risk_level"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
        assert r["data_source"] == "synthetic_demo"

# 2. Risk level matches documented score thresholds
def test_risk_level_threshold_mapping():
    mock_item = {"id": "ITEM-1", "current_quantity": 10000.0, "minimum_threshold": 1000.0}
    mock_depot = {"id": "DEPOT-1", "name": "Test Depot"}
    mock_stockout_low = {"risk_level": "LOW", "days_until_threshold_breach": None}
    mock_stockout_crit = {"risk_level": "CRITICAL", "days_until_threshold_breach": 0}

    # Healthy -> LOW
    res_low = assess_logistics_risk(mock_item, mock_depot, mock_stockout_low, [], [])
    assert res_low["risk_level"] == "LOW"
    assert res_low["risk_score"] < 35.0

    # Critical stockout -> CRITICAL
    res_crit = assess_logistics_risk(mock_item, mock_depot, mock_stockout_crit, [], [])
    assert res_crit["risk_level"] == "CRITICAL"
    assert res_crit["risk_score"] >= 40.0

# 3. Stock-out information is incorporated
def test_stockout_information_incorporation():
    mock_item = {"id": "ITEM-SO", "current_quantity": 5000.0, "minimum_threshold": 1000.0}
    mock_depot = {"id": "DEPOT-1"}

    so_low = {"risk_level": "LOW"}
    so_high = {"risk_level": "HIGH"}

    res_low = assess_logistics_risk(mock_item, mock_depot, so_low, [], [])
    res_high = assess_logistics_risk(mock_item, mock_depot, so_high, [], [])

    assert res_high["risk_score"] > res_low["risk_score"]
    assert res_high["stockout_risk"] == "HIGH"

# 4. Below-threshold inventory increases risk
def test_below_threshold_inventory_increases_risk():
    mock_depot = {"id": "DEPOT-1"}
    so_dummy = {"risk_level": "LOW"}

    item_healthy = {"id": "ITEM-1", "current_quantity": 5000.0, "minimum_threshold": 1000.0}
    item_below = {"id": "ITEM-1", "current_quantity": 500.0, "minimum_threshold": 1000.0}

    res_healthy = assess_logistics_risk(item_healthy, mock_depot, so_dummy, [], [])
    res_below = assess_logistics_risk(item_below, mock_depot, so_dummy, [], [])

    assert res_below["risk_score"] > res_healthy["risk_score"]
    assert res_below["inventory_signal"]["status"] == "BELOW_THRESHOLD"

# 5. Incident signal handling (Active incident vs No incident)
def test_incident_signal_handling():
    mock_item = {"id": "ITEM-1", "current_quantity": 5000.0, "minimum_threshold": 1000.0}
    mock_depot = {"id": "DEPOT-1"}
    so_dummy = {"risk_level": "LOW"}

    no_incidents = []
    active_incidents = [
        {"id": "INC-1", "severity": "HIGH", "is_active": 1, "title": "Landslide"}
    ]

    res_no_inc = assess_logistics_risk(mock_item, mock_depot, so_dummy, no_incidents, [])
    res_inc = assess_logistics_risk(mock_item, mock_depot, so_dummy, active_incidents, [])

    assert res_inc["risk_score"] > res_no_inc["risk_score"]
    assert res_inc["incident_signal"]["contribution"] == 20.0
    assert res_no_inc["incident_signal"]["contribution"] == 0.0

# 6. Explanation contains actual contributing factors
def test_explanation_contains_contributing_factors():
    mock_item = {"id": "ITEM-EXP", "item_name": "Rations Pack", "current_quantity": 500.0, "minimum_threshold": 1000.0, "unit": "BOXES"}
    mock_depot = {"id": "DEPOT-1", "name": "Forward Depot"}
    so = {"risk_level": "CRITICAL", "days_until_threshold_breach": 0}
    active_inc = [{"id": "INC-1", "severity": "HIGH", "is_active": 1, "title": "Flood"}]

    res = assess_logistics_risk(mock_item, mock_depot, so, active_inc, [])
    exp = res["explanation"]

    assert "Rations Pack" in exp
    assert "Forward Depot" in exp
    assert "Score:" in exp
    assert "500.0 BOXES" in exp
    assert "1,000.0 BOXES" in exp
    assert len(res["contributing_factors"]) == 4

# 7. GET /api/risk endpoint and filters
def test_risk_api_endpoints(client):
    # Unfiltered
    resp = client.get("/api/risk")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    for r in data:
        assert r["data_source"] == "synthetic_demo"

    # Filter by inventory_item_id
    resp_item = client.get("/api/risk?inventory_item_id=INV-IMP-RATIONS")
    assert resp_item.status_code == 200
    data_item = resp_item.json()
    assert len(data_item) == 1
    assert data_item[0]["inventory_item_id"] == "INV-IMP-RATIONS"

    # Filter by risk_level
    resp_risk = client.get("/api/risk?risk_level=CRITICAL")
    assert resp_risk.status_code == 200
    for r in resp_risk.json():
        assert r["risk_level"] == "CRITICAL"

    # Single item endpoint GET /api/risk/{inventory_item_id}
    resp_single = client.get("/api/risk/INV-IMP-RATIONS")
    assert resp_single.status_code == 200
    assert resp_single.json()["inventory_item_id"] == "INV-IMP-RATIONS"

    # Unknown item returns 404
    resp_404 = client.get("/api/risk/NONEXISTENT-ITEM")
    assert resp_404.status_code == 404

# 8. Phase 10C: Environmental risk signal appears when route mapping exists
def test_environmental_risk_integration_mapped(setup_test_db):
    results = RiskService.get_risk_assessments(depot_id="DEPOT-TWA-AMM", db_path=setup_test_db)
    assert len(results) > 0
    res = results[0]

    assert "environmental_signal" in res
    env_sig = res["environmental_signal"]
    assert env_sig["status"] == "AVAILABLE"
    assert env_sig["route_id"] == "TEZ-TWA"
    assert env_sig["environmental_risk_score"] >= 75.0
    assert env_sig["contribution"] > 10.0
    assert env_sig["classification"] == "CRITICAL"
    assert env_sig["dominant_dimension"] == "WEATHER"

    # Verify structured contributing factor
    env_factors = [f for f in res["contributing_factors"] if f["signal"] == "environmental_risk"]
    assert len(env_factors) == 1
    assert env_factors[0]["severity"] == "CRITICAL"
    assert "TEZ-TWA" in env_factors[0]["message"]

# 9. Phase 10C: Unmapped depot is handled safely without error or fabricated route
def test_environmental_risk_unmapped_depot():
    mock_item = {"id": "ITEM-UNMAPPED", "depot_id": "DEPOT-UNMAPPED-999", "current_quantity": 5000.0, "minimum_threshold": 1000.0}
    mock_depot = {"id": "DEPOT-UNMAPPED-999", "name": "Unmapped Test Depot"}
    so_dummy = {"risk_level": "LOW"}

    res = assess_logistics_risk(mock_item, mock_depot, so_dummy, [], [], environmental_assessment=None)
    assert res["environmental_signal"]["status"] == "UNAVAILABLE"
    assert res["environmental_signal"]["route_id"] is None
    assert res["environmental_signal"]["contribution"] == 0.0
    assert 0.0 <= res["risk_score"] <= 100.0

# 10. Phase 10C: Severe environmental conditions increase operational risk score
def test_severe_environmental_conditions_increase_risk():
    mock_item = {"id": "ITEM-TEST", "current_quantity": 5000.0, "minimum_threshold": 1000.0}
    mock_depot = {"id": "DEPOT-TWA-AMM"}
    so_dummy = {"risk_level": "LOW"}

    mild_env = {"route_id": "GHY-TEZ", "environmental_risk_score": 10.0, "classification": "LOW", "weather_risk_score": 2.0, "terrain_risk_score": 8.0}
    severe_env = {"route_id": "TEZ-TWA", "environmental_risk_score": 93.0, "classification": "CRITICAL", "weather_risk_score": 49.0, "terrain_risk_score": 44.0}

    res_mild = assess_logistics_risk(mock_item, mock_depot, so_dummy, [], [], environmental_assessment=mild_env)
    res_severe = assess_logistics_risk(mock_item, mock_depot, so_dummy, [], [], environmental_assessment=severe_env)

    assert res_severe["risk_score"] > res_mild["risk_score"]
    assert res_severe["environmental_signal"]["contribution"] > res_mild["environmental_signal"]["contribution"]

