"""
SENTINEL LOGIX AI - Stock-Out Prediction API Router
Exposes GET /api/stockout for forward-looking 7-day stock-out risk assessment.
"""

from fastapi import APIRouter, Query
from typing import List, Optional
from ..stockout.schemas import StockoutPredictionOut
from ..stockout.service import StockoutService

router = APIRouter(prefix="/api/stockout", tags=["Stock-Out Prediction"])

@router.get("", response_model=List[StockoutPredictionOut])
async def get_stockout_predictions(
    inventory_item_id: Optional[str] = Query(None, description="Filter by inventory item ID"),
    depot_id: Optional[str] = Query(None, description="Filter by parent depot ID"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level (CRITICAL, HIGH, MEDIUM, LOW)"),
    horizon_days: int = Query(7, ge=1, le=14, description="Forecast horizon in days (default 7)")
):
    """
    Returns 7-day forward-looking stock projections, threshold breach dates,
    stock-out zero dates, risk classifications, and human-readable explanations.
    """
    return StockoutService.predict_stockout(
        inventory_item_id=inventory_item_id,
        depot_id=depot_id,
        risk_level=risk_level,
        horizon_days=horizon_days
    )
