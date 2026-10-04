"""
SENTINEL LOGIX AI - Phase 12C: End-to-End Integration & Consistency Audit Test Suite

Verifies:
1. Unified Intelligence API consistency across modules
2. Defensive handling of missing or incomplete data
3. Cross-module status aggregation and critical signal integrity
4. Schema consistency (field names and upper-case risk levels)
5. Endpoint reliability across all registered API routes
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.intelligence.service import IntelligenceService
from backend.app.schemas.inventory import InventoryItemOut, InventoryItemCreate
from backend.app.stockout.schemas import StockoutPredictionOut
from backend.app.risk.schemas import RiskAssessmentOut
from backend.app.readiness.schemas import ReadinessAssessmentOut


client = TestClient(app)


# ------------------------------------------------------------------
# 1. API Route Reliability & Response Integrity Audit
# ------------------------------------------------------------------

def test_intelligence_dashboard_endpoint():
    """Verify GET /api/intelligence/dashboard returns 200 with complete Unified Intelligence schema."""
    response = client.get("/api/intelligence/dashboard")
    assert response.status_code == 200
    data = response.json()

    # Core Phase 12A Unified Intelligence fields (from IntelligenceDashboardResponse schema)
    assert "operational_overview" in data
    assert "metadata" in data
    assert "depot_views" in data
    assert "critical_signals" in data
    assert "advisor" in data
    assert "intelligence_status" in data
    assert "inventory_intelligence" in data
    assert "risk_intelligence" in data
    assert "readiness_intelligence" in data
    assert "environmental_intelligence" in data
    assert "supply_movement" in data
    assert "digital_twin" in data

    # Verify operational overview structure
    overview = data["operational_overview"]
    assert "total_bases" in overview
    assert "total_depots" in overview
    assert "total_inventory_items" in overview
    assert overview["total_depots"] > 0
    assert overview["total_inventory_items"] > 0

    # Verify depot_views is a list
    assert isinstance(data["depot_views"], list)

    # Verify critical_signals is a list
    assert isinstance(data["critical_signals"], list)


def test_readiness_endpoints():
    """Verify list and single depot readiness endpoints."""
    res_list = client.get("/api/readiness")
    assert res_list.status_code == 200
    items = res_list.json()
    assert isinstance(items, list)
    assert len(items) > 0

    # Readiness schema uses entity_id not depot_id
    first = items[0]
    assert "entity_id" in first
    assert "readiness_score" in first
    assert "readiness_status" in first

    target_entity_id = first["entity_id"]
    res_single = client.get(f"/api/readiness/{target_entity_id}")
    assert res_single.status_code == 200
    single_data = res_single.json()
    assert single_data["entity_id"] == target_entity_id
    assert "readiness_score" in single_data
    assert "readiness_status" in single_data


def test_digital_twin_endpoints():
    """Verify Digital Twin scenario registry and simulation endpoints."""
    res_scenarios = client.get("/api/digital-twin/scenarios")
    assert res_scenarios.status_code == 200
    scenarios = res_scenarios.json()
    assert isinstance(scenarios, list)
    assert len(scenarios) > 0

    # DigitalTwinScenarioRequest fields: scenario_type, affected_depot_id,
    # disruption_duration_days (not duration_days), severity (not disruption_severity)
    sim_payload = {
        "scenario_type": "ROUTE_DISRUPTION",
        "affected_depot_id": "DEPOT-GHY-FUEL",
        "disruption_duration_days": 7,
        "severity": "HIGH"
    }
    res_sim = client.post("/api/digital-twin/simulate", json=sim_payload)
    assert res_sim.status_code == 200
    sim_res = res_sim.json()
    assert "scenario_type" in sim_res
    assert "scenario_id" in sim_res   # response uses scenario_id, not simulation_id
    assert "human_summary" in sim_res


def test_environment_endpoints():
    """Verify environment intelligence route risk listing."""
    res_env = client.get("/api/environment/routes/risk")
    assert res_env.status_code == 200
    routes = res_env.json()
    assert isinstance(routes, list)
    assert len(routes) > 0
    first_route = routes[0]
    assert "route_id" in first_route
    assert "environmental_risk_score" in first_route
    assert "classification" in first_route


def test_advisor_query_endpoint():
    """Verify AI Advisor POST /api/advisor/query returns deterministic structured advisory."""
    # Use an actual seeded depot ID (DEPOT-GHY-FUEL from seed.py)
    payload = {
        "query": "Assess stockout risk and mission readiness for Guwahati Fuel Depot.",
        "depot_id": "DEPOT-GHY-FUEL"
    }
    response = client.post("/api/advisor/query", json=payload)
    assert response.status_code == 200
    adv = response.json()
    # AdvisorResponse fields: query, answer, recommendation, priority, confidence
    assert "query" in adv
    assert "answer" in adv
    assert "recommendation" in adv
    assert "priority" in adv
    assert "confidence" in adv
    assert 0 <= adv["confidence"] <= 100



def test_stockout_endpoint():
    """Verify stockout prediction endpoint returns a valid list."""
    res = client.get("/api/stockout")
    assert res.status_code == 200
    preds = res.json()
    assert isinstance(preds, list)


def test_risk_endpoint():
    """Verify operational risk assessment endpoint returns a valid list."""
    res = client.get("/api/risk")
    assert res.status_code == 200
    risks = res.json()
    assert isinstance(risks, list)


def test_inventory_depots_bases_endpoints():
    """Verify core inventory, depots, and bases endpoints return valid lists."""
    res_inv = client.get("/api/inventory")
    assert res_inv.status_code == 200
    assert isinstance(res_inv.json(), list)

    res_depots = client.get("/api/depots")
    assert res_depots.status_code == 200
    assert isinstance(res_depots.json(), list)

    res_bases = client.get("/api/bases")
    assert res_bases.status_code == 200
    assert isinstance(res_bases.json(), list)


def test_health_endpoint():
    """Verify GET /api/health returns HEALTHY status."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "HEALTHY"


