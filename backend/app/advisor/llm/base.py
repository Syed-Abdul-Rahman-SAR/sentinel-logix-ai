"""
SENTINEL LOGIX AI - Abstract LLM Provider Interface & Grounding Prompt Builder
Phase 11C: LLM Provider Abstraction & Grounded Advisor

Defines the provider-agnostic interface BaseLLMProvider.
Constructs compact, grounded system prompts containing only verified SENTINEL intelligence data.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from ..context import AdvisorContext


class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM Providers.
    All implementations must return a dictionary compatible with AdvisorResponse.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the provider name tag (e.g. 'mock', 'openai', 'gemini')."""
        pass

    @abstractmethod
    def generate(
        self,
        context: AdvisorContext,
        deterministic_result: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """
        Generate a structured advisory response from the supplied context.
        Must return a dict representation matching AdvisorResponse schema.
        """
        pass

    def build_grounding_prompt(self, context: AdvisorContext, query: str) -> str:
        """
        Constructs a compact structured context string containing ONLY verified SENTINEL data,
        explicitly separated into:
          - Channel A: CURRENT OPERATIONAL CONTEXT (Authoritative for live values)
          - Channel B: STATIC KNOWLEDGE (Explanatory methodology & terminology)
        """
        prompt_parts = [
            "SYSTEM INSTRUCTIONS & GROUNDING CONSTRAINTS:",
            "- System: SENTINEL LOGIX AI Logistics Advisor.",
            "- Provenance Tag: data_source='synthetic_demo', environment='demo'.",
            "- GROUNDING CONSTRAINTS:",
            "  1. Operational context is the authoritative source for current system state.",
            "  2. Knowledge articles explain concepts and methodology but are not current measurements.",
            "  3. If operational context and knowledge text appear inconsistent, use operational context for current values and acknowledge the limitation.",
            "  4. Never invent information that does not exist in either source.",
            "  5. Do not infer unavailable operational facts.",
            "  6. Recommendations are decision support for human review; do not claim autonomous action execution.",
            "  7. Return a valid JSON response matching the required AdvisorResponse schema format.",
            "",
            f"USER QUERY: \"{query}\"",
            "",
            "CHANNEL A — CURRENT OPERATIONAL CONTEXT (Authoritative Live System Measurements):"
        ]

        # Inventory Context
        if context.inventory_items:
            prompt_parts.append(f"- Inventory Items Tracked: {len(context.inventory_items)}")
            for item in context.inventory_items[:5]:
                prompt_parts.append(
                    f"  * {item.get('id')}: {item.get('item_name')} = {item.get('current_quantity')} "
                    f"(Min Threshold: {item.get('minimum_threshold')})"
                )

        # Stockout Predictions
        if context.stockout_predictions:
            prompt_parts.append("- Stock-out Predictions:")
            for p in context.stockout_predictions[:5]:
                prompt_parts.append(
                    f"  * Item {p.get('inventory_item_id')} at Depot {p.get('depot_id')}: "
                    f"Risk={p.get('risk_level')}, DaysUntilStockout={p.get('days_until_stockout')}"
                )

        # Operational Risk
        if context.risk_assessments:
            prompt_parts.append("- Operational Risk Assessments:")
            for r in context.risk_assessments[:5]:
                prompt_parts.append(
                    f"  * Depot {r.get('depot_id')}, Item {r.get('inventory_item_id')}: "
                    f"Score={r.get('risk_score')}, RiskLevel={r.get('risk_level')}"
                )

        # Mission Readiness
        if context.readiness_assessments:
            prompt_parts.append("- Mission Readiness Assessments:")
            for rd in context.readiness_assessments[:5]:
                prompt_parts.append(
                    f"  * Depot {rd.get('depot_id')}: Status={rd.get('readiness_status')}, Score={rd.get('readiness_score')}"
                )

        # Environmental Risk
        if context.environmental_risk:
            env = context.environmental_risk
            prompt_parts.append(
                f"- Route Environmental Risk ({env.get('route_id')}): "
                f"Classification={env.get('classification')}, RiskScore={env.get('environmental_risk_score')}, "
                f"WeatherScore={env.get('weather_risk_score')}, TerrainScore={env.get('terrain_risk_score')}"
            )

        # Active Shipments
        if context.shipments:
            prompt_parts.append(f"- Active Replenishment Shipments: {len(context.shipments)}")
            for s in context.shipments[:3]:
                prompt_parts.append(
                    f"  * Shipment {s.get('shipment_id')} ({s.get('route_id')}): Status={s.get('status')}"
                )

        # Phase 11G: Digital Twin Scenario Context
        if context.scenario_result:
            sc = context.scenario_result
            prompt_parts.append(f"- Digital Twin Scenario ID: {sc.get('scenario_id')}")
            prompt_parts.append(f"  Scenario Type: {sc.get('scenario_type')}")
            prompt_parts.append(f"  Affected Depot: {sc.get('affected_depot_name')} ({sc.get('affected_depot_id')})")
            prompt_parts.append(
                f"  Baseline Risk: {sc.get('baseline_risk_score'):.1f} ({sc.get('baseline_risk_level')}) "
                f"-> Scenario Risk: {sc.get('simulated_risk_score'):.1f} ({sc.get('simulated_risk_level')})"
            )
            prompt_parts.append(
                f"  Baseline Readiness: {sc.get('baseline_readiness_score'):.1f} ({sc.get('baseline_readiness_status')}) "
                f"-> Scenario Readiness: {sc.get('simulated_readiness_score'):.1f} ({sc.get('simulated_readiness_status')})"
            )
            if sc.get("stockout_day") is not None:
                prompt_parts.append(f"  Stockout Day (Scenario): Day {sc.get('stockout_day')}")
            prompt_parts.append(f"  Inventory Shortfall: {sc.get('inventory_shortfall', 0):.0f} units")
            prompt_parts.append(f"  Affected Shipments: {len(sc.get('affected_shipments', []))}")
            if sc.get("causal_chain"):
                prompt_parts.append(f"  Causal Chain: {' -> '.join(sc.get('causal_chain', []))}")
            if sc.get("human_summary"):
                prompt_parts.append(f"  Human Summary: {sc.get('human_summary')}")
            prompt_parts.append(
                "  [CONSTRAINT: Use these scenario values verbatim. Do NOT recalculate or invent scenario metrics.]"
            )

        if context.errors:
            prompt_parts.append(f"- Operational Context Retrieval Errors/Limitations: {context.errors}")

        # Channel B: Static Knowledge Base Context
        if context.kb_excerpts:
            prompt_parts.append("")
            prompt_parts.append("CHANNEL B — STATIC SENTINEL KNOWLEDGE BASE ARTICLES (Retrieved for Explanations/Methodology, NOT Current Measurements):")
            for kb in context.kb_excerpts:
                prompt_parts.append(f"  [{kb.article_id}] {kb.title} (relevance={kb.relevance})")
                if kb.excerpt:
                    excerpt_preview = kb.excerpt[:300].replace("\n", " ").strip()
                    prompt_parts.append(f"    Excerpt: {excerpt_preview}...")


        return "\n".join(prompt_parts)

