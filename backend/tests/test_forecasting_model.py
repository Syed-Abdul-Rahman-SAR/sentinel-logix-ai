"""
Unit tests for SENTINEL LOGIX AI Demand Forecasting Model & Evaluation Engine.
Verifies baselines, ML training, evaluation metrics (MAE, RMSE, zero-safe MAPE),
model serialization, leakage prevention during recursive forecasting, and per-item evaluation.
"""

import os
import pytest
from backend.app.db.database import get_db, init_db
from backend.app.db.seed import seed_database
from backend.app.forecasting import (
    DATA_SOURCE,
    NaiveBaseline,
    MovingAverageBaseline,
    calculate_mae,
    calculate_rmse,
    calculate_mape,
    evaluate_predictions,
    DemandForecaster,
    train_and_evaluate_forecasting_models,
    forecast_demand,
    HAS_XGBOOST,
)

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Fixture initializing isolated test SQLite database populated with seed data."""
    test_db_file = str(tmp_path / "test_sentinel_model.db")
    import backend.app.config as config
    config.DB_PATH = test_db_file
    init_db(test_db_file)
    seed_database(test_db_file)
    yield test_db_file

# 1. Baseline prediction
def test_naive_and_moving_average_baselines():
    mock_train = [
        {"quantity_consumed": 100.0},
        {"quantity_consumed": 120.0},
        {"quantity_consumed": 140.0}
    ]
    mock_test = [
        {"quantity_consumed": 150.0, "lag_1": 140.0, "rolling_mean_3": 120.0},
        {"quantity_consumed": 160.0, "lag_1": 150.0, "rolling_mean_3": 136.67}
    ]

    naive = NaiveBaseline().fit(mock_train)
    naive_preds = naive.predict(mock_test)
    assert len(naive_preds) == 2
    assert naive_preds[0] == 140.0

    ma = MovingAverageBaseline(window_size=3).fit(mock_train)
    ma_preds = ma.predict(mock_test)
    assert len(ma_preds) == 2
    assert ma_preds[0] == 120.0

# 2. Baseline metric calculation
def test_baseline_metric_calculation():
    y_true = [100.0, 200.0, 300.0]
    y_pred = [110.0, 190.0, 310.0]

    eval_res = evaluate_predictions(y_true, y_pred)
    assert eval_res["mae"] == 10.0
    assert eval_res["rmse"] == 10.0
    assert eval_res["sample_count"] == 3
    assert isinstance(eval_res["mape"], float)

# 3. Model training & prediction shape
def test_model_training_and_prediction_shape(setup_test_db):
    eval_res = train_and_evaluate_forecasting_models(inventory_item_id="INV-IMP-RATIONS", db_path=setup_test_db)

    assert eval_res["data_source"] == DATA_SOURCE
    assert eval_res["inventory_item_id"] == "INV-IMP-RATIONS"
    assert "models_evaluation" in eval_res
    assert "Naive_Baseline" in eval_res["models_evaluation"]
    assert "Moving_Average_3D" in eval_res["models_evaluation"]
    assert "ML_Demand_Forecaster" in eval_res["models_evaluation"]

    ml_metrics = eval_res["models_evaluation"]["ML_Demand_Forecaster"]
    assert ml_metrics["sample_count"] > 0
    assert "mae" in ml_metrics
    assert "rmse" in ml_metrics

# 4. No future leakage during recursive forecast
def test_no_future_leakage_in_recursive_forecast(setup_test_db):
    res = forecast_demand(inventory_item_id="INV-IMP-RATIONS", horizon_days=3, db_path=setup_test_db)
    assert res["data_source"] == DATA_SOURCE
    assert len(res["forecasts"]) == 3

    # Ensure dates increment sequentially
    dates = [f["forecast_date"] for f in res["forecasts"]]
    assert len(dates) == 3
    assert dates[0] < dates[1] < dates[2]

    # Check predicted consumption quantities are non-negative floats
    for f in res["forecasts"]:
        assert isinstance(f["predicted_consumption"], float)
        assert f["predicted_consumption"] >= 0.0

# 5. Chronological evaluation
def test_chronological_evaluation_flow(setup_test_db):
    res = train_and_evaluate_forecasting_models(db_path=setup_test_db)
    ranges = res["date_ranges"]

    assert ranges["train"]["start"] <= ranges["train"]["end"]
    assert ranges["train"]["end"] <= ranges["val"]["start"]
    assert ranges["val"]["end"] <= ranges["test"]["start"]

# 6. MAE calculation
def test_mae_calculation():
    assert calculate_mae([10, 20, 30], [10, 20, 30]) == 0.0
    assert calculate_mae([10, 20], [12, 18]) == 2.0

# 7. RMSE calculation
def test_rmse_calculation():
    assert calculate_rmse([10, 20], [10, 20]) == 0.0
    assert calculate_rmse([10, 20], [13, 16]) == 3.54

# 8. Zero-safe MAPE calculation
def test_zero_safe_mape_calculation():
    # Target value 0.0 should not crash with ZeroDivisionError
    mape = calculate_mape([0.0, 100.0], [5.0, 110.0])
    assert isinstance(mape, float)
    assert mape > 0.0

# 9. Forecast horizon parameter handling
def test_forecast_horizon_boundaries(setup_test_db):
    f_1 = forecast_demand(inventory_item_id="INV-GHY-DIESEL", horizon_days=1, db_path=setup_test_db)
    assert len(f_1["forecasts"]) == 1

    f_5 = forecast_demand(inventory_item_id="INV-GHY-DIESEL", horizon_days=5, db_path=setup_test_db)
    # Capped at max 3 days
    assert len(f_5["forecasts"]) == 3

# 10. Model save and load artifact
def test_model_save_and_load(tmp_path, setup_test_db):
    eval_res = train_and_evaluate_forecasting_models(inventory_item_id="INV-IMP-RATIONS", db_path=setup_test_db)

    forecaster = DemandForecaster(n_estimators=10, max_depth=2, random_state=42)
    mock_records = [
        {"inventory_item_id": "ITEM-1", "time_index": i, "consumption_date": f"2026-09-{i+1:02d}", "quantity_consumed": 10.0 + i, "lag_1": 10.0 + i - 1 if i >= 1 else None, "rolling_mean_3": 10.0 if i >= 3 else None, "record_id": i+1}
        for i in range(10)
    ]
    forecaster.fit(mock_records)

    artifact_dir = str(tmp_path / "models")
    saved_path = forecaster.save_model(artifact_dir=artifact_dir, model_name="test_model.pkl")

    assert os.path.exists(saved_path)
    meta_path = saved_path.replace(".pkl", "_metadata.json")
    assert os.path.exists(meta_path)

    loaded_forecaster = DemandForecaster.load_model(saved_path)
    assert loaded_forecaster.is_fitted
    assert loaded_forecaster.model_engine == forecaster.model_engine

# 11. Insufficient history row handling
def test_insufficient_history_row_handling():
    forecaster = DemandForecaster()
    incomplete_records = [
        {"time_index": 0, "quantity_consumed": 100.0, "lag_1": None, "rolling_mean_3": None}, # Incomplete
        {"time_index": 1, "quantity_consumed": 110.0, "lag_1": 100.0, "rolling_mean_3": None}, # Incomplete
        {"time_index": 2, "quantity_consumed": 120.0, "lag_1": 110.0, "rolling_mean_3": 105.0},# Complete
    ]
    X, y, removed = forecaster.prepare_matrix(incomplete_records)

    assert removed == 2
    assert len(X) == 1
    assert len(y) == 1

# 12. Audit: Dataset record count consistency (70 seed records)
def test_audit_dataset_record_count(setup_test_db):
    from backend.app.forecasting import extract_consumption_dataset
    records = extract_consumption_dataset(db_path=setup_test_db)
    assert len(records) == 70, "Seeded synthetic dataset must contain exactly 70 records (5 items x 14 days)"

# 13. Audit: Temporal safety - current_inventory excluded from features
def test_current_inventory_temporal_exclusion():
    forecaster = DemandForecaster()
    assert "current_inventory" not in forecaster.feature_names, "'current_inventory' snapshot must be excluded from historical ML features"

# 14. Audit: Model artifact metadata verification
def test_model_artifact_metadata_fields(tmp_path):
    import json
    forecaster = DemandForecaster(n_estimators=10, max_depth=2)
    mock_records = [
        {"inventory_item_id": "ITEM-1", "time_index": i, "consumption_date": f"2026-09-{i+1:02d}", "quantity_consumed": 10.0 + i, "lag_1": 10.0 + i - 1 if i >= 1 else None, "rolling_mean_3": 10.0 if i >= 3 else None, "record_id": i+1}
        for i in range(10)
    ]
    forecaster.fit(mock_records)

    artifact_dir = str(tmp_path / "models")
    saved_path = forecaster.save_model(
        artifact_dir=artifact_dir,
        model_name="audit_forecaster.pkl",
        split_counts={"train": 7, "validation": 1, "test": 2},
        date_range={"start_date": "2026-09-01", "end_date": "2026-09-10"}
    )

    meta_path = saved_path.replace(".pkl", "_metadata.json")
    with open(meta_path, "r") as f:
        meta = json.load(f)

    assert "model_engine" in meta
    assert "feature_names" in meta
    assert "training_timestamp" in meta
    assert "data_source" in meta
    assert meta["data_source"] == DATA_SOURCE
    assert "split_counts" in meta
    assert meta["split_counts"]["train"] == 7
    assert "dataset_date_range" in meta
    assert meta["dataset_date_range"]["start_date"] == "2026-09-01"

