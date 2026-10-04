"""
SENTINEL LOGIX AI - Risk Intelligence Assessment Engine
Computes explainable, deterministic 0-100 risk scores by combining stock-out predictions,
inventory ratios, active operational incidents, and logistics movement signals.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# Named Constants for Signal Weighting (Max Total = 100.0)
MAX_STOCKOUT_POINTS = 40.0
MAX_INVENTORY_POINTS = 25.0
MAX_INCIDENT_POINTS = 20.0
MAX_MOVEMENT_POINTS = 15.0

# Risk Score Thresholds
THRESHOLD_CRITICAL = 75.0
THRESHOLD_HIGH = 55.0
THRESHOLD_MEDIUM = 35.0

def assess_logistics_risk(
    inventory_item: Dict[str, Any],
    depot_record: Dict[str, Any],
    stockout_prediction: Dict[str, Any],
    active_incidents: List[Dict[str, Any]],
    active_trips: List[Dict[str, Any]],
    environmental_assessment: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates operational signals (stock-out, inventory ratio, incidents, movement)
    and optional environmental risk signal to calculate a deterministic 0-100 risk score,
    risk classification, structured contributing factors, and explanation narrative.
    """
    item_id = inventory_item["id"]
    item_name = inventory_item.get("item_name", item_id)
    depot_id = depot_record.get("id", inventory_item.get("depot_id", "UNKNOWN"))
    depot_name = depot_record.get("name", depot_id)
    base_id = depot_record.get("base_id")
    category = inventory_item.get("category", "N/A")
    unit = inventory_item.get("unit", "units")

    raw_curr = inventory_item.get("current_quantity")
    current_qty = float(raw_curr) if raw_curr is not None else 0.0

    raw_thresh = inventory_item.get("minimum_threshold")
    min_thresh = float(raw_thresh) if raw_thresh is not None else 0.0

    factors: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # SIGNAL A: STOCK-OUT PREDICTION SIGNAL (Max 40.0 pts)
    # -------------------------------------------------------------------------
    so_risk = stockout_prediction.get("risk_level", "LOW").upper()
    days_breach = stockout_prediction.get("days_until_threshold_breach")
    days_stockout = stockout_prediction.get("days_until_stockout")

    if so_risk == "CRITICAL":
        so_pts = 40.0
        so_severity = "CRITICAL"
        if days_breach == 0:
            so_msg = "Stock-Out Risk is CRITICAL: minimum threshold is already breached."
        elif days_stockout is not None:
            so_msg = f"Stock-Out Risk is CRITICAL: zero stock expected in {days_stockout} day(s)."
        else:
            so_msg = "Stock-Out Risk is CRITICAL: threshold breach projected within 2 days."
    elif so_risk == "HIGH":
        so_pts = 28.0
        so_severity = "HIGH"
        so_msg = "Stock-Out Risk is HIGH: threshold breach projected within 3-5 days."
    elif so_risk == "MEDIUM":
        so_pts = 16.0
        so_severity = "MEDIUM"
        so_msg = "Stock-Out Risk is MEDIUM: stock trajectory indicates depletion near end of forecast window."
    else:
        so_pts = 5.0
        so_severity = "LOW"
        so_msg = "Stock-Out Risk is LOW: stock projection remains comfortably above threshold."

    factors.append({
        "signal": "stockout_risk",
        "severity": so_severity,
        "score_contribution": round(so_pts, 1),
        "message": so_msg
    })

    # -------------------------------------------------------------------------
    # SIGNAL B: CURRENT INVENTORY CONDITION SIGNAL (Max 25.0 pts)
    # -------------------------------------------------------------------------
    stock_ratio = (current_qty / min_thresh) if min_thresh > 0 else 2.0

    if current_qty <= min_thresh:
        inv_pts = 25.0
        inv_status = "BELOW_THRESHOLD"
        inv_severity = "CRITICAL"
        inv_msg = f"Current stock ({current_qty:,.1f} {unit}) is below minimum threshold ({min_thresh:,.1f} {unit})."
    elif stock_ratio <= 1.25:
        inv_pts = 18.0
        inv_status = "NEAR_THRESHOLD"
        inv_severity = "HIGH"
        inv_msg = f"Current stock ({current_qty:,.1f} {unit}) is near minimum threshold ({min_thresh:,.1f} {unit})."
    elif stock_ratio <= 1.5:
        inv_pts = 10.0
        inv_status = "MODERATE_BUFFER"
        inv_severity = "MEDIUM"
        inv_msg = f"Current stock ({current_qty:,.1f} {unit}) has moderate safety buffer."
    else:
        inv_pts = 2.0
        inv_status = "HEALTHY_BUFFER"
        inv_severity = "LOW"
        inv_msg = f"Current stock ({current_qty:,.1f} {unit}) has healthy safety buffer."

    factors.append({
        "signal": "inventory_condition",
        "severity": inv_severity,
        "score_contribution": round(inv_pts, 1),
        "message": inv_msg
    })

    # -------------------------------------------------------------------------
    # SIGNAL C: OPERATIONAL INCIDENT DISRUPTION SIGNAL (Max 20.0 pts)
    # -------------------------------------------------------------------------
    matching_incidents = [
        inc for inc in active_incidents
        if inc.get("is_active") == 1 or inc.get("is_active") is True
    ]

    max_inc_severity = None
    if matching_incidents:
        severities = [str(inc.get("severity", "LOW")).upper() for inc in matching_incidents]
        if "CRITICAL" in severities or "HIGH" in severities:
            inc_pts = 20.0
            inc_severity = "HIGH"
            max_inc_severity = "HIGH"
            inc_title = matching_incidents[0].get("title", "Active Disruption")
            inc_msg = f"Active high-severity road disruption reported in sector: '{inc_title}'."
        elif "MEDIUM" in severities:
            inc_pts = 10.0
            inc_severity = "MEDIUM"
            max_inc_severity = "MEDIUM"
            inc_msg = f"Active medium-severity incident reported in sector."
        else:
            inc_pts = 5.0
            inc_severity = "LOW"
            max_inc_severity = "LOW"
            inc_msg = f"Minor active incident reported in sector."
    else:
        inc_pts = 0.0
        inc_severity = "NONE"
        inc_msg = "No active road disruptions or incidents reported in operational sector."

    factors.append({
        "signal": "operational_incident",
        "severity": inc_severity,
        "score_contribution": round(inc_pts, 1),
        "message": inc_msg
    })

    # -------------------------------------------------------------------------
    # SIGNAL D: MOVEMENT / TRIP DISRUPTION SIGNAL (Max 15.0 pts)
    # -------------------------------------------------------------------------
    matching_trips = [t for t in active_trips if t.get("status") == "ACTIVE"]

    if matching_trips:
        move_pts = 5.0
        move_severity = "LOW"
        move_msg = f"{len(matching_trips)} active supply trip(s) currently in transit."
    else:
        move_pts = 0.0
        move_severity = "NONE"
        move_msg = "No active supply trips currently in transit targeting this depot."

    factors.append({
        "signal": "movement_status",
        "severity": move_severity,
        "score_contribution": round(move_pts, 1),
        "message": move_msg
    })

    # -------------------------------------------------------------------------
    # SIGNAL E: ENVIRONMENTAL RISK SIGNAL (Max 15.0 pts, 15% weight)
    # -------------------------------------------------------------------------
    env_signal_data: Dict[str, Any] = {}
    if environmental_assessment and isinstance(environmental_assessment, dict):
        env_score = float(environmental_assessment.get("environmental_risk_score", 0.0))
        env_class = environmental_assessment.get("classification", "LOW")
        env_route_id = environmental_assessment.get("route_id", "UNKNOWN")
        env_dominant = "WEATHER" if float(environmental_assessment.get("weather_risk_score", 0.0)) >= float(environmental_assessment.get("terrain_risk_score", 0.0)) else "TERRAIN"

        env_pts = round((env_score / 100.0) * 15.0, 1)

        if env_score >= THRESHOLD_CRITICAL:
            env_sev = "CRITICAL"
        elif env_score >= THRESHOLD_HIGH:
            env_sev = "HIGH"
        elif env_score >= THRESHOLD_MEDIUM:
            env_sev = "MEDIUM"
        elif env_pts > 0:
            env_sev = "LOW"
        else:
            env_sev = "NONE"

        if env_pts > 0:
            factors.append({
                "signal": "environmental_risk",
                "severity": env_sev,
                "score_contribution": env_pts,
                "message": f"Environmental risk on corridor '{env_route_id}' ({env_class}, Score: {env_score:.1f}/100) adds {env_pts:.1f} pts. Dominant factor: {env_dominant}."
            })

        env_signal_data = {
            "route_id": env_route_id,
            "environmental_risk_score": env_score,
            "classification": env_class,
            "dominant_dimension": env_dominant,
            "contribution": env_pts,
            "status": "AVAILABLE"
        }
        total_raw = (so_pts + inv_pts + inc_pts + move_pts) * 0.85 + env_pts
    else:
        env_signal_data = {
            "route_id": None,
            "environmental_risk_score": 0.0,
            "classification": None,
            "dominant_dimension": None,
            "contribution": 0.0,
            "status": "UNAVAILABLE"
        }
        total_raw = so_pts + inv_pts + inc_pts + move_pts

    # -------------------------------------------------------------------------
    # COMPOSITE SCORE & DETERMINISTIC RISK LEVEL CLASSIFICATION
    # -------------------------------------------------------------------------
    risk_score = min(100.0, max(0.0, round(total_raw, 1)))

    if risk_score >= THRESHOLD_CRITICAL or so_risk == "CRITICAL":
        risk_level = "CRITICAL"
    elif risk_score >= THRESHOLD_HIGH or so_risk == "HIGH":
        risk_level = "HIGH"
    elif risk_score >= THRESHOLD_MEDIUM:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # -------------------------------------------------------------------------
    # EXPLANATION GENERATION FROM CALCULATED SIGNALS
    # -------------------------------------------------------------------------
    major_reasons = [f["message"] for f in factors if f["score_contribution"] > 0]

    explanation = (
        f"Item '{item_name}' at depot '{depot_name}' assessed at Risk Level {risk_level} (Score: {risk_score:.1f}/100). "
        f"Primary contributing factors: " + " ".join(major_reasons)
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    return {
        "inventory_item_id": item_id,
        "inventory_item_name": item_name,
        "depot_id": depot_id,
        "depot_name": depot_name,
        "base_id": base_id,
        "category": category,
        "unit": unit,
        "current_quantity": current_qty,
        "minimum_threshold": min_thresh,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "stockout_risk": so_risk,
        "inventory_signal": {
            "status": inv_status,
            "stock_ratio": round(stock_ratio, 2),
            "contribution": inv_pts
        },
        "incident_signal": {
            "active_incidents_count": len(matching_incidents),
            "max_severity": max_inc_severity,
            "contribution": inc_pts
        },
        "movement_signal": {
            "active_trips_count": len(matching_trips),
            "disrupted_trips_count": 0,
            "contribution": move_pts
        },
        "environmental_signal": env_signal_data,
        "contributing_factors": factors,
        "explanation": explanation,
        "data_source": "synthetic_demo",
        "generated_at": now_iso
    }

