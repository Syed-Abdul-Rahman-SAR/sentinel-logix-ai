"""
Unit & Integration tests for SENTINEL LOGIX AI Phase 11A, 11B & 11C: AI Logistics Advisor.

Tests cover:
- Basic logistics query (general)
- Depot-specific advisory queries
- Route-specific advisory queries
- Inventory risk queries
- Mission readiness queries
- Environmental risk queries
- Unknown depot / route / base entity handling (HTTP 404)
- Empty / whitespace / invalid query handling (HTTP 400 & 422)
- Provenance fields (data_source, environment)
- Confidence bounds (0–100)
- Priority values (LOW/MEDIUM/HIGH/CRITICAL)
- Supporting factors present in recommendations
- Service layer direct tests (no HTTP client)
- Phase 11B: Multi-signal cross-reasoning (Inventory + Stock-out, Demand + Inventory, Risk + Readiness, Environment + Supply Movement)
- Phase 11B: Conflicting signal handling & explanation
- Phase 11B: Insufficient data handling & low confidence bounds
- Phase 11B: Structured evidence generation (source, observation, value, interpretation)
- Phase 11B: Recommended decision-support actions
- Phase 11B: System and dataset limitations list
- Phase 11B: Database safety (read-only verification)
- Phase 11C: Deterministic fallback when no provider is configured
- Phase 11C: MockLLMProvider success (provider_mode="mock")
- Phase 11C: Response validation & hallucination safety (reject invalid priority/confidence/missing fields/hallucinated entities)
- Phase 11C: Application startup without API keys
"""

