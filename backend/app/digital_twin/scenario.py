"""
SENTINEL LOGIX AI - Digital Twin Scenario Management
Validates scenario definitions, maintains scenario templates, and generates scenario metadata.
"""

import uuid
from typing import Dict, Any, List
from fastapi import HTTPException
from .schemas import DigitalTwinScenarioRequest

SUPPORTED_SCENARIO_TYPES = ["ROUTE_DISRUPTION"]
VALID_SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

DEMO_SCENARIOS = [
    {
        "scenario_id": "DEMO-ROUTE-DISRUPTION-01",
        "scenario_type": "ROUTE_DISRUPTION",
        "affected_depot_id": "DEPOT-IMP-SUP",
        "affected_route_id": "SIL-IMP",
        "disruption_duration_days": 3,
        "additional_delay_days": 2,
        "severity": "HIGH",
        "description": "High severity mudslide disrupting NH-37 transit corridor into Imphal Depot."
    },
    {
        "scenario_id": "DEMO-ROUTE-DISRUPTION-02",
        "scenario_type": "ROUTE_DISRUPTION",
        "affected_depot_id": "DEPOT-TWA-AMM",
        "affected_route_id": "TEZ-TWA",
        "disruption_duration_days": 5,
        "additional_delay_days": 3,
        "severity": "CRITICAL",
        "description": "Extreme weather blizzard blocking Sela Pass transit route into Tawang Munitions Depot."
    }
]

def validate_scenario_request(req: DigitalTwinScenarioRequest) -> DigitalTwinScenarioRequest:
    """
    Validates scenario request parameters cleanly. Throws HTTPException 400/422 if invalid.
    """
    st_upper = req.scenario_type.upper()
    if st_upper not in SUPPORTED_SCENARIO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported scenario_type '{req.scenario_type}'. Supported types: {SUPPORTED_SCENARIO_TYPES}"
        )
    req.scenario_type = st_upper

    sev_upper = req.severity.upper()
    if sev_upper not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity '{req.severity}'. Valid severities: {VALID_SEVERITIES}"
        )
    req.severity = sev_upper

    if req.disruption_duration_days <= 0:
        raise HTTPException(
            status_code=400,
            detail="disruption_duration_days must be strictly greater than 0"
        )

    if req.additional_delay_days < 0:
        raise HTTPException(
            status_code=400,
            detail="additional_delay_days must be greater than or equal to 0"
        )

    if not req.affected_depot_id or not req.affected_depot_id.strip():
        raise HTTPException(
            status_code=400,
            detail="affected_depot_id must be provided"
        )

    if not req.scenario_id:
        req.scenario_id = f"SCENARIO-{uuid.uuid4().hex[:8].upper()}"

    return req
