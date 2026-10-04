"""
SENTINEL LOGIX AI - Deterministic Mock LLM Provider
Phase 11C: LLM Provider Abstraction & Grounded Advisor

Deterministic Mock Provider for development, automated testing, and CI/CD environments.
Requires no network access and no API key.
"""

from typing import Dict, Any, Optional
from .base import BaseLLMProvider
from ..context import AdvisorContext


class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM Provider that synthesizes grounded advisory responses from structured context.
    Supports test behaviors for verifying validation failure & deterministic fallback logic.
    """

    def __init__(self, behavior: str = "normal"):
        """
        behavior modes:
          - 'normal': returns valid grounded response with provider_mode='mock'
          - 'knowledge_grounded': returns concept-grounded response using KB articles
          - 'operational_plus_knowledge': returns mixed response combining live values & KB methodology
          - 'unsupported_kb_source': introduces an unretrieved KB article ID 'kb-fake-unsupported-999'
          - 'unsupported_operational_entity': introduces an unsupported entity ID 'DEPOT-FAKE-HALLUCINATED-999'
          - 'malformed_priority': returns invalid priority value (e.g. 'EXTREME_INVALID')
          - 'malformed_confidence': returns out-of-bounds confidence (e.g. 250)
          - 'missing_field': omits required 'answer' field
          - 'provider_failure': raises RuntimeError simulating provider connectivity/network failure
          - 'scenario_grounded': Phase 11G — returns scenario-aware response using DT result values
          - 'scenario_fabricated_entity': Phase 11G — introduces fabricated entity to test hallucination guard
        """
        self.behavior = behavior


    @property
    def provider_name(self) -> str:
        return "mock"

    def generate(
        self,
        context: AdvisorContext,
        deterministic_result: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """Generates mock response dictionary."""
        # Simulated Provider Failure
        if self.behavior == "provider_failure":
            raise RuntimeError("Simulated LLM Provider network / API failure")

        # Simulated Malformed behaviors for test coverage
        if self.behavior == "malformed_priority":
            bad = dict(deterministic_result)
            bad["priority"] = "EXTREME_INVALID"
            bad["provider_mode"] = "mock"
            return bad

        if self.behavior == "malformed_confidence":
            bad = dict(deterministic_result)
            bad["confidence"] = 250
            bad["provider_mode"] = "mock"
            return bad

        if self.behavior == "missing_field":
            bad = dict(deterministic_result)
            bad.pop("answer", None)
            bad["provider_mode"] = "mock"
            return bad

        if self.behavior == "unsupported_operational_entity" or self.behavior == "hallucinated_entity":
            bad = dict(deterministic_result)
            bad_entities = list(bad.get("relevant_entities", []))
            bad_entities.append({
                "entity_type": "depot",
                "entity_id": "DEPOT-FAKE-HALLUCINATED-999",
                "entity_name": "Non-existent Hallucinated Depot"
            })
            bad["relevant_entities"] = bad_entities
            bad["provider_mode"] = "mock"
            return bad

        if self.behavior == "unsupported_kb_source":
            bad = dict(deterministic_result)
            bad["knowledge_sources"] = ["kb-fake-unsupported-999"]
            bad["provider_mode"] = "mock"
            return bad

        # Derive knowledge and operational sources
        kb_sources = [kb.article_id for kb in context.kb_excerpts]
        op_sources = list(deterministic_result.get("operational_sources", []))

        # Phase 11G: Scenario-grounded mock behavior
        if self.behavior == "scenario_grounded" and context.scenario_result:
            sc = context.scenario_result
            answer_text = (
                f"[Mock LLM Scenario Analysis] Digital Twin scenario '{sc.get('scenario_id')}' "
                f"for depot '{sc.get('affected_depot_name')}': "
                f"Risk {sc.get('baseline_risk_score'):.1f} -> {sc.get('simulated_risk_score'):.1f}, "
                f"Readiness {sc.get('baseline_readiness_score'):.1f} -> {sc.get('simulated_readiness_score'):.1f}. "
                f"Values taken from authoritative Digital Twin result."
            )
            return {
                "query": query,
                "answer": answer_text,
                "recommendation": f"[Mock LLM] {deterministic_result.get('recommendation', '')}",
                "priority": deterministic_result.get("priority", "HIGH"),
                "confidence": deterministic_result.get("confidence", 85),
                "reasoning_summary": f"[Mock LLM Scenario] {deterministic_result.get('reasoning_summary', '')}",
                "evidence": deterministic_result.get("evidence", []),
                "recommended_actions": deterministic_result.get("recommended_actions", []),
                "limitations": deterministic_result.get("limitations", []),
                "supporting_factors": deterministic_result.get("supporting_factors", []),
                "relevant_entities": deterministic_result.get("relevant_entities", []),
                "knowledge_sources": kb_sources,
                "operational_sources": op_sources,
                "provider_mode": "mock",
                "data_source": "synthetic_demo",
                "environment": "demo",
            }

        if self.behavior == "scenario_fabricated_entity":
            bad = dict(deterministic_result)
            bad_entities = list(bad.get("relevant_entities", []))
            bad_entities.append({
                "entity_type": "depot",
                "entity_id": "DEPOT-FAKE-SCENARIO-HALLUCINATED-999",
                "entity_name": "Non-existent Hallucinated Scenario Depot"
            })
            bad["relevant_entities"] = bad_entities
            bad["provider_mode"] = "mock"
            return bad

        # Specialized grounded behavior modes
        if self.behavior == "knowledge_grounded":
            top_kb_title = context.kb_excerpts[0].title if context.kb_excerpts else "SENTINEL Methodology"
            answer_text = (
                f"[Mock LLM Grounded Explanation] Query '{query}' is explained by SENTINEL KB article '{top_kb_title}'. "
                f"Static knowledge provides methodology while live measurements are evaluated separately."
            )
        elif self.behavior == "operational_plus_knowledge":
            top_kb_title = context.kb_excerpts[0].title if context.kb_excerpts else "SENTINEL Risk System"
            answer_text = (
                f"[Mock LLM Hybrid Analysis] Live system measurements indicate elevated risk. "
                f"According to SENTINEL KB '{top_kb_title}', this classification reflects critical threshold pressure."
            )
        else:
            answer_text = f"[Mock LLM Analysis] {deterministic_result.get('answer', '')}"

        recommendation_text = f"[Mock LLM Recommendation] {deterministic_result.get('recommendation', '')}"
        reasoning = (
            f"[Mock LLM Reasoning Engine] Grounded analysis completed for query '{query}'. "
            f"{deterministic_result.get('reasoning_summary', '')}"
        )

        return {
            "query": query,
            "answer": answer_text,
            "recommendation": recommendation_text,
            "priority": deterministic_result.get("priority", "LOW"),
            "confidence": deterministic_result.get("confidence", 80),
            "reasoning_summary": reasoning,
            "evidence": deterministic_result.get("evidence", []),
            "recommended_actions": deterministic_result.get("recommended_actions", []),
            "limitations": deterministic_result.get("limitations", []),
            "supporting_factors": deterministic_result.get("supporting_factors", []),
            "relevant_entities": deterministic_result.get("relevant_entities", []),
            "knowledge_sources": kb_sources,
            "operational_sources": op_sources,
            "provider_mode": "mock",
            "data_source": "synthetic_demo",
            "environment": "demo",
        }

