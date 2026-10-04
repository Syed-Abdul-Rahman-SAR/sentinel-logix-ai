"""
SENTINEL LOGIX AI - Time-Series Validation & Data Quality Report
Provides data quality metrics, anomaly detection, missing date identification, and validation reports.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta

DATA_SOURCE = "synthetic_demo"

def validate_time_series_data(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validates time-series consumption records for anomalies, duplicates, missing dates,
    and invalid consumption values.
    
    Returns a deterministic validation summary dictionary.
    """
    records_received = len(records)
    if records_received == 0:
        return {
            "data_source": DATA_SOURCE,
            "records_received": 0,
            "records_valid": 0,
            "duplicates": 0,
            "missing_dates": 0,
            "invalid_consumption": 0,
            "valid_percentage": 0.0,
            "issues": ["No consumption records provided"]
        }

    records_valid = 0
    duplicates = 0
    invalid_consumption = 0
    issues = []

    # Track item date coverage
    items_map: Dict[str, List[Dict[str, Any]]] = {}

    for idx, rec in enumerate(records):
        item_id = rec.get("inventory_item_id")
        depot_id = rec.get("depot_id")
        raw_date = rec.get("consumption_date")
        qty = rec.get("quantity_consumed")

        is_record_valid = True

        # 1. Relational Integrity
        if not item_id or not depot_id:
            issues.append(f"Record at index {idx} missing inventory_item_id or depot_id")
            is_record_valid = False

        # 2. Consumption Date Parsing
        parsed_date = None
        if raw_date:
            try:
                parsed_date = datetime.strptime(str(raw_date).split("T")[0], "%Y-%m-%d").date()
            except Exception:
                issues.append(f"Record at index {idx} has invalid consumption_date: '{raw_date}'")
                is_record_valid = False
        else:
            issues.append(f"Record at index {idx} has null or empty consumption_date")
            is_record_valid = False

        # 3. Non-positive / Non-numeric Consumption
        if qty is None or not isinstance(qty, (int, float)) or qty <= 0:
            invalid_consumption += 1
            issues.append(f"Record at index {idx} has invalid quantity_consumed: {qty}")
            is_record_valid = False

        if is_record_valid:
            records_valid += 1
            if item_id not in items_map:
                items_map[item_id] = []
            items_map[item_id].append({
                "record_id": rec.get("record_id"),
                "date": parsed_date,
                "date_str": str(parsed_date),
                "qty": qty,
                "intensity": rec.get("operational_intensity", "NORMAL")
            })

    # 4. Duplicate and Missing Dates Detection per Inventory Item
    missing_dates = 0
    for item_id, item_records in items_map.items():
        # Check duplicates
        dates_seen = set()
        for r in item_records:
            d_str = r["date_str"]
            if d_str in dates_seen:
                duplicates += 1
                issues.append(f"Duplicate consumption record for item '{item_id}' on date '{d_str}'")
            else:
                dates_seen.add(d_str)

        # Check chronological sequence and missing calendar days
        if item_records:
            unique_dates = sorted(list(set(r["date"] for r in item_records)))
            start_d = unique_dates[0]
            end_d = unique_dates[-1]

            cur_d = start_d
            while cur_d <= end_d:
                if cur_d not in unique_dates:
                    missing_dates += 1
                    issues.append(f"Missing date in sequence for item '{item_id}': '{cur_d}'")
                cur_d += timedelta(days=1)

    valid_percentage = round((records_valid / records_received) * 100.0, 2) if records_received > 0 else 0.0

    return {
        "data_source": DATA_SOURCE,
        "records_received": records_received,
        "records_valid": records_valid,
        "duplicates": duplicates,
        "missing_dates": missing_dates,
        "invalid_consumption": invalid_consumption,
        "valid_percentage": valid_percentage,
        "issues": issues
    }

