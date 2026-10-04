"""
SENTINEL LOGIX AI - Risk Intelligence Service Layer
Orchestrates inventory items, depots, stock-out predictions, active incidents,
and movement signals to produce risk assessments.
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from ..services.inventory_service import InventoryService
from ..services.depot_service import DepotService
from ..services.incident_service import IncidentService
from ..services.trip_service import TripService
from ..stockout.service import StockoutService
from ..environment.service import EnvironmentService
from .assessment import assess_logistics_risk

DEPOT_ROUTE_MAPPING = {
    "DEPOT-GHY-FUEL": "GHY-TEZ",
    "DEPOT-GHY-FOOD": "GHY-TEZ",
    "DEPOT-SHL-MED": "GHY-SHL",
    "DEPOT-IMP-SUP": "SIL-IMP",
    "DEPOT-TWA-AMM": "TEZ-TWA",
}

BASE_ROUTE_MAPPING = {
    "BASE-GHY": "GHY-TEZ",
    "BASE-SHL": "GHY-SHL",
    "BASE-IMP": "SIL-IMP",
    "BASE-TWA": "TEZ-TWA",
}

def get_route_id_for_depot(depot_id: Optional[str], base_id: Optional[str] = None) -> Optional[str]:
    """Returns the deterministic synthetic logistics route ID for a depot or base, or None if unmapped."""
    if depot_id and depot_id in DEPOT_ROUTE_MAPPING:
        return DEPOT_ROUTE_MAPPING[depot_id]
    if base_id and base_id in BASE_ROUTE_MAPPING:
        return BASE_ROUTE_MAPPING[base_id]
    return None

class RiskService:
    @staticmethod
    def get_risk_assessments(
        inventory_item_id: Optional[str] = None,
        depot_id: Optional[str] = None,
        risk_level: Optional[str] = None,
        db_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves inventory items, joins depot metadata, gathers active incidents, active trips,
        and environmental intelligence, calls Stock-Out prediction, and returns transparent risk assessments.
        """
        if inventory_item_id:
            single_item = InventoryService.get_inventory_item(inventory_item_id, db_path=db_path)
            if not single_item:
                raise HTTPException(status_code=404, detail=f"Inventory item '{inventory_item_id}' not found")
            items = [single_item]
        else:
            items = InventoryService.list_inventory(depot_id=depot_id, db_path=db_path)

        depots_list = DepotService.list_depots(db_path=db_path)
        depots_map = {d["id"]: d for d in depots_list}

        active_incidents = IncidentService.list_incidents(is_active=True, db_path=db_path)
        active_trips = TripService.list_trips(status="ACTIVE", db_path=db_path)

        assessments = []

        for item in items:
            item_depot_id = item.get("depot_id")
            depot_rec = depots_map.get(item_depot_id, {"id": item_depot_id, "name": item_depot_id})
            base_id = depot_rec.get("base_id")

            # Route mapping & EnvironmentService call
            route_id = get_route_id_for_depot(item_depot_id, base_id)
            env_assessment = None
            if route_id:
                try:
                    env_assessment = EnvironmentService.get_environmental_risk(route_id)
                except Exception:
                    env_assessment = None

            # Re-use existing Stock-Out prediction
            so_preds = StockoutService.predict_stockout(inventory_item_id=item["id"], db_path=db_path)
            so_pred = so_preds[0] if so_preds else {}

            assessment = assess_logistics_risk(
                inventory_item=item,
                depot_record=depot_rec,
                stockout_prediction=so_pred,
                active_incidents=active_incidents,
                active_trips=active_trips,
                environmental_assessment=env_assessment
            )

            # Risk level filter
            if risk_level and assessment["risk_level"].upper() != risk_level.upper():
                continue

            assessments.append(assessment)

        return assessments


    @staticmethod
    def get_single_item_risk(inventory_item_id: str, db_path: Optional[str] = None) -> Dict[str, Any]:
        """Returns risk assessment for a specific inventory item, throwing HTTP 404 if not found."""
        results = RiskService.get_risk_assessments(inventory_item_id=inventory_item_id, db_path=db_path)
        if not results:
            raise HTTPException(status_code=404, detail=f"Inventory item '{inventory_item_id}' not found")
        return results[0]
