"""
SENTINEL LOGIX AI - Intelligence Dashboard Schemas
Pydantic models for aggregating operational, forecasting, risk, readiness,
supply movement, and Digital Twin intelligence into a unified command-center response.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class DashboardMetadata(BaseModel):
    data_source: str = "synthetic_demo"
    environment: str = "demo"
    generated_at: str

class OperationalOverview(BaseModel):
    total_bases: int
    total_depots: int
    total_inventory_items: int
    active_trips_count: int
    active_incidents_count: int

class InventoryItemSnapshot(BaseModel):
    id: str
    depot_id: str
    item_name: str
    category: str
    unit: str
    current_quantity: float
    minimum_threshold: float
    criticality: str

class InventoryIntelligence(BaseModel):
    total_tracked_inventory_quantity: float
    critical_inventory_items_count: int
    high_risk_inventory_items_count: int
    stockout_projected_count: int
    items_below_threshold_count: int
    items_summary: List[InventoryItemSnapshot] = Field(default_factory=list)

class RiskIntelligenceSummary(BaseModel):
    overall_risk_level: str
    risk_classification_counts: Dict[str, int]
    highest_risk_depot_id: Optional[str] = None
    highest_risk_depot_name: Optional[str] = None
    highest_risk_score: float

class ReadinessIntelligenceSummary(BaseModel):
    overall_readiness_status: str
    readiness_status_counts: Dict[str, int]
    lowest_readiness_depot_id: Optional[str] = None
    lowest_readiness_depot_name: Optional[str] = None
    lowest_readiness_score: float
    average_readiness_score: float

class HighPressureItem(BaseModel):
    item_id: str
    depot_id: str
    item_name: str
    days_until_stockout: Optional[int] = None
    days_until_threshold_breach: Optional[int] = None

class DemandIntelligenceSummary(BaseModel):
    forecast_horizon_days: int = 14
    forecast_model_status: str = "ACTIVE"
    high_pressure_items: List[HighPressureItem] = Field(default_factory=list)

class SupplyMovementSummary(BaseModel):
    total_shipments_count: int
    in_transit_shipments_count: int
    delayed_shipments_count: int
    total_delayed_quantity: float
    shipment_routes_count: int

class EnvironmentalRouteSummary(BaseModel):
    route_id: str
    route_name: str
    weather_risk_score: float
    terrain_risk_score: float
    environmental_risk_score: float
    classification: str
    dominant_dimension: str
    explanation: str

class EnvironmentalIntelligenceSummary(BaseModel):
    total_routes_assessed: int
    low_risk_routes: int
    medium_risk_routes: int
    high_risk_routes: int
    critical_risk_routes: int
    highest_risk_route: Optional[str] = None
    highest_risk_score: float = 0.0
    weather_dominant_routes: int = 0
    terrain_dominant_routes: int = 0
    routes: List[EnvironmentalRouteSummary] = Field(default_factory=list)
    data_source: str = "synthetic_demo"
    environment: str = "demo"

class DigitalTwinSummary(BaseModel):
    scenario_available: bool = False
    scenario_type: Optional[str] = None
    affected_depot_id: Optional[str] = None
    risk_delta: Optional[float] = None
    readiness_delta: Optional[float] = None
    human_summary: Optional[str] = None
    available_scenarios: List[Dict[str, Any]] = Field(default_factory=list)

class AdvisorSummary(BaseModel):
    status: str = "AVAILABLE"
    kb_articles_loaded: int = 10
    llm_provider_configured: bool = False
    mock_mode: bool = True

class DepotInventorySnapshot(BaseModel):
    total_items: int = 0
    total_quantity: float = 0.0
    critical_items_count: int = 0
    items_below_threshold_count: int = 0

class DepotStockoutSummary(BaseModel):
    projected_stockouts_count: int = 0
    high_pressure_items_count: int = 0
    high_pressure_items: List[Dict[str, Any]] = Field(default_factory=list)

class DepotOperationalRiskSummary(BaseModel):
    risk_score: float = 0.0
    risk_level: str = "LOW"
    top_contributing_factors: List[str] = Field(default_factory=list)

class DepotMissionReadinessSummary(BaseModel):
    readiness_score: float = 100.0
    readiness_status: str = "READY"
    key_issues: List[str] = Field(default_factory=list)

class DepotEnvironmentalExposure(BaseModel):
    route_id: Optional[str] = None
    environmental_risk_score: Optional[float] = None
    classification: Optional[str] = None
    dominant_dimension: Optional[str] = None
    explanation: Optional[str] = None
    status: str = "UNAVAILABLE"
    limitation: Optional[str] = None

class DepotSupplyMovementSummary(BaseModel):
    active_shipments_count: int = 0
    delayed_shipments_count: int = 0
    total_inbound_quantity: float = 0.0

class DepotUnifiedView(BaseModel):
    depot_id: str
    depot_name: str
    base_id: Optional[str] = None
    base_name: Optional[str] = None
    inventory_health: DepotInventorySnapshot
    stock_out_risk: DepotStockoutSummary
    operational_risk: DepotOperationalRiskSummary
    mission_readiness: DepotMissionReadinessSummary
    demand_pressure: Dict[str, Any] = Field(default_factory=dict)
    environmental_exposure: DepotEnvironmentalExposure
    relevant_supply_movement: DepotSupplyMovementSummary
    data_source: str = "synthetic_demo"
    environment: str = "demo"

class UnifiedSignal(BaseModel):
    signal_id: str
    source_module: str
    entity_type: str
    entity_id: str
    classification: str
    relevant_value: Any
    explanation: str

class IntelligenceModuleStatus(BaseModel):
    operational_data: str = "AVAILABLE"
    inventory: str = "AVAILABLE"
    forecasting: str = "AVAILABLE"
    risk_engine: str = "AVAILABLE"
    readiness_engine: str = "AVAILABLE"
    environmental_intelligence: str = "AVAILABLE"
    supply_movement: str = "AVAILABLE"
    digital_twin: str = "NO_ACTIVE_SCENARIO"
    advisor: str = "AVAILABLE"
    data_source: str = "synthetic_demo"
    environment: str = "demo"

class IntelligenceDashboardResponse(BaseModel):
    metadata: DashboardMetadata
    operational_overview: OperationalOverview
    inventory_intelligence: InventoryIntelligence
    risk_intelligence: RiskIntelligenceSummary
    readiness_intelligence: ReadinessIntelligenceSummary
    demand_intelligence: DemandIntelligenceSummary
    supply_movement: SupplyMovementSummary
    environmental_intelligence: EnvironmentalIntelligenceSummary
    digital_twin: DigitalTwinSummary
    advisor: AdvisorSummary = Field(default_factory=AdvisorSummary)
    depot_views: List[DepotUnifiedView] = Field(default_factory=list)
    critical_signals: List[UnifiedSignal] = Field(default_factory=list)
    intelligence_status: IntelligenceModuleStatus


