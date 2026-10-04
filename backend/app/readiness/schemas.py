"""
SENTINEL LOGIX AI - Mission Readiness Schemas
Pydantic data models for explainable depot readiness assessments, component breakdowns,
supporting metrics, and API response structures.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ReadinessFactor(BaseModel):
    factor: str            # e.g. "inventory_readiness", "stockout_condition", "operational_risk", "demand_pressure"
    impact: str            # positive, negative, neutral
    severity: str          # CRITICAL, HIGH, MEDIUM, LOW, NONE
    score_contribution: float
    message: str

class ReadinessComponents(BaseModel):
    inventory_component: float       # Max 35.0
    stockout_component: float        # Max 30.0
    operational_risk_component: float # Max 20.0
    demand_pressure_component: float  # Max 15.0

class SupportingInfo(BaseModel):
    total_items_count: int
    critical_inventory_count: int
    below_threshold_count: int
    critical_stockout_count: int
    worst_stockout_risk: str
    max_risk_score: float
    max_risk_level: str

class ReadinessAssessmentOut(BaseModel):
    entity_id: str
    entity_type: str = "DEPOT"
    entity_name: str
    base_id: Optional[str] = None
    base_name: Optional[str] = None
    readiness_score: float = Field(..., ge=0.0, le=100.0, description="Bounded readiness score from 0.0 to 100.0")
    readiness_status: str   # READY, CAUTION, DEGRADED, CRITICAL
    components: ReadinessComponents
    supporting_info: SupportingInfo
    contributing_factors: List[ReadinessFactor]
    explanation: str
    data_source: str = "synthetic_demo"
    generated_at: str
