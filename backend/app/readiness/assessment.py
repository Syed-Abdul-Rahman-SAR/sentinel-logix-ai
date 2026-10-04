"""
SENTINEL LOGIX AI - Mission Readiness Assessment Engine
Computes explainable, deterministic 0-100 depot mission readiness scores by combining
inventory health, stock-out predictions, operational risk assessments, and demand pressure.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# Readiness Thresholds
SCORE_READY = 85.0
SCORE_CAUTION = 65.0
SCORE_DEGRADED = 45.0

def assess_depot_readiness(
    depot_record: Dict[str, Any],
    base_record: Optional[Dict[str, Any]],
    inventory_items: List[Dict[str, Any]],
    stockout_predictions: List[Dict[str, Any]],
    risk_assessments: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluates 4 operational dimensions to calculate a deterministic 0-100 readiness score for a depot.
    Returns structured breakdown, status, supporting metrics, factors, and narrative explanation.
    """
    depot_id = depot_record["id"]
    depot_name = depot_record.get("name", depot_id)
    base_id = base_record.get("id") if base_record else depot_record.get("base_id")
    base_name = base_record.get("name") if base_record else None

    total_items = len(inventory_items)
    below_threshold_count = 0
    critical_inventory_count = 0
    
    for item in inventory_items:
        cur_q = float(item.get("current_quantity") or 0.0)
        min_t = float(item.get("minimum_threshold") or 0.0)
        if cur_q <= min_t:
            below_threshold_count += 1
        if cur_q == 0.0 or (min_t > 0 and cur_q / min_t <= 0.5):
            critical_inventory_count += 1

    factors: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # 1. INVENTORY COMPONENT (Max 35.0 pts)
    # -------------------------------------------------------------------------
    if total_items > 0:
        healthy_count = total_items - below_threshold_count
        healthy_ratio = healthy_count / total_items
        inv_pts = round(healthy_ratio * 35.0, 1)
    else:
        inv_pts = 35.0

    if below_threshold_count > 0:
        inv_severity = "CRITICAL" if below_threshold_count >= 2 or critical_inventory_count > 0 else "HIGH"
        inv_impact = "negative"
        inv_msg = f"{below_threshold_count} of {total_items} item(s) below minimum safety threshold."
    else:
        inv_severity = "NONE"
        inv_impact = "positive"
        inv_msg = "All inventory items maintained above minimum safety thresholds."

    factors.append({
        "factor": "inventory_readiness",
        "impact": inv_impact,
        "severity": inv_severity,
        "score_contribution": round(inv_pts, 1),
        "message": inv_msg
    })

    # -------------------------------------------------------------------------
    # 2. STOCKOUT COMPONENT (Max 30.0 pts)
    # -------------------------------------------------------------------------
    stockout_severities = [
        str(so.get("risk_level", "LOW")).upper()
        for so in stockout_predictions
    ]
    critical_so_count = sum(1 for s in stockout_severities if s == "CRITICAL")
    
    if "CRITICAL" in stockout_severities:
        worst_so_risk = "CRITICAL"
        so_pts = 0.0
        so_severity = "CRITICAL"
        so_impact = "negative"
        so_msg = f"Critical stock-out risk detected in {critical_so_count} item(s)."
    elif "HIGH" in stockout_severities:
        worst_so_risk = "HIGH"
        so_pts = 10.0
        so_severity = "HIGH"
        so_impact = "negative"
        so_msg = "High stock-out risk projected for depot inventory within 3-5 days."
    elif "MEDIUM" in stockout_severities:
        worst_so_risk = "MEDIUM"
        so_pts = 20.0
        so_severity = "MEDIUM"
        so_impact = "negative"
        so_msg = "Moderate stock-out risk projected near end of forecast window."
    else:
        worst_so_risk = "LOW"
        so_pts = 30.0
        so_severity = "NONE"
        so_impact = "positive"
        so_msg = "No forward stock-out risk detected across depot inventory."

    factors.append({
        "factor": "stockout_condition",
        "impact": so_impact,
        "severity": so_severity,
        "score_contribution": round(so_pts, 1),
        "message": so_msg
    })

    # -------------------------------------------------------------------------
    # 3. OPERATIONAL RISK COMPONENT (Max 20.0 pts)
    # -------------------------------------------------------------------------
    item_risk_scores = [float(r.get("risk_score", 0.0)) for r in risk_assessments]
    max_risk_score = max(item_risk_scores) if item_risk_scores else 0.0

    if max_risk_score >= 75.0:
        max_risk_level = "CRITICAL"
        risk_pts = 0.0
        risk_severity = "CRITICAL"
        risk_impact = "negative"
        risk_msg = f"Peak operational risk score is CRITICAL ({max_risk_score:.1f}/100)."
    elif max_risk_score >= 55.0:
        max_risk_level = "HIGH"
        risk_pts = 7.0
        risk_severity = "HIGH"
        risk_impact = "negative"
        risk_msg = f"Peak operational risk score is HIGH ({max_risk_score:.1f}/100)."
    elif max_risk_score >= 35.0:
        max_risk_level = "MEDIUM"
        risk_pts = 14.0
        risk_severity = "MEDIUM"
        risk_impact = "negative"
        risk_msg = f"Peak operational risk score is MEDIUM ({max_risk_score:.1f}/100)."
    else:
        max_risk_level = "LOW"
        risk_pts = 20.0
        risk_severity = "NONE"
        risk_impact = "positive"
        risk_msg = "Depot operational risk profile remains LOW across all metrics."

    factors.append({
        "factor": "operational_risk",
        "impact": risk_impact,
        "severity": risk_severity,
        "score_contribution": round(risk_pts, 1),
        "message": risk_msg
    })

    # -------------------------------------------------------------------------
    # 4. DEMAND PRESSURE COMPONENT (Max 15.0 pts)
    # -------------------------------------------------------------------------
    high_consumption_items = [
        item for item in inventory_items
        if (item.get("criticality") == "CRITICAL" and float(item.get("daily_consumption_rate") or 0.0) > 1000.0)
    ]
    if high_consumption_items and below_threshold_count > 0:
        demand_pts = 5.0
        demand_severity = "HIGH"
        demand_impact = "negative"
        demand_msg = "High demand pressure on critical operational inventory."
    elif high_consumption_items:
        demand_pts = 10.0
        demand_severity = "MEDIUM"
        demand_impact = "neutral"
        demand_msg = "Moderate demand pressure with heavy daily throughput."
    else:
        demand_pts = 15.0
        demand_severity = "NONE"
        demand_impact = "positive"
        demand_msg = "Normal consumption pressure within planned operational parameters."

    factors.append({
        "factor": "demand_pressure",
        "impact": demand_impact,
        "severity": demand_severity,
        "score_contribution": round(demand_pts, 1),
        "message": demand_msg
    })

    # -------------------------------------------------------------------------
    # COMPOSITE SCORE & READINESS STATUS MAPPING
    # -------------------------------------------------------------------------
    raw_total = inv_pts + so_pts + risk_pts + demand_pts
    readiness_score = min(100.0, max(0.0, round(raw_total, 1)))

    if readiness_score >= SCORE_READY:
        readiness_status = "READY"
    elif readiness_score >= SCORE_CAUTION:
        readiness_status = "CAUTION"
    elif readiness_score >= SCORE_DEGRADED:
        readiness_status = "DEGRADED"
    else:
        readiness_status = "CRITICAL"

    # Strict Cap: If there is a CRITICAL stockout risk or 0 stock item, cap status to DEGRADED max
    if (critical_so_count > 0 or critical_inventory_count > 0) and readiness_status in ("READY", "CAUTION"):
        readiness_status = "DEGRADED"

    # -------------------------------------------------------------------------
    # EXPLANATION NARRATIVE GENERATION
    # -------------------------------------------------------------------------
    narrative_parts = [
        f"Depot '{depot_name}' Mission Readiness status evaluated at {readiness_status} (Score: {readiness_score:.1f}/100)."
    ]
    if base_name:
        narrative_parts.append(f"Parent Base: {base_name}.")

    key_concerns = [f["message"] for f in factors if f["impact"] == "negative"]
    if key_concerns:
        narrative_parts.append("Operational constraints: " + " ".join(key_concerns))
    else:
        narrative_parts.append("All logistics vectors indicate full mission operational readiness.")

    explanation = " ".join(narrative_parts)
    now_iso = datetime.now(timezone.utc).isoformat()

    return {
        "entity_id": depot_id,
        "entity_type": "DEPOT",
        "entity_name": depot_name,
        "base_id": base_id,
        "base_name": base_name,
        "readiness_score": readiness_score,
        "readiness_status": readiness_status,
        "components": {
            "inventory_component": round(inv_pts, 1),
            "stockout_component": round(so_pts, 1),
            "operational_risk_component": round(risk_pts, 1),
            "demand_pressure_component": round(demand_pts, 1)
        },
        "supporting_info": {
            "total_items_count": total_items,
            "critical_inventory_count": critical_inventory_count,
            "below_threshold_count": below_threshold_count,
            "critical_stockout_count": critical_so_count,
            "worst_stockout_risk": worst_so_risk,
            "max_risk_score": max_risk_score,
            "max_risk_level": max_risk_level
        },
        "contributing_factors": factors,
        "explanation": explanation,
        "data_source": "synthetic_demo",
        "generated_at": now_iso
    }
