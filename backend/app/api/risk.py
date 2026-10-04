"""
SENTINEL LOGIX AI - Risk Intelligence API Router
Exposes GET /api/risk and GET /api/risk/{inventory_item_id} for explainable logistics risk assessments.
"""

from fastapi import APIRouter, Query, Path
from typing import List, Optional
from ..risk.schemas import RiskAssessmentOut
from ..risk.service import RiskService

router = APIRouter(prefix="/api/risk", tags=["Risk Intelligence"])

@router.get("", response_model=List[RiskAssessmentOut])
async def list_risk_assessments(
    inventory_item_id: Optional[str] = Query(None, description="Filter by inventory item ID"),
    depot_id: Optional[str] = Query(None, description="Filter by parent depot ID"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level (CRITICAL, HIGH, MEDIUM, LOW)")
):
    """
    Returns transparent logistics risk assessments combining stock-out predictions,
    inventory condition ratios, operational incident signals, and movement status.
    """
    return RiskService.get_risk_assessments(
        inventory_item_id=inventory_item_id,
        depot_id=depot_id,
        risk_level=risk_level
    )

@router.get("/{inventory_item_id}", response_model=RiskAssessmentOut)
async def get_single_risk_assessment(
    inventory_item_id: str = Path(..., description="Target Inventory Item ID")
):
    """
    Returns transparent logistics risk assessment for a specific inventory item.
    Returns HTTP 404 if the item is not found.
    """
    return RiskService.get_single_item_risk(inventory_item_id=inventory_item_id)
