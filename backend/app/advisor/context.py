"""
SENTINEL LOGIX AI - Advisor Context Builder
Phase 11A: AI Logistics Advisor Backend Foundation
Phase 11D: Knowledge Base retrieval integrated.

AdvisorContextBuilder gathers intelligence from existing SENTINEL service modules
and populates an AdvisorContext dataclass. No new risk/readiness/stockout
calculations are performed here — the builder is purely an aggregator of
existing service outputs.

Phase 11D adds lightweight KB retrieval (keyword search over local articles)
stored in AdvisorContext.kb_excerpts. KB retrieval is fail-safe; errors
do not break the advisor response flow.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..services.depot_service import DepotService
from ..services.base_service import BaseService
from ..services.inventory_service import InventoryService
from ..stockout.service import StockoutService
from ..risk.service import RiskService, DEPOT_ROUTE_MAPPING, BASE_ROUTE_MAPPING, get_route_id_for_depot
from ..readiness.service import ReadinessService
from ..environment.service import EnvironmentService
from ..environment.data import KNOWN_ROUTE_IDS
from ..digital_twin.shipments import get_synthetic_shipments
from ..digital_twin.service import DigitalTwinService
from ..digital_twin.schemas import DigitalTwinScenarioRequest
from ..digital_twin.scenario import DEMO_SCENARIOS
from .knowledge_base import KnowledgeRetriever, KBSearchResult


# ---------------------------------------------------------------------------
# Context Dataclass
# ---------------------------------------------------------------------------

@dataclass
class AdvisorContext:
    """
    Aggregated intelligence snapshot gathered from existing SENTINEL services.
    Populated by AdvisorContextBuilder. Not computed here — consumed from
    existing service layers.
    """

    # Scope identifiers from the request
    query: str = ""
    depot_id: Optional[str] = None
    base_id: Optional[str] = None
    route_id: Optional[str] = None

    # Resolved entities
    depot_record: Optional[Dict[str, Any]] = None
    base_record: Optional[Dict[str, Any]] = None
    all_depots: List[Dict[str, Any]] = field(default_factory=list)
    all_bases: List[Dict[str, Any]] = field(default_factory=list)

    # Inventory
    inventory_items: List[Dict[str, Any]] = field(default_factory=list)
    items_below_threshold: List[Dict[str, Any]] = field(default_factory=list)

    # Stockout predictions
    stockout_predictions: List[Dict[str, Any]] = field(default_factory=list)
    high_risk_stockouts: List[Dict[str, Any]] = field(default_factory=list)

    # Risk assessments
    risk_assessments: List[Dict[str, Any]] = field(default_factory=list)
    critical_risks: List[Dict[str, Any]] = field(default_factory=list)

    # Readiness assessments
    readiness_assessments: List[Dict[str, Any]] = field(default_factory=list)
    degraded_depots: List[Dict[str, Any]] = field(default_factory=list)

    # Environmental / route intelligence
    environmental_risk: Optional[Dict[str, Any]] = None
    route_env_risks: List[Dict[str, Any]] = field(default_factory=list)  # all known routes
    known_route_ids: List[str] = field(default_factory=list)

    # Supply movement / shipments
    shipments: List[Dict[str, Any]] = field(default_factory=list)

    # Knowledge Base retrieval (Phase 11D)
    # Populated by KnowledgeRetriever; contains relevant KB article excerpts
    # for the current query. Used by the reasoning engine for richer explanations.
    # This field contains static SENTINEL knowledge, NOT live operational data.
    kb_excerpts: List[KBSearchResult] = field(default_factory=list)

    # Phase 11G: Digital Twin Scenario context
    # If a scenario_id was supplied, this contains the resolved Digital Twin
    # simulation result dict. Populated by AdvisorContextBuilder from the
    # existing DigitalTwinService — no duplicate calculation is performed here.
    # Absent (None) when no scenario_id is supplied; backward-compatible.
    scenario_id: Optional[str] = None
    scenario_result: Optional[Dict[str, Any]] = None  # raw DT simulation result dict

    # Phase 12A: Unified Intelligence Context Overview
    unified_intelligence_overview: Optional[Dict[str, Any]] = None

    # Metadata
    errors: List[str] = field(default_factory=list)
    modules_available: Dict[str, bool] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Context Builder
# ---------------------------------------------------------------------------

class AdvisorContextBuilder:
    """
    Builds an AdvisorContext by calling existing SENTINEL service layers.
    Never duplicates risk, readiness, or stockout calculations.
    Fails safely — partial failures populate context.errors but do not
    raise exceptions, so the advisor can still generate a partial response.
    """

    @staticmethod
    def build(
        query: str,
        depot_id: Optional[str] = None,
        base_id: Optional[str] = None,
        route_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
        db_path: Optional[str] = None
    ) -> AdvisorContext:
        """
        Gathers context from all relevant SENTINEL modules.
        Returns a populated AdvisorContext.
        """
        ctx = AdvisorContext(
            query=query,
            depot_id=depot_id,
            base_id=base_id,
            route_id=route_id,
            scenario_id=scenario_id,
            known_route_ids=list(KNOWN_ROUTE_IDS),
        )

        # --- Phase 12A: Unified Intelligence Overview ---
        try:
            from ..intelligence.service import IntelligenceService
            ctx.unified_intelligence_overview = IntelligenceService.get_dashboard_intelligence(db_path=db_path)
            ctx.modules_available["unified_intelligence"] = True
        except Exception as exc:
            ctx.errors.append(f"Unified intelligence overview unavailable: {exc}")
            ctx.modules_available["unified_intelligence"] = False

        # --- Resolve depots & bases ---
        try:
            ctx.all_depots = DepotService.list_depots(db_path=db_path)
            ctx.modules_available["depots"] = True
        except Exception as exc:
            ctx.errors.append(f"Depot data unavailable: {exc}")
            ctx.modules_available["depots"] = False

        try:
            ctx.all_bases = BaseService.list_bases(db_path=db_path)
            ctx.modules_available["bases"] = True
        except Exception as exc:
            ctx.errors.append(f"Base data unavailable: {exc}")
            ctx.modules_available["bases"] = False

        # Resolve specific depot / base records
        if depot_id and ctx.all_depots:
            depot_map = {d["id"]: d for d in ctx.all_depots}
            ctx.depot_record = depot_map.get(depot_id)

        if base_id and ctx.all_bases:
            base_map = {b["id"]: b for b in ctx.all_bases}
            ctx.base_record = base_map.get(base_id)

        # Infer base_id from depot if not provided
        resolved_base_id = base_id
        if not resolved_base_id and ctx.depot_record:
            resolved_base_id = ctx.depot_record.get("base_id")

        # --- Inventory ---
        try:
            ctx.inventory_items = InventoryService.list_inventory(
                depot_id=depot_id, db_path=db_path
            )
            ctx.items_below_threshold = [
                item for item in ctx.inventory_items
                if float(item.get("current_quantity") or 0.0)
                   <= float(item.get("minimum_threshold") or 0.0)
            ]
            ctx.modules_available["inventory"] = True
        except Exception as exc:
            ctx.errors.append(f"Inventory data unavailable: {exc}")
            ctx.modules_available["inventory"] = False

        # --- Stockout predictions ---
        try:
            ctx.stockout_predictions = StockoutService.predict_stockout(
                depot_id=depot_id, db_path=db_path
            )
            ctx.high_risk_stockouts = [
                p for p in ctx.stockout_predictions
                if p.get("risk_level") in ("HIGH", "CRITICAL")
            ]
            ctx.modules_available["stockout"] = True
        except Exception as exc:
            ctx.errors.append(f"Stockout prediction unavailable: {exc}")
            ctx.modules_available["stockout"] = False

        # --- Risk assessments ---
        try:
            ctx.risk_assessments = RiskService.get_risk_assessments(
                depot_id=depot_id, db_path=db_path
            )
            ctx.critical_risks = [
                r for r in ctx.risk_assessments
                if r.get("risk_level") in ("HIGH", "CRITICAL")
            ]
            ctx.modules_available["risk"] = True
        except Exception as exc:
            ctx.errors.append(f"Risk intelligence unavailable: {exc}")
            ctx.modules_available["risk"] = False

        # --- Readiness assessments ---
        try:
            ctx.readiness_assessments = ReadinessService.get_readiness_assessments(
                depot_id=depot_id, base_id=base_id, db_path=db_path
            )
            ctx.degraded_depots = [
                r for r in ctx.readiness_assessments
                if r.get("readiness_status") in ("DEGRADED", "CRITICAL")
            ]
            ctx.modules_available["readiness"] = True
        except Exception as exc:
            ctx.errors.append(f"Readiness intelligence unavailable: {exc}")
            ctx.modules_available["readiness"] = False

        # --- Environmental / route risk ---
        # Resolve effective route_id: explicit > depot mapping > base mapping
        effective_route_id = route_id
        if not effective_route_id and depot_id:
            effective_route_id = get_route_id_for_depot(depot_id, resolved_base_id)
        if not effective_route_id and resolved_base_id:
            effective_route_id = BASE_ROUTE_MAPPING.get(resolved_base_id)

        if effective_route_id:
            try:
                ctx.environmental_risk = EnvironmentService.get_environmental_risk(effective_route_id)
                ctx.modules_available["environment"] = True
            except Exception as exc:
                ctx.errors.append(f"Environmental risk unavailable for route '{effective_route_id}': {exc}")
                ctx.modules_available["environment"] = False

        # Gather all known-route environmental risks for system-wide queries
        ctx.route_env_risks = []
        for rid in KNOWN_ROUTE_IDS:
            try:
                env = EnvironmentService.get_environmental_risk(rid)
                ctx.route_env_risks.append(env)
            except Exception:
                pass  # skip unmapped routes silently

        # --- Supply movement / shipments ---
        try:
            if depot_id:
                ctx.shipments = get_synthetic_shipments(depot_id=depot_id)
            else:
                ctx.shipments = get_synthetic_shipments()
            ctx.modules_available["shipments"] = True
        except Exception as exc:
            ctx.errors.append(f"Shipment data unavailable: {exc}")
            ctx.modules_available["shipments"] = False

        # --- Knowledge Base retrieval (Phase 11D) ---
        # KB retrieval is fail-safe: errors do not block the advisor response.
        # Live operational data is NOT stored in the KB; it is always read from
        # the service layers above. KB articles provide contextual explanations
        # about SENTINEL concepts (risk scoring, readiness thresholds, etc.).
        try:
            ctx.kb_excerpts = KnowledgeRetriever.search(query, top_k=3)
            ctx.modules_available["knowledge_base"] = True
        except Exception as exc:
            ctx.errors.append(f"Knowledge base retrieval unavailable: {exc}")
            ctx.modules_available["knowledge_base"] = False

        # --- Phase 11G: Digital Twin Scenario Resolution ---
        # If a scenario_id is provided, resolve it using the existing
        # DigitalTwinService. The scenario result is consumed as-is;
        # no risk/readiness/stockout calculations are duplicated here.
        # This is fail-safe: an unresolvable scenario_id sets an error
        # but does not abort the rest of the advisor response.
        if scenario_id:
            ctx.scenario_id = scenario_id
            # Look up matching DEMO_SCENARIO template
            matched_template = next(
                (s for s in DEMO_SCENARIOS if s["scenario_id"] == scenario_id),
                None
            )
            if matched_template:
                try:
                    dt_req = DigitalTwinScenarioRequest(
                        scenario_id=matched_template["scenario_id"],
                        scenario_type=matched_template["scenario_type"],
                        affected_depot_id=matched_template["affected_depot_id"],
                        affected_route_id=matched_template.get("affected_route_id"),
                        disruption_duration_days=matched_template["disruption_duration_days"],
                        additional_delay_days=matched_template.get("additional_delay_days", 0),
                        severity=matched_template.get("severity", "HIGH"),
                        description=matched_template.get("description"),
                    )
                    ctx.scenario_result = DigitalTwinService.simulate_scenario(
                        dt_req, db_path=db_path
                    )
                    ctx.modules_available["digital_twin_scenario"] = True
                except Exception as exc:
                    ctx.errors.append(
                        f"Digital Twin scenario '{scenario_id}' simulation failed: {exc}"
                    )
                    ctx.modules_available["digital_twin_scenario"] = False
            else:
                # Unknown scenario ID — do not fabricate data
                ctx.errors.append(
                    f"Digital Twin scenario '{scenario_id}' not found in the SENTINEL scenario registry. "
                    f"No scenario data will be used. Valid demo scenario IDs: "
                    f"{[s['scenario_id'] for s in DEMO_SCENARIOS]}"
                )
                ctx.modules_available["digital_twin_scenario"] = False

        return ctx
