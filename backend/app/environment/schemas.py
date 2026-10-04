"""
SENTINEL LOGIX AI - Environment Intelligence Schemas
Phase 10A: Weather & Terrain Intelligence Foundation

Pydantic data models for:
  - WeatherConditions       (per-route synthetic weather snapshot)
  - TerrainCharacteristics  (per-route static terrain descriptor)
  - WeatherContributingFactor (explainability entry)
  - EnvironmentalRiskAssessment (combined risk output)

All records carry:
  data_source = "synthetic_demo"
  environment = "demo"

This schema is intentionally separate from the operational risk schema
(backend/app/risk/schemas.py) to keep the two intelligence dimensions independent.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class WeatherConditions(BaseModel):
    """
    Synthetic weather snapshot for a logistics route segment.
    All numeric values carry explicit SI/metric units.
    """
    route_id: str = Field(..., description="Logistics route / corridor identifier")
    route_name: str = Field(..., description="Human-readable route label")

    # ── Atmospheric conditions ──────────────────────────────────────────────
    temperature_celsius: float = Field(..., description="Air temperature in degrees Celsius")
    rainfall_mm: float = Field(..., ge=0.0, description="Rainfall intensity in mm/hr")
    visibility_km: float = Field(..., ge=0.0, description="Horizontal visibility in kilometres")
    wind_speed_kmh: float = Field(..., ge=0.0, description="Wind speed in km/h")
    precipitation_type: str = Field(..., description="NONE | RAIN | HEAVY_RAIN | SNOW | BLIZZARD | DRIZZLE | FOG")
    weather_condition: str = Field(..., description="Human-readable overall condition label")

    # ── Provenance ──────────────────────────────────────────────────────────
    data_source: str = Field("synthetic_demo", description="Always 'synthetic_demo' for this layer")
    environment: str = Field("demo", description="Always 'demo' for this layer")


class TerrainCharacteristics(BaseModel):
    """
    Static terrain descriptor for a logistics route segment.
    Derived from existing synthetic corridor data; does not claim real-world accuracy.
    """
    route_id: str = Field(..., description="Logistics route / corridor identifier")
    route_name: str = Field(..., description="Human-readable route label")

    # ── Terrain profile ─────────────────────────────────────────────────────
    terrain_type: str = Field(
        ...,
        description="Dominant terrain: PLAINS | HILLY | MOUNTAINOUS | FLOOD_PRONE | LANDSLIDE_PRONE"
    )
    terrain_risk_level: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    elevation_factor: float = Field(
        ..., ge=0.0, le=1.0,
        description="Normalised elevation risk factor (0.0=flat, 1.0=extreme altitude)"
    )
    slope_factor: float = Field(
        ..., ge=0.0, le=1.0,
        description="Normalised slope/gradient risk factor (0.0=level, 1.0=severe grade)"
    )
    road_condition: str = Field(
        ...,
        description="Current baseline road-surface condition: EXCELLENT | GOOD | FAIR | POOR | CRITICAL"
    )
    distance_km: float = Field(..., ge=0.0, description="Approximate route distance in kilometres")
    max_elevation_gain_m: float = Field(..., description="Maximum elevation gain in metres on this segment")

    # ── Hazard flags ────────────────────────────────────────────────────────
    flood_prone: bool = Field(False, description="True if route passes through flood-prone terrain")
    landslide_prone: bool = Field(False, description="True if route is known for landslide exposure")

    # ── Provenance ──────────────────────────────────────────────────────────
    data_source: str = Field("synthetic_demo")
    environment: str = Field("demo")


class WeatherContributingFactor(BaseModel):
    """
    A single explainability entry for the environmental risk assessment.
    Each factor describes one observable condition and its risk implication.
    """
    factor: str = Field(..., description="Short factor label, e.g. 'heavy_rainfall'")
    source: str = Field(..., description="'weather' or 'terrain'")
    severity: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    score_contribution: float = Field(..., ge=0.0, description="Points this factor contributes to the total")
    description: str = Field(..., description="What was observed")
    impact: str = Field(..., description="What operational implication this factor creates")


class EnvironmentalRiskAssessment(BaseModel):
    """
    Full environmental risk assessment output for a single logistics route.

    Score formula (documented in assessment.py):
        weather_risk_score   ∈ [0, 50]  — derived from 4 weather sub-signals
        terrain_risk_score   ∈ [0, 50]  — derived from 4 terrain sub-signals
        environmental_risk_score = weather_risk_score + terrain_risk_score  ∈ [0, 100]

    Classification thresholds:
        CRITICAL  ≥ 75
        HIGH      ≥ 50
        MEDIUM    ≥ 25
        LOW       <  25
    """
    # ── Route metadata ───────────────────────────────────────────────────────
    route_id: str
    route_name: str

    # ── Weather snapshot ─────────────────────────────────────────────────────
    weather: WeatherConditions

    # ── Terrain snapshot ─────────────────────────────────────────────────────
    terrain: TerrainCharacteristics

    # ── Scored dimensions ────────────────────────────────────────────────────
    weather_risk_score: float = Field(..., ge=0.0, le=50.0)
    terrain_risk_score: float = Field(..., ge=0.0, le=50.0)
    environmental_risk_score: float = Field(..., ge=0.0, le=100.0)
    classification: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")

    # ── Explainability ───────────────────────────────────────────────────────
    contributing_factors: List[WeatherContributingFactor]
    explanation: str = Field(..., description="Concise human-readable summary")

    # ── Provenance ───────────────────────────────────────────────────────────
    data_source: str = Field("synthetic_demo")
    environment: str = Field("demo")
    generated_at: str