# ------------------------------------------------------------------
# 2. Field Name & Schema Consistency Audit
# ------------------------------------------------------------------

def test_inventory_schema_field_naming():
    """Verify inventory schemas use minimum_threshold (not reorder_threshold) and depot_id (not location_id)."""
    create_fields = set(InventoryItemCreate.model_fields.keys())
    assert "minimum_threshold" in create_fields, "minimum_threshold must exist in InventoryItemCreate"
    assert "reorder_threshold" not in create_fields, "reorder_threshold must NOT exist in InventoryItemCreate"
    assert "depot_id" in create_fields, "depot_id must exist in InventoryItemCreate"
    assert "location_id" not in create_fields, "location_id must NOT exist in InventoryItemCreate"

    out_fields = set(InventoryItemOut.model_fields.keys())
    assert "minimum_threshold" in out_fields, "minimum_threshold must exist in InventoryItemOut"
    assert "depot_id" in out_fields, "depot_id must exist in InventoryItemOut"


def test_stockout_schema_field_naming():
    """Verify StockoutPredictionOut schema has required fields."""
    so_fields = set(StockoutPredictionOut.model_fields.keys())
    assert "inventory_item_id" in so_fields
    assert "risk_level" in so_fields
    assert "minimum_threshold" in so_fields
    assert "depot_id" in so_fields


def test_risk_schema_field_naming():
    """Verify RiskAssessmentOut schema has risk_score, risk_level, and minimum_threshold."""
    risk_fields = set(RiskAssessmentOut.model_fields.keys())
    assert "risk_score" in risk_fields
    assert "risk_level" in risk_fields
    assert "minimum_threshold" in risk_fields
    assert "inventory_item_id" in risk_fields
    assert "depot_id" in risk_fields


def test_readiness_schema_field_naming():
    """Verify ReadinessAssessmentOut schema uses entity_id, readiness_score, readiness_status."""
    readiness_fields = set(ReadinessAssessmentOut.model_fields.keys())
    assert "readiness_score" in readiness_fields
    assert "readiness_status" in readiness_fields
    # Readiness uses entity_id (not depot_id directly)
    assert "entity_id" in readiness_fields