def generate_quality_report(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates a detailed forecasting data quality report containing dataset-level
    and item-level consumption statistics.
    """
    if not records:
        return {
            "data_source": DATA_SOURCE,
            "total_records": 0,
            "inventory_items_count": 0,
            "depots_count": 0,
            "date_range": {"start_date": None, "end_date": None, "days_span": 0},
            "overall_stats": {"min_consumption": 0.0, "max_consumption": 0.0, "avg_consumption": 0.0},
            "item_level_reports": {}
        }

    val_res = validate_time_series_data(records)

    # Group by item
    item_groups: Dict[str, List[Dict[str, Any]]] = {}
    depot_ids = set()

    for rec in records:
        item_id = rec.get("inventory_item_id", "UNKNOWN")
        depot_id = rec.get("depot_id")
        if depot_id:
            depot_ids.add(depot_id)
        if item_id not in item_groups:
            item_groups[item_id] = []
        item_groups[item_id].append(rec)

    all_dates = sorted(list(set(r.get("consumption_date") for r in records if r.get("consumption_date"))))
    all_quantities = [float(r.get("quantity_consumed", 0)) for r in records if r.get("quantity_consumed") is not None]

    min_date = all_dates[0] if all_dates else None
    max_date = all_dates[-1] if all_dates else None
    days_span = 0
    if min_date and max_date:
        try:
            d1 = datetime.strptime(min_date, "%Y-%m-%d")
            d2 = datetime.strptime(max_date, "%Y-%m-%d")
            days_span = (d2 - d1).days + 1
        except Exception:
            days_span = len(all_dates)

    overall_min = round(min(all_quantities), 2) if all_quantities else 0.0
    overall_max = round(max(all_quantities), 2) if all_quantities else 0.0
    overall_avg = round(sum(all_quantities) / len(all_quantities), 2) if all_quantities else 0.0

    item_level_reports = {}
    for item_id, item_recs in item_groups.items():
        sample = item_recs[0]
        q_list = [float(r.get("quantity_consumed", 0)) for r in item_recs if r.get("quantity_consumed") is not None]
        dates_list = sorted(list(set(r.get("consumption_date") for r in item_recs if r.get("consumption_date"))))

        # Operational intensity breakdown
        intensity_counts = {"NORMAL": 0, "HIGH": 0, "CRITICAL": 0}
        for r in item_recs:
            op_int = str(r.get("operational_intensity", "NORMAL")).upper()
            intensity_counts[op_int] = intensity_counts.get(op_int, 0) + 1

        item_val = validate_time_series_data(item_recs)

        item_level_reports[item_id] = {
            "inventory_item_id": item_id,
            "item_name": sample.get("item_name", item_id),
            "category": sample.get("category", "N/A"),
            "unit": sample.get("unit", "N/A"),
            "records_count": len(item_recs),
            "date_range": {
                "start_date": dates_list[0] if dates_list else None,
                "end_date": dates_list[-1] if dates_list else None,
            },
            "min_consumption": round(min(q_list), 2) if q_list else 0.0,
            "max_consumption": round(max(q_list), 2) if q_list else 0.0,
            "avg_daily_consumption": round(sum(q_list) / len(q_list), 2) if q_list else 0.0,
            "missing_dates": item_val["missing_dates"],
            "duplicates": item_val["duplicates"],
            "invalid_consumption": item_val["invalid_consumption"],
            "operational_intensity_breakdown": intensity_counts
        }

    return {
        "data_source": DATA_SOURCE,
        "total_records": len(records),
        "inventory_items_count": len(item_groups),
        "depots_count": len(depot_ids),
        "date_range": {
            "start_date": min_date,
            "end_date": max_date,
            "days_span": days_span
        },
        "overall_stats": {
            "min_consumption": overall_min,
            "max_consumption": overall_max,
            "avg_consumption": overall_avg
        },
        "validation_summary": val_res,
        "item_level_reports": item_level_reports
    }
