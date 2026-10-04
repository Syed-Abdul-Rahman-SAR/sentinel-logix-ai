"""
SENTINEL LOGIX AI - Digital Twin Comparison & Explainability Engine
Generates structured baseline vs. scenario comparison metrics, causal chains,
contributing factors, and human-readable summaries without database mutations.
"""

from typing import Dict, Any, List, Optional

def generate_digital_twin_explainability(
    req: Any,
    depot_record: Dict[str, Any],
    primary_item: Dict[str, Any],
    trajectory: List[Dict[str, Any]],
    affected_shipments: List[Dict[str, Any]],
    baseline_risk_score: float,
    baseline_risk_level: str,
    simulated_risk_score: float,
    simulated_risk_level: str,
    baseline_readiness_score: float,
    baseline_readiness_status: str,
    simulated_readiness_score: float,
    simulated_readiness_status: str,
    simulated_threshold_breach_day: Optional[int],
    simulated_stockout_day: Optional[int],
    min_simulated_inv: float,
    inv_shortfall: float,
    environmental_impact: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generates structured baseline vs. scenario comparison metrics, explicit causal chain,
    contributing factors list, and a factual human-readable summary.
    Does NOT mutate any database tables.
    """
    depot_name = depot_record.get("name", req.affected_depot_id)
    item_thresh = float(primary_item.get("minimum_threshold") or 0.0)
    item_curr = float(primary_item.get("current_quantity") or 0.0)

    # 1. Baseline trajectory metrics
    min_baseline_inv = min((t["baseline_inventory"] for t in trajectory), default=item_curr)
    final_baseline_inv = trajectory[-1]["baseline_inventory"] if trajectory else item_curr
    final_simulated_inv = trajectory[-1]["simulated_inventory"] if trajectory else item_curr
    baseline_shortfall = max(0.0, round(item_thresh - min_baseline_inv, 2))

    baseline_stockout = any(t["baseline_inventory"] <= 0.0 for t in trajectory)
    simulated_stockout = (simulated_stockout_day is not None) or any(t["simulated_inventory"] <= 0.0 for t in trajectory)

    baseline_stockout_day = next((t["day"] for t in trajectory if t["baseline_inventory"] <= 0.0), None)
    baseline_breach_day = next((t["day"] for t in trajectory if t["baseline_inventory"] <= item_thresh), None)

    delayed_shipments = [s for s in affected_shipments if s.get("delay_days", 0) > 0]
    affected_shipment_count = len(delayed_shipments)
    total_delayed_qty = sum(float(s["quantity"]) for s in delayed_shipments)
    max_shipment_delay = max([int(s["delay_days"]) for s in delayed_shipments], default=0)

    risk_delta = round(simulated_risk_score - baseline_risk_score, 1)
    readiness_delta = round(simulated_readiness_score - baseline_readiness_score, 1)

    # 2. Structured comparison dictionary
    comparison = {
        "minimum_inventory": {
            "baseline": round(min_baseline_inv, 2),
            "scenario": round(min_simulated_inv, 2),
            "delta": round(min_simulated_inv - min_baseline_inv, 2)
        },
        "final_inventory": {
            "baseline": round(final_baseline_inv, 2),
            "scenario": round(final_simulated_inv, 2),
            "delta": round(final_simulated_inv - final_baseline_inv, 2)
        },
        "inventory_shortfall": {
            "baseline": round(baseline_shortfall, 2),
            "scenario": round(inv_shortfall, 2),
            "delta": round(inv_shortfall - baseline_shortfall, 2)
        },
        "stockout_occurrence": {
            "baseline": baseline_stockout,
            "scenario": simulated_stockout,
            "changed": (baseline_stockout != simulated_stockout)
        },
        "stockout_day": {
            "baseline": baseline_stockout_day,
            "scenario": simulated_stockout_day,
            "changed": (baseline_stockout_day != simulated_stockout_day)
        },
        "threshold_breach_day": {
            "baseline": baseline_breach_day,
            "scenario": simulated_threshold_breach_day,
            "changed": (baseline_breach_day != simulated_threshold_breach_day)
        },
        "risk_score": {
            "baseline": round(baseline_risk_score, 1),
            "scenario": round(simulated_risk_score, 1),
            "delta": risk_delta
        },
        "risk_classification": {
            "baseline": baseline_risk_level,
            "scenario": simulated_risk_level,
            "changed": (baseline_risk_level != simulated_risk_level)
        },
        "readiness_score": {
            "baseline": round(baseline_readiness_score, 1),
            "scenario": round(simulated_readiness_score, 1),
            "delta": readiness_delta
        },
        "readiness_status": {
            "baseline": baseline_readiness_status,
            "scenario": simulated_readiness_status,
            "changed": (baseline_readiness_status != simulated_readiness_status)
        },
        "affected_shipment_count": {
            "baseline": 0,
            "scenario": affected_shipment_count,
            "delta": affected_shipment_count
        },
        "total_delayed_shipment_quantity": {
            "baseline": 0.0,
            "scenario": round(total_delayed_qty, 2),
            "delta": round(total_delayed_qty, 2)
        },
        "max_shipment_delay_days": {
            "baseline": 0,
            "scenario": max_shipment_delay,
            "delta": max_shipment_delay
        }
    }

    # 3. Causal chain of major events
    causal_chain: List[str] = []
    if req.affected_route_id:
        causal_chain.append(f"Simulated corridor disruption '{req.affected_route_id}' affecting depot '{depot_name}'.")
    else:
        causal_chain.append(f"Simulated {req.scenario_type} disruption targeting depot '{depot_name}'.")

    if environmental_impact and environmental_impact.get("status") == "AVAILABLE":
        env_r_id = environmental_impact.get("route_id", "UNKNOWN")
        env_c = environmental_impact.get("classification", "LOW")
        env_s = float(environmental_impact.get("environmental_risk_score", 0.0))
        env_dom = environmental_impact.get("dominant_dimension", "WEATHER")
        env_m_mult = float(environmental_impact.get("movement_impact_factor", 1.0))
        env_d_days = int(environmental_impact.get("environmental_delay_days", 0))

        causal_chain.append(
            f"Corridor '{env_r_id}' environmental risk assessed as {env_c} (Score: {env_s:.1f}/100, dominant: {env_dom})."
        )
        if env_d_days > 0 or env_m_mult > 1.0:
            causal_chain.append(
                f"Environmental conditions apply {env_m_mult:.2f}x movement delay multiplier (+{env_d_days} environmental delay days)."
            )

    if affected_shipment_count > 0:
        causal_chain.append(f"{affected_shipment_count} replenishment shipment(s) delayed by up to {max_shipment_delay} days.")
        causal_chain.append(f"{total_delayed_qty:.1f} total units of inbound supply postponed.")
    else:
        causal_chain.append("No active inbound shipments affected by corridor disruption.")

    if req.severity in ("CRITICAL", "HIGH", "MEDIUM"):
        causal_chain.append(f"Severity '{req.severity}' applied elevated daily consumption rate during disruption.")

    if simulated_threshold_breach_day is not None:
        causal_chain.append(f"Depot inventory falls below minimum threshold on day {simulated_threshold_breach_day}.")

    if simulated_stockout_day is not None:
        causal_chain.append(f"Zero inventory stock-out projected on day {simulated_stockout_day}.")

    if risk_delta > 0:
        causal_chain.append(f"Operational risk score increased by +{risk_delta:.1f} pts ({baseline_risk_level} -> {simulated_risk_level}).")

    if readiness_delta != 0:
        direction = "degraded" if readiness_delta < 0 else "improved"
        causal_chain.append(f"Mission readiness {direction} by {abs(readiness_delta):.1f} pts ({baseline_readiness_status} -> {simulated_readiness_status}).")

    # 4. Contributing factors list (strictly derived from simulation data)
    contributing_factors: List[Dict[str, Any]] = []

    contributing_factors.append({
        "factor": "ROUTE_DISRUPTION",
        "severity": req.severity,
        "description": f"Simulated {req.scenario_type} hazard on logistics corridor.",
        "impact": f"Transits disrupted for {req.disruption_duration_days} days (+{req.additional_delay_days} days additional delay)."
    })

    if environmental_impact and environmental_impact.get("status") == "AVAILABLE" and float(environmental_impact.get("environmental_risk_score", 0.0)) > 0:
        env_c = environmental_impact.get("classification", "MEDIUM")
        env_s = float(environmental_impact.get("environmental_risk_score", 0.0))
        env_d_days = int(environmental_impact.get("environmental_delay_days", 0))
        contributing_factors.append({
            "factor": "ENVIRONMENTAL_EXPOSURE",
            "severity": env_c,
            "description": f"Corridor '{environmental_impact.get('route_id')}' environmental risk level: {env_c} (Score: {env_s:.1f}/100).",
            "impact": f"Weather and terrain conditions add +{env_d_days} day(s) transit delay to inbound replenishment."
        })

    if affected_shipment_count > 0:
        ship_sev = "CRITICAL" if max_shipment_delay >= 5 else ("HIGH" if max_shipment_delay >= 3 else "MEDIUM")
        contributing_factors.append({
            "factor": "SHIPMENT_DELAY",
            "severity": ship_sev,
            "description": f"{affected_shipment_count} replenishment shipment(s) delayed.",
            "impact": f"{total_delayed_qty:.1f} units postponed by up to {max_shipment_delay} days."
        })

    if req.severity in ("CRITICAL", "HIGH", "MEDIUM"):
        contributing_factors.append({
            "factor": "INCREASED_CONSUMPTION",
            "severity": req.severity,
            "description": f"Disruption severity '{req.severity}' increased operational demand rate.",
            "impact": "Daily consumption rate multiplied during disruption period."
        })

    if min_simulated_inv < item_curr:
        depletion_qty = item_curr - min_simulated_inv
        dep_sev = "CRITICAL" if min_simulated_inv <= 0 else ("HIGH" if min_simulated_inv <= item_thresh else "MEDIUM")
        contributing_factors.append({
            "factor": "INVENTORY_DEPLETION",
            "severity": dep_sev,
            "description": f"Inventory depleted from initial {item_curr:.1f} to minimum {min_simulated_inv:.1f} units.",
            "impact": f"Net inventory depletion of {depletion_qty:.1f} units."
        })

    if simulated_threshold_breach_day is not None:
        contributing_factors.append({
            "factor": "THRESHOLD_BREACH",
            "severity": "HIGH",
            "description": f"Simulated inventory breached minimum threshold on day {simulated_threshold_breach_day}.",
            "impact": f"Stock fell below minimum safety threshold of {item_thresh:.1f} units."
        })

    if simulated_stockout_day is not None:
        contributing_factors.append({
            "factor": "STOCKOUT_PROJECTED",
            "severity": "CRITICAL",
            "description": f"Zero inventory stock-out projected on day {simulated_stockout_day}.",
            "impact": f"Depot supply exhausted completely on day {simulated_stockout_day}."
        })

    # 5. Human-readable summary
    summary_parts = []
    summary_parts.append(f"Simulated '{req.scenario_type}' disruption on depot '{depot_name}' ({req.disruption_duration_days} days disruption, severity: {req.severity}).")

    if environmental_impact and environmental_impact.get("status") == "AVAILABLE" and float(environmental_impact.get("environmental_risk_score", 0.0)) > 0:
        env_c = environmental_impact.get("classification", "LOW")
        env_s = float(environmental_impact.get("environmental_risk_score", 0.0))
        env_d_days = int(environmental_impact.get("environmental_delay_days", 0))
        summary_parts.append(f"Corridor environmental risk ({env_c}, Score: {env_s:.1f}/100) contributed +{env_d_days} day(s) environmental transit delay.")

    if affected_shipment_count > 0:
        summary_parts.append(f"Delayed {affected_shipment_count} replenishment shipment(s) totaling {total_delayed_qty:.1f} units by up to {max_shipment_delay} days.")
    else:
        summary_parts.append("No active inbound shipments were affected.")

    if simulated_stockout_day is not None:
        summary_parts.append(f"Inventory breached threshold on day {simulated_threshold_breach_day or 1} and reached stock-out on day {simulated_stockout_day}.")
    elif simulated_threshold_breach_day is not None:
        summary_parts.append(f"Inventory fell below the minimum safety threshold of {item_thresh:.1f} units on day {simulated_threshold_breach_day}.")

    summary_parts.append(f"Assessed risk shifted from {baseline_risk_level} ({baseline_risk_score:.1f}) to {simulated_risk_level} ({simulated_risk_score:.1f}), and mission readiness degraded from {baseline_readiness_status} ({baseline_readiness_score:.1f}/100) to {simulated_readiness_status} ({simulated_readiness_score:.1f}/100).")

    human_summary = " ".join(summary_parts)

    return {
        "comparison": comparison,
        "causal_chain": causal_chain,
        "contributing_factors": contributing_factors,
        "human_summary": human_summary
    }