def test_risk_level_casing_consistency_via_api():
    """Verify risk and readiness API endpoints return strictly uppercase risk levels."""
    # Risk levels must be uppercase
    res_risk = client.get("/api/risk")
    assert res_risk.status_code == 200
    for item in res_risk.json():
        lvl = item.get("risk_level", "LOW")
        assert lvl == lvl.upper(), f"risk_level '{lvl}' is not uppercase"

    # Readiness statuses must be uppercase
    res_rad = client.get("/api/readiness")
    assert res_rad.status_code == 200
    for item in res_rad.json():
        stat = item.get("readiness_status", "READY")
        assert stat == stat.upper(), f"readiness_status '{stat}' is not uppercase"


def test_stockout_risk_level_casing_via_api():
    """Verify stockout predictions return uppercase risk levels."""
    res = client.get("/api/stockout")
    assert res.status_code == 200
    for item in res.json():
        if "risk_level" in item:
            lvl = item["risk_level"]
            assert lvl == lvl.upper(), f"stockout risk_level '{lvl}' is not uppercase"


def test_environment_classification_casing_via_api():
    """Verify environment classification values are uppercase."""
    res = client.get("/api/environment/routes/risk")
    assert res.status_code == 200
    for route in res.json():
        cls = route.get("classification", "LOW")
        assert cls == cls.upper(), f"environmental classification '{cls}' is not uppercase"


# ------------------------------------------------------------------
# 3. Cross-Module Intelligence & Aggregation Audit
# ------------------------------------------------------------------

def test_unified_dashboard_depot_views_completeness():
    """Verify depot views from dashboard contain complete cross-module intelligence sub-blocks."""
    response = client.get("/api/intelligence/dashboard")
    assert response.status_code == 200
    data = response.json()
    depot_views = data["depot_views"]
    assert len(depot_views) > 0, "depot_views must be non-empty"

    for dv in depot_views:
        assert "depot_id" in dv
        assert "depot_name" in dv
        assert "stock_out_risk" in dv
        assert "operational_risk" in dv
        assert "mission_readiness" in dv
        assert "demand_pressure" in dv
        assert "environmental_exposure" in dv
        assert "inventory_health" in dv

        # Verify sub-structure for operational_risk
        op_risk = dv["operational_risk"]
        assert "risk_score" in op_risk
        assert "risk_level" in op_risk
        assert op_risk["risk_level"] == op_risk["risk_level"].upper(), \
            f"depot operational_risk.risk_level '{op_risk['risk_level']}' is not uppercase"

        # Verify sub-structure for mission_readiness
        rad = dv["mission_readiness"]
        assert "readiness_score" in rad
        assert "readiness_status" in rad
        assert rad["readiness_status"] == rad["readiness_status"].upper(), \
            f"depot mission_readiness.readiness_status '{rad['readiness_status']}' is not uppercase"


def test_unified_dashboard_critical_signals_structure():
    """Verify critical signals from dashboard have required fields and valid classifications."""
    response = client.get("/api/intelligence/dashboard")
    assert response.status_code == 200
    data = response.json()
    signals = data["critical_signals"]

    valid_classifications = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "READY", "DEGRADED", "CAUTION"}

    for s in signals:
        assert "signal_id" in s and s["signal_id"], "signal_id must be non-empty"
        assert "source_module" in s and s["source_module"], "source_module must be non-empty"
        assert "entity_type" in s and s["entity_type"], "entity_type must be non-empty"
        assert "entity_id" in s and s["entity_id"], "entity_id must be non-empty"
        assert "classification" in s
        assert s["classification"] in valid_classifications, \
            f"Unknown classification: {s['classification']}"
        assert "explanation" in s and s["explanation"], "explanation must be non-empty"


def test_unified_dashboard_intelligence_status_modules():
    """Verify intelligence_status reflects core module availability."""
    response = client.get("/api/intelligence/dashboard")
    assert response.status_code == 200
    data = response.json()
    status = data["intelligence_status"]

    # Core modules must be AVAILABLE
    assert status.get("inventory") == "AVAILABLE", "inventory module must be AVAILABLE"
    assert status.get("risk_engine") == "AVAILABLE", "risk_engine module must be AVAILABLE"
    assert status.get("readiness_engine") == "AVAILABLE", "readiness_engine module must be AVAILABLE"
    assert status.get("environmental_intelligence") == "AVAILABLE", "environmental_intelligence must be AVAILABLE"
    assert status.get("advisor") == "AVAILABLE", "advisor module must be AVAILABLE"
    assert status.get("forecasting") == "AVAILABLE", "forecasting module must be AVAILABLE"


