"""
SENTINEL LOGIX AI - AI Advisor Request/Response Schemas
Phase 11A: AI Logistics Advisor Backend Foundation

All schema types are deterministic. No external LLM / AI inference is used in this phase.
Every response is derived from existing SENTINEL intelligence service outputs.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Priority & Confidence bounds
# ---------------------------------------------------------------------------

PRIORITY_VALUES = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# ---------------------------------------------------------------------------
# Request Schema
# ---------------------------------------------------------------------------

class AdvisorRequest(BaseModel):
    """Incoming logistics advisory query."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural-language logistics query or question.",
        examples=["Which depot needs attention?"]
    )
    depot_id: Optional[str] = Field(
        None,
        description="Optional depot ID to scope the advisory context."
    )
    base_id: Optional[str] = Field(
        None,
        description="Optional base ID to scope the advisory context."
    )
    route_id: Optional[str] = Field(
        None,
        description="Optional synthetic route ID (e.g. 'SIL-IMP') to scope environmental context."
    )
    scenario_id: Optional[str] = Field(
        None,
        description=(
            "Phase 11G: Optional Digital Twin scenario ID to scope the advisory to a specific "
            "simulation result. If supplied, the Advisor will explain scenario impacts using the "
            "existing Digital Twin result. Clients that omit this field continue to work unchanged."
        )
    )


# ---------------------------------------------------------------------------
# Supporting / Contextual sub-models
# ---------------------------------------------------------------------------

class SupportingFactor(BaseModel):
    """A single explainable supporting factor for a recommendation."""
    factor: str = Field(..., description="Short label/key for the factor.")
    detail: str = Field(..., description="Human-readable explanation of the factor.")
    value: Optional[str] = Field(None, description="Numeric or categorical value, if applicable.")


class RelevantEntity(BaseModel):
    """Reference to a logistics entity mentioned in the advisory response."""
    entity_type: str = Field(..., description="Type of entity, e.g. 'depot', 'inventory_item', 'route'.")
    entity_id: str = Field(..., description="Identifier of the entity.")
    entity_name: Optional[str] = Field(None, description="Human-readable name of the entity.")


class EvidenceItem(BaseModel):
    """Structured evidence item supporting the advisory reasoning."""
    source: str = Field(..., description="Module/service source, e.g. 'stockout_prediction', 'risk_service'.")
    observation: str = Field(..., description="Metric name or observation label.")
    value: str = Field(..., description="Observed value or state.")
    interpretation: str = Field(..., description="What this observation implies for logistics decision support.")


# ---------------------------------------------------------------------------
# Response Schema
# ---------------------------------------------------------------------------

class AdvisorResponse(BaseModel):
    """
    Structured advisory response generated deterministically from SENTINEL
    intelligence service outputs. All values are derived from existing modules;
    no external AI is invoked.

    confidence is a decision-support indicator (0–100), NOT a
    statistically validated probability.
    """

    query: str = Field(..., description="The original query that was submitted.")
    answer: str = Field(..., description="Direct answer to the query in plain language.")
    recommendation: str = Field(..., description="Concrete recommended action.")
    priority: PRIORITY_VALUES = Field(..., description="Urgency classification of the recommendation.")
    confidence: int = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Decision-support confidence indicator (0–100). "
            "Reflects how many SENTINEL intelligence signals support the recommendation. "
            "NOT a statistically validated probability."
        )
    )
    reasoning_summary: Optional[str] = Field(
        None,
        description="Concise summary of the multi-signal cross-reasoning process."
    )
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Structured evidence items with source, observation, value, and interpretation."
    )
    recommended_actions: List[str] = Field(
        default_factory=list,
        description="List of practical decision-support recommended actions for human review."
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Applicable dataset or system limitations."
    )
    supporting_factors: List[SupportingFactor] = Field(
        default_factory=list,
        description="Explainable factors derived from SENTINEL intelligence services."
    )
    relevant_entities: List[RelevantEntity] = Field(
        default_factory=list,
        description="Logistics entities referenced in this advisory response."
    )
    kb_context: List[str] = Field(
        default_factory=list,
        description="Phase 11D: Titles of relevant SENTINEL KB articles retrieved for this query. "
                    "Informational only; KB articles contain static explanatory content, not live operational data."
    )
    knowledge_sources: List[str] = Field(
        default_factory=list,
        description="Phase 11E: List of KB article IDs (e.g. ['kb-readiness-01']) actually used in response grounding."
    )
    operational_sources: List[str] = Field(
        default_factory=list,
        description="Phase 11E: List of intelligence module names (e.g. ['inventory', 'risk', 'readiness', 'stockout', 'environment', 'digital_twin', 'shipments']) actually used in response grounding."
    )
    provider_mode: Literal["deterministic", "mock", "llm"] = Field(
        default="deterministic",
        description="Execution mode tag: 'deterministic' (fallback engine), 'mock' (test provider), or 'llm' (live provider)."
    )
    data_source: str = Field(
        default="synthetic_demo",
        description="Provenance tag. All data in this system is synthetic demonstration data."
    )
    environment: str = Field(
        default="demo",
        description="Deployment environment tag."
    )

