"""
SENTINEL LOGIX AI - Digital Twin Simulation Engine
Performs safe, in-memory what-if simulations of logistics disruptions without database mutation.
Calculates simulated inventory trajectories, impact detection, risk deltas, and readiness deltas.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from ..services.depot_service import DepotService
from ..services.base_service import BaseService
from ..services.inventory_service import InventoryService
from ..stockout.prediction import calculate_stockout_prediction
from ..stockout.service import StockoutService
from ..risk.assessment import assess_logistics_risk
from ..risk.service import RiskService, get_route_id_for_depot
from ..readiness.assessment import assess_depot_readiness
from ..readiness.service import ReadinessService
from ..environment.service import EnvironmentService
from .schemas import DigitalTwinScenarioRequest, DigitalTwinSimulationResult, DailyTrajectoryPoint
from .shipments import get_synthetic_shipments

def run_digital_twin_simulation(
    req: DigitalTwinScenarioRequest,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes an in-memory what-if simulation for a hypothetical logistics disruption scenario,
    incorporating Phase 10D Environmental Intelligence context and delay multipliers when route is specified.
    Does NOT mutate the production database.
    """
    depot_id = req.affected_depot_id

    # 1. Baseline Snapshot Retrieval (In-Memory Copy)
    depot_record = DepotService.get_depot(depot_id, db_path=db_path)
    if not depot_record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Depot '{depot_id}' not found")

    base_id = depot_record.get("base_id")
    base_record = BaseService.get_base(base_id, db_path=db_path) if base_id else None

    # Environment intelligence retrieval: strictly per Section 10, when affected_route_id is present
    target_route_id = req.affected_route_id or get_route_id_for_depot(depot_id, base_id)

    env_assessment = None
    if target_route_id:
        try:
            env_assessment = EnvironmentService.get_environmental_risk(target_route_id)
        except Exception:
            env_assessment = None

    if req.affected_route_id and env_assessment and isinstance(env_assessment, dict):
        env_score = float(env_assessment.get("environmental_risk_score", 0.0))
        env_class = str(env_assessment.get("classification", "LOW")).upper()
        env_w_score = float(env_assessment.get("weather_risk_score", 0.0))
        env_t_score = float(env_assessment.get("terrain_risk_score", 0.0))
        env_dominant = "WEATHER" if env_w_score >= env_t_score else "TERRAIN"
        env_route_id = env_assessment.get("route_id", target_route_id)
        env_route_name = env_assessment.get("route_name", env_route_id)
        env_explanation = env_assessment.get("explanation")

        if env_class == "CRITICAL":
            movement_impact_factor = 1.35
            env_delay_days = 3
        elif env_class == "HIGH":
            movement_impact_factor = 1.20
            env_delay_days = 2
        elif env_class == "MEDIUM":
            movement_impact_factor = 1.10
            env_delay_days = 1
        else:
            movement_impact_factor = 1.00
            env_delay_days = 0

        env_impact_dict = {
            "route_id": env_route_id,
            "route_name": env_route_name,
            "environmental_risk_score": env_score,
            "classification": env_class,
            "weather_risk_score": env_w_score,
            "terrain_risk_score": env_t_score,
            "dominant_dimension": env_dominant,
            "movement_impact_factor": movement_impact_factor,
            "environmental_delay_days": env_delay_days,
            "explanation": env_explanation,
            "status": "AVAILABLE",
            "data_source": "synthetic_demo",
            "environment": "demo"
        }
    else:
        movement_impact_factor = 1.00
        env_delay_days = 0
        env_impact_dict = {
            "route_id": target_route_id if req.affected_route_id else None,
            "route_name": None,
            "environmental_risk_score": float(env_assessment.get("environmental_risk_score", 0.0)) if env_assessment else 0.0,
            "classification": env_assessment.get("classification") if env_assessment else None,
            "weather_risk_score": float(env_assessment.get("weather_risk_score", 0.0)) if env_assessment else 0.0,
            "terrain_risk_score": float(env_assessment.get("terrain_risk_score", 0.0)) if env_assessment else 0.0,
            "dominant_dimension": None,
            "movement_impact_factor": 1.00,
            "environmental_delay_days": 0,
            "explanation": "Environmental intelligence assessment unavailable or unmapped for scenario request.",
            "status": "UNAVAILABLE" if not req.affected_route_id else ("AVAILABLE" if env_assessment else "UNAVAILABLE"),
            "data_source": "synthetic_demo",
            "environment": "demo"
        }
        if env_assessment and req.affected_route_id:
            env_impact_dict["status"] = "AVAILABLE"
            env_impact_dict["route_id"] = env_assessment.get("route_id")
            env_impact_dict["route_name"] = env_assessment.get("route_name")

    inventory_items = InventoryService.list_inventory(depot_id=depot_id, db_path=db_path)
    if not inventory_items:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No inventory items found for depot '{depot_id}'")

    baseline_risk_list = RiskService.get_risk_assessments(depot_id=depot_id, db_path=db_path)
    baseline_readiness_list = ReadinessService.get_readiness_assessments(depot_id=depot_id, db_path=db_path)

    baseline_readiness = baseline_readiness_list[0] if baseline_readiness_list else {}
    baseline_risk_scores = [float(r["risk_score"]) for r in baseline_risk_list]
    baseline_risk_score = max(baseline_risk_scores) if baseline_risk_scores else 0.0
    
    baseline_risk_levels = [r["risk_level"] for r in baseline_risk_list]
    if "CRITICAL" in baseline_risk_levels:
        baseline_risk_level = "CRITICAL"
    elif "HIGH" in baseline_risk_levels:
        baseline_risk_level = "HIGH"
    elif "MEDIUM" in baseline_risk_levels:
        baseline_risk_level = "MEDIUM"
    else:
        baseline_risk_level = "LOW"

    baseline_readiness_score = float(baseline_readiness.get("readiness_score", 100.0))
    baseline_readiness_status = str(baseline_readiness.get("readiness_status", "READY"))

    # 2. Multi-Day Simulation Trajectory
    primary_item = inventory_items[0]
    item_id = primary_item["id"]
    item_thresh = float(primary_item.get("minimum_threshold") or 0.0)
    item_curr = float(primary_item.get("current_quantity") or 0.0)

    total_disruption_days = req.disruption_duration_days + req.additional_delay_days

    # Query synthetic replenishment shipments for depot
    all_depot_shipments = get_synthetic_shipments(depot_id=depot_id)

    max_expected_arrival = max([int(s.get("expected_arrival_day", 1)) for s in all_depot_shipments], default=1)
    horizon_days = max(14, total_disruption_days + max_expected_arrival + 2)

    so_pred = calculate_stockout_prediction(primary_item, horizon_days=horizon_days, db_path=db_path)
    forecasted_points = so_pred.get("forecasted_consumption", [])

    today = datetime.now(timezone.utc).date()

    # Severity multiplier for daily consumption during disruption
    sev_mult = 1.0
    if req.severity == "CRITICAL":
        sev_mult = 1.35
    elif req.severity == "HIGH":
        sev_mult = 1.20
    elif req.severity == "MEDIUM":
        sev_mult = 1.10

    affected_shipments_list = []
    processed_shipments = []

    for s in all_depot_shipments:
        # Check if shipment is affected by target route or general depot disruption
        is_affected = False
        if req.affected_route_id:
            is_affected = (s.get("route_id") == req.affected_route_id)
        else:
            is_affected = True

        total_delay = total_disruption_days if is_affected else 0
        exp_day = int(s.get("expected_arrival_day", 1))
        sim_day = exp_day + total_delay
        status = "DELAYED" if is_affected else s.get("status", "IN_TRANSIT")

        p_ship = dict(s)
        p_ship["simulated_arrival_day"] = sim_day
        p_ship["delay_days"] = total_delay
        p_ship["effective_status"] = status
        processed_shipments.append(p_ship)

        affected_shipments_list.append({
            "shipment_id": s["shipment_id"],
            "cargo_item_id": s["cargo_item_id"],
            "quantity": float(s["quantity"]),
            "origin_base_id": s["origin_base_id"],
            "destination_depot_id": s["destination_depot_id"],
            "route_id": s["route_id"],
            "expected_arrival_day": exp_day,
            "simulated_arrival_day": sim_day,
            "delay_days": total_delay,
            "status": status,
            "data_source": "synthetic_demo"
        })


    primary_shipments = [s for s in processed_shipments if s.get("cargo_item_id") == item_id]

    trajectory: List[Dict[str, Any]] = []
    running_baseline = item_curr
    running_simulated = item_curr

    simulated_threshold_breach_day: Optional[int] = None
    simulated_stockout_day: Optional[int] = None

    for step in range(1, horizon_days + 1):
        p_date = str(today + timedelta(days=step - 1))
        f_cons = forecasted_points[step - 1]["predicted_consumption"] if step <= len(forecasted_points) else float(primary_item.get("daily_consumption_rate") or 100.0)

        b_cons = f_cons

        if step <= req.disruption_duration_days:
            s_cons = f_cons * sev_mult
        else:
            s_cons = f_cons

        # Arrivals for primary item on day 'step'
        b_arr = sum(float(s["quantity"]) for s in primary_shipments if s["expected_arrival_day"] == step)
        s_arr = sum(float(s["quantity"]) for s in primary_shipments if s["simulated_arrival_day"] == step)

        # Track trajectory values at start of day
        curr_b_inv = round(running_baseline, 2)
        curr_s_inv = round(running_simulated, 2)

        trajectory.append({
            "day": step,
            "date": p_date,
            "baseline_inventory": curr_b_inv,
            "simulated_inventory": curr_s_inv,
            "forecast_consumption": round(f_cons, 2),
            "simulated_arrival": round(s_arr, 2),
            "threshold": round(item_thresh, 2)
        })

        # Track breach & stockout
        if simulated_threshold_breach_day is None and curr_s_inv <= item_thresh:
            simulated_threshold_breach_day = step

        if simulated_stockout_day is None and curr_s_inv <= 0.0:
            simulated_stockout_day = step

        # Update end-of-day running stock with arrivals and consumption
        running_baseline = max(0.0, running_baseline + b_arr - b_cons)
        running_simulated = max(0.0, running_simulated + s_arr - s_cons)

    # 3. Impact Detection Metrics
    min_simulated_inv = min(t["simulated_inventory"] for t in trajectory)
    inv_shortfall = max(0.0, round(item_thresh - min_simulated_inv, 2))

    # 4. In-Memory Simulated Risk & Readiness Assessments
    simulated_items = []
    simulated_so_preds = []
    
    # Create simulated item copy with updated stock
    for item in inventory_items:
        sim_item = dict(item)
        sim_item["current_quantity"] = max(0.0, min_simulated_inv)
        simulated_items.append(sim_item)

        sim_so = calculate_stockout_prediction(sim_item, horizon_days=horizon_days, db_path=db_path)
        if simulated_stockout_day is not None and simulated_stockout_day <= 3:
            sim_so["risk_level"] = "CRITICAL"
        elif simulated_threshold_breach_day is not None and simulated_threshold_breach_day <= 3:
            sim_so["risk_level"] = "HIGH"
        simulated_so_preds.append(sim_so)

    # Inject simulated road disruption incident
    simulated_incidents = [
        {
            "id": f"INC-SIM-{req.scenario_id}",
            "severity": req.severity,
            "is_active": True,
            "title": f"Simulated {req.scenario_type} Corridor Hazard"
        }
    ]

    simulated_risk_assessments = []
    for s_item, s_so in zip(simulated_items, simulated_so_preds):
        sim_risk = assess_logistics_risk(
            inventory_item=s_item,
            depot_record=depot_record,
            stockout_prediction=s_so,
            active_incidents=simulated_incidents,
            active_trips=[],
            environmental_assessment=env_assessment
        )
        simulated_risk_assessments.append(sim_risk)

    simulated_readiness = assess_depot_readiness(
        depot_record=depot_record,
        base_record=base_record,
        inventory_items=simulated_items,
        stockout_predictions=simulated_so_preds,
        risk_assessments=simulated_risk_assessments
    )

    sim_risk_scores = [float(r["risk_score"]) for r in simulated_risk_assessments]
    simulated_risk_score = max(sim_risk_scores) if sim_risk_scores else baseline_risk_score
    
    sim_risk_levels = [r["risk_level"] for r in simulated_risk_assessments]
    if "CRITICAL" in sim_risk_levels or (simulated_stockout_day and simulated_stockout_day <= 3):
        simulated_risk_level = "CRITICAL"
    elif "HIGH" in sim_risk_levels or (simulated_threshold_breach_day and simulated_threshold_breach_day <= 3):
        simulated_risk_level = "HIGH"
    elif "MEDIUM" in sim_risk_levels:
        simulated_risk_level = "MEDIUM"
    else:
        simulated_risk_level = "LOW"

    simulated_readiness_score = float(simulated_readiness["readiness_score"])
    simulated_readiness_status = str(simulated_readiness["readiness_status"])

    risk_score_delta = round(simulated_risk_score - baseline_risk_score, 1)
    readiness_score_delta = round(simulated_readiness_score - baseline_readiness_score, 1)

    # 5. Explanations, Impact List & Documented Assumptions
    contributing_impacts = []
    if simulated_threshold_breach_day:
        contributing_impacts.append(f"Threshold breach projected on day {simulated_threshold_breach_day}.")
    if simulated_stockout_day:
        contributing_impacts.append(f"Zero stock-out projected on day {simulated_stockout_day}.")
    for s_imp in affected_shipments_list:
        if s_imp["delay_days"] > 0:
            contributing_impacts.append(
                f"Replenishment shipment {s_imp['shipment_id']} delayed by +{s_imp['delay_days']} days (day {s_imp['expected_arrival_day']} -> day {s_imp['simulated_arrival_day']})."
            )
    if risk_score_delta > 0:
        contributing_impacts.append(f"Operational risk score increased by +{risk_score_delta:.1f} pts.")
    if readiness_score_delta < 0:
        contributing_impacts.append(f"Mission readiness score degraded by {readiness_score_delta:.1f} pts.")

    narrative = (
        f"Digital Twin simulation '{req.scenario_type}' for depot '{depot_record.get('name', depot_id)}' "
        f"(Disruption: {req.disruption_duration_days} days, Severity: {req.severity}). "
        f"Baseline readiness: {baseline_readiness_status} ({baseline_readiness_score:.1f}/100) vs "
        f"Simulated readiness: {simulated_readiness_status} ({simulated_readiness_score:.1f}/100). "
        f"Readiness Delta: {readiness_score_delta:+.1f} pts. Risk Delta: {risk_score_delta:+.1f} pts."
    )

    assumptions = [
        f"Synthetic replenishment shipments modeled for depot '{depot_id}' with expected arrival schedules.",
        f"A '{req.scenario_type}' scenario delays inbound supply replenishment by {total_disruption_days} base days.",
        f"Severity '{req.severity}' applies a {sev_mult:.2f}x operational consumption rate multiplier during disruption days.",
        "Simulation executed entirely in-memory. Zero database mutations were performed against production tables."
    ]

    if env_impact_dict["status"] == "AVAILABLE":
        assumptions.append(
            f"Synthetic environmental demonstration assumption: Route '{env_impact_dict['route_id']}' environmental risk ({env_impact_dict['classification']}, Score: {env_impact_dict['environmental_risk_score']:.1f}/100) applies a {movement_impact_factor:.2f}x movement delay multiplier (+{env_delay_days} environmental delay days)."
        )

    # Phase 7C & 10D: Explainability Engine
    from .explainability import generate_digital_twin_explainability
    explainability_res = generate_digital_twin_explainability(
        req=req,
        depot_record=depot_record,
        primary_item=primary_item,
        trajectory=trajectory,
        affected_shipments=affected_shipments_list,
        baseline_risk_score=baseline_risk_score,
        baseline_risk_level=baseline_risk_level,
        simulated_risk_score=simulated_risk_score,
        simulated_risk_level=simulated_risk_level,
        baseline_readiness_score=baseline_readiness_score,
        baseline_readiness_status=baseline_readiness_status,
        simulated_readiness_score=simulated_readiness_score,
        simulated_readiness_status=simulated_readiness_status,
        simulated_threshold_breach_day=simulated_threshold_breach_day,
        simulated_stockout_day=simulated_stockout_day,
        min_simulated_inv=min_simulated_inv,
        inv_shortfall=inv_shortfall,
        environmental_impact=env_impact_dict
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    return {
        "scenario_id": req.scenario_id,
        "scenario_type": req.scenario_type,
        "scenario_description": req.description or f"Simulated {req.scenario_type} disruption on depot {depot_id}",
        "affected_depot_id": depot_id,
        "affected_depot_name": depot_record.get("name", depot_id),
        "base_id": base_id,
        "base_name": base_record.get("name") if base_record else None,
        "baseline_risk_score": baseline_risk_score,
        "baseline_risk_level": baseline_risk_level,
        "baseline_readiness_score": baseline_readiness_score,
        "baseline_readiness_status": baseline_readiness_status,
        "simulated_risk_score": simulated_risk_score,
        "simulated_risk_level": simulated_risk_level,
        "simulated_readiness_score": simulated_readiness_score,
        "simulated_readiness_status": simulated_readiness_status,
        "risk_score_delta": risk_score_delta,
        "readiness_score_delta": readiness_score_delta,
        "threshold_breach_day": simulated_threshold_breach_day,
        "stockout_day": simulated_stockout_day,
        "minimum_simulated_inventory": min_simulated_inv,
        "inventory_shortfall": inv_shortfall,
        "trajectory": trajectory,
        "affected_shipments": affected_shipments_list,
        "contributing_impacts": contributing_impacts,
        "explanation": narrative,
        "assumptions": assumptions,
        # Phase 7C fields
        "comparison": explainability_res["comparison"],
        "causal_chain": explainability_res["causal_chain"],
        "contributing_factors": explainability_res["contributing_factors"],
        "human_summary": explainability_res["human_summary"],
        # Phase 10D field
        "environmental_impact": env_impact_dict,
        "data_source": "synthetic_demo",
        "generated_at": now_iso
    }

