"""
SENTINEL LOGIX AI - Demand Forecasting Module
Includes data extraction, validation, feature engineering, baselines, ML model training,
evaluation metrics, model artifact serialization, and multi-day recursive forecasting.
"""

from .dataset import (
    DATA_SOURCE,
    extract_consumption_dataset,
    chronological_split,
    prepare_forecasting_dataset,
)
from .validation import (
    validate_time_series_data,
    generate_quality_report,
)
from .features import (
    engineer_features,
)
from .baseline import (
    NaiveBaseline,
    MovingAverageBaseline,
)
from .evaluation import (
    calculate_mae,
    calculate_rmse,
    calculate_mape,
    evaluate_predictions,
)
from .model import (
    DemandForecaster,
    train_and_evaluate_forecasting_models,
    forecast_demand,
    HAS_XGBOOST,
)

__all__ = [
    "DATA_SOURCE",
    "extract_consumption_dataset",
    "chronological_split",
    "prepare_forecasting_dataset",
    "validate_time_series_data",
    "generate_quality_report",
    "engineer_features",
    "NaiveBaseline",
    "MovingAverageBaseline",
    "calculate_mae",
    "calculate_rmse",
    "calculate_mape",
    "evaluate_predictions",
    "DemandForecaster",
    "train_and_evaluate_forecasting_models",
    "forecast_demand",
    "HAS_XGBOOST",
]
