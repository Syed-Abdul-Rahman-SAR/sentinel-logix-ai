"""
SENTINEL LOGIX AI - Intelligence Dashboard API Router
Exposes GET /api/intelligence/dashboard to serve unified command-center intelligence.
"""

from fastapi import APIRouter
from ..intelligence.schemas import IntelligenceDashboardResponse
from ..intelligence.service import IntelligenceService

router = APIRouter(prefix="/api/intelligence", tags=["Intelligence Dashboard"])

@router.get("/dashboard", response_model=IntelligenceDashboardResponse)
async def get_dashboard_intelligence():
    """
    Returns aggregated command-center intelligence combining operational state,
    inventory intelligence, risk assessment, mission readiness, demand forecasts,
    supply movement, and Digital Twin status.
    """
    return IntelligenceService.get_dashboard_intelligence()
