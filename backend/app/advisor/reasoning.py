"""
SENTINEL LOGIX AI - Context-Aware AI Advisor Reasoning Engine
Phase 11B: Multi-Signal Reasoning Layer

Analyzes multiple SENTINEL intelligence signals together (Inventory, Stock-out,
Operational Risk, Mission Readiness, Environmental & Terrain Risk, Digital Twin)
to generate context-aware, explainable logistics recommendations.

Design Principles:
------------------
1. Purely deterministic reasoning engine — no external LLM or AI API invoked.
2. Grounded strictly in pre-computed outputs from SENTINEL service modules.
3. Does NOT recalculate or compete with underlying risk/readiness/stockout formulas.
4. Explores cross-signal interactions (e.g., Inventory + Stock-out, Risk + Readiness,
   Environment + Supply Movement).
5. Explicitly handles signal conflicts and insufficient data without fabricating facts.
6. Generates structured EvidenceItem entries, human-in-the-loop Recommended Actions,
   and contextual Limitations.
"""

from typing import List, Dict, Any, Optional, Tuple

from .schemas import (
    SupportingFactor,
    RelevantEntity,
    EvidenceItem,
    PRIORITY_VALUES,
)
from .context import AdvisorContext


# ---------------------------------------------------------------------------
# Priority Weight Helper
# ---------------------------------------------------------------------------

_PRIORITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

def _max_priority(p1: str, p2: str) -> str:
    w1 = _PRIORITY_ORDER.get(p1.upper(), 1)
    w2 = _PRIORITY_ORDER.get(p2.upper(), 1)
    return p1.upper() if w1 >= w2 else p2.upper()


# ---------------------------------------------------------------------------
# Core Reasoning Engine
# ---------------------------------------------------------------------------

