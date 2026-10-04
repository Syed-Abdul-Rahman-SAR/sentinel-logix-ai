from fastapi import APIRouter, Query, Path
from typing import List, Optional
from ..schemas.base import BaseCreate, BaseUpdate, BaseOut
from ..services.base_service import BaseService

router = APIRouter(prefix="/api/bases", tags=["Bases"])

@router.get("", response_model=List[BaseOut])
async def list_bases(
    base_type: Optional[str] = Query(None, description="Filter by base type (FORWARD_BASE, MAIN_BASE, SUPPORT_BASE, LOGISTICS_HUB)"),
    status: Optional[str] = Query(None, description="Filter by status (OPERATIONAL, LIMITED, OFFLINE)")
):
    return BaseService.list_bases(base_type=base_type, status=status)

@router.get("/{base_id}", response_model=BaseOut)
async def get_base(base_id: str = Path(..., description="Base ID")):
    return BaseService.get_base(base_id)

@router.post("", response_model=BaseOut, status_code=201)
async def create_base(req: BaseCreate):
    return BaseService.create_base(req)

@router.put("/{base_id}", response_model=BaseOut)
async def update_base(base_id: str, req: BaseUpdate):
    return BaseService.update_base(base_id, req)
