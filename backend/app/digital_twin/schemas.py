"""
SENTINEL LOGIX AI - Digital Twin Schemas
Pydantic data models for what-if scenario requests, daily inventory trajectory points,
impact metrics, and full Digital Twin simulation responses.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DigitalTwinScenarioRequest(BaseModel):
    scenario_id: Optional[str] = Field(None, description="Optional custom scenario identifier; generated if omitted.")
    scenario_type: str = Field(..., description="Scenario type e.g. ROUTE_DISRUPTION")
    affected_depot_id: str = Field(..., description="Target Depot ID affected by hypothetical scenario")
    affected_route_id: Optional[str] = Field(None, description="Optional affected route/corridor ID")
    disruption_duration_days: int = Field(..., gt=0, description="Duration of disruption in days (must be > 0)")
    additional_delay_days: int = Field(0, ge=0, description="Additional replenishment delay in days (must be >= 0)")
    severity: str = Field("HIGH", description="Severity: CRITICAL, HIGH, MEDIUM, LOW")
    description: Optional[str] = Field(None, description="Optional custom scenario description")

class DailyTrajectoryPoint(BaseModel):
    day: int
    date: str
    baseline_inventory: float
    simulated_inventory: float
    forecast_consumption: float
    simulated_arrival: float
    threshold: float

class ShipmentImpact(BaseModel):
    shipment_id: str
    cargo_item_id: str
    quantity: float
    origin_base_id: str
    destination_depot_id: str
    route_id: str
    expected_arrival_day: int
    simulated_arrival_day: int
    delay_days: int
    status: str
    data_source: str = "synthetic_demo"

class NumericComparisonMetric(BaseModel):
    baseline: float
    scenario: float
    delta: float

class StringComparisonMetric(BaseModel):
    baseline: str
    scenario: str
    changed: bool

class OptionalIntComparisonMetric(BaseModel):
    baseline: Optional[int] = None
    scenario: Optional[int] = None
    changed: bool

class BoolComparisonMetric(BaseModel):
    baseline: bool
    scenario: bool
    changed: bool

class ScenarioComparisonSummary(BaseModel):
    minimum_inventory: NumericComparisonMetric
    final_inventory: NumericComparisonMetric
    inventory_shortfall: NumericComparisonMetric
    stockout_occurrence: BoolComparisonMetric
    stockout_day: OptionalIntComparisonMetric
    threshold_breach_day: OptionalIntComparisonMetric
    risk_score: NumericComparisonMetric
    risk_classification: StringComparisonMetric
    readiness_score: NumericComparisonMetric
    readiness_status: StringComparisonMetric
    affected_shipment_count: NumericComparisonMetric
    total_delayed_shipment_quantity: NumericComparisonMetric
    max_shipment_delay_days: NumericComparisonMetric

class ContributingFactor(BaseModel):
    factor: str
    severity: str
    description: str
    impact: str

class EnvironmentalImpactOut(BaseModel):
    route_id: Optional[str] = None
    route_name: Optional[str] = None
    environmental_risk_score: float = 0.0
    classification: Optional[str] = None
    weather_risk_score: float = 0.0
    terrain_risk_score: float = 0.0
    dominant_dimension: Optional[str] = None
    movement_impact_factor: float = 1.0
    environmental_delay_days: int = 0
    explanation: Optional[str] = None
    status: str = "AVAILABLE"
    data_source: str = "synthetic_demo"
    environment: str = "demo"

class DigitalTwinSimulationResult(BaseModel):
    scenario_id: str
    scenario_type: str
    scenario_description: str
    affected_depot_id: str
    affected_depot_name: str
    base_id: Optional[str] = None
    base_name: Optional[str] = None
    
    baseline_risk_score: float
    baseline_risk_level: str
    baseline_readiness_score: float
    baseline_readiness_status: str
    
    simulated_risk_score: float
    simulated_risk_level: str
    simulated_readiness_score: float
    simulated_readiness_status: str
    
    risk_score_delta: float
    readiness_score_delta: float
    threshold_breach_day: Optional[int] = None
    stockout_day: Optional[int] = None
    minimum_simulated_inventory: float
    inventory_shortfall: float
    
    trajectory: List[DailyTrajectoryPoint]
    affected_shipments: List[ShipmentImpact] = Field(default_factory=list)
    contributing_impacts: List[str]
    explanation: str
    assumptions: List[str]
    
    # Phase 7C comparison & explainability additions
    comparison: Optional[ScenarioComparisonSummary] = None
    causal_chain: List[str] = Field(default_factory=list)
    contributing_factors: List[ContributingFactor] = Field(default_factory=list)
    human_summary: Optional[str] = None
    
    # Phase 10D environmental impact addition
    environmental_impact: Optional[EnvironmentalImpactOut] = None

    data_source: str = "synthetic_demo"
    generated_at: str