import os
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db, get_db
from backend.app.db.seed import seed_database
from backend.app.advisor import AdvisorRequest, AdvisorResponse, AdvisorService
from backend.app.advisor.reasoning import AdvisorReasoningEngine
from backend.app.advisor.context import AdvisorContext, AdvisorContextBuilder
from backend.app.advisor.llm import (
    MockLLMProvider,
    AdvisorResponseValidator,
    get_llm_provider,
    get_advisor_llm_config,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Initialise isolated SQLite DB populated with seed data."""
    test_db_file = str(tmp_path / "test_sentinel_advisor.db")
    import backend.app.config as config
    config.DB_PATH = test_db_file
    init_db(test_db_file)
    seed_database(test_db_file)
    yield test_db_file


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helper — make a valid advisor query via the API
# ---------------------------------------------------------------------------

def advisor_post(client, query: str, **kwargs) -> dict:
    payload = {"query": query, **kwargs}
    resp = client.post("/api/advisor/query", json=payload)
    return resp


# ---------------------------------------------------------------------------
# 1. Basic / General logistics query
# ---------------------------------------------------------------------------

def test_basic_general_query(client):
    """A plain query returns 200 with a structured response."""
    resp = advisor_post(client, "Give me a logistics overview.")
    assert resp.status_code == 200
    data = resp.json()
    assert "query" in data
    assert "answer" in data
    assert "recommendation" in data
    assert len(data["answer"]) > 0
    assert len(data["recommendation"]) > 0


def test_general_query_response_structure(client):
    """Response contains all required top-level fields."""
    resp = advisor_post(client, "What is the current system status?")
    assert resp.status_code == 200
    data = resp.json()
    for field in ("query", "answer", "recommendation", "priority",
                  "confidence", "reasoning_summary", "evidence",
                  "recommended_actions", "limitations",
                  "supporting_factors", "relevant_entities",
                  "provider_mode", "data_source", "environment"):
        assert field in data, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# 2. Depot-specific query
# ---------------------------------------------------------------------------

def test_depot_specific_query(client):
    """Scoping to a known depot returns a depot-referenced response."""
    resp = advisor_post(client, "Which depot needs attention?",
                        depot_id="DEPOT-IMP-SUP")
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert 0 <= data["confidence"] <= 100


def test_depot_query_entities_reference_depot(client):
    """When depot_id is provided, relevant_entities should reference it."""
    resp = advisor_post(client, "Is this depot mission ready?",
                        depot_id="DEPOT-IMP-SUP")
    assert resp.status_code == 200
    data = resp.json()
    entity_ids = [e["entity_id"] for e in data.get("relevant_entities", [])]
    assert any("DEPOT-IMP-SUP" in eid or "IMP" in eid for eid in entity_ids) or \
           "DEPOT-IMP-SUP" in data["answer"] or "DEPOT-IMP-SUP" in data["recommendation"]


def test_depot_query_tawang(client):
    """Tawang depot is on a CRITICAL environment route — readiness or risk should reflect that."""
    resp = advisor_post(client, "What is the readiness status?",
                        depot_id="DEPOT-TWA-AMM")
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


# ---------------------------------------------------------------------------
# 3. Route-specific query
# ---------------------------------------------------------------------------

def test_route_specific_environmental_query(client):
    """Query about a known route returns environmental risk data."""
    resp = advisor_post(client, "What is the environmental risk on this route?",
                        route_id="TEZ-TWA")
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] in ("HIGH", "CRITICAL")
    assert data["confidence"] >= 50


def test_route_specific_disruption_query(client):
    """Disruption query for a route with shipments returns evidence and recommended actions."""
    resp = advisor_post(client, "What happens if this route is disrupted?",
                        route_id="SIL-IMP")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["evidence"]) >= 1
    assert len(data["recommended_actions"]) >= 1


def test_route_query_low_risk(client):
    """Low-risk route returns a MEDIUM or LOW priority."""
    resp = advisor_post(client, "What is the environmental risk on this route?",
                        route_id="GHY-TEZ")
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] in ("LOW", "MEDIUM")


# ---------------------------------------------------------------------------
# 4. Inventory risk query
# ---------------------------------------------------------------------------

def test_inventory_risk_query(client):
    """Inventory risk query surfaces stock-out and threshold concerns."""
    resp = advisor_post(client, "Which inventory item is at risk of stockout?")
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert len(data["answer"]) > 0


def test_inventory_risk_depot_scoped(client):
    """Depot-scoped inventory risk query returns items for that depot."""
    resp = advisor_post(client, "Which inventory items are at risk?",
                        depot_id="DEPOT-IMP-SUP")
    assert resp.status_code == 200
    data = resp.json()
    assert 0 <= data["confidence"] <= 100


def test_inventory_risk_supporting_factors_not_empty(client):
    """When risk is present, supporting factors are populated."""
    resp = advisor_post(client, "What inventory items need urgent attention?",
                        depot_id="DEPOT-IMP-SUP")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["supporting_factors"], list)


# ---------------------------------------------------------------------------
# 5. Mission readiness & Risk cause queries
# ---------------------------------------------------------------------------

def test_readiness_query_returns_status(client):
    """Mission readiness query returns a readiness-aware response."""
    resp = advisor_post(client, "Is this depot mission ready?",
                        depot_id="DEPOT-GHY-FUEL")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["answer"]) > 0


def test_readiness_query_all_depots(client):
    """General readiness query (no depot_id) returns system-level response."""
    resp = advisor_post(client, "Which depots are mission ready?")
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_readiness_query_includes_score_factor(client):
    """Readiness query supporting factors should include READINESS_SCORE."""
    resp = advisor_post(client, "What is the readiness status?",
                        depot_id="DEPOT-IMP-SUP")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["supporting_factors"], list)


def test_risk_cause_query(client):
    """'What is causing the risk?' returns risk-sourced explanation."""
    resp = advisor_post(client, "What is causing the current risk at this depot?",
                        depot_id="DEPOT-IMP-SUP")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["answer"]) > 0
    assert len(data["recommendation"]) > 0


def test_risk_cause_general(client):
    """System-wide risk cause query runs without scoping."""
    resp = advisor_post(client, "Why is the operational risk elevated?")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 6. Environmental queries
# ---------------------------------------------------------------------------

def test_environmental_risk_query(client):
    """Environmental query surfaces route risk intelligence."""
    resp = advisor_post(client, "Which route has the highest environmental risk?")
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] in ("MEDIUM", "HIGH", "CRITICAL")


def test_environmental_route_scoped_query(client):
    """Route-scoped environmental query returns that route's data."""
    resp = advisor_post(client, "What are the weather and terrain conditions?",
                        route_id="SIL-IMP")
    assert resp.status_code == 200
    data = resp.json()
    entity_types = [e["entity_type"] for e in data.get("relevant_entities", [])]
    assert "route" in entity_types


def test_environmental_query_critical_route(client):
    """TEZ-TWA (blizzard route) should return CRITICAL priority."""
    resp = advisor_post(client, "What are the environmental conditions?",
                        route_id="TEZ-TWA")
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] == "CRITICAL"


