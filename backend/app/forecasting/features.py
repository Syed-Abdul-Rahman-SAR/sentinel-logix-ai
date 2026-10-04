"""
SENTINEL LOGIX AI - Forecasting Feature Engineering
Generates leakage-free calendar, lag, rolling, and contextual features for demand forecasting models.
"""

from typing import List, Dict, Any
from datetime import datetime

def engineer_features(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Engineers time-series features for forecasting from chronologically sorted consumption records.
    
    Guarantees strict prevention of data leakage:
    - Lag features (lag_1, lag_2, lag_3, lag_7) use ONLY past observations (t-1, t-2, etc.).
    - Rolling mean features (rolling_mean_3, rolling_mean_7) use ONLY past observations (excluding current t).
    - Insufficient history yields explicit None values.
    """
    if not records:
        return []

    # Group records by inventory item to prevent cross-item contamination
    grouped_items: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        item_id = r.get("inventory_item_id", "UNKNOWN")
        if item_id not in grouped_items:
            grouped_items[item_id] = []
        grouped_items[item_id].append(r)

    engineered_records: List[Dict[str, Any]] = []

    for item_id, item_records in grouped_items.items():
        # Sort chronologically by consumption_date and record_id
        sorted_item_records = sorted(
            item_records,
            key=lambda x: (str(x.get("consumption_date", "")), int(x.get("record_id", 0) or 0))
        )

        n = len(sorted_item_records)

        for i in range(n):
            rec = sorted_item_records[i]
            c_date_str = str(rec.get("consumption_date", "")).split("T")[0]
            
            try:
                dt = datetime.strptime(c_date_str, "%Y-%m-%d")
                day_of_week = dt.weekday()     # 0 = Monday, 6 = Sunday
                day_of_month = dt.day         # 1 - 31
                month = dt.month              # 1 - 12
            except Exception:
                day_of_week = None
                day_of_month = None
                month = None

            time_index = i

            # Target variable (current day consumption)
            target_quantity = float(rec.get("quantity_consumed", 0.0))

            # ------------------------------------------------------------------
            # LAG FEATURES (Strictly previous time steps)
            # ------------------------------------------------------------------
            lag_1 = float(sorted_item_records[i - 1].get("quantity_consumed", 0.0)) if i >= 1 else None
            lag_2 = float(sorted_item_records[i - 2].get("quantity_consumed", 0.0)) if i >= 2 else None
            lag_3 = float(sorted_item_records[i - 3].get("quantity_consumed", 0.0)) if i >= 3 else None
            lag_7 = float(sorted_item_records[i - 7].get("quantity_consumed", 0.0)) if i >= 7 else None

            # ------------------------------------------------------------------
            # ROLLING MEAN FEATURES (Strictly previous time steps, excluding current i)
            # ------------------------------------------------------------------
            if i >= 3:
                vals_3 = [float(sorted_item_records[j].get("quantity_consumed", 0.0)) for j in range(i - 3, i)]
                rolling_mean_3 = round(sum(vals_3) / 3.0, 2)
            else:
                rolling_mean_3 = None

            if i >= 7:
                vals_7 = [float(sorted_item_records[j].get("quantity_consumed", 0.0)) for j in range(i - 7, i)]
                rolling_mean_7 = round(sum(vals_7) / 7.0, 2)
            else:
                rolling_mean_7 = None

            # Build enriched record preserving metadata & context
            feat_rec = {
                # Primary Keys & Metadata
                "record_id": rec.get("record_id"),
                "inventory_item_id": item_id,
                "depot_id": rec.get("depot_id"),
                "item_name": rec.get("item_name"),
                "category": rec.get("category"),
                "unit": rec.get("unit"),
                "consumption_date": c_date_str,

                # Target Variable
                "quantity_consumed": target_quantity,

                # Calendar & Time Index Features
                "time_index": time_index,
                "day_of_week": day_of_week,
                "day_of_month": day_of_month,
                "month": month,

                # Lag Features
                "lag_1": lag_1,
                "lag_2": lag_2,
                "lag_3": lag_3,
                "lag_7": lag_7,

                # Rolling Window Features
                "rolling_mean_3": rolling_mean_3,
                "rolling_mean_7": rolling_mean_7,

                # Operational Context Features
                "operational_intensity": rec.get("operational_intensity", "NORMAL"),
                "inventory_criticality": rec.get("inventory_criticality", "MEDIUM"),
                "current_inventory": float(rec.get("current_quantity", 0.0)) if rec.get("current_quantity") is not None else 0.0,
                "minimum_threshold": float(rec.get("minimum_threshold", 0.0)) if rec.get("minimum_threshold") is not None else 0.0,
                "maximum_capacity": float(rec.get("maximum_capacity", 0.0)) if rec.get("maximum_capacity") is not None else 0.0,
                "daily_consumption_rate": float(rec.get("daily_consumption_rate", 0.0)) if rec.get("daily_consumption_rate") is not None else 0.0,
            }

            engineered_records.append(feat_rec)

    # Sort final feature dataset chronologically by date and item_id
    engineered_records.sort(key=lambda x: (str(x.get("consumption_date", "")), str(x.get("inventory_item_id", ""))))
    return engineered_records
