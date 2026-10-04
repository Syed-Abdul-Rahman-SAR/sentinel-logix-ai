"""
SENTINEL LOGIX AI - AI Logistics Advisor Service Layer
Phase 11C: LLM Provider Abstraction & Grounded Advisor

Orchestrates context retrieval, intent classification, multi-signal reasoning
(via AdvisorReasoningEngine), optional LLM Provider execution, Response Validation,
and structured response synthesis with safe deterministic fallback.

Public interface AdvisorService.query() is strictly maintained for API contract compatibility.
"""

from __future__ import annotations

import re
import logging
from typing import List, Optional, Dict, Any

from .schemas import (
    AdvisorRequest,
    AdvisorResponse,
    SupportingFactor,
    RelevantEntity,
    EvidenceItem,
)
from .context import AdvisorContext, AdvisorContextBuilder
from .reasoning import AdvisorReasoningEngine, _max_priority
from .llm import get_llm_provider, BaseLLMProvider, AdvisorResponseValidator

logger = logging.getLogger("sentinel.advisor.service")


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

_INTENT_PATTERNS = [
    ("concept_knowledge",    r"what is|what does|what do|how is|how does|meaning|explain|concept|methodology|threshold|mean\?"),
    ("scenario_explanation", r"scenario|digital.?twin|what.?happen|what.?if|disrupt|why.?did|readiness.?fall|inventory.?fall|stock.?out|shipment.?affect|risk.?increas|explain.?impact|causal|contributing|baseline|compare"),
    ("route_disruption",     r"disrupt|what.?if|simulate"),
    ("route_environment",    r"route|environmental|weather|terrain|condition"),
    ("inventory_risk",       r"inventory|stock.?out|item.?at.?risk|risk.?item"),
    ("readiness",            r"read(y|iness)|mission.?ready|operationally"),
    ("risk_cause",           r"caus(e|ing)|why|reason"),
    ("depot_attention",      r"depot|attention|focus|priorit|check.?first|what.?should"),
]

def _detect_intent(query: str) -> str:
    """Returns the best-matching intent key, or 'general' as fallback."""
    lower = query.lower()
    for intent, pattern in _INTENT_PATTERNS:
        if re.search(pattern, lower):
            return intent
    return "general"


# ---------------------------------------------------------------------------
# Public Service Layer
# ---------------------------------------------------------------------------

class AdvisorService:
    """
    Context-aware AI Logistics Advisor Service (Phase 11C).

    Combines AdvisorContextBuilder, AdvisorReasoningEngine, optional LLM Providers,
    and AdvisorResponseValidator for grounded, safe advisory responses.
    """

    @staticmethod
    def query(
        request: AdvisorRequest,
        db_path: Optional[str] = None,
        provider: Optional[BaseLLMProvider] = None
    ) -> AdvisorResponse:
        """
        Entry point:
          1. Build AdvisorContext from existing SENTINEL service modules.
          2. Classify intent.
          3. Perform multi-signal reasoning via AdvisorReasoningEngine.
          4. Resolve LLM provider (environment or explicit argument).
          5. If LLM provider active: generate candidate response & validate schema/entities.
          6. If provider fails or validation fails: fall back safely to deterministic reasoning.
          7. Return complete AdvisorResponse matching Phase 11A/11B/11C schema contract.
        """
        # Step 1: Build context from existing SENTINEL service layers
        ctx = AdvisorContextBuilder.build(
            query=request.query,
            depot_id=request.depot_id,
            base_id=request.base_id,
            route_id=request.route_id,
            scenario_id=getattr(request, "scenario_id", None),
            db_path=db_path,
        )

        # Step 2: Detect query intent
        intent = _detect_intent(request.query)

        # Phase 11G: If a scenario was resolved, always use scenario_explanation intent.
        # This prevents concept_knowledge (which matches "explain") from intercepting
        # scenario-bearing queries before the scenario reasoning branch can fire.
        if ctx.scenario_result is not None:
            intent = "scenario_explanation"

        # Step 3: Run Multi-Signal Reasoning Engine (Deterministic Baseline)
        deterministic_result = AdvisorReasoningEngine.evaluate(ctx, intent)

        # Ensure requested route_id or depot_id is present in entities if resolved
        all_entities: List[RelevantEntity] = list(deterministic_result["relevant_entities"])
        if request.route_id and not any(e.entity_id == request.route_id for e in all_entities):
            all_entities.append(RelevantEntity(
                entity_type="route",
                entity_id=request.route_id,
                entity_name=ctx.environmental_risk.get("route_name", request.route_id) if ctx.environmental_risk else request.route_id
            ))

        if request.depot_id and not any(e.entity_id == request.depot_id for e in all_entities):
            depot_name = ctx.depot_record.get("name", request.depot_id) if ctx.depot_record else request.depot_id
            all_entities.append(RelevantEntity(
                entity_type="depot",
                entity_id=request.depot_id,
                entity_name=depot_name
            ))

        deterministic_result["relevant_entities"] = all_entities
        deterministic_result["query"] = request.query
        deterministic_result["provider_mode"] = "deterministic"

        # Phase 11D: Attach KB article titles retrieved for this query
        deterministic_result["kb_context"] = [
            f"{r.title} [{r.article_id}]"
            for r in ctx.kb_excerpts
        ]

        # Step 4: Resolve Active LLM Provider (if unconfigured, returns None -> deterministic mode)
        active_provider = provider or get_llm_provider()

        if active_provider is None:
            # Deterministic Fallback Mode
            return AdvisorResponse(**deterministic_result)

        # Step 5: LLM Provider Execution & Response Validation
        try:
            raw_output = active_provider.generate(ctx, deterministic_result, request.query)
            is_valid, error_reason, cleaned_dict = AdvisorResponseValidator.validate(raw_output, ctx)

            if is_valid and cleaned_dict:
                cleaned_dict["provider_mode"] = active_provider.provider_name
                return AdvisorResponse(**cleaned_dict)
            else:
                logger.warning(
                    f"LLM Provider '{active_provider.provider_name}' generated invalid output: {error_reason}. "
                    f"Falling back safely to deterministic reasoning."
                )
                fallback_dict = dict(deterministic_result)
                fallback_dict["provider_mode"] = "deterministic"
                fallback_dict["limitations"] = list(fallback_dict.get("limitations", [])) + [
                    f"LLM Provider '{active_provider.provider_name}' output failed validation ({error_reason}); fell back to deterministic reasoning."
                ]
                return AdvisorResponse(**fallback_dict)

        except Exception as exc:
            logger.error(
                f"LLM Provider '{active_provider.provider_name}' raised an unhandled error: {exc}. "
                f"Falling back safely to deterministic reasoning."
            )
            fallback_dict = dict(deterministic_result)
            fallback_dict["provider_mode"] = "deterministic"
            fallback_dict["limitations"] = list(fallback_dict.get("limitations", [])) + [
                f"LLM Provider error ({exc}); fell back to deterministic reasoning."
            ]
            return AdvisorResponse(**fallback_dict)
