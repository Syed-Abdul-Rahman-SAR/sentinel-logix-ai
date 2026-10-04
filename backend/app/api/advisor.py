"""
SENTINEL LOGIX AI - AI Advisor API Router
Phase 11A: AI Logistics Advisor Backend Foundation

Exposes POST /api/advisor/query — validates the request, builds context,
generates deterministic advisory response from existing SENTINEL intelligence,
and returns structured JSON.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from ..advisor.schemas import AdvisorRequest, AdvisorResponse
from ..advisor.service import AdvisorService
from ..services.depot_service import DepotService
from ..services.base_service import BaseService
from ..environment.data import KNOWN_ROUTE_IDS
from ..digital_twin.scenario import DEMO_SCENARIOS
import backend.app.config as config

router = APIRouter(prefix="/api/advisor", tags=["AI Advisor"])


@router.post(
    "/query",
    response_model=AdvisorResponse,
    summary="AI Logistics Advisor Query",
    description=(
        "Accepts a natural-language logistics query with optional scoping to a depot, base, or route. "
        "Returns a deterministic, explainable advisory recommendation grounded in existing SENTINEL "
        "intelligence service outputs (inventory, risk, readiness, stock-out, environmental, supply movement). "
        "No external AI or LLM is invoked. All data is synthetic demonstration data."
    )
)
def advisor_query(request: AdvisorRequest) -> AdvisorResponse:
    """
    Main advisory endpoint. Fails safely:
    - HTTP 400 for empty query.
    - HTTP 404 for unknown depot_id, base_id, or route_id.
    - HTTP 422 for schema validation errors (handled by FastAPI automatically).
    """
    db_path: Optional[str] = getattr(config, "DB_PATH", None)

    # --- Validate query is non-empty after stripping ---
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must be a non-empty string.")

    # --- Validate depot_id if provided ---
    if request.depot_id:
        depots = DepotService.list_depots(db_path=db_path)
        depot_ids = {d["id"] for d in depots}
        if request.depot_id not in depot_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Depot '{request.depot_id}' not found. Valid depot IDs: {sorted(depot_ids)}"
            )

    # --- Validate base_id if provided ---
    if request.base_id:
        bases = BaseService.list_bases(db_path=db_path)
        base_ids = {b["id"] for b in bases}
        if request.base_id not in base_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Base '{request.base_id}' not found. Valid base IDs: {sorted(base_ids)}"
            )

    # --- Validate route_id if provided ---
    if request.route_id:
        if request.route_id not in KNOWN_ROUTE_IDS:
            raise HTTPException(
                status_code=404,
                detail=f"Route '{request.route_id}' not found in synthetic dataset. "
                       f"Known route IDs: {sorted(KNOWN_ROUTE_IDS)}"
            )

    # --- Phase 11G: Validate scenario_id if provided ---
    if getattr(request, "scenario_id", None):
        valid_scenario_ids = {s["scenario_id"] for s in DEMO_SCENARIOS}
        if request.scenario_id not in valid_scenario_ids:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Scenario '{request.scenario_id}' not found in SENTINEL scenario registry. "
                    f"Valid scenario IDs: {sorted(valid_scenario_ids)}"
                )
            )

    # --- Dispatch to Advisor Service ---
    try:
        response = AdvisorService.query(request, db_path=db_path)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Advisor service encountered an unexpected error: {exc}"
        )

    return response
