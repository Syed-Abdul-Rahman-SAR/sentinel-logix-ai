from fastapi import APIRouter, Query, Path
from typing import List, Optional
from ..schemas.inventory import InventoryItemCreate, InventoryItemUpdate, InventoryItemOut
from ..services.inventory_service import InventoryService

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])

@router.get("", response_model=List[InventoryItemOut])
async def list_inventory(
    depot_id: Optional[str] = Query(None, description="Filter by parent Depot ID"),
    category: Optional[str] = Query(None, description="Filter by category (FUEL, FOOD, MEDICAL, GENERAL)"),
    criticality: Optional[str] = Query(None, description="Filter by criticality (LOW, MEDIUM, HIGH, CRITICAL)")
):
    return InventoryService.list_inventory(depot_id=depot_id, category=category, criticality=criticality)

@router.get("/{item_id}", response_model=InventoryItemOut)
async def get_inventory_item(item_id: str = Path(..., description="Inventory Item ID")):
    return InventoryService.get_inventory_item(item_id)

@router.post("", response_model=InventoryItemOut, status_code=201)
async def create_inventory_item(req: InventoryItemCreate):
    return InventoryService.create_inventory_item(req)

@router.put("/{item_id}", response_model=InventoryItemOut)
async def update_inventory_item(item_id: str, req: InventoryItemUpdate):
    return InventoryService.update_inventory_item(item_id, req)
