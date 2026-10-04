from fastapi import APIRouter, Query
from typing import List, Optional
from ..schemas.consumption import ConsumptionRecordCreate, ConsumptionRecordOut
from ..services.consumption_service import ConsumptionService

router = APIRouter(prefix="/api/consumption", tags=["Consumption History"])

@router.get("", response_model=List[ConsumptionRecordOut])
async def list_consumption_history(
    inventory_item_id: Optional[str] = Query(None, description="Filter by Inventory Item ID"),
    depot_id: Optional[str] = Query(None, description="Filter by Depot ID"),
    start_date: Optional[str] = Query(None, description="Filter start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter end date (YYYY-MM-DD)")
):
    return ConsumptionService.list_records(
        inventory_item_id=inventory_item_id,
        depot_id=depot_id,
        start_date=start_date,
        end_date=end_date
    )

@router.post("", response_model=ConsumptionRecordOut, status_code=201)
async def create_consumption_record(req: ConsumptionRecordCreate):
    return ConsumptionService.create_record(req)
