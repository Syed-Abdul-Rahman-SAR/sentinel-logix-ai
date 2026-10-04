"""
SENTINEL LOGIX AI - Environment Intelligence Service Layer
Phase 10A: Weather & Terrain Intelligence Foundation

Clean service abstraction over the synthetic data store and assessment engine.
All other application modules that need environmental intelligence should call
EnvironmentService — they must not reach directly into data.py or assessment.py.

This abstraction ensures that if a real weather/terrain data provider is integrated
in a future phase, only this service layer needs to change.
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from .data import (
    get_weather_for_route,
    get_terrain_for_route,
    KNOWN_ROUTE_IDS,
)
from .assessment import assess_environmental_risk


class EnvironmentService:
    """
    Service interface for Weather & Terrain Intelligence.
    All methods are deterministic and do not access the operational database.
    """

    @staticmethod
    def get_weather(route_id: str) -> Dict[str, Any]:
        """
        Returns the synthetic weather snapshot for the given route.
        Raises HTTP 404 if the route is not in the synthetic dataset.
        """
        weather = get_weather_for_route(route_id)
        if weather is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No synthetic weather data found for route '{route_id}'. "
                    f"Known routes: {KNOWN_ROUTE_IDS}"
                )
            )
        return weather

    @staticmethod
    def get_terrain(route_id: str) -> Dict[str, Any]:
        """
        Returns the synthetic terrain characteristics for the given route.
        Raises HTTP 404 if the route is not in the synthetic dataset.
        """
        terrain = get_terrain_for_route(route_id)
        if terrain is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No synthetic terrain data found for route '{route_id}'. "
                    f"Known routes: {KNOWN_ROUTE_IDS}"
                )
            )
        return terrain

    @staticmethod
    def get_environmental_risk(route_id: str) -> Dict[str, Any]:
        """
        Returns the full environmental risk assessment for a given route,
        combining weather and terrain intelligence into a single scored response.
        Raises HTTP 404 for unknown routes.
        """
        weather = get_weather_for_route(route_id)
        terrain = get_terrain_for_route(route_id)

        if weather is None or terrain is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No environmental data found for route '{route_id}'. "
                    f"Known routes: {KNOWN_ROUTE_IDS}"
                )
            )

        return assess_environmental_risk(weather, terrain)

    @staticmethod
    def list_environmental_risks() -> List[Dict[str, Any]]:
        """
        Returns environmental risk assessments for all known routes,
        sorted by environmental_risk_score descending (highest risk first).
        """
        results = []
        for route_id in KNOWN_ROUTE_IDS:
            weather = get_weather_for_route(route_id)
            terrain = get_terrain_for_route(route_id)
            if weather and terrain:
                results.append(assess_environmental_risk(weather, terrain))

        results.sort(key=lambda r: r["environmental_risk_score"], reverse=True)
        return results
