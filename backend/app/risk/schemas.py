"""
SENTINEL LOGIX AI - Risk Intelligence Schemas
Pydantic data models for explainable risk assessment, signal breakdowns, and API outputs.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ContributingFactor(BaseModel):
    signal: str            # e.g. "stockout_risk", "inventory_condition", "operational_incident", "movement_status"
    severity: str          # CRITICAL, HIGH, MEDIUM, LOW, NONE
    score_contribution: float
    message: str

class InventorySignal(BaseModel):
    status: str            # BELOW_THRESHOLD, NEAR_THRESHOLD, MODERATE_BUFFER, HEALTHY_BUFFER
    stock_ratio: float
    contribution: float

class IncidentSignal(BaseModel):
    active_incidents_count: int
    max_severity: Optional[str] = None
    contribution: float

class MovementSignal(BaseModel):
    active_trips_count: int
    disrupted_trips_count: int
    contribution: float

class EnvironmentalSignal(BaseModel):
    route_id: Optional[str] = None
    environmental_risk_score: float = 0.0
    classification: Optional[str] = None
    dominant_dimension: Optional[str] = None
    contribution: float = 0.0
    status: str = "AVAILABLE"

class RiskAssessmentOut(BaseModel):
    inventory_item_id: str
    inventory_item_name: str
    depot_id: str
    depot_name: str
    base_id: Optional[str] = None
    category: str
    unit: str
    current_quantity: float
    minimum_threshold: float
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Bounded risk score from 0.0 to 100.0")
    risk_level: str   # CRITICAL, HIGH, MEDIUM, LOW
    stockout_risk: str # CRITICAL, HIGH, MEDIUM, LOW
    inventory_signal: InventorySignal
    incident_signal: IncidentSignal
    movement_signal: MovementSignal
    environmental_signal: Optional[EnvironmentalSignal] = None
    contributing_factors: List[ContributingFactor]
    explanation: str
    data_source: str = "synthetic_demo"
    generated_at: str

