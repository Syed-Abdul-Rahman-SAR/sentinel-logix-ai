"""
SENTINEL LOGIX AI - Stock-Out Service Layer
Queries inventory items and executes Stock-Out prediction engine for single items or filtered lists.
"""

from typing import List, Dict, Any, Optional
from ..services.inventory_service import InventoryService
from .prediction import calculate_stockout_prediction

class StockoutService:
    @staticmethod
    def predict_stockout(
        inventory_item_id: Optional[str] = None,
        depot_id: Optional[str] = None,
        risk_level: Optional[str] = None,
        horizon_days: int = 7,
        db_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves inventory items and computes 7-day Stock-Out predictions for each item.
        Supports filtering by inventory_item_id, depot_id, and risk_level.
        """
        if inventory_item_id:
            item = InventoryService.get_inventory_item(inventory_item_id, db_path=db_path)
            items = [item] if item else []
        else:
            items = InventoryService.list_inventory(depot_id=depot_id, db_path=db_path)

        predictions = []
        for item in items:
            pred = calculate_stockout_prediction(item_record=item, horizon_days=horizon_days, db_path=db_path)
            
            # Risk level filter
            if risk_level and pred["risk_level"].upper() != risk_level.upper():
                continue

            predictions.append(pred)

        return predictions
