"""
SENTINEL LOGIX AI - Intelligence Dashboard Service Layer
Phase 12A: Unified Intelligence Integration & Cross-Module Consistency
Aggregates operational state, inventory intelligence, risk assessments,
mission readiness assessments, demand forecasts, supply movement, Digital Twin,
Advisor status, and unified cross-module depot views & signals into a coherent,
read-only command-center payload.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from ..services.base_service import BaseService
from ..services.depot_service import DepotService
from ..services.inventory_service import InventoryService
from ..services.incident_service import IncidentService
from ..services.trip_service import TripService
from ..stockout.service import StockoutService
from ..risk.service import RiskService, get_route_id_for_depot
from ..readiness.service import ReadinessService
from ..digital_twin.shipments import get_synthetic_shipments
from ..digital_twin.service import DigitalTwinService
from ..environment.service import EnvironmentService
from .schemas import (
    IntelligenceDashboardResponse,
    DashboardMetadata,
    OperationalOverview,
    InventoryIntelligence,
    InventoryItemSnapshot,
    RiskIntelligenceSummary,
    ReadinessIntelligenceSummary,
    DemandIntelligenceSummary,
    HighPressureItem,
    SupplyMovementSummary,
    DigitalTwinSummary,
    AdvisorSummary,
    DepotInventorySnapshot,
    DepotStockoutSummary,
    DepotOperationalRiskSummary,
    DepotMissionReadinessSummary,
    DepotEnvironmentalExposure,
    DepotSupplyMovementSummary,
    DepotUnifiedView,
    UnifiedSignal,
    IntelligenceModuleStatus
)

class IntelligenceService:
    @staticmethod
    def get_dashboard_intelligence(
        db_path: Optional[str] = None,
        active_simulation_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Aggregates outputs from existing services into a comprehensive dashboard intelligence payload.
        Provides a unified cross-module operational picture with depot-level views and signal aggregation.
        Handles partial module failures safely without mutating persistent storage.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        module_status = IntelligenceModuleStatus()

        bases, depots, inventory_items, active_trips, active_incidents = [], [], [], [], []
        stockout_preds = []
        risk_assessments = []
        readiness_assessments = []
        env_assessments = []
        shipments = []

        # 1. Operational Overview
        try:
            bases = BaseService.list_bases(db_path=db_path)
            depots = DepotService.list_depots(db_path=db_path)
            inventory_items = InventoryService.list_inventory(db_path=db_path)
            active_trips = TripService.list_trips(status="ACTIVE", db_path=db_path)
            active_incidents = IncidentService.list_incidents(is_active=True, db_path=db_path)

            operational_overview = {
                "total_bases": len(bases),
                "total_depots": len(depots),
                "total_inventory_items": len(inventory_items),
                "active_trips_count": len(active_trips),
                "active_incidents_count": len(active_incidents)
            }
            module_status.operational_data = "AVAILABLE"
        except Exception:
            operational_overview = {
                "total_bases": 0,
                "total_depots": 0,
                "total_inventory_items": 0,
                "active_trips_count": 0,
                "active_incidents_count": 0
            }
            module_status.operational_data = "UNAVAILABLE"

        # 2. Inventory Intelligence & Stockout Predictions
        high_pressure_items = []
        try:
            total_qty = sum(float(item.get("current_quantity") or 0.0) for item in inventory_items)
            critical_items_count = sum(
                1 for item in inventory_items
                if item.get("criticality") == "CRITICAL" or float(item.get("current_quantity") or 0.0) <= float(item.get("minimum_threshold") or 0.0)
            )
            items_below_thresh_count = sum(
                1 for item in inventory_items
                if float(item.get("current_quantity") or 0.0) <= float(item.get("minimum_threshold") or 0.0)
            )

            items_snapshots = [
                {
                    "id": item["id"],
                    "depot_id": item["depot_id"],
                    "item_name": item["item_name"],
                    "category": item["category"],
                    "unit": item["unit"],
                    "current_quantity": float(item["current_quantity"]),
                    "minimum_threshold": float(item["minimum_threshold"]),
                    "criticality": item["criticality"]
                }
                for item in inventory_items
            ]

            # Stockout predictions for high pressure items & stockout projected count
            stockout_preds = StockoutService.predict_stockout(db_path=db_path)
            stockout_projected_count = sum(1 for p in stockout_preds if p.get("days_until_stockout") is not None)

            for p in stockout_preds:
                days_so = p.get("days_until_stockout")
                days_br = p.get("days_until_threshold_breach")
                if days_so is not None or (days_br is not None and days_br <= 7):
                    high_pressure_items.append({
                        "item_id": p["inventory_item_id"],
                        "depot_id": p["depot_id"],
                        "item_name": p["item_name"],
                        "days_until_stockout": days_so,
                        "days_until_threshold_breach": days_br
                    })

            inventory_intel = {
                "total_tracked_inventory_quantity": round(total_qty, 2),
                "critical_inventory_items_count": critical_items_count,
                "high_risk_inventory_items_count": 0,  # Updated after risk assessment
                "stockout_projected_count": stockout_projected_count,
                "items_below_threshold_count": items_below_thresh_count,
                "items_summary": items_snapshots
            }
            module_status.inventory = "AVAILABLE"
            module_status.forecasting = "AVAILABLE"
        except Exception:
            inventory_intel = {
                "total_tracked_inventory_quantity": 0.0,
                "critical_inventory_items_count": 0,
                "high_risk_inventory_items_count": 0,
                "stockout_projected_count": 0,
                "items_below_threshold_count": 0,
                "items_summary": []
            }
            high_pressure_items = []
            module_status.inventory = "UNAVAILABLE"
            module_status.forecasting = "UNAVAILABLE"

        # 3. Risk Intelligence
        try:
            risk_assessments = RiskService.get_risk_assessments(db_path=db_path)
            risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            highest_risk_score = 0.0
            highest_risk_depot_id = None
            highest_risk_depot_name = None

            for r in risk_assessments:
                lvl = r.get("risk_level", "LOW").upper()
                if lvl in risk_counts:
                    risk_counts[lvl] += 1
                score = float(r.get("risk_score", 0.0))
                if score >= highest_risk_score:
                    highest_risk_score = score
                    highest_risk_depot_id = r.get("depot_id")
                    highest_risk_depot_name = r.get("depot_name")

            if risk_counts["CRITICAL"] > 0:
                overall_risk_lvl = "CRITICAL"
            elif risk_counts["HIGH"] > 0:
                overall_risk_lvl = "HIGH"
            elif risk_counts["MEDIUM"] > 0:
                overall_risk_lvl = "MEDIUM"
            else:
                overall_risk_lvl = "LOW"

            high_risk_items_count = risk_counts["CRITICAL"] + risk_counts["HIGH"]
            inventory_intel["high_risk_inventory_items_count"] = high_risk_items_count

            risk_intel = {
                "overall_risk_level": overall_risk_lvl,
                "risk_classification_counts": risk_counts,
                "highest_risk_depot_id": highest_risk_depot_id,
                "highest_risk_depot_name": highest_risk_depot_name,
                "highest_risk_score": round(highest_risk_score, 1)
            }
            module_status.risk_engine = "AVAILABLE"
        except Exception:
            risk_intel = {
                "overall_risk_level": "LOW",
                "risk_classification_counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "highest_risk_depot_id": None,
                "highest_risk_depot_name": None,
                "highest_risk_score": 0.0
            }
            module_status.risk_engine = "UNAVAILABLE"

        # 4. Readiness Intelligence
        try:
            readiness_assessments = ReadinessService.get_readiness_assessments(db_path=db_path)
            readiness_counts = {"READY": 0, "CAUTION": 0, "DEGRADED": 0, "CRITICAL": 0}
            lowest_readiness_score = 100.0
            lowest_readiness_depot_id = None
            lowest_readiness_depot_name = None
            total_readiness_sum = 0.0

            for rad in readiness_assessments:
                stat = rad.get("readiness_status", "READY").upper()
                if stat in readiness_counts:
                    readiness_counts[stat] += 1
                score = float(rad.get("readiness_score", 100.0))
                total_readiness_sum += score
                if score <= lowest_readiness_score:
                    lowest_readiness_score = score
                    lowest_readiness_depot_id = rad.get("depot_id")
                    lowest_readiness_depot_name = rad.get("depot_name")

            if readiness_counts["CRITICAL"] > 0:
                overall_readiness_stat = "CRITICAL"
            elif readiness_counts["DEGRADED"] > 0:
                overall_readiness_stat = "DEGRADED"
            elif readiness_counts["CAUTION"] > 0:
                overall_readiness_stat = "CAUTION"
            else:
                overall_readiness_stat = "READY"

            avg_readiness = round(total_readiness_sum / len(readiness_assessments), 1) if readiness_assessments else 100.0

            readiness_intel = {
                "overall_readiness_status": overall_readiness_stat,
                "readiness_status_counts": readiness_counts,
                "lowest_readiness_depot_id": lowest_readiness_depot_id,
                "lowest_readiness_depot_name": lowest_readiness_depot_name,
                "lowest_readiness_score": round(lowest_readiness_score, 1),
                "average_readiness_score": avg_readiness
            }
            module_status.readiness_engine = "AVAILABLE"
        except Exception:
            readiness_intel = {
                "overall_readiness_status": "READY",
                "readiness_status_counts": {"READY": 0, "CAUTION": 0, "DEGRADED": 0, "CRITICAL": 0},
                "lowest_readiness_depot_id": None,
                "lowest_readiness_depot_name": None,
                "lowest_readiness_score": 100.0,
                "average_readiness_score": 100.0
            }
            module_status.readiness_engine = "UNAVAILABLE"

        # 5. Demand Intelligence
        demand_intel = {
            "forecast_horizon_days": 14,
            "forecast_model_status": "ACTIVE" if module_status.forecasting == "AVAILABLE" else "UNAVAILABLE",
            "high_pressure_items": high_pressure_items
        }

        # 6. Supply Movement
        try:
            shipments = get_synthetic_shipments()
            total_shipments = len(shipments)
            in_transit_count = sum(1 for s in shipments if s.get("status") == "IN_TRANSIT")
            routes_count = len(set(s.get("route_id") for s in shipments if s.get("route_id")))

            delayed_count = 0
            delayed_qty = 0.0

            if active_simulation_result and "affected_shipments" in active_simulation_result:
                aff_ships = active_simulation_result["affected_shipments"]
                delayed_ships = [s for s in aff_ships if s.get("delay_days", 0) > 0]
                delayed_count = len(delayed_ships)
                delayed_qty = sum(float(s.get("quantity", 0.0)) for s in delayed_ships)

            supply_movement = {
                "total_shipments_count": total_shipments,
                "in_transit_shipments_count": in_transit_count,
                "delayed_shipments_count": delayed_count,
                "total_delayed_quantity": round(delayed_qty, 2),
                "shipment_routes_count": routes_count
            }
            module_status.supply_movement = "AVAILABLE"
        except Exception:
            supply_movement = {
                "total_shipments_count": 0,
                "in_transit_shipments_count": 0,
                "delayed_shipments_count": 0,
                "total_delayed_quantity": 0.0,
                "shipment_routes_count": 0
            }
            module_status.supply_movement = "UNAVAILABLE"

        # 7. Environmental Intelligence
        route_map = {}
        route_summaries = []
        try:
            env_assessments = EnvironmentService.list_environmental_risks()
            total_routes = len(env_assessments)
            low_count = sum(1 for a in env_assessments if a.get("classification") == "LOW")
            med_count = sum(1 for a in env_assessments if a.get("classification") == "MEDIUM")
            high_count = sum(1 for a in env_assessments if a.get("classification") == "HIGH")
            crit_count = sum(1 for a in env_assessments if a.get("classification") == "CRITICAL")

            highest_route = None
            highest_score = 0.0
            if env_assessments:
                top = env_assessments[0]
                highest_route = top.get("route_id")
                highest_score = float(top.get("environmental_risk_score", 0.0))

            weather_dom_count = sum(
                1 for a in env_assessments if float(a.get("weather_risk_score", 0.0)) >= float(a.get("terrain_risk_score", 0.0))
            )
            terrain_dom_count = sum(
                1 for a in env_assessments if float(a.get("terrain_risk_score", 0.0)) > float(a.get("weather_risk_score", 0.0))
            )

            for a in env_assessments:
                r_id = a.get("route_id")
                route_map[r_id] = a
                route_summaries.append({
                    "route_id": r_id,
                    "route_name": a.get("route_name", r_id),
                    "weather_risk_score": float(a.get("weather_risk_score", 0.0)),
                    "terrain_risk_score": float(a.get("terrain_risk_score", 0.0)),
                    "environmental_risk_score": float(a.get("environmental_risk_score", 0.0)),
                    "classification": a.get("classification", "LOW"),
                    "dominant_dimension": "WEATHER" if float(a.get("weather_risk_score", 0.0)) >= float(a.get("terrain_risk_score", 0.0)) else "TERRAIN",
                    "explanation": a.get("explanation", "")
                })

            env_intel = {
                "total_routes_assessed": total_routes,
                "low_risk_routes": low_count,
                "medium_risk_routes": med_count,
                "high_risk_routes": high_count,
                "critical_risk_routes": crit_count,
                "highest_risk_route": highest_route,
                "highest_risk_score": round(highest_score, 1),
                "weather_dominant_routes": weather_dom_count,
                "terrain_dominant_routes": terrain_dom_count,
                "routes": route_summaries,
                "data_source": "synthetic_demo",
                "environment": "demo"
            }
            module_status.environmental_intelligence = "AVAILABLE"
        except Exception:
            env_intel = {
                "total_routes_assessed": 0,
                "low_risk_routes": 0,
                "medium_risk_routes": 0,
                "high_risk_routes": 0,
                "critical_risk_routes": 0,
                "highest_risk_route": None,
                "highest_risk_score": 0.0,
                "weather_dominant_routes": 0,
                "terrain_dominant_routes": 0,
                "routes": [],
                "data_source": "synthetic_demo",
                "environment": "demo"
            }
            module_status.environmental_intelligence = "UNAVAILABLE"

        # 8. Digital Twin Summary
        available_scenarios = []
        try:
            available_scenarios = DigitalTwinService.get_available_scenarios()
        except Exception:
            available_scenarios = []

        if active_simulation_result:
            digital_twin_summary = {
                "scenario_available": True,
                "scenario_type": active_simulation_result.get("scenario_type"),
                "affected_depot_id": active_simulation_result.get("affected_depot_id"),
                "risk_delta": active_simulation_result.get("risk_score_delta"),
                "readiness_delta": active_simulation_result.get("readiness_score_delta"),
                "human_summary": active_simulation_result.get("human_summary") or active_simulation_result.get("explanation"),
                "available_scenarios": available_scenarios
            }
            module_status.digital_twin = "AVAILABLE"
        else:
            digital_twin_summary = {
                "scenario_available": False,
                "scenario_type": None,
                "affected_depot_id": None,
                "risk_delta": None,
                "readiness_delta": None,
                "human_summary": None,
                "available_scenarios": available_scenarios
            }
            module_status.digital_twin = "NO_ACTIVE_SCENARIO"

        # 9. Advisor Summary
        advisor_summary = {
            "status": "AVAILABLE",
            "kb_articles_loaded": 10,
            "llm_provider_configured": False,
            "mock_mode": True
        }
        module_status.advisor = "AVAILABLE"

        # 10. Cross-Module Depot Views
        bases_map = {b["id"]: b for b in bases} if bases else {}
        depot_views = []

        for d in depots:
            depot_id = d["id"]
            depot_name = d.get("name", depot_id)
            base_id = d.get("base_id")
            base_rec = bases_map.get(base_id, {}) if base_id else {}
            base_name = base_rec.get("name") if base_rec else None

            # Inventory Health
            depot_items = [item for item in inventory_items if item.get("depot_id") == depot_id]
            depot_qty = sum(float(item.get("current_quantity") or 0.0) for item in depot_items)
            depot_crit_items = sum(
                1 for item in depot_items
                if item.get("criticality") == "CRITICAL" or float(item.get("current_quantity") or 0.0) <= float(item.get("minimum_threshold") or 0.0)
            )
            depot_thresh_items = sum(
                1 for item in depot_items
                if float(item.get("current_quantity") or 0.0) <= float(item.get("minimum_threshold") or 0.0)
            )

            inv_health = {
                "total_items": len(depot_items),
                "total_quantity": round(depot_qty, 2),
                "critical_items_count": depot_crit_items,
                "items_below_threshold_count": depot_thresh_items
            }

            # Stock-out Risk
            depot_so = [p for p in stockout_preds if p.get("depot_id") == depot_id]
            proj_so_cnt = sum(1 for p in depot_so if p.get("days_until_stockout") is not None)
            depot_hp_items = [
                p for p in depot_so
                if p.get("days_until_stockout") is not None or (p.get("days_until_threshold_breach") is not None and p["days_until_threshold_breach"] <= 7)
            ]

            stock_out_risk = {
                "projected_stockouts_count": proj_so_cnt,
                "high_pressure_items_count": len(depot_hp_items),
                "high_pressure_items": depot_hp_items
            }

            # Operational Risk (verbatim from RiskService)
            depot_risk_recs = [r for r in risk_assessments if r.get("depot_id") == depot_id]
            if depot_risk_recs:
                top_risk = max(depot_risk_recs, key=lambda x: float(x.get("risk_score", 0.0)))
                d_risk_score = float(top_risk.get("risk_score", 0.0))
                d_risk_level = top_risk.get("risk_level", "LOW")
                d_risk_factors = top_risk.get("top_contributing_factors", [])
            else:
                d_risk_score = 0.0
                d_risk_level = "LOW"
                d_risk_factors = []

            op_risk = {
                "risk_score": round(d_risk_score, 1),
                "risk_level": d_risk_level,
                "top_contributing_factors": d_risk_factors
            }

            # Mission Readiness (verbatim from ReadinessService)
            depot_rad_rec = next(
                (r for r in readiness_assessments if (r.get("entity_id") == depot_id or r.get("depot_id") == depot_id)),
                None
            )
            if depot_rad_rec:
                d_rad_score = float(depot_rad_rec.get("readiness_score", 100.0))
                d_rad_status = depot_rad_rec.get("readiness_status", "READY")
                d_rad_issues = depot_rad_rec.get("key_issues", []) or [f["message"] for f in depot_rad_rec.get("contributing_factors", []) if f.get("impact") == "negative"]
            else:
                d_rad_score = 100.0
                d_rad_status = "READY"
                d_rad_issues = []

            mission_readiness = {
                "readiness_score": round(d_rad_score, 1),
                "readiness_status": d_rad_status,
                "key_issues": d_rad_issues
            }

            # Demand Pressure
            demand_pressure = {
                "forecast_status": "ACTIVE" if module_status.forecasting == "AVAILABLE" else "UNAVAILABLE",
                "high_pressure_items": depot_hp_items
            }

            # Environmental Exposure (verbatim route mapping & assessment)
            route_id = get_route_id_for_depot(depot_id, base_id)
            env_route = route_map.get(route_id) if (route_id and route_map) else None
            if env_route:
                env_exposure = {
                    "route_id": route_id,
                    "environmental_risk_score": float(env_route.get("environmental_risk_score", 0.0)),
                    "classification": env_route.get("classification", "LOW"),
                    "dominant_dimension": "WEATHER" if float(env_route.get("weather_risk_score", 0.0)) >= float(env_route.get("terrain_risk_score", 0.0)) else "TERRAIN",
                    "explanation": env_route.get("explanation", ""),
                    "status": "MAPPED",
                    "limitation": None
                }
            else:
                env_exposure = {
                    "route_id": route_id,
                    "environmental_risk_score": None,
                    "classification": None,
                    "dominant_dimension": None,
                    "explanation": None,
                    "status": "UNAVAILABLE",
                    "limitation": f"Environmental route mapping unavailable for depot '{depot_id}'"
                }

            # Supply Movement for depot
            depot_shipments = [
                s for s in shipments
                if s.get("origin_depot_id") == depot_id or s.get("destination_depot_id") == depot_id
            ]
            depot_active_shipments = sum(1 for s in depot_shipments if s.get("status") == "IN_TRANSIT")
            depot_delayed_shipments = sum(1 for s in depot_shipments if s.get("status") == "DELAYED" or s.get("delay_days", 0) > 0)
            depot_inbound_qty = sum(float(s.get("quantity", 0.0)) for s in depot_shipments if s.get("destination_depot_id") == depot_id)

            relevant_supply = {
                "active_shipments_count": depot_active_shipments,
                "delayed_shipments_count": depot_delayed_shipments,
                "total_inbound_quantity": round(depot_inbound_qty, 2)
            }

            depot_views.append({
                "depot_id": depot_id,
                "depot_name": depot_name,
                "base_id": base_id,
                "base_name": base_name,
                "inventory_health": inv_health,
                "stock_out_risk": stock_out_risk,
                "operational_risk": op_risk,
                "mission_readiness": mission_readiness,
                "demand_pressure": demand_pressure,
                "environmental_exposure": env_exposure,
                "relevant_supply_movement": relevant_supply,
                "data_source": "synthetic_demo",
                "environment": "demo"
            })

        # 11. Cross-Module Critical Signals Aggregation
        critical_signals = []

        # Stockout signals
        for p in stockout_preds:
            days_so = p.get("days_until_stockout")
            if days_so is not None:
                critical_signals.append({
                    "signal_id": f"SIG-STOCKOUT-{p.get('inventory_item_id')}",
                    "source_module": "stockout",
                    "entity_type": "INVENTORY_ITEM",
                    "entity_id": p.get("inventory_item_id", "UNKNOWN"),
                    "classification": "CRITICAL" if days_so <= 3 else "HIGH",
                    "relevant_value": days_so,
                    "explanation": f"Item '{p.get('item_name')}' projected stock-out in {days_so} days at depot {p.get('depot_id')}"
                })

        # Risk signals
        for r in risk_assessments:
            lvl = r.get("risk_level", "LOW").upper()
            score = float(r.get("risk_score", 0.0))
            if lvl in ("HIGH", "CRITICAL") or score >= 60.0:
                critical_signals.append({
                    "signal_id": f"SIG-RISK-{r.get('inventory_item_id', r.get('depot_id'))}",
                    "source_module": "risk_engine",
                    "entity_type": "DEPOT",
                    "entity_id": r.get("depot_id", "UNKNOWN"),
                    "classification": lvl,
                    "relevant_value": round(score, 1),
                    "explanation": f"Depot '{r.get('depot_name')}' item '{r.get('item_name')}' operational risk score ({round(score, 1)}) classified as {lvl}"
                })

        # Readiness signals
        for rad in readiness_assessments:
            stat = rad.get("readiness_status", "READY").upper()
            score = float(rad.get("readiness_score", 100.0))
            if stat in ("DEGRADED", "CRITICAL") or score <= 60.0:
                rad_depot_id = rad.get("entity_id") or rad.get("depot_id", "UNKNOWN")
                rad_depot_name = rad.get("entity_name") or rad.get("depot_name", rad_depot_id)
                critical_signals.append({
                    "signal_id": f"SIG-READINESS-{rad_depot_id}",
                    "source_module": "readiness_engine",
                    "entity_type": "DEPOT",
                    "entity_id": rad_depot_id,
                    "classification": stat,
                    "relevant_value": round(score, 1),
                    "explanation": f"Depot '{rad_depot_name}' readiness compromised ({round(score, 1)}/100) classified as {stat}"
                })

        # Environmental signals
        for route in route_summaries:
            cls = route.get("classification", "LOW").upper()
            score = float(route.get("environmental_risk_score", 0.0))
            if cls in ("HIGH", "CRITICAL") or score >= 60.0:
                critical_signals.append({
                    "signal_id": f"SIG-ENV-{route.get('route_id')}",
                    "source_module": "environmental_intelligence",
                    "entity_type": "ROUTE",
                    "entity_id": route.get("route_id", "UNKNOWN"),
                    "classification": cls,
                    "relevant_value": round(score, 1),
                    "explanation": f"Route '{route.get('route_name')}' environmental hazard score ({round(score, 1)}) driven by {route.get('dominant_dimension')}"
                })

        # Supply Movement signals
        for s in shipments:
            if s.get("status") == "DELAYED" or s.get("delay_days", 0) > 0:
                critical_signals.append({
                    "signal_id": f"SIG-SHIPMENT-{s.get('shipment_id', 'UNKNOWN')}",
                    "source_module": "supply_movement",
                    "entity_type": "SHIPMENT",
                    "entity_id": s.get("shipment_id", "UNKNOWN"),
                    "classification": "HIGH" if s.get("delay_days", 0) > 2 else "MEDIUM",
                    "relevant_value": s.get("delay_days", 0),
                    "explanation": f"Shipment {s.get('shipment_id')} to {s.get('destination_depot_id')} delayed by {s.get('delay_days', 0)} days"
                })

        # Digital Twin signals
        if active_simulation_result:
            r_delta = active_simulation_result.get("risk_score_delta", 0.0)
            if r_delta > 0 or active_simulation_result.get("affected_depot_id"):
                critical_signals.append({
                    "signal_id": "SIG-SCENARIO-ACTIVE",
                    "source_module": "digital_twin",
                    "entity_type": "SCENARIO",
                    "entity_id": active_simulation_result.get("scenario_type", "SIMULATION"),
                    "classification": "CRITICAL" if r_delta >= 15.0 else "HIGH",
                    "relevant_value": round(r_delta, 1),
                    "explanation": active_simulation_result.get("human_summary") or "Active what-if scenario impacting logistics operational metrics"
                })

        metadata = {
            "data_source": "synthetic_demo",
            "environment": "demo",
            "generated_at": now_iso
        }

        return {
            "metadata": metadata,
            "operational_overview": operational_overview,
            "inventory_intelligence": inventory_intel,
            "risk_intelligence": risk_intel,
            "readiness_intelligence": readiness_intel,
            "demand_intelligence": demand_intel,
            "supply_movement": supply_movement,
            "environmental_intelligence": env_intel,
            "digital_twin": digital_twin_summary,
            "advisor": advisor_summary,
            "depot_views": depot_views,
            "critical_signals": critical_signals,
            "intelligence_status": module_status.model_dump()
        }


