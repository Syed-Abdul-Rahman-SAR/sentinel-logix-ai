"""
SENTINEL LOGIX AI - Digital Twin Service Layer
Orchestrates scenario validation, template catalog management, and execution of what-if simulations.
"""

from typing import List, Dict, Any, Optional
from .schemas import DigitalTwinScenarioRequest
from .scenario import validate_scenario_request, DEMO_SCENARIOS
from .simulation import run_digital_twin_simulation

class DigitalTwinService:
    @staticmethod
    def simulate_scenario(
        req: DigitalTwinScenarioRequest,
        db_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates request and executes safe in-memory Digital Twin what-if simulation.
        """
        validated_req = validate_scenario_request(req)
        return run_digital_twin_simulation(validated_req, db_path=db_path)

    @staticmethod
    def get_available_scenarios() -> List[Dict[str, Any]]:
        """
        Returns a catalog of registered demo scenario templates and recent what-if definitions.
        """
        return DEMO_SCENARIOS
