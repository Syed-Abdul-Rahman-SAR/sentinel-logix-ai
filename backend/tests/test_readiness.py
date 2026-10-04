"""
Unit tests for SENTINEL LOGIX AI Mission Readiness Engine & API.
Verifies signal aggregation, 0-100 deterministic readiness scoring, strict capping rules,
narrative explanation generation, and GET /api/readiness API endpoints and filters.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db
from backend.app.db.seed import seed_database
from backend.app.readiness import assess_depot_readiness, ReadinessService

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Fixture initializing isolated test SQLite database populated with seed data."""
    test_db_file = str(tmp_path / "test_sentinel_readiness.db")
    import backend.app.config as config
    config.DB_PATH = test_db_file
    init_db(test_db_file)
    seed_database(test_db_file)
    yield test_db_file

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# 1. Readiness assessment score bounds & status mapping
def test_readiness_assessment_generation_and_score_bounds(setup_test_db):
    results = ReadinessService.get_readiness_assessments(db_path=setup_test_db)
    assert len(results) > 0
    for r in results:
        assert 0.0 <= r["readiness_score"] <= 100.0
        assert r["readiness_status"] in ("READY", "CAUTION", "DEGRADED", "CRITICAL")
        assert r["data_source"] == "synthetic_demo"
        assert "components" in r
        assert "supporting_info" in r
        assert "contributing_factors" in r

# 2. Healthy depot yields high readiness score (READY)
def test_healthy_depot_readiness_mapping():
    mock_depot = {"id": "DEPOT-HEALTHY", "name": "Guwahati Strategic Fuel Depot", "base_id": "BASE-GHY"}
    mock_base = {"id": "BASE-GHY", "name": "Guwahati Central Logistics Hub"}
    mock_items = [
        {"id": "INV-1", "current_quantity": 38000.0, "minimum_threshold": 10000.0, "daily_consumption_rate": 500.0, "criticality": "CRITICAL"}
    ]
    mock_so = [{"risk_level": "LOW"}]
    mock_risk = [{"risk_score": 15.0, "risk_level": "LOW"}]

    res = assess_depot_readiness(mock_depot, mock_base, mock_items, mock_so, mock_risk)
    assert res["readiness_score"] >= 85.0
    assert res["readiness_status"] == "READY"
    assert res["components"]["inventory_component"] == 35.0
    assert res["components"]["stockout_component"] == 30.0

# 3. Critical stock-out risk triggers status cap to DEGRADED
def test_critical_stockout_triggers_degraded_cap():
    mock_depot = {"id": "DEPOT-CRIT-SO", "name": "Critical Depot", "base_id": "BASE-IMP"}
    mock_base = {"id": "BASE-IMP", "name": "Imphal Forward Base"}
    mock_items = [
        {"id": "INV-1", "current_quantity": 5000.0, "minimum_threshold": 1000.0, "daily_consumption_rate": 200.0, "criticality": "HIGH"}
    ]
    # Critical stockout risk present
    mock_so = [{"risk_level": "CRITICAL"}]
    mock_risk = [{"risk_score": 30.0, "risk_level": "LOW"}]

    res = assess_depot_readiness(mock_depot, mock_base, mock_items, mock_so, mock_risk)
    assert res["components"]["stockout_component"] == 0.0
    assert res["supporting_info"]["critical_stockout_count"] == 1
    # Even if total score could be > 65, status capped to DEGRADED
    assert res["readiness_status"] in ("DEGRADED", "CRITICAL")

# 4. Inventory below threshold reduces inventory component
def test_below_threshold_inventory_reduces_score():
    mock_depot = {"id": "DEPOT-BELOW", "name": "Depot Below", "base_id": "BASE-TWA"}
    mock_base = {"id": "BASE-TWA", "name": "Tawang FOB"}
    mock_items = [
        {"id": "INV-1", "current_quantity": 400.0, "minimum_threshold": 1000.0, "daily_consumption_rate": 100.0, "criticality": "HIGH"}
    ]
    mock_so = [{"risk_level": "LOW"}]
    mock_risk = [{"risk_score": 20.0, "risk_level": "LOW"}]

    res = assess_depot_readiness(mock_depot, mock_base, mock_items, mock_so, mock_risk)
    assert res["components"]["inventory_component"] == 0.0
    assert res["supporting_info"]["below_threshold_count"] == 1

# 5. Narrative explanation content verification
def test_readiness_narrative_explanation():
    mock_depot = {"id": "DEPOT-1", "name": "Shillong Med Depot", "base_id": "BASE-SHL"}
    mock_base = {"id": "BASE-SHL", "name": "Shillong Base"}
    mock_items = [{"id": "INV-1", "current_quantity": 600.0, "minimum_threshold": 500.0}]
    mock_so = [{"risk_level": "LOW"}]
    mock_risk = [{"risk_score": 10.0, "risk_level": "LOW"}]

    res = assess_depot_readiness(mock_depot, mock_base, mock_items, mock_so, mock_risk)
    exp = res["explanation"]

    assert "Shillong Med Depot" in exp
    assert "Shillong Base" in exp
    assert "Score:" in exp
    assert "Mission Readiness status evaluated at" in exp

# 6. GET /api/readiness API endpoints and filter testing
def test_readiness_api_endpoints(client):
    # Unfiltered query
    resp = client.get("/api/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    for item in data:
        assert item["data_source"] == "synthetic_demo"

    # Filter by depot_id
    resp_depot = client.get("/api/readiness?depot_id=DEPOT-GHY-FUEL")
    assert resp_depot.status_code == 200
    data_depot = resp_depot.json()
    assert len(data_depot) == 1
    assert data_depot[0]["entity_id"] == "DEPOT-GHY-FUEL"

    # Filter by base_id
    resp_base = client.get("/api/readiness?base_id=BASE-GHY")
    assert resp_base.status_code == 200
    data_base = resp_base.json()
    assert len(data_base) == 2  # GHY fuel & GHY food depots

    # Filter by readiness_status
    resp_status = client.get("/api/readiness?readiness_status=READY")
    assert resp_status.status_code == 200
    for item in resp_status.json():
        assert item["readiness_status"] == "READY"

    # Single depot GET /api/readiness/{depot_id}
    resp_single = client.get("/api/readiness/DEPOT-GHY-FUEL")
    assert resp_single.status_code == 200
    assert resp_single.json()["entity_id"] == "DEPOT-GHY-FUEL"

    # Unknown depot returns 404
    resp_404 = client.get("/api/readiness/NONEXISTENT-DEPOT")
    assert resp_404.status_code == 404