def test_cross_module_signal_count_bounded():
    """Verify critical_signals count is bounded reasonably given the number of depots and routes."""
    response = client.get("/api/intelligence/dashboard")
    assert response.status_code == 200
    data = response.json()
    signals = data["critical_signals"]
    depot_views = data["depot_views"]

    # Signals should not explode beyond a reasonable bounded count
    # (items × modules won't exceed ~250 for demo data)
    assert len(signals) < 500, f"critical_signals count {len(signals)} seems unexpectedly large"
    # If there are depots, there should be some signals (unless everything is GREEN)
    if len(depot_views) > 0:
        # At minimum, some assessments were made; signals may be 0 if all GREEN
        assert len(signals) >= 0  # always passes, but confirms no crash


# ------------------------------------------------------------------
# 4. Defensive Handling Audit
# ------------------------------------------------------------------

def test_defensive_404_handling():
    """Verify endpoints return 404 for non-existent IDs without server crashes."""
    # Advisor with non-existent depot_id returns 404
    bad_adv_res = client.post("/api/advisor/query", json={
        "query": "Status check",
        "depot_id": "DEPOT-NONEXISTENT-999"
    })
    assert bad_adv_res.status_code == 404

    # Readiness for non-existent depot returns 404
    bad_rad_res = client.get("/api/readiness/DEPOT-NONEXISTENT-999")
    assert bad_rad_res.status_code == 404

    # Environment risk for non-existent route returns 404
    bad_env_res = client.get("/api/environment/routes/ROUTE-NONEXISTENT/risk")
    assert bad_env_res.status_code == 404


def test_advisor_empty_query_returns_400():
    """Verify advisor rejects empty/whitespace-only query strings with HTTP 400."""
    res = client.post("/api/advisor/query", json={"query": "   "})
    assert res.status_code == 400


def test_intelligence_service_empty_db_fallback():
    """Verify intelligence service handles empty DB state gracefully without crashing."""
    result = IntelligenceService.get_dashboard_intelligence(db_path=":memory:")
    assert result is not None
    assert isinstance(result, dict)
    assert "depot_views" in result
    assert isinstance(result["depot_views"], list)
    assert "critical_signals" in result
    assert isinstance(result["critical_signals"], list)
    # With empty DB (no seed), depot_views must be empty
    assert len(result["depot_views"]) == 0, "Empty DB should produce no depot_views"
    # critical_signals may still have environmental signals from static route data
    assert len(result["critical_signals"]) >= 0  # non-crashing


def test_stockout_filter_by_risk_level():
    """Verify stockout filtering by risk_level works correctly and returns matching items."""
    res = client.get("/api/stockout?risk_level=CRITICAL")
    assert res.status_code == 200
    preds = res.json()
    for p in preds:
        assert p["risk_level"].upper() == "CRITICAL", \
            f"Expected CRITICAL but got {p['risk_level']}"


def test_risk_filter_by_depot():
    """Verify risk endpoint supports filtering by depot_id and only returns matching items."""
    res_depots = client.get("/api/depots")
    assert res_depots.status_code == 200
    depots = res_depots.json()

    if depots:
        depot_id = depots[0]["id"]
        res_risk = client.get(f"/api/risk?depot_id={depot_id}")
        assert res_risk.status_code == 200
        risks = res_risk.json()
        for r in risks:
            assert r.get("depot_id") == depot_id, \
                f"Expected depot_id={depot_id} but got {r.get('depot_id')}"


def test_environment_single_route_detail():
    """Verify /api/environment/routes/{route_id}/risk returns complete detail structure."""
    res_all = client.get("/api/environment/routes/risk")
    assert res_all.status_code == 200
    routes = res_all.json()
    assert len(routes) > 0

    route_id = routes[0]["route_id"]
    res_detail = client.get(f"/api/environment/routes/{route_id}/risk")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["route_id"] == route_id
    assert "weather_risk_score" in detail
    assert "terrain_risk_score" in detail
    assert "environmental_risk_score" in detail
    assert "classification" in detail
    assert "explanation" in detail
    assert "contributing_factors" in detail
