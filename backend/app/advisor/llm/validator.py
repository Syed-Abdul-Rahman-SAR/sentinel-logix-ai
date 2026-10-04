"""
SENTINEL LOGIX AI - LLM Response Validation & Hallucination Safety Layer
Phase 11C: LLM Provider Abstraction & Grounded Advisor

Strictly validates LLM provider output against schema contracts and guards against hallucinated entities.
If validation fails, signals the system to fall back safely to deterministic reasoning.
"""

from typing import Dict, Any, Tuple, Optional, Set
from ..schemas import AdvisorResponse, PRIORITY_VALUES
from ..context import AdvisorContext


class AdvisorResponseValidator:
    """
    Validates candidate LLM outputs for schema compliance, value bounds,
    provenance preservation, and entity grounding safety.
    """

    @staticmethod
    def extract_known_entity_ids(context: AdvisorContext) -> Set[str]:
        """Collects all verified entity IDs present in the supplied AdvisorContext."""
        known: Set[str] = set()

        if context.depot_id:
            known.add(context.depot_id)
        if context.base_id:
            known.add(context.base_id)
        if context.route_id:
            known.add(context.route_id)

        for d in context.all_depots:
            if d.get("id"):
                known.add(d["id"])
        for b in context.all_bases:
            if b.get("id"):
                known.add(b["id"])
        for i in context.inventory_items:
            if i.get("id"):
                known.add(i["id"])
        for rid in context.known_route_ids:
            known.add(rid)
        for s in context.shipments:
            if s.get("shipment_id"):
                known.add(s["shipment_id"])

        return known

    @classmethod
    def validate(
        cls,
        candidate_data: Dict[str, Any],
        context: AdvisorContext
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validates candidate dictionary from LLM provider.

        Returns:
            (is_valid, error_reason, cleaned_data_dict)
        """
        if not isinstance(candidate_data, dict):
            return False, "Candidate output is not a dictionary", None

        # 1. Check required non-empty string fields
        for req_field in ("query", "answer", "recommendation"):
            val = candidate_data.get(req_field)
            if not val or not isinstance(val, str) or not val.strip():
                return False, f"Missing or invalid required field '{req_field}'", None

        # 2. Check Priority values
        priority = candidate_data.get("priority")
        if priority not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            return False, f"Invalid priority value '{priority}'", None

        # 3. Check Confidence bounds (0..100)
        confidence = candidate_data.get("confidence")
        if not isinstance(confidence, (int, float)) or not (0 <= int(confidence) <= 100):
            return False, f"Confidence '{confidence}' is out of bounds (0-100)", None

        candidate_data["confidence"] = int(confidence)

        # 4. Check Provenance tags
        data_source = candidate_data.get("data_source", "synthetic_demo")
        environment = candidate_data.get("environment", "demo")
        if data_source != "synthetic_demo" or environment != "demo":
            return False, f"Invalid provenance tags data_source='{data_source}', environment='{environment}'", None

        # 5. Hallucination Safety Check: Entity Grounding Verification
        known_entities = cls.extract_known_entity_ids(context)
        relevant_entities = candidate_data.get("relevant_entities", [])

        if isinstance(relevant_entities, list):
            for ent in relevant_entities:
                if isinstance(ent, dict):
                    ent_id = ent.get("entity_id")
                    # If entity_id is provided and not in known context entities, reject as hallucination
                    if ent_id and ent_id not in known_entities:
                        return False, f"Hallucinated entity detected: entity_id '{ent_id}' not present in context", None

        # 5.5 Knowledge Source Verification (Phase 11E)
        # The LLM response must not claim that an article was consulted unless that article was actually retrieved.
        retrieved_kb_ids: Set[str] = {kb.article_id for kb in context.kb_excerpts}
        candidate_kb_sources = candidate_data.get("knowledge_sources", [])
        if isinstance(candidate_kb_sources, list):
            for kb_id in candidate_kb_sources:
                if isinstance(kb_id, str) and kb_id not in retrieved_kb_ids:
                    return False, f"Unsupported knowledge source ID detected: '{kb_id}' not in retrieved context articles", None

        # 6. Pydantic schema validation check
        try:
            # Clean/instantiate AdvisorResponse to confirm strict Pydantic compliance
            resp_obj = AdvisorResponse(**candidate_data)
            cleaned_dict = resp_obj.model_dump()
            return True, None, cleaned_dict
        except Exception as exc:
            return False, f"Pydantic schema validation error: {exc}", None

