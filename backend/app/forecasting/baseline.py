"""
SENTINEL LOGIX AI - Demand Forecasting Baselines
Provides Naive (t-1) and Moving Average baseline forecasters for baseline performance comparisons.
"""

from typing import List, Dict, Any, Optional

class NaiveBaseline:
    """
    Naive Baseline Forecaster.
    Predicts next day consumption as the most recently observed consumption value (t-1).
    """
    def __init__(self):
        self.last_observed_value: Optional[float] = None

    def fit(self, records: List[Dict[str, Any]]) -> "NaiveBaseline":
        """Fits baseline by recording the last valid quantity_consumed in training data."""
        valid_vals = [
            float(r["quantity_consumed"])
            for r in records
            if r.get("quantity_consumed") is not None
        ]
        if valid_vals:
            self.last_observed_value = valid_vals[-1]
        return self

    def predict_record(self, record: Dict[str, Any]) -> float:
        """
        Predicts consumption for a single feature record using lag_1 if available,
        otherwise falling back to stored last observed training value or 0.0.
        """
        if record.get("lag_1") is not None:
            return float(record["lag_1"])
        if self.last_observed_value is not None:
            return self.last_observed_value
        return float(record.get("quantity_consumed", 0.0))

    def predict(self, records: List[Dict[str, Any]]) -> List[float]:
        """Generates predictions for a list of feature records."""
        return [self.predict_record(r) for r in records]


class MovingAverageBaseline:
    """
    Moving Average Baseline Forecaster.
    Predicts next day consumption as the average of recent historical observations (e.g. 3-day rolling mean).
    """
    def __init__(self, window_size: int = 3):
        self.window_size = window_size
        self.last_rolling_mean: Optional[float] = None

    def fit(self, records: List[Dict[str, Any]]) -> "MovingAverageBaseline":
        """Fits baseline by recording the recent moving average of training records."""
        valid_vals = [
            float(r["quantity_consumed"])
            for r in records
            if r.get("quantity_consumed") is not None
        ]
        if valid_vals:
            recent = valid_vals[-self.window_size:]
            self.last_rolling_mean = round(sum(recent) / len(recent), 2)
        return self

    def predict_record(self, record: Dict[str, Any]) -> float:
        """
        Predicts consumption using rolling_mean_3 if available,
        otherwise lag_1, or fallback to stored moving average.
        """
        if record.get("rolling_mean_3") is not None:
            return float(record["rolling_mean_3"])
        if record.get("lag_1") is not None:
            return float(record["lag_1"])
        if self.last_rolling_mean is not None:
            return self.last_rolling_mean
        return float(record.get("quantity_consumed", 0.0))

    def predict(self, records: List[Dict[str, Any]]) -> List[float]:
        """Generates predictions for a list of feature records."""
        return [self.predict_record(r) for r in records]
