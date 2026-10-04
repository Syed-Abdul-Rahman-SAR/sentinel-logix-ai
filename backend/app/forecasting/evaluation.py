"""
SENTINEL LOGIX AI - Forecasting Evaluation Metrics
Computes MAE, RMSE, and zero-safe MAPE for time-series demand models.
"""

import math
from typing import List, Dict, Any, Union

def calculate_mae(y_true: List[float], y_pred: List[float]) -> float:
    """Calculates Mean Absolute Error (MAE)."""
    if not y_true or not y_pred or len(y_true) != len(y_pred):
        return 0.0
    n = len(y_true)
    total_err = sum(abs(yt - yp) for yt, yp in zip(y_true, y_pred))
    return round(total_err / n, 2)


def calculate_rmse(y_true: List[float], y_pred: List[float]) -> float:
    """Calculates Root Mean Squared Error (RMSE)."""
    if not y_true or not y_pred or len(y_true) != len(y_pred):
        return 0.0
    n = len(y_true)
    mse = sum((yt - yp) ** 2 for yt, yp in zip(y_true, y_pred)) / n
    return round(math.sqrt(mse), 2)


def calculate_mape(y_true: List[float], y_pred: List[float], epsilon: float = 1e-5) -> Union[float, str]:
    """
    Calculates Mean Absolute Percentage Error (MAPE, %).
    Protects against division by zero by adding epsilon or filtering zero target values.
    """
    if not y_true or not y_pred or len(y_true) != len(y_pred):
        return "N/A"

    pct_errors = []
    for yt, yp in zip(y_true, y_pred):
        denom = abs(yt) if abs(yt) > epsilon else epsilon
        pct_errors.append((abs(yt - yp) / denom) * 100.0)

    if not pct_errors:
        return "N/A"

    avg_mape = sum(pct_errors) / len(pct_errors)
    return round(avg_mape, 2)


def evaluate_predictions(y_true: List[float], y_pred: List[float]) -> Dict[str, Any]:
    """
    Evaluates predictions against ground truth target values.
    Returns structured metric dictionary containing MAE, RMSE, MAPE, and sample count.
    """
    if not y_true or not y_pred or len(y_true) == 0:
        return {
            "sample_count": 0,
            "mae": 0.0,
            "rmse": 0.0,
            "mape": "N/A",
            "status": "Insufficient data"
        }

    mae = calculate_mae(y_true, y_pred)
    rmse = calculate_rmse(y_true, y_pred)
    mape = calculate_mape(y_true, y_pred)

    return {
        "sample_count": len(y_true),
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "status": "Evaluated"
    }
