"""
Unit tests for SENTINEL LOGIX AI Stock-Out Prediction Engine & API.
Tests stock projections, threshold breach dates, stock-out zero dates, risk classification,
explainability narrative generation, and GET /api/stockout endpoint filtering.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db
from backend.app.db.seed import seed_database
from backend.app.stockout import (
    calculate_stockout_prediction,
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_MEDIUM,
    RISK_LOW,
)

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Fixture initializing isolated test SQLite database populated with seed data."""
    test_db_file = str(tmp_path / "test_sentinel_stockout.db")
    import backend.app.config as config
    config.DB_PATH = test_db_file
    init_db(test_db_file)
    seed_database(test_db_file)
    yield test_db_file

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# 1. Healthy inventory remains LOW risk
def test_healthy_inventory_risk_low(setup_test_db):
    mock_item = {
        "id": "ITEM-HEALTHY",
        "item_name": "Healthy Rations Pack",
        "depot_id": "DEPOT-1",
        "category": "FOOD",
        "unit": "BOXES",
        "current_quantity": 10000.0,
        "minimum_threshold": 1000.0,
        "maximum_capacity": 20000.0,
        "daily_consumption_rate": 50.0
    }
    pred = calculate_stockout_prediction(item_record=mock_item, horizon_days=7, db_path=setup_test_db)
    assert pred["risk_level"] == RISK_LOW
    assert pred["days_until_threshold_breach"] is None
    assert pred["expected_threshold_breach_date"] is None
    assert pred["days_until_stockout"] is None

# 2. Inventory already below threshold becomes CRITICAL risk
def test_inventory_already_below_threshold_critical(setup_test_db):
    mock_item = {
        "id": "ITEM-CRITICAL-NOW",
        "item_name": "Depleted Fuel Storage",
        "depot_id": "DEPOT-1",
        "category": "FUEL",
        "unit": "LITERS",
        "current_quantity": 500.0,
        "minimum_threshold": 2000.0,
        "maximum_capacity": 10000.0,
        "daily_consumption_rate": 100.0
    }
    pred = calculate_stockout_prediction(item_record=mock_item, horizon_days=7, db_path=setup_test_db)
    assert pred["risk_level"] == RISK_CRITICAL
    assert pred["days_until_threshold_breach"] == 0
    assert pred["expected_threshold_breach_date"] is not None

# 3. Inventory crossing threshold during forecast gets correct breach date
def test_threshold_breach_during_forecast(setup_test_db):
    mock_item = {
        "id": "ITEM-BREACH-SOON",
        "item_name": "Medical Kits",
        "depot_id": "DEPOT-1",
        "category": "MEDICAL",
        "unit": "BOXES",
        "current_quantity": 1200.0,
        "minimum_threshold": 1000.0,
        "maximum_capacity": 5000.0,
        "daily_consumption_rate": 100.0
    }
    pred = calculate_stockout_prediction(item_record=mock_item, horizon_days=7, db_path=setup_test_db)
    # Day 1: 1200 - 100 = 1100 > 1000. Day 2: 1100 - 100 = 1000 <= 1000 (breach at step 2!)
    assert pred["days_until_threshold_breach"] == 2
    assert pred["expected_threshold_breach_date"] is not None
    assert pred["risk_level"] == RISK_CRITICAL

# 4. Inventory reaching zero gets stock-out date
def test_stockout_zero_date_detection(setup_test_db):
    mock_item = {
        "id": "ITEM-DEPLETING",
        "item_name": "Aviation Fuel",
        "depot_id": "DEPOT-1",
        "category": "FUEL",
        "unit": "LITERS",
        "current_quantity": 300.0,
        "minimum_threshold": 500.0,
        "maximum_capacity": 5000.0,
        "daily_consumption_rate": 100.0
    }
    pred = calculate_stockout_prediction(item_record=mock_item, horizon_days=7, db_path=setup_test_db)
    assert pred["days_until_stockout"] is not None
    assert pred["days_until_stockout"] <= 3
    assert pred["expected_stockout_date"] is not None

# 5. Inventory not reaching zero returns null
def test_stock_not_reaching_zero_returns_null(setup_test_db):
    mock_item = {
        "id": "ITEM-STABLE",
        "item_name": "Stable Rations",
        "depot_id": "DEPOT-1",
        "category": "FOOD",
        "unit": "BOXES",
        "current_quantity": 5000.0,
        "minimum_threshold": 1000.0,
        "maximum_capacity": 10000.0,
        "daily_consumption_rate": 10.0
    }
    pred = calculate_stockout_prediction(item_record=mock_item, horizon_days=7, db_path=setup_test_db)
    assert pred["days_until_stockout"] is None
    assert pred["expected_stockout_date"] is None

