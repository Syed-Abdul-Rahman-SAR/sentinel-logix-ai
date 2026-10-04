"""
SENTINEL LOGIX AI - Stock-Out Prediction Schemas
Pydantic data models for stock-out risk assessment, stock projections, and API responses.
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field

class DailyForecastPoint(BaseModel):
    step: int
    date: str
    predicted_consumption: float

class DailyProjectionPoint(BaseModel):
    step: int
    date: str
    projected_quantity: float

class StockoutPredictionOut(BaseModel):
    inventory_item_id: str
    item_name: str
    depot_id: str
    category: str
    unit: str
    current_quantity: float
    minimum_threshold: float
    maximum_capacity: float
    forecast_horizon_days: int
    forecasted_consumption: List[DailyForecastPoint]
    projected_inventory: List[DailyProjectionPoint]
    days_until_threshold_breach: Optional[int] = None
    expected_threshold_breach_date: Optional[str] = None
    days_until_stockout: Optional[int] = None
    expected_stockout_date: Optional[str] = None
    risk_level: str  # CRITICAL, HIGH, MEDIUM, LOW
    explanation: str
    data_source: str = "synthetic_demo"