class AdvisorReasoningEngine:
    """
    Context-aware multi-signal reasoning engine for SENTINEL AI Logistics Advisor.
    Evaluates cross-signal relationships from AdvisorContext and outputs a
    structured reasoning dictionary.
    """

    @staticmethod
    def evaluate(ctx: AdvisorContext, intent: str) -> Dict[str, Any]:
        """
        Main entry point for multi-signal evaluation.
        Flow:
          1. Signal Analysis & Evidence Extraction
          2. Cross-Signal Reasoning & Conflict Detection
          3. Prioritization & Confidence Assessment
          4. Natural-Language Synthesis & Recommendation Generation
          5. Action & Limitation Compilation
        """
        # Step 1: Extract structured evidence from context
        evidence: List[EvidenceItem] = []
        factors: List[SupportingFactor] = []
        entities: List[RelevantEntity] = []
        limitations: List[str] = [
            "This assessment uses synthetic demonstration data.",
            "Environmental intelligence is derived from deterministic synthetic demonstration data.",
            "No real-time external IoT sensor or live weather feed is connected.",
            "Decision-support confidence reflects signal alignment and context completeness, not statistical probability."
        ]
        conflicts: List[str] = []

        # Derive active operational & knowledge sources
        knowledge_sources: List[str] = [kb.article_id for kb in ctx.kb_excerpts]
        operational_sources: List[str] = []
        if ctx.inventory_items:
            operational_sources.append("inventory")
        if ctx.stockout_predictions:
            operational_sources.append("stockout")
        if ctx.risk_assessments:
            operational_sources.append("risk")
        if ctx.readiness_assessments:
            operational_sources.append("readiness")
        if ctx.environmental_risk or ctx.route_env_risks:
            operational_sources.append("environment")
        if ctx.shipments:
            operational_sources.append("shipments")
        if ctx.all_depots:
            operational_sources.append("depots")
        if ctx.all_bases:
            operational_sources.append("bases")
        # Phase 11G: track Digital Twin scenario source
        if ctx.scenario_result:
            operational_sources.append("digital_twin_scenario")

        # Track module errors as explicit limitations
        for err in ctx.errors:
            limitations.append(err)

        # -------------------------------------------------------------------
        # Phase 11G: SCENARIO REASONING BRANCH
        # Activated when intent is 'scenario_explanation' AND a resolved
        # Digital Twin scenario result exists in context.
        # ALL values are consumed from the existing DT simulation output;
        # NO new risk/readiness/stockout calculations are performed.
        # -------------------------------------------------------------------
        if intent == "scenario_explanation" and ctx.scenario_result:
            return AdvisorReasoningEngine._evaluate_scenario(
                ctx, ctx.scenario_result, knowledge_sources, operational_sources,
                limitations, evidence, factors, entities
            )

        # -------------------------------------------------------------------
        # Step 1A: Extract Inventory Evidence
        # -------------------------------------------------------------------
        total_inv_count = len(ctx.inventory_items)
        below_thresh_count = len(ctx.items_below_threshold)

        if total_inv_count > 0:
            evidence.append(EvidenceItem(
                source="inventory_service",
                observation="Tracked Inventory Items",
                value=f"{total_inv_count} item(s)",
                interpretation=f"{below_thresh_count} item(s) are at or below minimum threshold."
                if below_thresh_count else "All tracked inventory items are above minimum threshold."
            ))

        for item in ctx.items_below_threshold:
            item_id = item.get("id", "")
            item_name = item.get("item_name", item_id)
            qty = float(item.get("current_quantity") or 0.0)
            min_thresh = float(item.get("minimum_threshold") or 0.0)

            factors.append(SupportingFactor(
                factor="INVENTORY_BELOW_THRESHOLD",
                detail=f"'{item_name}' quantity ({qty:.0f}) is at or below threshold ({min_thresh:.0f}).",
                value=f"{qty:.0f}/{min_thresh:.0f}"
            ))
            entities.append(RelevantEntity(
                entity_type="inventory_item",
                entity_id=item_id,
                entity_name=item_name
            ))

        # -------------------------------------------------------------------
        # Step 1B: Extract Stockout Evidence
        # -------------------------------------------------------------------
        high_critical_stockouts = ctx.high_risk_stockouts

        for pred in ctx.stockout_predictions:
            risk_lvl = pred.get("risk_level", "LOW")
            item_name = pred.get("item_name", pred.get("inventory_item_id", ""))
            days = pred.get("days_until_stockout")
            already_breached = pred.get("already_breached", False)

            if risk_lvl in ("HIGH", "CRITICAL"):
                interp_str = (
                    f"Stock-out breached or imminent (day {days})"
                    if already_breached or (days is not None and days <= 1)
                    else f"Projected stock-out within {days} days requiring replenishment."
                    if days is not None else "High risk of inventory exhaustion."
                )
                evidence.append(EvidenceItem(
                    source="stockout_prediction",
                    observation="Projected Stock-out Risk",
                    value=f"{risk_lvl}" + (f" ({days} days)" if days is not None else ""),
                    interpretation=f"'{item_name}' at depot '{pred.get('depot_name', pred.get('depot_id'))}': {interp_str}"
                ))

        # -------------------------------------------------------------------
        # Step 1C: Extract Operational Risk Evidence
        # -------------------------------------------------------------------
        for risk in ctx.risk_assessments:
            r_lvl = risk.get("risk_level", "LOW")
            r_score = float(risk.get("risk_score", 0.0))
            if r_lvl in ("HIGH", "CRITICAL"):
                evidence.append(EvidenceItem(
                    source="risk_service",
                    observation="Operational Risk Assessment",
                    value=f"{r_score:.1f}/100 ({r_lvl})",
                    interpretation=f"Depot '{risk.get('depot_name', risk.get('depot_id'))}' exhibits elevated operational risk for '{risk.get('item_name','item')}'."
                ))

        # -------------------------------------------------------------------
        # Step 1D: Extract Readiness Evidence
        # -------------------------------------------------------------------
        for r_rec in ctx.readiness_assessments:
            r_status = r_rec.get("readiness_status", "READY")
            r_score = float(r_rec.get("readiness_score", 100.0))
            depot_name = r_rec.get("depot_name", r_rec.get("depot_id", ""))

            if r_status in ("CAUTION", "DEGRADED", "CRITICAL"):
                evidence.append(EvidenceItem(
                    source="readiness_service",
                    observation="Mission Readiness Assessment",
                    value=f"{r_status} ({r_score:.1f}/100)",
                    interpretation=f"Depot '{depot_name}' mission readiness is {r_status}."
                ))
                entities.append(RelevantEntity(
                    entity_type="depot",
                    entity_id=r_rec.get("depot_id", ""),
                    entity_name=depot_name
                ))

        # -------------------------------------------------------------------
        # Step 1E: Extract Environmental Evidence
        # -------------------------------------------------------------------
        env = ctx.environmental_risk
        if env:
            env_class = env.get("classification", "LOW")
            env_score = float(env.get("environmental_risk_score", 0.0))
            route_name = env.get("route_name", env.get("route_id", ""))

            evidence.append(EvidenceItem(
                source="environment_service",
                observation="Route Environmental Classification",
                value=f"{env_class} ({env_score:.1f}/100)",
                interpretation=f"Supply route '{route_name}' environmental hazard level is {env_class}."
            ))
            entities.append(RelevantEntity(
                entity_type="route",
                entity_id=env.get("route_id", ""),
                entity_name=route_name
            ))

        # -------------------------------------------------------------------
        # Step 1F: Extract Supply Movement / Shipment Evidence
        # -------------------------------------------------------------------
        active_shipments = [s for s in ctx.shipments if s.get("status") in ("IN_TRANSIT", "SCHEDULED")]
        if active_shipments:
            evidence.append(EvidenceItem(
                source="digital_twin",
                observation="Replenishment Supply Movement",
                value=f"{len(active_shipments)} active/scheduled shipment(s)",
                interpretation=f"{len(active_shipments)} shipment(s) currently tracked on supply routes."
            ))

        # -------------------------------------------------------------------
        # Step 2: Cross-Signal Reasoning & Conflict Analysis
        # -------------------------------------------------------------------
        cross_signal_findings: List[str] = []

        # Relationship A: Inventory + Stockout
        if below_thresh_count > 0 and high_critical_stockouts:
            cross_signal_findings.append(
                f"Multi-Signal Convergence: {below_thresh_count} item(s) are below threshold AND "
                f"{len(high_critical_stockouts)} item(s) have HIGH/CRITICAL stock-out predictions, confirming immediate inventory depletion pressure."
            )

        # Relationship B: Demand + Inventory
        for item in ctx.items_below_threshold:
            item_id = item.get("id")
            # find corresponding stockout pred
            matching_so = next((s for s in ctx.stockout_predictions if s.get("inventory_item_id") == item_id), None)
            if matching_so:
                avg_rate = matching_so.get("avg_daily_consumption", 0.0)
                if avg_rate and avg_rate > 0:
                    cross_signal_findings.append(
                        f"Demand-Inventory Pressure: '{item.get('item_name')}' has active daily consumption ({avg_rate:.1f} units/day) "
                        f"while quantity ({item.get('current_quantity',0):.0f}) is at or below threshold ({item.get('minimum_threshold',0):.0f})."
                    )

        # Relationship C: Operational Risk + Mission Readiness
        for r_rec in ctx.readiness_assessments:
            d_id = r_rec.get("depot_id")
            d_status = r_rec.get("readiness_status", "READY")
            depot_risks = [rk for rk in ctx.risk_assessments if rk.get("depot_id") == d_id and rk.get("risk_level") in ("HIGH", "CRITICAL")]

            if depot_risks and d_status in ("DEGRADED", "CRITICAL"):
                cross_signal_findings.append(
                    f"Operational Vulnerability Alignment: Depot '{r_rec.get('depot_name', d_id)}' shows both "
                    f"{d_status} mission readiness AND high operational risk, confirming severe operational stress."
                )
            elif depot_risks and d_status == "READY":
                conflicts.append(
                    f"Signal Conflict at Depot '{r_rec.get('depot_name', d_id)}': Item-level operational risk is elevated "
                    f"({depot_risks[0].get('risk_level')}), but overall depot mission readiness status remains marked 'READY'. "
                    f"Reasoning: Depot readiness accounts for multi-item stock buffer, while specific item inventory is stressed."
                )

        # Relationship D: Environment + Supply Movement
        if env and env.get("classification") in ("HIGH", "CRITICAL"):
            route_id = env.get("route_id")
            route_name = env.get("route_name", route_id)
            route_shipments = [s for s in active_shipments if s.get("route_id") == route_id]

            if route_shipments:
                cross_signal_findings.append(
                    f"Supply Movement Hazard: Inbound supply route '{route_name}' has {env.get('classification')} environmental risk "
                    f"AND {len(route_shipments)} active shipment(s) in transit, creating direct convoy delay exposure."
                )
            else:
                conflicts.append(
                    f"Signal Conflict on Route '{route_name}': Route environmental risk is {env.get('classification')}, "
                    f"but no active replenishment shipments are currently in transit on this route in the synthetic dataset."
                )

        # Relationship E: Environment + Inventory (Route risk with healthy inventory vs low inventory)
        if env and env.get("classification") in ("HIGH", "CRITICAL"):
            if not below_thresh_count and not high_critical_stockouts:
                conflicts.append(
                    f"Signal Conflict: Inbound supply route '{env.get('route_name')}' has {env.get('classification')} environmental risk, "
                    f"but current depot inventory remains healthy (above minimum thresholds). Immediate stock-out is not indicated; "
                    f"continued monitoring of supply movement is recommended."
                )

        # Relationship F: Low Inventory with Low Stockout Risk
        for item in ctx.inventory_items:
            item_id = item.get("id")
            qty = float(item.get("current_quantity") or 0.0)
            thresh = float(item.get("minimum_threshold") or 0.0)
            matching_so = next((s for s in ctx.stockout_predictions if s.get("inventory_item_id") == item_id), None)
            if matching_so:
                so_lvl = matching_so.get("risk_level", "LOW")
                if qty <= thresh and so_lvl == "LOW":
                    conflicts.append(
                        f"Signal Nuance for '{item.get('item_name')}': Quantity ({qty:.0f}) is near threshold ({thresh:.0f}), "
                        f"but stock-out risk is evaluated as LOW due to minimal historical daily consumption rate."
                    )

        # -------------------------------------------------------------------
        # Step 3: Prioritization & Confidence Assessment
        # -------------------------------------------------------------------
        priority: PRIORITY_VALUES = "LOW"

        # Scope filter lists if explicit depot or route scope was provided
        relevant_stockouts = [
            p for p in ctx.stockout_predictions
            if not ctx.depot_id or p.get("depot_id") == ctx.depot_id
        ] if not ctx.route_id else [
            p for p in ctx.stockout_predictions
            if ctx.depot_id and p.get("depot_id") == ctx.depot_id
        ]

        relevant_risks = [
            r for r in ctx.risk_assessments
            if not ctx.depot_id or r.get("depot_id") == ctx.depot_id
        ] if not ctx.route_id else [
            r for r in ctx.risk_assessments
            if ctx.depot_id and r.get("depot_id") == ctx.depot_id
        ]

        relevant_readiness = [
            r for r in ctx.readiness_assessments
            if not ctx.depot_id or r.get("depot_id") == ctx.depot_id
        ] if not ctx.route_id else [
            r for r in ctx.readiness_assessments
            if ctx.depot_id and r.get("depot_id") == ctx.depot_id
        ]

        # Evaluate Highest Risk/Urgency Level from scoped signals
        for pred in relevant_stockouts:
            r_lvl = pred.get("risk_level", "LOW")
            days = pred.get("days_until_stockout")
            if r_lvl == "CRITICAL" or (days is not None and days <= 1):
                priority = _max_priority(priority, "CRITICAL")
            elif r_lvl == "HIGH":
                priority = _max_priority(priority, "HIGH")

        for risk in relevant_risks:
            r_lvl = risk.get("risk_level", "LOW")
            priority = _max_priority(priority, r_lvl)

        for r_rec in relevant_readiness:
            status = r_rec.get("readiness_status", "READY")
            if status == "CRITICAL":
                priority = _max_priority(priority, "CRITICAL")
            elif status == "DEGRADED":
                priority = _max_priority(priority, "HIGH")
            elif status == "CAUTION":
                priority = _max_priority(priority, "MEDIUM")

        if env:
            e_class = env.get("classification", "LOW")
            route_shipments = [s for s in active_shipments if s.get("route_id") == env.get("route_id")]
            if ctx.route_id and not ctx.depot_id:
                # Scoped specifically to a route query without a depot: route hazard dictates priority
                if e_class == "CRITICAL":
                    priority = "CRITICAL"
                elif e_class == "HIGH":
                    priority = "HIGH"
                elif e_class == "MEDIUM":
                    priority = "MEDIUM"
                else:
                    priority = "LOW"
            else:
                if e_class == "CRITICAL":
                    priority = _max_priority(priority, "CRITICAL" if route_shipments else "HIGH")
                elif e_class == "HIGH":
                    priority = _max_priority(priority, "HIGH" if route_shipments else "MEDIUM")
                elif e_class == "MEDIUM":
                    priority = _max_priority(priority, "MEDIUM")

        # Deterministic Confidence Calculation (0–100)
        # Base confidence = 60
        confidence = 60

        # Signal completeness bonus: +5 per available module (up to 30)
        available_modules_count = sum(1 for v in ctx.modules_available.values() if v)
        confidence += min(30, available_modules_count * 5)

        # Specificity bonus: +10 if scoped to specific depot, base, or route
        if ctx.depot_id or ctx.base_id or ctx.route_id:
            confidence += 10

        # Multi-signal agreement bonus: +10
        if cross_signal_findings:
            confidence += 10

        # Penalty for signal conflicts: -10
        if conflicts:
            confidence -= 10

        # Penalty for missing errors or unmapped entities: -15
        if ctx.errors:
            confidence -= 15

        # Penalty if no evidence found at all (insufficient data): -25
        if not evidence:
            confidence -= 25

        confidence = max(0, min(100, confidence))

        # -------------------------------------------------------------------
        # Step 4: Natural-Language Synthesis & Recommendation Generation
        # -------------------------------------------------------------------
        reasoning_summary_parts: List[str] = []
        answer: str = ""
        recommendation: str = ""
        recommended_actions: List[str] = []

        # Insufficient Data Handling
        if not ctx.inventory_items and not ctx.risk_assessments and not ctx.readiness_assessments and not env:
            answer = "Available SENTINEL intelligence data is insufficient to evaluate logistics status for the requested scope."
            recommendation = "Verify scope parameters (depot_id, base_id, route_id) and ensure underlying service datasets are initialized."
            reasoning_summary = "Insufficient data available: No inventory, risk, readiness, or environmental signals could be retrieved."
            recommended_actions.append("Inspect API scope parameters and query syntax.")
            recommended_actions.append("Confirm target depot or route exists in the SENTINEL logistics registry.")
            limitations.append("Insufficient data retrieved for requested query parameters.")

            return {
                "answer": answer,
                "recommendation": recommendation,
                "priority": "LOW",
                "confidence": confidence,
                "reasoning_summary": reasoning_summary,
                "evidence": evidence,
                "recommended_actions": recommended_actions,
                "limitations": limitations,
                "supporting_factors": factors,
                "relevant_entities": entities,
                "knowledge_sources": knowledge_sources,
                "operational_sources": operational_sources,
            }

        # Concept-knowledge question handling (Phase 11E)
        if intent == "concept_knowledge" and ctx.kb_excerpts:
            top_kb = ctx.kb_excerpts[0]
            excerpt_text = top_kb.excerpt[:220].replace("\n", " ").strip()
            answer = f"According to SENTINEL Knowledge Base [{top_kb.article_id}] ({top_kb.title}): {excerpt_text}..."
            recommendation = f"Consult full SENTINEL KB article '{top_kb.title}' [{top_kb.article_id}] for complete operational methodology and threshold definitions."
            reasoning_summary = f"Retrieved static Knowledge Base article [{top_kb.article_id}] to answer concept inquiry for query '{ctx.query}'."
            if not (high_critical_stockouts or ctx.degraded_depots):
                priority = "LOW"
            confidence = max(confidence, 85)
        else:
            # Synthesize Answer & Recommendation based on signals
            if cross_signal_findings:
                reasoning_summary_parts.extend(cross_signal_findings)

        if conflicts:
            reasoning_summary_parts.extend(conflicts)

        # Build concise answer text if not already synthesized by concept knowledge handling
        if not answer:
            if priority in ("CRITICAL", "HIGH"):
                target_depot = (ctx.depot_record.get("name") if ctx.depot_record else None) or ctx.depot_id
                target_route = (env.get("route_name") if env else None) or ctx.route_id

                if target_depot and target_route:
                    answer = (
                        f"Depot '{target_depot}' requires urgent logistics attention. "
                        f"Supply route '{target_route}' faces {env.get('classification','HIGH')} environmental risk, "
                        f"while {below_thresh_count or len(high_critical_stockouts)} item(s) exhibit stock-out or threshold pressure."
                    )
                elif target_depot:
                    answer = (
                        f"Depot '{target_depot}' requires high-priority logistics attention. "
                        f"Current intelligence indicates {below_thresh_count or len(high_critical_stockouts)} item(s) "
                        f"under stock-out or threshold pressure."
                    )
                elif target_route:
                    answer = (
                        f"Supply route '{target_route}' requires active risk management due to "
                        f"{env.get('classification','HIGH')} environmental risk classification."
                    )
                else:
                    answer = (
                        f"SENTINEL intelligence identified {priority}-priority logistics pressure across "
                        f"{len(high_critical_stockouts) or below_thresh_count or len(ctx.degraded_depots)} critical focus area(s)."
                    )

                recommendation = (
                    f"Prioritise immediate replenishment for vulnerable inventory items and evaluate alternative "
                    f"transit options for high-risk supply routes. Review detailed evidence below before dispatching convoys."
                )
            elif priority == "MEDIUM":
                answer = (
                    "Logistics operations show moderate risk or emerging supply pressure. "
                    "Current stock levels are functional but require continued tracking."
                )
                recommendation = (
                    "Maintain active monitoring. Pre-position safety stock where supply route environmental risk "
                    "or consumption rates indicate potential future bottlenecks."
                )
            else:
                answer = (
                    "Logistics operations and supply routes are currently operating within nominal parameters. "
                    "No urgent operational intervention is required."
                )
                recommendation = "Continue routine logistics tracking and standard monitoring schedule."

        # Append conflict explanation to answer if conflicts exist
        if conflicts and priority != "CRITICAL":
            answer += " Note: Signal nuances exist (e.g. inventory levels vs. route risk alignment)."

        # Standard Recommended Actions (Decision Support Only — Human in the loop)
        if high_critical_stockouts or below_thresh_count:
            recommended_actions.append("Review replenishment schedule and expedite priority supply shipments.")
            recommended_actions.append("Monitor daily inventory consumption rates for items below threshold.")

        if env and env.get("classification") in ("HIGH", "CRITICAL"):
            recommended_actions.append(f"Inspect environmental hazard report for supply route '{env.get('route_name', env.get('route_id'))}'.")
            recommended_actions.append("Evaluate alternative convoy routes or pre-position supplies ahead of route deterioration.")

        if ctx.degraded_depots:
            recommended_actions.append("Review mission readiness metrics and address specific contributing signal gaps.")

        if active_shipments:
            recommended_actions.append("Track active replenishment shipments and verify expected arrival windows.")

        recommended_actions.append("Run a Digital Twin simulation to project multi-day scenario trajectory under disruptions.")

        # Reasoning Summary text
        if not reasoning_summary_parts:
            reasoning_summary = (
                f"Evaluated {len(evidence)} intelligence signal(s) across Inventory, Risk, Readiness, and Environment. "
                f"Overall status is evaluated as {priority} priority with {confidence}% decision-support confidence."
            )
        else:
            reasoning_summary = " ".join(reasoning_summary_parts)

        # Deduplicate entities
        seen_entities = set()
        unique_entities: List[RelevantEntity] = []
        for ent in entities:
            key = (ent.entity_type, ent.entity_id)
            if key not in seen_entities and ent.entity_id:
                seen_entities.add(key)
                unique_entities.append(ent)

        return {
            "answer": answer,
            "recommendation": recommendation,
            "priority": priority,
            "confidence": confidence,
            "reasoning_summary": reasoning_summary,
            "evidence": evidence,
            "recommended_actions": recommended_actions,
            "limitations": limitations,
            "supporting_factors": factors,
            "relevant_entities": unique_entities,
            "knowledge_sources": knowledge_sources,
            "operational_sources": operational_sources,
        }

    # -------------------------------------------------------------------
    # Phase 11G: Scenario Reasoning
    # -------------------------------------------------------------------

    @staticmethod
    def _evaluate_scenario(
        ctx: "AdvisorContext",
        sc: Dict[str, Any],
        knowledge_sources: List[str],
        operational_sources: List[str],
        limitations: List[str],
        evidence: List[EvidenceItem],
        factors: List[SupportingFactor],
        entities: List[RelevantEntity],
    ) -> Dict[str, Any]:
        """
        Phase 11G scenario-aware reasoning path.

        Consumes the Digital Twin simulation result (sc) verbatim.
        Does NOT recalculate risk, readiness, stock-out, inventory trajectories,
        environmental risk, or shipment delays. The DT result is authoritative.
        """
        recommended_actions: List[str] = []

        # --- Read DT values verbatim — no recalculation ---
        scenario_id   = sc.get("scenario_id", "")
        scenario_type = sc.get("scenario_type", "ROUTE_DISRUPTION")
        depot_id      = sc.get("affected_depot_id", "")
        depot_name    = sc.get("affected_depot_name", depot_id)
        base_name     = sc.get("base_name") or sc.get("base_id", "")

        baseline_risk        = float(sc.get("baseline_risk_score", 0.0))
        sim_risk             = float(sc.get("simulated_risk_score", 0.0))
        risk_delta           = float(sc.get("risk_score_delta", sim_risk - baseline_risk))
        baseline_risk_level  = sc.get("baseline_risk_level", "LOW")
        sim_risk_level       = sc.get("simulated_risk_level", "LOW")

        baseline_readiness        = float(sc.get("baseline_readiness_score", 0.0))
        sim_readiness             = float(sc.get("simulated_readiness_score", 0.0))
        readiness_delta           = float(sc.get("readiness_score_delta", sim_readiness - baseline_readiness))
        baseline_readiness_status = sc.get("baseline_readiness_status", "READY")
        sim_readiness_status      = sc.get("simulated_readiness_status", "READY")

        stockout_day         = sc.get("stockout_day")
        threshold_breach_day = sc.get("threshold_breach_day")
        min_sim_inv          = float(sc.get("minimum_simulated_inventory", 0.0))
        inv_shortfall        = float(sc.get("inventory_shortfall", 0.0))

        affected_shipments       = sc.get("affected_shipments", []) or []
        causal_chain             = sc.get("causal_chain", []) or []
        contributing_factors_raw = sc.get("contributing_factors", []) or []
        human_summary            = sc.get("human_summary") or sc.get("explanation", "")
        env_impact               = sc.get("environmental_impact")  # dict or None

        comparison = sc.get("comparison") or {}
        comp_stockout               = (comparison.get("stockout_occurrence") or {}) if comparison else {}
        baseline_stockout_occurred  = comp_stockout.get("baseline", False)
        scenario_stockout_occurred  = comp_stockout.get("scenario", False)

        # --- Evidence items from DT result (authoritative values only) ---
        evidence.append(EvidenceItem(
            source="digital_twin_simulation",
            observation="Scenario ID",
            value=scenario_id,
            interpretation=(
                f"Digital Twin '{scenario_type}' scenario for depot '{depot_name}'"
                + (f" (Base: {base_name})." if base_name else ".")
            )
        ))
        evidence.append(EvidenceItem(
            source="digital_twin_simulation",
            observation="Risk Score: Baseline -> Scenario",
            value=f"{baseline_risk:.1f} -> {sim_risk:.1f} (delta {risk_delta:+.1f})",
            interpretation=(
                f"Risk classification: {baseline_risk_level} -> {sim_risk_level}. "
                + ("Risk worsened under scenario conditions." if risk_delta > 0 else "Risk unchanged or improved.")
            )
        ))
        evidence.append(EvidenceItem(
            source="digital_twin_simulation",
            observation="Readiness Score: Baseline -> Scenario",
            value=f"{baseline_readiness:.1f} -> {sim_readiness:.1f} (delta {readiness_delta:+.1f})",
            interpretation=(
                f"Mission readiness: {baseline_readiness_status} -> {sim_readiness_status}. "
                + ("Readiness degraded under scenario conditions." if readiness_delta < 0 else "Readiness stable or improved.")
            )
        ))

        if stockout_day is not None:
            preexisting_note = (
                "This is a pre-existing condition in the baseline."
                if baseline_stockout_occurred
                else "This stock-out is induced by the scenario disruption."
            )
            evidence.append(EvidenceItem(
                source="digital_twin_simulation",
                observation="Projected Stock-out Day (Scenario)",
                value=f"Day {stockout_day}",
                interpretation=f"Stock-out projected on Day {stockout_day}. {preexisting_note}"
            ))

        if threshold_breach_day is not None:
            evidence.append(EvidenceItem(
                source="digital_twin_simulation",
                observation="Inventory Threshold Breach Day (Scenario)",
                value=f"Day {threshold_breach_day}",
                interpretation=f"Inventory falls below minimum threshold on Day {threshold_breach_day} under scenario."
            ))

        if inv_shortfall > 0:
            evidence.append(EvidenceItem(
                source="digital_twin_simulation",
                observation="Inventory Shortfall (Scenario)",
                value=f"{inv_shortfall:.0f} units below minimum threshold",
                interpretation=(
                    f"Minimum simulated inventory: {min_sim_inv:.0f} units, "
                    f"shortfall: {inv_shortfall:.0f} units."
                )
            ))

        if affected_shipments:
            delayed   = [s for s in affected_shipments if (s.get("delay_days") or 0) > 0]
            total_qty = sum(float(s.get("quantity", 0)) for s in affected_shipments)
            max_delay = max((s.get("delay_days") or 0) for s in affected_shipments)
            evidence.append(EvidenceItem(
                source="digital_twin_simulation",
                observation="Affected Shipments",
                value=f"{len(affected_shipments)} shipment(s), {len(delayed)} delayed, max {max_delay} day(s)",
                interpretation=(
                    f"Total cargo quantity affected: {total_qty:.0f} units; "
                    f"up to {max_delay}-day delay."
                )
            ))

        if env_impact and isinstance(env_impact, dict):
            env_score = float(env_impact.get("environmental_risk_score", 0.0))
            env_class = env_impact.get("classification", "LOW")
            env_delay = int(env_impact.get("environmental_delay_days", 0))
            env_route = env_impact.get("route_name") or env_impact.get("route_id", "")
            evidence.append(EvidenceItem(
                source="digital_twin_simulation",
                observation="Environmental Impact (Scenario Route)",
                value=f"{env_class} ({env_score:.1f}/100), +{env_delay} day(s) delay",
                interpretation=(
                    f"Route '{env_route}' has {env_class} environmental risk contributing "
                    f"to {env_delay} additional day(s) of movement delay."
                )
            ))
            entities.append(RelevantEntity(
                entity_type="route",
                entity_id=env_impact.get("route_id", env_route),
                entity_name=env_route
            ))

        # Contributing factors from DT result (not invented)
        for cf in contributing_factors_raw:
            if isinstance(cf, dict):
                cf_factor = cf.get("factor", "")
                cf_desc   = cf.get("description", "")
                cf_sev    = cf.get("severity", "") or None
            else:
                cf_factor = str(cf)
                cf_desc   = ""
                cf_sev    = None
            factors.append(SupportingFactor(
                factor=f"DT_CONTRIBUTING_FACTOR: {cf_factor}",
                detail=cf_desc or cf_factor,
                value=cf_sev
            ))

        # Affected depot entity
        entities.append(RelevantEntity(
            entity_type="depot",
            entity_id=depot_id,
            entity_name=depot_name
        ))

        # --- Priority from DT sim classification (no recalculation) ---
        priority: PRIORITY_VALUES = "LOW"
        if sim_risk_level == "CRITICAL" or sim_readiness_status == "CRITICAL":
            priority = "CRITICAL"
        elif sim_risk_level == "HIGH" or sim_readiness_status == "DEGRADED":
            priority = "HIGH"
        elif sim_risk_level == "MEDIUM" or sim_readiness_status == "CAUTION":
            priority = "MEDIUM"

        # --- Confidence ---
        confidence = 85
        if ctx.kb_excerpts:
            confidence = min(100, confidence + 5)
        if not causal_chain:
            confidence = max(0, confidence - 10)

        # --- Causal narrative (from DT, not invented) ---
        if causal_chain:
            causal_narrative = " -> ".join(causal_chain)
        else:
            causal_narrative = (
                "Causal chain detail is unavailable for this scenario. "
                "Impact values are taken from the authoritative simulation output."
            )

        # --- Stock-out: pre-existing vs scenario-induced ---
        if scenario_stockout_occurred and baseline_stockout_occurred:
            stockout_note = (
                "Stock-out was already present in the baseline before the scenario. "
                "The scenario may have accelerated or worsened this pre-existing condition."
            )
        elif scenario_stockout_occurred and not baseline_stockout_occurred:
            stockout_note = (
                f"Stock-out on Day {stockout_day} is scenario-induced "
                "(not present in the baseline)."
            )
        else:
            stockout_note = "No stock-out occurred under this scenario."

        # --- Answer synthesis ---
        answer_parts: List[str] = []
        if human_summary:
            answer_parts.append(human_summary)
        else:
            answer_parts.append(
                f"Digital Twin scenario '{scenario_id}' ({scenario_type}) affects depot '{depot_name}'. "
                f"Risk: {baseline_risk:.1f} -> {sim_risk:.1f} ({baseline_risk_level} -> {sim_risk_level}). "
                f"Readiness: {baseline_readiness:.1f} -> {sim_readiness:.1f} "
                f"({baseline_readiness_status} -> {sim_readiness_status})."
            )
        if causal_chain:
            answer_parts.append(f"Causal chain: {causal_narrative}.")
        answer_parts.append(stockout_note)
        if env_impact and isinstance(env_impact, dict):
            e_class = env_impact.get("classification", "LOW")
            e_route = env_impact.get("route_name") or env_impact.get("route_id", "")
            e_delay = int(env_impact.get("environmental_delay_days", 0))
            answer_parts.append(
                f"Environmental impact on route '{e_route}': {e_class} risk, +{e_delay} day(s) delay."
            )
        answer = " ".join(answer_parts)

        # KB explanatory grounding (Channel B — does not override DT values)
        if ctx.kb_excerpts:
            top_kb = ctx.kb_excerpts[0]
            answer += (
                f" [SENTINEL KB: {top_kb.title} ({top_kb.article_id}) provides "
                f"methodology context for this classification.]"
            )

        # --- Recommendation ---
        rec_parts = [f"Review the Digital Twin scenario '{scenario_id}' impact on depot '{depot_name}'."]
        if affected_shipments:
            rec_parts.append(f"Verify revised arrival schedules for {len(affected_shipments)} affected shipment(s).")
        if inv_shortfall > 0:
            rec_parts.append(f"Address inventory shortfall of {inv_shortfall:.0f} units via replenishment planning.")
        if readiness_delta < -5:
            rec_parts.append("Examine readiness restoration options.")
        if risk_delta > 0:
            rec_parts.append(f"Mitigate {sim_risk_level}-level risk conditions.")
        recommendation = " ".join(rec_parts)

        # --- Recommended actions (decision-support only) ---
        if affected_shipments:
            recommended_actions.append(
                f"Review {len(affected_shipments)} affected shipment(s) and verify revised arrival schedules."
            )
        if inv_shortfall > 0:
            recommended_actions.append(
                f"Inspect inventory replenishment plan for depot '{depot_name}' — "
                f"shortfall of {inv_shortfall:.0f} units projected."
            )
        if readiness_delta < -5:
            recommended_actions.append(
                f"Examine readiness degradation ({baseline_readiness:.1f} -> {sim_readiness:.1f}) "
                "and identify contributing signal gaps."
            )
        if risk_delta > 0:
            recommended_actions.append(
                f"Evaluate risk escalation ({baseline_risk_level} -> {sim_risk_level}) and "
                "consider route alternatives or pre-positioned supply."
            )
        if env_impact and isinstance(env_impact, dict) and env_impact.get("classification") in ("HIGH", "CRITICAL"):
            e_route = env_impact.get("route_name") or env_impact.get("route_id", "")
            recommended_actions.append(
                f"Review environmental hazard report for route '{e_route}' and assess convoy exposure."
            )
        if causal_chain:
            recommended_actions.append(
                "Trace the causal chain in the Digital Twin result to identify the primary disruption trigger."
            )
        if not recommended_actions:
            recommended_actions.append(
                "Review full Digital Twin scenario result and compare baseline vs scenario metrics."
            )
        recommended_actions.append(
            "All recommended actions are decision-support only. "
            "Human operator review is required before any operational change."
        )

        # --- Reasoning summary ---
        reasoning_summary = (
            f"Phase 11G Scenario Analysis: Digital Twin result for scenario '{scenario_id}' "
            f"at depot '{depot_name}'. Risk delta: {risk_delta:+.1f}. "
            f"Readiness delta: {readiness_delta:+.1f}. "
            f"{len(affected_shipments)} affected shipment(s). "
            + ("Causal chain: " + causal_narrative if causal_chain else "Causal chain unavailable.")
        )

        limitations.append(
            "Phase 11G: Scenario values are taken verbatim from the Digital Twin simulation result. "
            "No recalculation of risk, readiness, stock-out, or environmental values is performed by the Advisor."
        )
        limitations.append(
            "Phase 11G: Scenario simulation uses synthetic demonstration data only. "
            "No real operational state is represented."
        )

        # Deduplicate entities
        seen_ents: set = set()
        unique_entities: List[RelevantEntity] = []
        for ent in entities:
            key = (ent.entity_type, ent.entity_id)
            if key not in seen_ents and ent.entity_id:
                seen_ents.add(key)
                unique_entities.append(ent)

        return {
            "answer": answer,
            "recommendation": recommendation,
            "priority": priority,
            "confidence": confidence,
            "reasoning_summary": reasoning_summary,
            "evidence": evidence,
            "recommended_actions": recommended_actions,
            "limitations": limitations,
            "supporting_factors": factors,
            "relevant_entities": unique_entities,
            "knowledge_sources": knowledge_sources,
            "operational_sources": operational_sources,
        }
