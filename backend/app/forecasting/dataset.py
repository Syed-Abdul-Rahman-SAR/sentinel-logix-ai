"""
SENTINEL LOGIX AI - Forecasting Dataset Preparation Pipeline
Handles chronological data extraction from SQLite DB, data cleaning, feature assembly,
and leakage-free chronological splitting.
"""

from typing import List, Dict, Any, Optional
from ..db.database import get_db
from .validation import validate_time_series_data, generate_quality_report
from .features import engineer_features

DATA_SOURCE = "synthetic_demo"

def extract_consumption_dataset(
    inventory_item_id: Optional[str] = None,
    depot_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Extracts consumption history records joined with inventory item and depot context.
    Results are strictly sorted in ascending chronological order (consumption_date ASC, c.id ASC).
    """
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        query = """
        SELECT 
            c.id AS record_id,
            c.depot_id,
            c.inventory_item_id,
            c.quantity_consumed,
            c.consumption_date,
            c.operational_intensity,
            i.item_name,
            i.category,
            i.unit,
            i.current_quantity,
            i.minimum_threshold,
            i.maximum_capacity,
            i.daily_consumption_rate,
            i.criticality AS inventory_criticality,
            d.name AS depot_name,
            d.base_id
        FROM consumption_history c
        JOIN inventory_items i ON c.inventory_item_id = i.id
        JOIN depots d ON c.depot_id = d.id
        WHERE 1=1
        """
        params = []

        if inventory_item_id:
            query += " AND c.inventory_item_id = ?"
            params.append(inventory_item_id)
        if depot_id:
            query += " AND c.depot_id = ?"
            params.append(depot_id)
        if start_date:
            query += " AND c.consumption_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND c.consumption_date <= ?"
            params.append(end_date)

        # STRICT CHRONOLOGICAL ORDERING
        query += " ORDER BY c.consumption_date ASC, c.id ASC"

        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

def chronological_split(
    records: List[Dict[str, Any]],
    train_pct: float = 0.70,
    val_pct: float = 0.15,
    test_pct: float = 0.15
) -> Dict[str, Any]:
    """
    Splits a chronologically ordered time-series dataset into training, validation,
    and test sets strictly sequentially without shuffling, preventing temporal data leakage.
    
    Default split ratio: 70% Training, 15% Validation, 15% Testing.
    """
    n = len(records)
    if n == 0:
        return {
            "total_records": 0,
            "train_count": 0,
            "val_count": 0,
            "test_count": 0,
            "train_data": [],
            "val_data": [],
            "test_data": []
        }

    # Normalize split percentages if needed
    total_pct = train_pct + val_pct + test_pct
    if total_pct <= 0:
        train_pct, val_pct, test_pct = 0.70, 0.15, 0.15
    else:
        train_pct /= total_pct
        val_pct /= total_pct

    train_end = int(n * train_pct)
    val_end = int(n * (train_pct + val_pct))

    # Guarantee at least 1 sample in training if n > 0
    if train_end == 0 and n > 0:
        train_end = 1

    train_data = records[:train_end]
    val_data = records[train_end:val_end]
    test_data = records[val_end:]

    def get_range(data_slice):
        if not data_slice:
            return None
        return {
            "start": data_slice[0].get("consumption_date"),
            "end": data_slice[-1].get("consumption_date")
        }

    return {
        "total_records": n,
        "split_ratio": {"train_pct": round(train_pct * 100, 1), "val_pct": round(val_pct * 100, 1), "test_pct": round(test_pct * 100, 1)},
        "train_count": len(train_data),
        "val_count": len(val_data),
        "test_count": len(test_data),
        "train_date_range": get_range(train_data),
        "val_date_range": get_range(val_data),
        "test_date_range": get_range(test_data),
        "train_data": train_data,
        "val_data": val_data,
        "test_data": test_data,
    }

def prepare_forecasting_dataset(
    inventory_item_id: Optional[str] = None,
    depot_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    End-to-end dataset preparation pipeline for forecasting models.
    
    Steps:
    1. Extract chronological consumption history & metadata
    2. Validate data quality & detect anomalies
    3. Generate detailed data quality report
    4. Engineer leakage-free time-series features (calendar, lags, rolling means)
    5. Perform chronological split (70% train / 15% val / 15% test)
    
    Returns structured dataset dictionary tagged with metadata data_source = 'synthetic_demo'.
    """
    raw_records = extract_consumption_dataset(
        inventory_item_id=inventory_item_id,
        depot_id=depot_id,
        start_date=start_date,
        end_date=end_date,
        db_path=db_path
    )

    validation_summary = validate_time_series_data(raw_records)
    quality_report = generate_quality_report(raw_records)
    feature_dataset = engineer_features(raw_records)
    splits = chronological_split(feature_dataset, train_pct=0.70, val_pct=0.15, test_pct=0.15)

    return {
        "data_source": DATA_SOURCE,
        "query_parameters": {
            "inventory_item_id": inventory_item_id,
            "depot_id": depot_id,
            "start_date": start_date,
            "end_date": end_date
        },
        "raw_records_count": len(raw_records),
        "validation_summary": validation_summary,
        "quality_report": quality_report,
        "feature_dataset": feature_dataset,
        "splits": splits
    }
