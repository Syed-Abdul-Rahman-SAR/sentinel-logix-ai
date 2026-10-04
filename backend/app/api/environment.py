"""
SENTINEL LOGIX AI - Environment Intelligence API Router
Phase 10A: Weather & Terrain Intelligence Foundation

Exposes read-only endpoints for synthetic weather/terrain intelligence.

Endpoints
─────────
  GET /api/environment/routes/risk
      Returns environmental risk assessments for all known routes,
      sorted highest risk first.

  GET /api/environment/routes/{route_id}/risk
      Returns the full environmental risk assessment for a specific route,
      including weather snapshot, terrain characteristics, sub-scores,
      classification, contributing factors, and human-readable explanation.

  GET /api/environment/routes/{route_id}/weather
      Returns the weather-only snapshot for a specific route.

  GET /api/environment/routes/{route_id}/terrain
      Returns the terrain-only characteristics for a specific route.

All responses carry data_source="synthetic_demo" and environment="demo".
HTTP 404 is returned for any unknown route identifier.
"""

from fastapi import APIRouter, Path
from typing import List

from ..environment.schemas import EnvironmentalRiskAssessment, WeatherConditions, TerrainCharacteristics
from ..environment.service import EnvironmentService

router = APIRouter(prefix="/api/environment", tags=["Environment Intelligence"])


@router.get(
    "/routes/risk",
    response_model=List[EnvironmentalRiskAssessment],
    summary="List environmental risk for all known routes"
)
async def list_route_environmental_risks():
    """
    Returns environmental risk assessments for all routes in the synthetic dataset,
    sorted by environmental_risk_score descending (highest risk first).

    All data is synthetic (data_source='synthetic_demo', environment='demo').
    """
    return EnvironmentService.list_environmental_risks()


@router.get(
    "/routes/{route_id}/risk",
    response_model=EnvironmentalRiskAssessment,
    summary="Environmental risk for a specific route"
)
async def get_route_environmental_risk(
    route_id: str = Path(..., description="Logistics route ID (e.g. TEZ-TWA, SIL-IMP, GHY-SHL)")
):
    """
    Returns the full environmental risk assessment for the specified route.

    The response includes:
    - weather snapshot (temperature, rainfall, visibility, wind, precipitation type)
    - terrain characteristics (type, elevation, slope, road condition, hazard flags)
    - weather_risk_score  ∈ [0, 50]
    - terrain_risk_score  ∈ [0, 50]
    - environmental_risk_score = sum of above ∈ [0, 100]
    - classification: LOW / MEDIUM / HIGH / CRITICAL
    - contributing_factors: structured explainability
    - explanation: concise human-readable narrative

    Returns HTTP 404 for unknown route IDs.
    All data is synthetic (data_source='synthetic_demo', environment='demo').
    """
    return EnvironmentService.get_environmental_risk(route_id)


@router.get(
    "/routes/{route_id}/weather",
    response_model=WeatherConditions,
    summary="Weather conditions for a specific route"
)
async def get_route_weather(
    route_id: str = Path(..., description="Logistics route ID (e.g. TEZ-TWA, SIL-IMP, GHY-SHL)")
):
    """
    Returns only the synthetic weather snapshot for the specified route.
    Returns HTTP 404 for unknown route IDs.
    All data is synthetic (data_source='synthetic_demo', environment='demo').
    """
    return EnvironmentService.get_weather(route_id)


@router.get(
    "/routes/{route_id}/terrain",
    response_model=TerrainCharacteristics,
    summary="Terrain characteristics for a specific route"
)
async def get_route_terrain(
    route_id: str = Path(..., description="Logistics route ID (e.g. TEZ-TWA, SIL-IMP, GHY-SHL)")
):
    """
    Returns only the synthetic terrain characteristics for the specified route.
    Returns HTTP 404 for unknown route IDs.
    All data is synthetic (data_source='synthetic_demo', environment='demo').
    """
    return EnvironmentService.get_terrain(route_id)
