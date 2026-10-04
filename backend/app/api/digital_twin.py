"""
SENTINEL LOGIX AI - Digital Twin API Router
Exposes POST /api/digital-twin/simulate and GET /api/digital-twin/scenarios for in-memory what-if simulations.
"""

from fastapi import APIRouter, Body
from typing import List, Dict, Any
from ..digital_twin.schemas import DigitalTwinScenarioRequest, DigitalTwinSimulationResult
from ..digital_twin.service import DigitalTwinService

router = APIRouter(prefix="/api/digital-twin", tags=["Digital Twin Scenario Engine"])

@router.post("/simulate", response_model=DigitalTwinSimulationResult)
async def simulate_scenario(
    req: DigitalTwinScenarioRequest = Body(..., description="Scenario request parameters")
):
    """
    Executes a safe, in-memory what-if simulation for a hypothetical logistics disruption scenario.
    Does NOT mutate actual operational data in the database.
    """
    return DigitalTwinService.simulate_scenario(req)

@router.get("/scenarios", response_model=List[Dict[str, Any]])
async def list_scenarios():
    """
    Returns a list of registered demo scenario templates and recent what-if definitions.
    """
    return DigitalTwinService.get_available_scenarios()
