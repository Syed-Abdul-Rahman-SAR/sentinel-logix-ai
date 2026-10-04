"""
Unit tests for SENTINEL LOGIX AI Demand Forecasting Data Pipeline.
Validates extraction, sorting, cleaning, feature engineering, data leakage prevention,
chronological splitting, and data quality reporting.
"""

import pytest
from datetime import datetime, timedelta
from backend.app.db.database import get_db, init_db
from backend.app.db.seed import seed_database
from backend.app.forecasting import (
    DATA_SOURCE,
    extract_consumption_dataset,
    validate_time_series_data,
    generate_quality_report,
    engineer_features,
    chronological_split,
    prepare_forecasting_dataset,
)

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Fixture initializing isolated test SQLite database populated with seed data."""
    test_db_file = str(tmp_path / "test_sentinel_forecasting.db")
    init_db(test_db_file)
    seed_database(test_db_file)
    yield test_db_file

# 1. Correct chronological ordering
def test_chronological_ordering(setup_test_db):
    records = extract_consumption_dataset(db_path=setup_test_db)
    assert len(records) > 0

    dates = [r["consumption_date"] for r in records]
    assert dates == sorted(dates), "Records must be sorted chronologically ascending"

# 2. Correct filtering by inventory_item_id
def test_filter_by_inventory_item_id(setup_test_db):
    target_item = "INV-IMP-RATIONS"
    records = extract_consumption_dataset(inventory_item_id=target_item, db_path=setup_test_db)
    assert len(records) == 14
    for r in records:
        assert r["inventory_item_id"] == target_item

# 3. Correct filtering by depot_id
def test_filter_by_depot_id(setup_test_db):
    target_depot = "DEPOT-IMP-SUP"
    records = extract_consumption_dataset(depot_id=target_depot, db_path=setup_test_db)
    assert len(records) > 0
    for r in records:
        assert r["depot_id"] == target_depot

# 4. Duplicate-date detection
def test_duplicate_date_detection():
    mock_records = [
        {"inventory_item_id": "ITEM-1", "depot_id": "DEPOT-1", "consumption_date": "2026-09-01", "quantity_consumed": 100},
        {"inventory_item_id": "ITEM-1", "depot_id": "DEPOT-1", "consumption_date": "2026-09-01", "quantity_consumed": 105}, # Duplicate date
    ]
    val = validate_time_series_data(mock_records)
    assert val["duplicates"] == 1
    assert any("Duplicate" in issue for issue in val["issues"])

# 5. Invalid consumption detection
def test_invalid_consumption_detection():
    mock_records = [
        {"inventory_item_id": "ITEM-1", "depot_id": "DEPOT-1", "consumption_date": "2026-09-01", "quantity_consumed": 100},
        {"inventory_item_id": "ITEM-1", "depot_id": "DEPOT-1", "consumption_date": "2026-09-02", "quantity_consumed": -10}, # Negative
        {"inventory_item_id": "ITEM-1", "depot_id": "DEPOT-1", "consumption_date": "2026-09-03", "quantity_consumed": 0},   # Non-positive
        {"inventory_item_id": "ITEM-1", "depot_id": "DEPOT-1", "consumption_date": "2026-09-04", "quantity_consumed": None},# Null
    ]
    val = validate_time_series_data(mock_records)
    assert val["invalid_consumption"] == 3
    assert val["records_valid"] == 1

# 6. Lag feature generation
def test_lag_feature_generation():
    mock_records = [
        {"inventory_item_id": "ITEM-1", "depot_id": "DEPOT-1", "consumption_date": f"2026-09-0{i+1}", "quantity_consumed": (i + 1) * 10, "record_id": i+1}
        for i in range(8)
    ]
    features = engineer_features(mock_records)
    assert len(features) == 8

    # Day 1 (index 0, qty=10): all lags should be None
    assert features[0]["quantity_consumed"] == 10.0
    assert features[0]["lag_1"] is None
    assert features[0]["lag_2"] is None
    assert features[0]["lag_3"] is None
    assert features[0]["lag_7"] is None

    # Day 2 (index 1, qty=20): lag_1 = 10.0, lag_2 = None
    assert features[1]["quantity_consumed"] == 20.0
    assert features[1]["lag_1"] == 10.0
    assert features[1]["lag_2"] is None

    # Day 4 (index 3, qty=40): lag_1 = 30.0, lag_2 = 20.0, lag_3 = 10.0
    assert features[3]["lag_1"] == 30.0
    assert features[3]["lag_2"] == 20.0
    assert features[3]["lag_3"] == 10.0

    # Day 8 (index 7, qty=80): lag_7 = 10.0
    assert features[7]["lag_7"] == 10.0

# 7. Rolling feature generation
def test_rolling_feature_generation():
    mock_records = [
        {"inventory_item_id": "ITEM-1", "depot_id": "DEPOT-1", "consumption_date": f"2026-09-{i+1:02d}", "quantity_consumed": 10.0, "record_id": i+1}
        for i in range(8)
    ]
    features = engineer_features(mock_records)

    # Days 0, 1, 2 (fewer than 3 prior days): rolling_mean_3 is None
    assert features[0]["rolling_mean_3"] is None
    assert features[1]["rolling_mean_3"] is None
    assert features[2]["rolling_mean_3"] is None

    # Day 3 (index 3, prior 3 days are indices 0,1,2 with qty=10,10,10): rolling_mean_3 = 10.0
    assert features[3]["rolling_mean_3"] == 10.0

    # Days 0 to 6 (fewer than 7 prior days): rolling_mean_7 is None
    assert features[6]["rolling_mean_7"] is None

    # Day 7 (index 7, prior 7 days are indices 0..6 with qty=10 each): rolling_mean_7 = 10.0
    assert features[7]["rolling_mean_7"] == 10.0

# 8. No future leakage verification
def test_no_future_data_leakage():
    # Day 1: 10, Day 2: 20, Day 3: 30, Day 4: 1000 (huge spike in future!)
    mock_records = [
        {"inventory_item_id": "ITEM-1", "depot_id": "DEPOT-1", "consumption_date": "2026-09-01", "quantity_consumed": 10, "record_id": 1},
        {"inventory_item_id": "ITEM-1", "depot_id": "DEPOT-1", "consumption_date": "2026-09-02", "quantity_consumed": 20, "record_id": 2},
        {"inventory_item_id": "ITEM-1", "depot_id": "DEPOT-1", "consumption_date": "2026-09-03", "quantity_consumed": 30, "record_id": 3},
        {"inventory_item_id": "ITEM-1", "depot_id": "DEPOT-1", "consumption_date": "2026-09-04", "quantity_consumed": 1000, "record_id": 4},
    ]
    features = engineer_features(mock_records)

    # For Day 3 (index 2, target=30):
    # lag_1 MUST be 20 (Day 2)
    # lag_2 MUST be 10 (Day 1)
    # rolling_mean_3 MUST be None (only 2 prior days exist)
    # The future spike of 1000 MUST NOT appear in any feature of Day 1, 2, or 3!
    for f in features[:3]:
        assert f["quantity_consumed"] < 1000
        assert f["lag_1"] is None or f["lag_1"] < 1000
        assert f["lag_2"] is None or f["lag_2"] < 1000
        assert f["lag_3"] is None or f["lag_3"] < 1000

# 9. Chronological split verification
def test_chronological_split():
    mock_records = [
        {"consumption_date": f"2026-09-{i+1:02d}", "val": i}
        for i in range(20)
    ]
    splits = chronological_split(mock_records, train_pct=0.70, val_pct=0.15, test_pct=0.15)

    assert splits["total_records"] == 20
    assert splits["train_count"] == 14
    assert splits["val_count"] == 3
    assert splits["test_count"] == 3

    # Check date ordering across splits
    train_end_date = splits["train_data"][-1]["consumption_date"]
    val_start_date = splits["val_data"][0]["consumption_date"]
    val_end_date = splits["val_data"][-1]["consumption_date"]
    test_start_date = splits["test_data"][0]["consumption_date"]

    assert train_end_date < val_start_date, "Train dataset must precede validation dataset chronologically"
    assert val_end_date < test_start_date, "Validation dataset must precede test dataset chronologically"

# 10. Dataset quality report verification
def test_dataset_quality_report(setup_test_db):
    records = extract_consumption_dataset(db_path=setup_test_db)
    report = generate_quality_report(records)

    assert report["data_source"] == DATA_SOURCE
    assert report["total_records"] == 70
    assert report["inventory_items_count"] == 5
    assert report["depots_count"] == 5
    assert report["date_range"]["start_date"] == "2026-09-17"
    assert report["date_range"]["end_date"] == "2026-09-30"

    # Item-level breakdown assertions
    item_reports = report["item_level_reports"]
    assert "INV-IMP-RATIONS" in item_reports
    imp_rations = item_reports["INV-IMP-RATIONS"]
    assert imp_rations["records_count"] == 14
    assert imp_rations["avg_daily_consumption"] > 0
    assert imp_rations["missing_dates"] == 0
    assert imp_rations["duplicates"] == 0

# 11. End-to-end pipeline preparation
def test_prepare_forecasting_dataset_pipeline(setup_test_db):
    prep = prepare_forecasting_dataset(inventory_item_id="INV-IMP-RATIONS", db_path=setup_test_db)

    assert prep["data_source"] == DATA_SOURCE
    assert prep["raw_records_count"] == 14
    assert prep["validation_summary"]["records_valid"] == 14
    assert len(prep["feature_dataset"]) == 14
    assert prep["splits"]["train_count"] > 0
