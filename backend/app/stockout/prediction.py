"""
SENTINEL LOGIX AI - Stock-Out Prediction Engine
Calculates forward-looking 7-day stock projections, threshold breach dates,
zero stock-out dates, risk classifications, and human-readable explanations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..forecasting import forecast_demand, DATA_SOURCE

# Named Risk Threshold Constants
RISK_CRITICAL = "CRITICAL"
RISK_HIGH = "HIGH"
RISK_MEDIUM = "MEDIUM"
RISK_LOW = "LOW"

CRITICAL_BREACH_WINDOW_DAYS = 2
CRITICAL_STOCKOUT_WINDOW_DAYS = 3
HIGH_BREACH_WINDOW_DAYS = 5
HIGH_STOCKOUT_WINDOW_DAYS = 7
MEDIUM_SAFETY_MARGIN_MULTIPLIER = 1.25

def calculate_stockout_prediction(
    item_record: Dict[str, Any],
    horizon_days: int = 7,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculates 7-day projected inventory trajectory, threshold breaches,
    stock-out dates, explainable risk levels, and diagnostic narratives.
    """
    item_id = item_record["id"]
    item_name = item_record.get("item_name", item_id)
    depot_id = item_record.get("depot_id", "UNKNOWN")
    category = item_record.get("category", "N/A")
    unit = item_record.get("unit", "units")
    raw_curr = item_record.get("current_quantity")
    current_qty = float(raw_curr) if raw_curr is not None else 0.0

    raw_thresh = item_record.get("minimum_threshold")
    min_thresh = float(raw_thresh) if raw_thresh is not None else 0.0

    raw_cap = item_record.get("maximum_capacity")
    max_cap = float(raw_cap) if raw_cap is not None else 1000.0

    raw_rate = item_record.get("daily_consumption_rate")
    base_rate = float(raw_rate) if raw_rate is not None else 0.0

    # 1. Obtain demand forecast for 7-day horizon
    forecast_res = forecast_demand(inventory_item_id=item_id, horizon_days=horizon_days, db_path=db_path)
    raw_forecasts = forecast_res.get("forecasts", [])

    today = datetime.now().date()
    forecasted_points = []
    
    # Fallback to baseline consumption rate if forecast pipeline returns insufficient points
    if not raw_forecasts:
        for step in range(1, horizon_days + 1):
            f_date = str(today + timedelta(days=step))
            forecasted_points.append({
                "step": step,
                "date": f_date,
                "predicted_consumption": base_rate
            })
    else:
        for f in raw_forecasts:
            forecasted_points.append({
                "step": f["step"],
                "date": f["forecast_date"],
                "predicted_consumption": float(f["predicted_consumption"])
            })

    # Ensure we cover the full requested horizon
    if len(forecasted_points) < horizon_days:
        last_step = forecasted_points[-1]["step"] if forecasted_points else 0
        last_date = datetime.strptime(forecasted_points[-1]["date"], "%Y-%m-%d").date() if forecasted_points else today
        last_val = forecasted_points[-1]["predicted_consumption"] if forecasted_points else base_rate
        for step in range(last_step + 1, horizon_days + 1):
            f_date = str(last_date + timedelta(days=step - last_step))
            forecasted_points.append({
                "step": step,
                "date": f_date,
                "predicted_consumption": last_val
            })

    # 2. Stock Projection Trajectory Calculation (clamped at 0.0)
    projected_points = []
    running_stock = current_qty

    days_until_breach: Optional[int] = None
    expected_breach_date: Optional[str] = None

    days_until_stockout: Optional[int] = None
    expected_stockout_date: Optional[str] = None

    # Check immediate day-0 status
    if current_qty <= min_thresh:
        days_until_breach = 0
        expected_breach_date = str(today)

    if current_qty <= 0.0:
        days_until_stockout = 0
        expected_stockout_date = str(today)

    for point in forecasted_points:
        step = point["step"]
        p_date = point["date"]
        cons_qty = point["predicted_consumption"]

        running_stock = max(0.0, running_stock - cons_qty)
        projected_points.append({
            "step": step,
            "date": p_date,
            "projected_quantity": round(running_stock, 2)
        })

        # Track threshold breach
        if days_until_breach is None and running_stock <= min_thresh:
            days_until_breach = step
            expected_breach_date = p_date

        # Track zero stock-out
        if days_until_stockout is None and running_stock <= 0.0:
            days_until_stockout = step
            expected_stockout_date = p_date

    # 3. Transparent Risk Classification Logic
    final_stock = projected_points[-1]["projected_quantity"] if projected_points else current_qty

    if (
        current_qty <= min_thresh
        or (days_until_breach is not None and days_until_breach <= CRITICAL_BREACH_WINDOW_DAYS)
        or (days_until_stockout is not None and days_until_stockout <= CRITICAL_STOCKOUT_WINDOW_DAYS)
    ):
        risk_level = RISK_CRITICAL
    elif (
        (days_until_breach is not None and days_until_breach <= HIGH_BREACH_WINDOW_DAYS)
        or (days_until_stockout is not None and days_until_stockout <= HIGH_STOCKOUT_WINDOW_DAYS)
    ):
        risk_level = RISK_HIGH
    elif (
        (days_until_breach is not None and days_until_breach > HIGH_BREACH_WINDOW_DAYS)
        or final_stock <= (min_thresh * MEDIUM_SAFETY_MARGIN_MULTIPLIER)
    ):
        risk_level = RISK_MEDIUM
    else:
        risk_level = RISK_LOW

    # 4. Human-Readable Explanation Generator
    avg_daily_forecast = round(
        sum(p["predicted_consumption"] for p in forecasted_points) / len(forecasted_points), 2
    ) if forecasted_points else base_rate

    if days_until_breach == 0:
        breach_desc = "already breached"
    elif days_until_breach is not None:
        breach_desc = f"expected in {days_until_breach} day(s) on {expected_breach_date}"
    else:
        breach_desc = "none in forecast window"

    if days_until_stockout == 0:
        stockout_desc = "depleted (0 stock)"
    elif days_until_stockout is not None:
        stockout_desc = f"in {days_until_stockout} day(s) on {expected_stockout_date}"
    else:
        stockout_desc = "none in forecast window"

    explanation = (
        f"Item '{item_name}' current stock is {current_qty:,.1f} {unit} against minimum threshold of {min_thresh:,.1f} {unit}. "
        f"Forecasted consumption averages {avg_daily_forecast:,.1f} {unit}/day over {horizon_days} days. "
        f"Threshold breach: {breach_desc}. Expected stock-out: {stockout_desc}. Risk Level: {risk_level}."
    )

    return {
        "inventory_item_id": item_id,
        "item_name": item_name,
        "depot_id": depot_id,
        "category": category,
        "unit": unit,
        "current_quantity": current_qty,
        "minimum_threshold": min_thresh,
        "maximum_capacity": max_cap,
        "forecast_horizon_days": horizon_days,
        "forecasted_consumption": forecasted_points,
        "projected_inventory": projected_points,
        "days_until_threshold_breach": days_until_breach,
        "expected_threshold_breach_date": expected_breach_date,
        "days_until_stockout": days_until_stockout,
        "expected_stockout_date": expected_stockout_date,
        "risk_level": risk_level,
        "explanation": explanation,
        "data_source": DATA_SOURCE
    }