# 6. Projected inventory clamped at 0.0 after stock-out
def test_projected_inventory_clamped_at_zero(setup_test_db):
    mock_item = {
        "id": "ITEM-EMPTY-FAST",
        "item_name": "Fast Depleting Item",
        "depot_id": "DEPOT-1",
        "category": "GENERAL",
        "unit": "UNITS",
        "current_quantity": 50.0,
        "minimum_threshold": 200.0,
        "maximum_capacity": 1000.0,
        "daily_consumption_rate": 100.0
    }
    pred = calculate_stockout_prediction(item_record=mock_item, horizon_days=7, db_path=setup_test_db)
    for point in pred["projected_inventory"]:
        assert point["projected_quantity"] >= 0.0, "Projected inventory must never drop below 0.0"

# 7. Risk classification rules test
def test_risk_classification_rules(setup_test_db):
    # High risk item (breach in day 4)
    item_high = {
        "id": "ITEM-HIGH-RISK",
        "item_name": "High Risk Item",
        "depot_id": "DEPOT-1",
        "category": "GENERAL",
        "unit": "UNITS",
        "current_quantity": 1400.0,
        "minimum_threshold": 1000.0,
        "maximum_capacity": 5000.0,
        "daily_consumption_rate": 100.0
    }
    pred_high = calculate_stockout_prediction(item_record=item_high, horizon_days=7, db_path=setup_test_db)
    assert pred_high["risk_level"] in (RISK_HIGH, RISK_CRITICAL)

# 8. Explanation contains calculated values
def test_explanation_contains_calculated_values(setup_test_db):
    mock_item = {
        "id": "ITEM-EXPLAIN",
        "item_name": "Explainable Item",
        "depot_id": "DEPOT-1",
        "category": "FOOD",
        "unit": "KG",
        "current_quantity": 2800.0,
        "minimum_threshold": 3000.0,
        "maximum_capacity": 10000.0,
        "daily_consumption_rate": 500.0
    }
    pred = calculate_stockout_prediction(item_record=mock_item, horizon_days=7, db_path=setup_test_db)
    exp = pred["explanation"]
    assert "Explainable Item" in exp
    assert "2,800.0 KG" in exp
    assert "3,000.0 KG" in exp
    assert "CRITICAL" in exp

# 9. API filtering on GET /api/stockout
def test_stockout_api_endpoint(client):
    # GET all stockout predictions
    resp = client.get("/api/stockout")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5  # 5 seeded items

    for p in data:
        assert "inventory_item_id" in p
        assert "current_quantity" in p
        assert "minimum_threshold" in p
        assert "forecast_horizon_days" in p
        assert p["forecast_horizon_days"] == 7
        assert "risk_level" in p
        assert "explanation" in p
        assert p["data_source"] == "synthetic_demo"

    # Filter by inventory_item_id
    resp_item = client.get("/api/stockout?inventory_item_id=INV-IMP-RATIONS")
    assert resp_item.status_code == 200
    data_item = resp_item.json()
    assert len(data_item) == 1
    assert data_item[0]["inventory_item_id"] == "INV-IMP-RATIONS"

    # Filter by risk_level
    resp_risk = client.get("/api/stockout?risk_level=CRITICAL")
    assert resp_risk.status_code == 200
    for p in resp_risk.json():
        assert p["risk_level"] == "CRITICAL"

# 10. Test null/None inventory field safety
def test_stockout_prediction_with_none_inventory_fields(setup_test_db):
    mock_item_with_nones = {
        "id": "ITEM-WITH-NULLS",
        "item_name": "Null Fields Item",
        "depot_id": "DEPOT-1",
        "category": "GENERAL",
        "unit": "UNITS",
        "current_quantity": None,
        "minimum_threshold": None,
        "maximum_capacity": None,
        "daily_consumption_rate": None
    }
    pred = calculate_stockout_prediction(item_record=mock_item_with_nones, horizon_days=7, db_path=setup_test_db)
    assert pred["current_quantity"] == 0.0
    assert pred["minimum_threshold"] == 0.0
    assert pred["risk_level"] is not None
    assert isinstance(pred["explanation"], str)

# 11. Test already breached threshold date semantics
def test_already_breached_date_semantics(setup_test_db):
    mock_item = {
        "id": "ITEM-ALREADY-BREACHED",
        "item_name": "Breached Item",
        "depot_id": "DEPOT-1",
        "category": "FUEL",
        "unit": "LITERS",
        "current_quantity": 100.0,
        "minimum_threshold": 500.0,
        "maximum_capacity": 5000.0,
        "daily_consumption_rate": 50.0
    }
    pred = calculate_stockout_prediction(item_record=mock_item, horizon_days=7, db_path=setup_test_db)
    assert pred["days_until_threshold_breach"] == 0, "Already breached threshold must have days_until_threshold_breach equal to 0"
    assert pred["expected_threshold_breach_date"] is not None
    assert "already breached" in pred["explanation"]