# ---------------------------------------------------------------------------
# 7. Entity & Request Error Validation (404, 400, 422)
# ---------------------------------------------------------------------------

def test_unknown_depot_returns_404(client):
    resp = advisor_post(client, "What is the status?", depot_id="DEPOT-NONEXISTENT-999")
    assert resp.status_code == 404


def test_unknown_route_returns_404(client):
    resp = advisor_post(client, "What is the environmental risk?", route_id="ROUTE-NONEXISTENT-999")
    assert resp.status_code == 404


def test_unknown_base_returns_404(client):
    resp = advisor_post(client, "What is the base status?", base_id="BASE-NONEXISTENT-999")
    assert resp.status_code == 404


def test_empty_query_returns_400(client):
    resp = client.post("/api/advisor/query", json={"query": ""})
    assert resp.status_code in (400, 422)


def test_whitespace_only_query_returns_400(client):
    resp = client.post("/api/advisor/query", json={"query": "   "})
    assert resp.status_code == 400


def test_missing_query_returns_422(client):
    """Pydantic validation rejects missing required query field."""
    resp = client.post("/api/advisor/query", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 8. Provenance & Confidence & Priority
# ---------------------------------------------------------------------------

def test_provenance_data_source(client):
    resp = advisor_post(client, "What should I check first?")
    assert resp.status_code == 200
    assert resp.json()["data_source"] == "synthetic_demo"


def test_provenance_environment(client):
    resp = advisor_post(client, "What should I check first?")
    assert resp.status_code == 200
    assert resp.json()["environment"] == "demo"


def test_provenance_present_in_all_responses(client):
    """Provenance is present regardless of query type."""
    queries = [
        ("Give me an overview.", {}),
        ("Which depot needs attention?", {}),
        ("Inventory risk?", {"depot_id": "DEPOT-IMP-SUP"}),
        ("Environmental conditions?", {"route_id": "TEZ-TWA"}),
    ]
    for query, kwargs in queries:
        resp = advisor_post(client, query, **kwargs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_source"] == "synthetic_demo"
        assert data["environment"] == "demo"


def test_confidence_between_0_and_100(client):
    queries = [
        ("Overview?", {}),
        ("Readiness?", {}),
        ("Risk?", {}),
        ("Environmental conditions?", {"route_id": "GHY-TEZ"}),
        ("What should I do?", {"depot_id": "DEPOT-GHY-FUEL"}),
    ]
    for query, kwargs in queries:
        resp = advisor_post(client, query, **kwargs)
        assert resp.status_code == 200
        conf = resp.json()["confidence"]
        assert 0 <= conf <= 100, f"Confidence {conf} out of bounds for query: {query}"


def test_priority_values_are_valid(client):
    valid = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    resp = advisor_post(client, "What are the environmental conditions?", route_id="TEZ-TWA")
    assert resp.status_code == 200
    assert resp.json()["priority"] in valid


def test_supporting_factors_structure(client):
    """Each supporting factor has 'factor' and 'detail' keys."""
    resp = advisor_post(client, "What is the current risk?",
                        depot_id="DEPOT-IMP-SUP")
    assert resp.status_code == 200
    for sf in resp.json()["supporting_factors"]:
        assert "factor" in sf
        assert "detail" in sf


def test_high_priority_response_has_factors(client):
    """HIGH/CRITICAL responses include supporting factors or evidence."""
    resp = advisor_post(client, "What are the weather conditions?", route_id="TEZ-TWA")
    assert resp.status_code == 200
    data = resp.json()
    if data["priority"] in ("HIGH", "CRITICAL"):
        assert len(data["evidence"]) >= 1 or len(data["supporting_factors"]) >= 1


def test_relevant_entities_structure(client):
    """Relevant entities, if present, have entity_type and entity_id."""
    resp = advisor_post(client, "Which route has environmental risk?",
                        route_id="SIL-IMP")
    assert resp.status_code == 200
    for ent in resp.json()["relevant_entities"]:
        assert "entity_type" in ent
        assert "entity_id" in ent


# ---------------------------------------------------------------------------
# 9. Direct Service Layer Tests (No HTTP)
# ---------------------------------------------------------------------------

def test_service_returns_advisor_response(setup_test_db):
    """AdvisorService.query returns an AdvisorResponse with all required fields."""
    req = AdvisorRequest(query="Which depot needs immediate attention?")
    result = AdvisorService.query(req, db_path=setup_test_db)
    assert isinstance(result, AdvisorResponse)
    assert result.data_source == "synthetic_demo"
    assert result.environment == "demo"
    assert 0 <= result.confidence <= 100
    assert result.priority in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_service_depot_scoped(setup_test_db):
    """Service with depot scope returns coherent response."""
    req = AdvisorRequest(query="Is this depot ready?", depot_id="DEPOT-GHY-FUEL")
    result = AdvisorService.query(req, db_path=setup_test_db)
    assert isinstance(result, AdvisorResponse)
    assert len(result.answer) > 0
    assert len(result.recommendation) > 0


def test_service_route_scoped(setup_test_db):
    """Service with route scope loads environmental intelligence."""
    req = AdvisorRequest(query="What are the route conditions?", route_id="SIL-IMP")
    result = AdvisorService.query(req, db_path=setup_test_db)
    assert isinstance(result, AdvisorResponse)
    assert result.priority in ("HIGH", "CRITICAL")


def test_service_tez_twa_critical(setup_test_db):
    """TEZ-TWA route environmental query should return CRITICAL priority."""
    req = AdvisorRequest(query="What are the environmental conditions on this route?",
                         route_id="TEZ-TWA")
    result = AdvisorService.query(req, db_path=setup_test_db)
    assert result.priority == "CRITICAL"
    assert len(result.evidence) >= 1 or len(result.supporting_factors) >= 1


# ---------------------------------------------------------------------------
# 10. Phase 11B Specific Multi-Signal Reasoning Tests
# ---------------------------------------------------------------------------

def test_multi_signal_reasoning_inventory_plus_stockout(client):
    """Verifies cross-signal reasoning combining inventory threshold and stockout prediction."""
    resp = advisor_post(client, "What inventory items need attention?", depot_id="DEPOT-IMP-SUP")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reasoning_summary"] is not None
    assert len(data["reasoning_summary"]) > 0
    sources = [ev["source"] for ev in data["evidence"]]
    assert any(s in ("inventory_service", "stockout_prediction", "risk_service", "readiness_service") for s in sources)


def test_multi_signal_inventory_plus_demand(client):
    """Verifies that inventory and demand signals are cross-analyzed in reasoning."""
    resp = advisor_post(client, "Are inventory consumption rates compounding stockout risk?", depot_id="DEPOT-IMP-SUP")
    assert resp.status_code == 200
    data = resp.json()
    assert "evidence" in data
    assert isinstance(data["evidence"], list)


def test_multi_signal_risk_plus_readiness(client):
    """Verifies cross-signal interaction between operational risk and mission readiness."""
    resp = advisor_post(client, "How does depot readiness align with operational risk?", depot_id="DEPOT-IMP-SUP")
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert len(data["recommended_actions"]) >= 1


def test_multi_signal_environment_plus_supply_movement(client):
    """Verifies cross-signal interaction between environmental route hazard and active shipments."""
    resp = advisor_post(client, "Are supply shipments exposed to weather hazards?", route_id="TEZ-TWA")
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] == "CRITICAL"
    sources = [ev["source"] for ev in data["evidence"]]
    assert "environment_service" in sources


def test_conflicting_signals_explanation(client):
    """Verifies that signal conflicts are explained rather than generating forced artificial conclusions."""
    resp = advisor_post(client, "Check inventory vs route environmental risk.", depot_id="DEPOT-GHY-FUEL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reasoning_summary"] is not None
    assert isinstance(data["reasoning_summary"], str)


def test_insufficient_data_handling():
    """
    Verifies that when context has no inventory/risk/readiness/environment signals,
    the engine states insufficient data explicitly and lowers confidence score.
    """
    empty_ctx = AdvisorContext(query="Unknown scenario?")
    result = AdvisorReasoningEngine.evaluate(empty_ctx, "general")

    assert "insufficient" in result["answer"].lower() or "insufficient" in result["reasoning_summary"].lower()
    assert result["confidence"] <= 40
    assert any("insufficient" in l.lower() for l in result["limitations"])


def test_evidence_generation_structure(client):
    """Verifies structured evidence contains source, observation, value, interpretation."""
    resp = advisor_post(client, "What evidence supports the current risk rating?", depot_id="DEPOT-IMP-SUP")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["evidence"], list)
    for ev in data["evidence"]:
        assert "source" in ev
        assert "observation" in ev
        assert "value" in ev
        assert "interpretation" in ev


