"""
SENTINEL LOGIX AI - Environment Intelligence Module
Phase 10A: Weather & Terrain Intelligence Foundation

Exports the environmental risk assessment engine, data access services,
and Pydantic schemas for the weather/terrain intelligence layer.

All data is synthetic demonstration data (data_source='synthetic_demo').
This module does NOT connect to any external weather API or live data provider.
"""

from .schemas import (
    WeatherConditions,
    TerrainCharacteristics,
    WeatherContributingFactor,
    EnvironmentalRiskAssessment,
)
from .data import SYNTHETIC_WEATHER_DATA, SYNTHETIC_TERRAIN_DATA, get_weather_for_route, get_terrain_for_route
from .assessment import assess_environmental_risk
from .service import EnvironmentService

__all__ = [
    "WeatherConditions",
    "TerrainCharacteristics",
    "WeatherContributingFactor",
    "EnvironmentalRiskAssessment",
    "SYNTHETIC_WEATHER_DATA",
    "SYNTHETIC_TERRAIN_DATA",
    "get_weather_for_route",
    "get_terrain_for_route",
    "assess_environmental_risk",
    "EnvironmentService",
]
