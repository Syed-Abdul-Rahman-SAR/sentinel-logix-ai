from fastapi import APIRouter, Query, Path
from typing import List, Optional
from ..schemas.depot import DepotCreate, DepotUpdate, DepotOut
from ..services.depot_service import DepotService

router = APIRouter(prefix="/api/depots", tags=["Depots"])

@router.get("", response_model=List[DepotOut])
async def list_depots(
    base_id: Optional[str] = Query(None, description="Filter by parent Base ID"),
    depot_type: Optional[str] = Query(None, description="Filter by depot type (FUEL, FOOD, MEDICAL, AMMUNITION, GENERAL_SUPPLY)")
):
    return DepotService.list_depots(base_id=base_id, depot_type=depot_type)

@router.get("/{depot_id}", response_model=DepotOut)
async def get_depot(depot_id: str = Path(..., description="Depot ID")):
    return DepotService.get_depot(depot_id)

@router.post("", response_model=DepotOut, status_code=201)
async def create_depot(req: DepotCreate):
    return DepotService.create_depot(req)

@router.put("/{depot_id}", response_model=DepotOut)
async def update_depot(depot_id: str, req: DepotUpdate):
    return DepotService.update_depot(depot_id, req)