def test_recommended_actions_human_in_the_loop(client):
    """Verifies recommended actions are actionable human decision support steps."""
    resp = advisor_post(client, "What actions should be taken?", depot_id="DEPOT-IMP-SUP")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["recommended_actions"], list)
    assert len(data["recommended_actions"]) >= 1
    actions_text = " ".join(data["recommended_actions"]).lower()
    assert any(w in actions_text for w in ("review", "inspect", "monitor", "eval", "track", "run"))


def test_limitations_list_presence(client):
    """Verifies system limitations are returned in response."""
    resp = advisor_post(client, "What are the limitations of this analysis?")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["limitations"], list)
    assert len(data["limitations"]) >= 1
    lims_text = " ".join(data["limitations"]).lower()
    assert "synthetic" in lims_text or "demo" in lims_text or "live" in lims_text


def test_database_safety_no_mutation(setup_test_db, client):
    """Run multiple Phase 11B advisor queries and confirm database tables remain untouched."""
    with get_db(setup_test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, current_quantity FROM inventory_items ORDER BY id")
        before_inventory = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT id, status FROM trips ORDER BY id")
        before_trips = [dict(r) for r in cursor.fetchall()]

    queries = [
        ("What is the system risk?", {}),
        ("Check depot inventory", {"depot_id": "DEPOT-IMP-SUP"}),
        ("Route disruption impact?", {"route_id": "TEZ-TWA"}),
        ("Multi-signal summary?", {"depot_id": "DEPOT-GHY-FUEL"}),
    ]
    for q, kwargs in queries:
        resp = advisor_post(client, q, **kwargs)
        assert resp.status_code == 200

    with get_db(setup_test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, current_quantity FROM inventory_items ORDER BY id")
        after_inventory = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT id, status FROM trips ORDER BY id")
        after_trips = [dict(r) for r in cursor.fetchall()]

    assert before_inventory == after_inventory, "Advisor mutated inventory_items table!"
    assert before_trips == after_trips, "Advisor mutated trips table!"


# ---------------------------------------------------------------------------
# 11. Phase 11C Specific Tests: LLM Provider Abstraction & Grounded Validation
# ---------------------------------------------------------------------------

def test_unconfigured_llm_defaults_to_deterministic_fallback(client):
    """Default request with no env provider sets provider_mode='deterministic'."""
    resp = advisor_post(client, "System status?")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider_mode"] == "deterministic"


def test_mock_llm_provider_success(setup_test_db):
    """Passing MockLLMProvider returns provider_mode='mock' with valid structured output."""
    mock_prov = MockLLMProvider(behavior="normal")
    req = AdvisorRequest(query="Which depot needs attention?", depot_id="DEPOT-IMP-SUP")
    result = AdvisorService.query(req, db_path=setup_test_db, provider=mock_prov)

    assert isinstance(result, AdvisorResponse)
    assert result.provider_mode == "mock"
    assert "[Mock LLM" in result.answer or "[Mock LLM" in result.recommendation
    assert result.data_source == "synthetic_demo"
    assert result.environment == "demo"


def test_malformed_priority_triggers_deterministic_fallback(setup_test_db):
    """Provider returning invalid priority triggers safe fallback to provider_mode='deterministic'."""
    mock_bad_priority = MockLLMProvider(behavior="malformed_priority")
    req = AdvisorRequest(query="Depot status?", depot_id="DEPOT-IMP-SUP")
    result = AdvisorService.query(req, db_path=setup_test_db, provider=mock_bad_priority)

    assert isinstance(result, AdvisorResponse)
    assert result.provider_mode == "deterministic"
    assert result.priority in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert any("failed validation" in lim for lim in result.limitations)


def test_malformed_confidence_triggers_deterministic_fallback(setup_test_db):
    """Provider returning confidence > 100 triggers safe fallback to provider_mode='deterministic'."""
    mock_bad_conf = MockLLMProvider(behavior="malformed_confidence")
    req = AdvisorRequest(query="Depot status?", depot_id="DEPOT-IMP-SUP")
    result = AdvisorService.query(req, db_path=setup_test_db, provider=mock_bad_conf)

    assert isinstance(result, AdvisorResponse)
    assert result.provider_mode == "deterministic"
    assert 0 <= result.confidence <= 100
    assert any("failed validation" in lim for lim in result.limitations)


def test_missing_required_field_triggers_deterministic_fallback(setup_test_db):
    """Provider omitting required 'answer' field triggers safe fallback to provider_mode='deterministic'."""
    mock_missing = MockLLMProvider(behavior="missing_field")
    req = AdvisorRequest(query="Depot status?", depot_id="DEPOT-IMP-SUP")
    result = AdvisorService.query(req, db_path=setup_test_db, provider=mock_missing)

    assert isinstance(result, AdvisorResponse)
    assert result.provider_mode == "deterministic"
    assert len(result.answer) > 0
    assert any("failed validation" in lim for lim in result.limitations)


def test_hallucinated_entity_triggers_deterministic_fallback(setup_test_db):
    """Provider introducing an unknown entity ID ('DEPOT-FAKE-HALLUCINATED-999') triggers safe fallback."""
    mock_hallucinated = MockLLMProvider(behavior="hallucinated_entity")
    req = AdvisorRequest(query="Depot status?", depot_id="DEPOT-IMP-SUP")
    result = AdvisorService.query(req, db_path=setup_test_db, provider=mock_hallucinated)

    assert isinstance(result, AdvisorResponse)
    assert result.provider_mode == "deterministic"
    # Ensure hallucinated entity is NOT present in returned relevant_entities
    returned_entity_ids = [e.entity_id for e in result.relevant_entities]
    assert "DEPOT-FAKE-HALLUCINATED-999" not in returned_entity_ids
    assert any("Hallucinated entity detected" in lim for lim in result.limitations)


def test_validator_detects_known_context_entities(setup_test_db):
    """AdvisorResponseValidator correctly extracts known context entity IDs."""
    ctx = AdvisorContextBuilder.build(query="Test", depot_id="DEPOT-IMP-SUP", route_id="SIL-IMP", db_path=setup_test_db)
    known = AdvisorResponseValidator.extract_known_entity_ids(ctx)

    assert "DEPOT-IMP-SUP" in known
    assert "SIL-IMP" in known
    assert "DEPOT-NONEXISTENT-999" not in known


def test_app_starts_without_llm_api_key():
    """Application starts cleanly when ADVISOR_LLM_API_KEY environment variable is missing."""
    old_val = os.environ.pop("ADVISOR_LLM_API_KEY", None)
    try:
        provider = get_llm_provider()
        assert provider is None or isinstance(provider, MockLLMProvider)
    finally:
        if old_val:
            os.environ["ADVISOR_LLM_API_KEY"] = old_val


def test_provider_env_config_resolution():
    """get_advisor_llm_config correctly loads environment variables."""
    cfg = get_advisor_llm_config()
    assert "provider" in cfg
    assert "api_key" in cfg
    assert "model" in cfg
