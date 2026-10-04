"""
SENTINEL LOGIX AI - Mission Readiness Service Layer
Orchestrates depots, parent bases, inventory items, stockout predictions, and risk assessments
to calculate explainable depot readiness assessments.
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from ..services.depot_service import DepotService
from ..services.base_service import BaseService
from ..services.inventory_service import InventoryService
from ..stockout.service import StockoutService
from ..risk.service import RiskService
from .assessment import assess_depot_readiness

class ReadinessService:
    @staticmethod
    def get_readiness_assessments(
        depot_id: Optional[str] = None,
        base_id: Optional[str] = None,
        readiness_status: Optional[str] = None,
        db_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves depots, parent bases, inventory items, stockout predictions, and risk assessments,
        and returns explainable Mission Readiness assessments.
        """
        if depot_id:
            single_depot = DepotService.get_depot(depot_id, db_path=db_path)
            if not single_depot:
                raise HTTPException(status_code=404, detail=f"Depot '{depot_id}' not found")
            depots = [single_depot]
        else:
            depots = DepotService.list_depots(base_id=base_id, db_path=db_path)

        bases_list = BaseService.list_bases(db_path=db_path)
        bases_map = {b["id"]: b for b in bases_list}

        results = []

        for depot in depots:
            curr_depot_id = depot["id"]
            curr_base_id = depot.get("base_id")
            base_rec = bases_map.get(curr_base_id)

            items = InventoryService.list_inventory(depot_id=curr_depot_id, db_path=db_path)
            stockout_preds = StockoutService.predict_stockout(depot_id=curr_depot_id, db_path=db_path)
            risk_assessments = RiskService.get_risk_assessments(depot_id=curr_depot_id, db_path=db_path)

            assessment = assess_depot_readiness(
                depot_record=depot,
                base_record=base_rec,
                inventory_items=items,
                stockout_predictions=stockout_preds,
                risk_assessments=risk_assessments
            )

            # Readiness status filter
            if readiness_status and assessment["readiness_status"].upper() != readiness_status.upper():
                continue

            results.append(assessment)

        return results

    @staticmethod
    def get_single_depot_readiness(depot_id: str, db_path: Optional[str] = None) -> Dict[str, Any]:
        """Returns readiness assessment for a specific depot, throwing HTTP 404 if not found."""
        results = ReadinessService.get_readiness_assessments(depot_id=depot_id, db_path=db_path)
        if not results:
            raise HTTPException(status_code=404, detail=f"Depot '{depot_id}' not found")
        return results[0]
