"""
SENTINEL LOGIX AI - Machine Learning Demand Forecaster
Implements decision tree ensemble regression (XGBoost / Gradient Boosting),
feature encoding, incomplete row filtering, feature importance, artifact saving/loading,
and recursive multi-day forecast generation.
"""

import os
import json
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

# Check for XGBoost availability; fall back to scikit-learn GradientBoostingRegressor
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

from sklearn.ensemble import GradientBoostingRegressor

from .dataset import DATA_SOURCE, prepare_forecasting_dataset, extract_consumption_dataset
from .validation import validate_time_series_data
from .features import engineer_features
from .baseline import NaiveBaseline, MovingAverageBaseline
from .evaluation import evaluate_predictions

# Categorical Encoders
INTENSITY_ENCODING = {"NORMAL": 0, "HIGH": 1, "CRITICAL": 2}
CRITICALITY_ENCODING = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

FEATURE_COLUMNS = [
    "time_index",
    "day_of_week",
    "day_of_month",
    "month",
    "lag_1",
    "lag_2",
    "lag_3",
    "rolling_mean_3",
    "operational_intensity_encoded",
    "inventory_criticality_encoded",
    "minimum_threshold",
    "daily_consumption_rate"
]

class DemandForecaster:
    """
    ML Demand Forecaster using Gradient Boosted Decision Trees (XGBoost or scikit-learn).
    Designed for small operational datasets with strict leakage prevention and feature encoding.
    """
    def __init__(self, n_estimators: int = 30, max_depth: int = 3, learning_rate: float = 0.05, random_state: int = 42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.random_state = random_state

        if HAS_XGBOOST:
            self.model_engine = "xgboost"
            self.model = xgb.XGBRegressor(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                random_state=self.random_state,
                objective="reg:squarederror"
            )
        else:
            self.model_engine = "sklearn_gradient_boosting"
            self.model = GradientBoostingRegressor(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                random_state=self.random_state
            )

        self.is_fitted = False
        self.feature_names = FEATURE_COLUMNS
        self.training_records_count = 0
        self.removed_incomplete_count = 0

    def encode_feature_record(self, record: Dict[str, Any]) -> Optional[List[float]]:
        """
        Converts a raw feature dictionary into a numeric feature vector.
        Returns None if required features (e.g. lag_1, rolling_mean_3) are missing (None).
        Note: 'current_inventory' is strictly excluded as it represents a present-day snapshot,
        not a historical time-series observation at time t.
        """
        lag_1 = record.get("lag_1")
        rolling_3 = record.get("rolling_mean_3")

        # Drop incomplete early history rows to prevent NaN contamination or improper imputation
        if lag_1 is None or rolling_3 is None:
            return None

        lag_2 = record.get("lag_2") if record.get("lag_2") is not None else lag_1
        lag_3 = record.get("lag_3") if record.get("lag_3") is not None else lag_2

        op_int_str = str(record.get("operational_intensity", "NORMAL")).upper()
        op_int_enc = float(INTENSITY_ENCODING.get(op_int_str, 0))

        crit_str = str(record.get("inventory_criticality", "MEDIUM")).upper()
        crit_enc = float(CRITICALITY_ENCODING.get(crit_str, 1))

        vector = [
            float(record.get("time_index", 0)),
            float(record.get("day_of_week", 0) if record.get("day_of_week") is not None else 0),
            float(record.get("day_of_month", 1) if record.get("day_of_month") is not None else 1),
            float(record.get("month", 1) if record.get("month") is not None else 1),
            float(lag_1),
            float(lag_2),
            float(lag_3),
            float(rolling_3),
            op_int_enc,
            crit_enc,
            float(record.get("minimum_threshold", 0.0)),
            float(record.get("daily_consumption_rate", 0.0))
        ]
        return vector

    def prepare_matrix(self, records: List[Dict[str, Any]]) -> Tuple[List[List[float]], List[float], int]:
        """
        Prepares numeric X feature matrix and y target vector from engineered records.
        Tracks and reports how many incomplete rows were removed.
        """
        X = []
        y = []
        removed_count = 0

        for r in records:
            vec = self.encode_feature_record(r)
            if vec is None:
                removed_count += 1
                continue
            X.append(vec)
            y.append(float(r.get("quantity_consumed", 0.0)))

        return X, y, removed_count

    def fit(self, records: List[Dict[str, Any]]) -> "DemandForecaster":
        """Fits the regression model using feature-complete training records."""
        X, y, removed = self.prepare_matrix(records)
        self.removed_incomplete_count = removed
        self.training_records_count = len(X)

        if len(X) == 0:
            raise ValueError("Cannot train demand forecasting model: no complete feature records available after filtering.")

        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, records: List[Dict[str, Any]]) -> List[float]:
        """Generates predictions for feature records."""
        if not self.is_fitted:
            raise RuntimeError("DemandForecaster is not fitted. Call fit() before predict().")

        preds = []
        for r in records:
            vec = self.encode_feature_record(r)
            if vec is None:
                # Fallback for early rows with insufficient history
                fallback = float(r.get("quantity_consumed", 0.0))
                preds.append(fallback)
            else:
                p = self.model.predict([vec])[0]
                preds.append(round(max(0.0, float(p)), 2))
        return preds

    def get_feature_importances(self) -> Dict[str, float]:
        """Extracts normalized feature importance rankings."""
        if not self.is_fitted:
            return {}

        importances = getattr(self.model, "feature_importances_", None)
        if importances is None:
            return {}

        importance_dict = {
            col: round(float(imp), 4)
            for col, imp in zip(self.feature_names, importances)
        }

        # Sort by importance descending
        return dict(sorted(importance_dict.items(), key=lambda item: item[1], reverse=True))

    def save_model(
        self,
        artifact_dir: str = "backend/models",
        model_name: str = "demand_forecaster.pkl",
        split_counts: Optional[Dict[str, int]] = None,
        date_range: Optional[Dict[str, str]] = None
    ) -> str:
        """Saves model artifact and metadata to local disk."""
        os.makedirs(artifact_dir, exist_ok=True)
        filepath = os.path.join(artifact_dir, model_name)

        payload = {
            "model_engine": self.model_engine,
            "has_xgboost": HAS_XGBOOST,
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "random_state": self.random_state,
            "feature_names": self.feature_names,
            "training_records_count": self.training_records_count,
            "removed_incomplete_count": self.removed_incomplete_count,
            "split_counts": split_counts or {
                "train": self.training_records_count,
                "validation": 0,
                "test": 0
            },
            "dataset_date_range": date_range or {"start_date": None, "end_date": None},
            "training_timestamp": datetime.now().isoformat(),
            "data_source": DATA_SOURCE,
            "model_object": self.model
        }

        with open(filepath, "wb") as f:
            pickle.dump(payload, f)

        # Save human-readable metadata JSON sidecar
        meta_path = os.path.join(artifact_dir, model_name.replace(".pkl", "_metadata.json"))
        meta_payload = {k: v for k, v in payload.items() if k != "model_object"}
        meta_payload["feature_importances"] = self.get_feature_importances()
        with open(meta_path, "w") as f:
            json.dump(meta_payload, f, indent=2)

        return filepath

    @classmethod
    def load_model(cls, filepath: str) -> "DemandForecaster":
        """Loads a saved model artifact from local disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model artifact file not found at: '{filepath}'")

        with open(filepath, "rb") as f:
            payload = pickle.load(f)

        forecaster = cls(
            n_estimators=payload.get("n_estimators", 30),
            max_depth=payload.get("max_depth", 3),
            learning_rate=payload.get("learning_rate", 0.05),
            random_state=payload.get("random_state", 42)
        )
        forecaster.model_engine = payload.get("model_engine", forecaster.model_engine)
        forecaster.model = payload["model_object"]
        forecaster.feature_names = payload.get("feature_names", FEATURE_COLUMNS)
        forecaster.training_records_count = payload.get("training_records_count", 0)
        forecaster.removed_incomplete_count = payload.get("removed_incomplete_count", 0)
        forecaster.is_fitted = True
        return forecaster


def train_and_evaluate_forecasting_models(
    inventory_item_id: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Trains Naive, Moving Average, and ML Demand Forecasters on training set and evaluates on unseen test set.
    Returns structured metrics comparison dictionary.
    """
    dataset_prep = prepare_forecasting_dataset(inventory_item_id=inventory_item_id, db_path=db_path)
    splits = dataset_prep["splits"]

    train_data = splits["train_data"]
    val_data = splits["val_data"]
    test_data = splits["test_data"]

    if not train_data or not test_data:
        return {
            "data_source": DATA_SOURCE,
            "inventory_item_id": inventory_item_id,
            "status": "Insufficient data to train and evaluate models",
            "test_metrics": {}
        }

    # 1. Fit Naive Baseline
    naive = NaiveBaseline().fit(train_data)
    naive_test_preds = naive.predict(test_data)
    test_y_true = [float(r["quantity_consumed"]) for r in test_data]
    naive_metrics = evaluate_predictions(test_y_true, naive_test_preds)

    # 2. Fit Moving Average Baseline
    ma_base = MovingAverageBaseline(window_size=3).fit(train_data)
    ma_test_preds = ma_base.predict(test_data)
    ma_metrics = evaluate_predictions(test_y_true, ma_test_preds)

    # 3. Fit ML Model (XGBoost / Gradient Boosting)
    ml_forecaster = DemandForecaster(n_estimators=30, max_depth=3, learning_rate=0.05, random_state=42)

    try:
        ml_forecaster.fit(train_data)
        ml_test_preds = ml_forecaster.predict(test_data)
        ml_metrics = evaluate_predictions(test_y_true, ml_test_preds)
        feat_importances = ml_forecaster.get_feature_importances()
        ml_status = "Trained & Evaluated"
    except Exception as e:
        ml_metrics = {"mae": 0.0, "rmse": 0.0, "mape": "N/A", "status": f"Training failed: {str(e)}"}
        feat_importances = {}
        ml_status = f"Error: {str(e)}"

    return {
        "data_source": DATA_SOURCE,
        "inventory_item_id": inventory_item_id or "ALL_ITEMS",
        "has_xgboost": HAS_XGBOOST,
        "active_model_engine": ml_forecaster.model_engine if ml_forecaster.is_fitted else "N/A",
        "record_counts": {
            "total_records": dataset_prep["raw_records_count"],
            "training_records": splits["train_count"],
            "validation_records": splits["val_count"],
            "test_records": splits["test_count"],
            "filtered_incomplete_records": ml_forecaster.removed_incomplete_count
        },
        "date_ranges": {
            "train": splits["train_date_range"],
            "val": splits["val_date_range"],
            "test": splits["test_date_range"],
        },
        "models_evaluation": {
            "Naive_Baseline": naive_metrics,
            "Moving_Average_3D": ma_metrics,
            "ML_Demand_Forecaster": ml_metrics,
        },
        "ml_feature_importances": feat_importances,
        "limitation_notice": "Evaluation uses synthetic demonstration data with only 14 days of history per item."
    }


