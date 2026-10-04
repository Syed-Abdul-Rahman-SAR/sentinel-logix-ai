"""
SENTINEL LOGIX AI - Stock-Out Prediction Engine Module
Provides forward-looking 7-day stock projections, threshold breach detection,
expected stock-out dates, explainable risk levels, and REST API handlers.
"""

from .schemas import StockoutPredictionOut
from .prediction import calculate_stockout_prediction, RISK_CRITICAL, RISK_HIGH, RISK_MEDIUM, RISK_LOW
from .service import StockoutService

__all__ = [
    "StockoutPredictionOut",
    "calculate_stockout_prediction",
    "StockoutService",
    "RISK_CRITICAL",
    "RISK_HIGH",
    "RISK_MEDIUM",
    "RISK_LOW",
]
