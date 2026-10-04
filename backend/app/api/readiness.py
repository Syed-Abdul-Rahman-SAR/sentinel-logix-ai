"""
SENTINEL LOGIX AI - Mission Readiness API Router
Exposes GET /api/readiness and GET /api/readiness/{depot_id} for explainable mission readiness assessments.
"""

from fastapi import APIRouter, Query, Path
from typing import List, Optional
from ..readiness.schemas import ReadinessAssessmentOut
from ..readiness.service import ReadinessService

router = APIRouter(prefix="/api/readiness", tags=["Mission Readiness"])

@router.get("", response_model=List[ReadinessAssessmentOut])
async def list_readiness_assessments(
    depot_id: Optional[str] = Query(None, description="Filter by depot ID"),
    base_id: Optional[str] = Query(None, description="Filter by parent base ID"),
    readiness_status: Optional[str] = Query(None, description="Filter by status (READY, CAUTION, DEGRADED, CRITICAL)")
):
    """
    Returns transparent Mission Readiness assessments for depots/bases based on inventory health,
    stock-out predictions, operational risk assessments, and demand pressure.
    """
    return ReadinessService.get_readiness_assessments(
        depot_id=depot_id,
        base_id=base_id,
        readiness_status=readiness_status
    )

@router.get("/{depot_id}", response_model=ReadinessAssessmentOut)
async def get_single_readiness_assessment(
    depot_id: str = Path(..., description="Target Depot ID")
):
    """
    Returns transparent Mission Readiness assessment for a specific depot.
    Returns HTTP 404 if the depot is not found.
    """
    return ReadinessService.get_single_depot_readiness(depot_id=depot_id)
