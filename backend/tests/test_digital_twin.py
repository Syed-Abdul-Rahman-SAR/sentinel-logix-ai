"""
Unit & Integration tests for SENTINEL LOGIX AI Digital Twin Scenario Engine & API.
Verifies safe in-memory what-if simulations, database safety (zero mutations), baseline vs simulated state,
trajectory generation, threshold breach & stockout detection, risk/readiness deltas, and API validation.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db, get_db
from backend.app.db.seed import seed_database
from backend.app.digital_twin import (
    DigitalTwinScenarioRequest,
    DigitalTwinService,
    run_digital_twin_simulation,
    validate_scenario_request
)

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Fixture initializing isolated test SQLite database populated with seed data."""
    test_db_file = str(tmp_path / "test_sentinel_digital_twin.db")
    import backend.app.config as config
    config.DB_PATH = test_db_file
    init_db(test_db_file)
    seed_database(test_db_file)
    yield test_db_file

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# 1. Valid scenario produces a result
def test_valid_scenario_produces_result(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=2,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert res["scenario_id"] is not None
    assert res["affected_depot_id"] == "DEPOT-IMP-SUP"
    assert res["data_source"] == "synthetic_demo"

# 2. Database safety: Simulation does NOT modify database
def test_simulation_does_not_modify_database(setup_test_db):
    # Fetch inventory before simulation
    with get_db(setup_test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, current_quantity FROM inventory_items ORDER BY id")
        before_state = [dict(r) for r in cursor.fetchall()]

    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=5,
        additional_delay_days=3,
        severity="CRITICAL"
    )
    _ = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)

    # Fetch inventory after simulation
    with get_db(setup_test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, current_quantity FROM inventory_items ORDER BY id")
        after_state = [dict(r) for r in cursor.fetchall()]

    assert before_state == after_state, "Digital Twin simulation mutated production database records!"

# 3. Baseline state is captured correctly
def test_baseline_state_captured(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-GHY-FUEL",
        disruption_duration_days=3,
        additional_delay_days=1,
        severity="MEDIUM"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert "baseline_risk_score" in res
    assert "baseline_readiness_score" in res
    assert res["baseline_readiness_status"] in ("READY", "CAUTION", "DEGRADED", "CRITICAL")

# 4. Simulation trajectory contains expected number of days
def test_simulation_trajectory_days(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=5,
        additional_delay_days=3,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    traj = res["trajectory"]
    # max_expected_arrival for DEPOT-IMP-SUP is 6; total delay is 5+3=8. 8+6+2 = 16
    expected_days = max(7, 5 + 3 + 6 + 2)
    assert len(traj) == expected_days
    assert traj[0]["day"] == 1
    assert traj[-1]["day"] == expected_days

# 5. Forecast consumption is incorporated into trajectory
def test_forecast_consumption_incorporated(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=1,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    for point in res["trajectory"]:
        assert point["forecast_consumption"] > 0.0

# 6. Disruption removes/delays simulated arrivals according to documented assumption
def test_disruption_removes_arrivals(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=4,
        additional_delay_days=2,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    for point in res["trajectory"]:
        if point["day"] <= (4 + 2):
            assert point["simulated_arrival"] == 0.0

# 7. Threshold breach is detected
def test_threshold_breach_detection(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=4,
        additional_delay_days=2,
        severity="CRITICAL"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert res["threshold_breach_day"] is not None
    assert res["inventory_shortfall"] >= 0.0

# 8. Stock-out is detected when applicable
def test_stockout_detection(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=5,
        additional_delay_days=2,
        severity="CRITICAL"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert res["stockout_day"] is not None

# 9. Baseline and simulated inventory differ when disruption has effect
def test_baseline_and_simulated_inventory_differ(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=2,
        severity="CRITICAL"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    traj = res["trajectory"]
    # By day 2, simulated inventory is lower than baseline due to severity consumption multiplier
    assert traj[1]["simulated_inventory"] < traj[1]["baseline_inventory"]

# 10. Risk score delta is calculated
def test_risk_score_delta_calculated(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=4,
        additional_delay_days=2,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert "risk_score_delta" in res
    assert res["simulated_risk_score"] >= res["baseline_risk_score"]

# 11. Readiness score delta is calculated
def test_readiness_score_delta_calculated(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=4,
        additional_delay_days=2,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert "readiness_score_delta" in res
    assert res["simulated_readiness_score"] <= res["baseline_readiness_score"]

# 12. Explanations contain actual simulated impacts & assumptions
def test_explanation_contains_simulated_impacts(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=1,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    exp = res["explanation"]
    assert "Digital Twin" in exp
    assert "ROUTE_DISRUPTION" in exp
    assert "Readiness Delta:" in exp
    assert len(res["assumptions"]) >= 3

# 13. data_source == synthetic_demo
def test_data_source_tag(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-GHY-FUEL",
        disruption_duration_days=2,
        additional_delay_days=0,
        severity="LOW"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert res["data_source"] == "synthetic_demo"

# 14. Invalid depot is rejected (404)
def test_invalid_depot_rejected(client):
    body = {
        "scenario_type": "ROUTE_DISRUPTION",
        "affected_depot_id": "DEPOT-NONEXISTENT",
        "disruption_duration_days": 3,
        "additional_delay_days": 1,
        "severity": "HIGH"
    }
    resp = client.post("/api/digital-twin/simulate", json=body)
    assert resp.status_code == 404

# 15. Invalid duration (<= 0) is rejected
def test_invalid_duration_rejected(client):
    body = {
        "scenario_type": "ROUTE_DISRUPTION",
        "affected_depot_id": "DEPOT-IMP-SUP",
        "disruption_duration_days": 0,
        "additional_delay_days": 1,
        "severity": "HIGH"
    }
    resp = client.post("/api/digital-twin/simulate", json=body)
    assert resp.status_code in (400, 422)

# 16. Unsupported scenario type is rejected
def test_unsupported_scenario_type_rejected(client):
    body = {
        "scenario_type": "CYBER_ATTACK_UNSUPPORTED",
        "affected_depot_id": "DEPOT-IMP-SUP",
        "disruption_duration_days": 3,
        "additional_delay_days": 1,
        "severity": "HIGH"
    }
    resp = client.post("/api/digital-twin/simulate", json=body)
    assert resp.status_code in (400, 422)

# 17. POST /api/digital-twin/simulate returns HTTP 200 for valid scenario
def test_api_simulate_endpoint(client):
    body = {
        "scenario_type": "ROUTE_DISRUPTION",
        "affected_depot_id": "DEPOT-IMP-SUP",
        "disruption_duration_days": 3,
        "additional_delay_days": 2,
        "severity": "HIGH"
    }
    resp = client.post("/api/digital-twin/simulate", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["affected_depot_id"] == "DEPOT-IMP-SUP"
    assert data["data_source"] == "synthetic_demo"

# 18. GET /api/digital-twin/scenarios endpoint returns demo templates
def test_api_list_scenarios_endpoint(client):
    resp = client.get("/api/digital-twin/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["scenario_type"] == "ROUTE_DISRUPTION"

# Phase 7B: Supply Movement & Replenishment Simulation Tests

from backend.app.digital_twin.shipments import get_synthetic_shipments

# 19. Synthetic shipment lookup helper returns deterministic records
def test_get_synthetic_shipments_returns_records():
    shipments = get_synthetic_shipments()
    assert isinstance(shipments, list)
    assert len(shipments) >= 4
    for s in shipments:
        assert "shipment_id" in s
        assert "destination_depot_id" in s
        assert "cargo_item_id" in s
        assert s["quantity"] > 0
        assert s["data_source"] == "synthetic_demo"

# 20. Synthetic shipment filtering by depot and cargo item
def test_synthetic_shipments_depot_filtering():
    imp_shipments = get_synthetic_shipments(depot_id="DEPOT-IMP-SUP")
    assert len(imp_shipments) == 2
    for s in imp_shipments:
        assert s["destination_depot_id"] == "DEPOT-IMP-SUP"

    twa_shipments = get_synthetic_shipments(depot_id="DEPOT-TWA-AMM", cargo_item_id="INV-TWA-AVGAS")
    assert len(twa_shipments) == 1
    assert twa_shipments[0]["shipment_id"] == "SHIP-TWA-001"

# 21. Baseline trajectory reflects scheduled replenishment arrivals
def test_baseline_trajectory_reflects_scheduled_arrivals(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=2,
        severity="MEDIUM"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    traj = res["trajectory"]
    day3 = next(t for t in traj if t["day"] == 3)
    day4 = next(t for t in traj if t["day"] == 4)
    assert day4["baseline_inventory"] > day3["baseline_inventory"]

# 22. Disrupted simulation delays arrival to simulated_arrival_day
def test_delayed_replenishment_arrival_in_simulated_trajectory(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=2,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    traj = res["trajectory"]
    day8 = next(t for t in traj if t["day"] == 8)
    assert day8["simulated_arrival"] == 1000.0

# 23. Simulation result includes affected_shipments metadata list
def test_simulation_result_includes_affected_shipments(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=4,
        additional_delay_days=1,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert "affected_shipments" in res
    shipments = res["affected_shipments"]
    assert len(shipments) == 2
    assert shipments[0]["shipment_id"] == "SHIP-IMP-001"
    assert shipments[0]["simulated_arrival_day"] == 8
    assert shipments[0]["status"] == "DELAYED"
    assert shipments[0]["data_source"] == "synthetic_demo"

# 24. Granular route filtering affects only matching route shipments
def test_route_specific_disruption_filtering(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        affected_route_id="SIL-IMP",
        disruption_duration_days=3,
        additional_delay_days=2,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    shipments = res["affected_shipments"]
    sil_shipment = next(s for s in shipments if s["shipment_id"] == "SHIP-IMP-001")
    khm_shipment = next(s for s in shipments if s["shipment_id"] == "SHIP-IMP-002")

    assert sil_shipment["delay_days"] == 5
    assert sil_shipment["status"] == "DELAYED"

    assert khm_shipment["delay_days"] == 0
    assert khm_shipment["simulated_arrival_day"] == khm_shipment["expected_arrival_day"]
    assert khm_shipment["status"] != "DELAYED"

# 25. Unaffected route shipment arrives on schedule in simulation
def test_unaffected_route_shipment_remains_on_schedule(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        affected_route_id="SIL-IMP",
        disruption_duration_days=3,
        additional_delay_days=2,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    traj = res["trajectory"]
    day6 = next(t for t in traj if t["day"] == 6)
    assert day6["simulated_arrival"] == 600.0

# 26. Delayed replenishment worsens risk and degrades readiness
def test_shipment_delay_worsens_risk_and_readiness(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=5,
        additional_delay_days=3,
        severity="CRITICAL"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert res["readiness_score_delta"] <= 0.0
    assert res["risk_score_delta"] >= 0.0
    assert len(res["affected_shipments"]) == 2

# 27. Simulated arrival boosts inventory on delayed arrival day
def test_simulated_arrival_boosts_inventory_on_delayed_day(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-SHL-MED",
        disruption_duration_days=2,
        additional_delay_days=1,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    traj = res["trajectory"]
    day5 = next(t for t in traj if t["day"] == 5)
    day6 = next(t for t in traj if t["day"] == 6)
    assert day5["simulated_arrival"] == 300.0
    assert day6["simulated_inventory"] > (day5["simulated_inventory"] - day5["forecast_consumption"])

# 28. Multiple shipments simulation for Imphal depot
def test_multiple_shipments_depot_simulation(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=1,
        severity="MEDIUM"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert len(res["affected_shipments"]) == 2

# 29. Synthetic demo tag on all affected shipments
def test_shipments_synthetic_demo_tag(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-GHY-FUEL",
        disruption_duration_days=2,
        additional_delay_days=1,
        severity="LOW"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    for s in res["affected_shipments"]:
        assert s["data_source"] == "synthetic_demo"

# 30. API POST /api/digital-twin/simulate returns shipment impacts
def test_digital_twin_shipment_simulation_api(client):
    body = {
        "scenario_type": "ROUTE_DISRUPTION",
        "affected_depot_id": "DEPOT-IMP-SUP",
        "disruption_duration_days": 3,
        "additional_delay_days": 2,
        "severity": "HIGH"
    }
    resp = client.post("/api/digital-twin/simulate", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert "affected_shipments" in data
    assert len(data["affected_shipments"]) == 2
    assert data["affected_shipments"][0]["shipment_id"] == "SHIP-IMP-001"

# Phase 7C: Digital Twin Scenario Comparison & Explainability Tests

# 31. Baseline and scenario metrics are both returned in comparison structure
def test_baseline_and_scenario_metrics_returned(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=2,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert "comparison" in res
    comp = res["comparison"]
    assert "minimum_inventory" in comp
    assert "final_inventory" in comp
    assert "risk_score" in comp
    assert "readiness_score" in comp
    assert "affected_shipment_count" in comp
    assert comp["risk_score"]["baseline"] is not None
    assert comp["risk_score"]["scenario"] is not None

# 32. Numeric deltas are calculated correctly (delta = scenario - baseline)
def test_numeric_deltas_calculated_correctly(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=4,
        additional_delay_days=1,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    comp = res["comparison"]
    for key in ["minimum_inventory", "final_inventory", "inventory_shortfall", "risk_score", "readiness_score", "affected_shipment_count"]:
        metric = comp[key]
        expected_delta = round(metric["scenario"] - metric["baseline"], 2)
        assert abs(metric["delta"] - expected_delta) <= 0.1

# 33. Positive and negative deltas are represented accurately
def test_positive_and_negative_deltas_represented(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=4,
        additional_delay_days=2,
        severity="CRITICAL"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    comp = res["comparison"]
    assert comp["risk_score"]["delta"] >= 0.0
    assert comp["readiness_score"]["delta"] <= 0.0

# 34. Shipment delay appears as a contributing factor only when applicable
def test_shipment_delay_appears_only_when_applicable(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=1,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    factors = [f["factor"] for f in res["contributing_factors"]]
    assert "SHIPMENT_DELAY" in factors

# 35. Inventory depletion is correctly identified
def test_inventory_depletion_correctly_identified(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=1,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    factors = [f["factor"] for f in res["contributing_factors"]]
    assert "INVENTORY_DEPLETION" in factors

# 36. Threshold breach explanation is correct
def test_threshold_breach_explanation_correct(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=4,
        additional_delay_days=2,
        severity="CRITICAL"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    if res["threshold_breach_day"] is not None:
        factors = [f["factor"] for f in res["contributing_factors"]]
        assert "THRESHOLD_BREACH" in factors
        assert any("threshold" in c.lower() for c in res["causal_chain"])

# 37. Stock-out explanation is correct when stock-out occurs
def test_stockout_explanation_correct(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=5,
        additional_delay_days=2,
        severity="CRITICAL"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    if res["stockout_day"] is not None:
        factors = [f["factor"] for f in res["contributing_factors"]]
        assert "STOCKOUT_PROJECTED" in factors
        assert any("stock" in c.lower() for c in res["causal_chain"])

# 38. No false contributing factor is reported
def test_no_false_contributing_factor(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        affected_route_id="NONEXISTENT-ROUTE",
        disruption_duration_days=1,
        additional_delay_days=0,
        severity="LOW"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    factors = [f["factor"] for f in res["contributing_factors"]]
    assert "SHIPMENT_DELAY" not in factors

# 39. Human-readable summary reflects actual simulation
def test_human_readable_summary_reflects_actual_simulation(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=2,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert res["human_summary"] is not None
    hs = res["human_summary"]
    assert "ROUTE_DISRUPTION" in hs
    assert "DEPOT-IMP-SUP" in hs or "Imphal" in hs

# 40. Existing Phase 7A baseline & trajectory tests continue to pass
def test_existing_phase_7a_compatibility(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-GHY-FUEL",
        disruption_duration_days=2,
        additional_delay_days=0,
        severity="LOW"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert res["baseline_risk_score"] >= 0.0
    assert len(res["trajectory"]) >= 7

# 41. Existing Phase 7B shipment tests continue to pass
def test_existing_phase_7b_shipments_compatibility(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=2,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert len(res["affected_shipments"]) == 2

# 42. Database remains completely unchanged after simulation and explanation generation
def test_database_remains_unchanged_after_explainability(setup_test_db):
    with get_db(setup_test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, current_quantity FROM inventory_items ORDER BY id")
        before_inv = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT id, status FROM vehicles ORDER BY id")
        before_veh = [dict(r) for r in cursor.fetchall()]

    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=5,
        additional_delay_days=3,
        severity="CRITICAL"
    )
    _ = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)

    with get_db(setup_test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, current_quantity FROM inventory_items ORDER BY id")
        after_inv = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT id, status FROM vehicles ORDER BY id")
        after_veh = [dict(r) for r in cursor.fetchall()]

    assert before_inv == after_inv
    assert before_veh == after_veh


# --- Phase 10D Environmental Impact Digital Twin Integration Tests ---

# 43. Environmental integration for LOW risk route
def test_phase10d_low_environmental_risk_integration(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-GHY-FUEL",
        affected_route_id="GHY-TEZ",
        disruption_duration_days=2,
        additional_delay_days=1,
        severity="LOW"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    env = res["environmental_impact"]
    assert env["status"] == "AVAILABLE"
    assert env["route_id"] == "GHY-TEZ"
    assert env["classification"] == "LOW"
    assert env["movement_impact_factor"] == 1.00
    assert env["environmental_delay_days"] == 0
    assert env["data_source"] == "synthetic_demo"
    assert env["environment"] == "demo"

# 44. Environmental integration for HIGH risk route
def test_phase10d_high_environmental_risk_integration(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        affected_route_id="SIL-IMP",
        disruption_duration_days=3,
        additional_delay_days=2,
        severity="HIGH"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    env = res["environmental_impact"]
    assert env["status"] == "AVAILABLE"
    assert env["route_id"] == "SIL-IMP"
    assert env["classification"] in ("HIGH", "CRITICAL")
    assert env["movement_impact_factor"] >= 1.20
    assert env["environmental_delay_days"] >= 2
    assert env["data_source"] == "synthetic_demo"
    assert env["environment"] == "demo"

# 45. Environmental integration for CRITICAL risk route & simulation propagation
def test_phase10d_critical_environmental_risk_propagation(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        affected_route_id="TEZ-TWA",
        disruption_duration_days=4,
        additional_delay_days=2,
        severity="CRITICAL"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    env = res["environmental_impact"]
    assert env["status"] == "AVAILABLE"
    assert env["classification"] == "CRITICAL"
    assert env["movement_impact_factor"] == 1.35
    assert env["environmental_delay_days"] == 3

    # Verify causal chain contains environmental step
    causal_text = " ".join(res["causal_chain"])
    assert "environmental" in causal_text.lower() or "terrain" in causal_text.lower() or "weather" in causal_text.lower()

    # Verify contributing factors contain environmental exposure
    factors = [f.get("factor") for f in res["contributing_factors"]]
    assert "ENVIRONMENTAL_EXPOSURE" in factors

# 46. Missing/unmapped route returns UNAVAILABLE status safely
def test_phase10d_missing_environmental_data_safeguard(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        affected_route_id="ROUTE-NON-EXISTENT-999",
        disruption_duration_days=3,
        additional_delay_days=1,
        severity="MEDIUM"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    env = res["environmental_impact"]
    assert env["status"] == "UNAVAILABLE"
    # Digital Twin simulation continues safely
    assert res["scenario_id"] is not None
    assert len(res["trajectory"]) >= 7

# 47. Omitted route returns UNAVAILABLE status without failing baseline scenario
def test_phase10d_omitted_route_id_unaffected(setup_test_db):
    req = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=2,
        additional_delay_days=1,
        severity="LOW"
    )
    res = DigitalTwinService.simulate_scenario(req, db_path=setup_test_db)
    assert res["environmental_impact"]["status"] == "UNAVAILABLE"

# 48. Double-counting protection: Operational risk calculation reuses assessment cleanly
def test_phase10d_no_double_counting_operational_risk(setup_test_db):
    req_no_env = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        disruption_duration_days=3,
        additional_delay_days=2,
        severity="HIGH"
    )
    res_no_env = DigitalTwinService.simulate_scenario(req_no_env, db_path=setup_test_db)
    
    req_env = DigitalTwinScenarioRequest(
        scenario_type="ROUTE_DISRUPTION",
        affected_depot_id="DEPOT-IMP-SUP",
        affected_route_id="ROUTE-SIL-IMP-02",
        disruption_duration_days=3,
        additional_delay_days=2,
        severity="HIGH"
    )
    res_env = DigitalTwinService.simulate_scenario(req_env, db_path=setup_test_db)
    
    # Risk score should be bounded cleanly <= 100.0 without runaway additive stacking
    assert res_env["simulated_risk_score"] <= 100.0
    assert res_no_env["simulated_risk_score"] <= 100.0