def forecast_demand(
    inventory_item_id: str,
    horizon_days: int = 3,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates multi-day recursive demand forecasts (1-3 days horizon) for a target inventory item.
    Uses ONLY predicted values for future lag features (preventing data leakage).
    """
    horizon_days = max(1, min(3, horizon_days))  # Enforce 1-3 days horizon boundary

    raw_records = extract_consumption_dataset(inventory_item_id=inventory_item_id, db_path=db_path)
    if not raw_records:
        return {
            "data_source": DATA_SOURCE,
            "inventory_item_id": inventory_item_id,
            "horizon_days": horizon_days,
            "status": "No historical consumption records found",
            "forecasts": []
        }

    # Engineer features on existing chronological records
    feat_records = engineer_features(raw_records)

    # Train forecaster on all historical records for this item
    forecaster = DemandForecaster(n_estimators=30, max_depth=3, learning_rate=0.05, random_state=42)
    forecaster.fit(feat_records)

    last_record = feat_records[-1]
    last_date_str = str(last_record["consumption_date"]).split("T")[0]
    last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()

    # Dynamic state tracking for recursive forecasting
    historical_quantities = [float(r["quantity_consumed"]) for r in feat_records]
    current_time_index = int(last_record.get("time_index", len(feat_records) - 1))

    forecast_results = []

    for step in range(1, horizon_days + 1):
        target_date = last_date + timedelta(days=step)
        target_date_str = str(target_date)

        next_time_index = current_time_index + step

        # Derive lags recursively from historical_quantities (which includes prior predictions)
        lag_1 = historical_quantities[-1] if len(historical_quantities) >= 1 else 0.0
        lag_2 = historical_quantities[-2] if len(historical_quantities) >= 2 else lag_1
        lag_3 = historical_quantities[-3] if len(historical_quantities) >= 3 else lag_2

        recent_3 = historical_quantities[-3:]
        rolling_3 = round(sum(recent_3) / len(recent_3), 2)

        synth_record = {
            "time_index": next_time_index,
            "day_of_week": target_date.weekday(),
            "day_of_month": target_date.day,
            "month": target_date.month,
            "lag_1": lag_1,
            "lag_2": lag_2,
            "lag_3": lag_3,
            "rolling_mean_3": rolling_3,
            "operational_intensity": last_record.get("operational_intensity", "NORMAL"),
            "inventory_criticality": last_record.get("inventory_criticality", "MEDIUM"),
            "current_inventory": last_record.get("current_inventory", 0.0),
            "minimum_threshold": last_record.get("minimum_threshold", 0.0),
            "daily_consumption_rate": last_record.get("daily_consumption_rate", 0.0),
            "quantity_consumed": 0.0  # Placeholder target
        }

        # Predict using trained model
        pred_qty = forecaster.predict([synth_record])[0]

        # Append prediction to state for subsequent step's lags (recursive update)
        historical_quantities.append(pred_qty)

        forecast_results.append({
            "step": step,
            "forecast_date": target_date_str,
            "predicted_consumption": pred_qty,
            "unit": last_record.get("unit", "units"),
            "item_name": last_record.get("item_name", inventory_item_id)
        })

    return {
        "data_source": DATA_SOURCE,
        "inventory_item_id": inventory_item_id,
        "item_name": last_record.get("item_name", inventory_item_id),
        "active_model_engine": forecaster.model_engine,
        "horizon_days": horizon_days,
        "forecasts": forecast_results,
        "limitation_notice": "Forecast generated using short 14-day synthetic demonstration dataset."
    }
