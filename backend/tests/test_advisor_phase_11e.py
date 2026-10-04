"""
Unit & Integration tests for SENTINEL LOGIX AI Phase 11E: Grounded RAG-Style Advisor Response.

Tests cover:
- 1. Concept-only KB question ("What is mission readiness?")
- 2. Operational-only question ("Which depot has lowest stock?")
- 3. Mixed operational + knowledge question ("Why is DEPOT-IMP-SUP high risk?")
- 4. Correct KB article attribution (knowledge_sources field)
- 5. Fabricated KB source rejection (unsupported_kb_source -> fallback to deterministic)
- 6. Fabricated operational entity rejection (unsupported_operational_entity -> fallback to deterministic)
- 7. Current operational values overriding explanatory knowledge
- 8. Missing KB results handling
- 9. LLM provider unavailable (provider is None)
- 10. LLM provider failure (exception raised in provider generate)
- 11. Malformed LLM response (schema validation failure)
- 12. Deterministic fallback behavior
- 13. Provenance preservation (data_source='synthetic_demo', environment='demo')
- 14. Execution mode tag (provider_mode field: 'deterministic', 'mock', 'llm')
- 15. Operational sources tracking (operational_sources field)
- 16. Read-only database safety verification
"""

import os
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db, get_db
from backend.app.db.seed import seed_database
from backend.app.advisor import AdvisorRequest, AdvisorResponse, AdvisorService
from backend.app.advisor.context import AdvisorContext, AdvisorContextBuilder
from backend.app.advisor.llm import (
    MockLLMProvider,
    AdvisorResponseValidator,
    get_llm_provider,
)
from backend.app.advisor.reasoning import AdvisorReasoningEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Initialise isolated SQLite DB populated with seed data."""
    test_db_file = str(tmp_path / "test_sentinel_phase_11e.db")
    import backend.app.config as config
    config.DB_PATH = test_db_file
    init_db(test_db_file)
    seed_database(test_db_file)
    yield test_db_file


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def advisor_post(client, query: str, **kwargs) -> dict:
    payload = {"query": query, **kwargs}
    return client.post("/api/advisor/query", json=payload)


# ---------------------------------------------------------------------------
# 1. Concept-only KB question
# ---------------------------------------------------------------------------

def test_concept_only_kb_question(client):
    """Questions about SENTINEL concepts retrieve KB articles and explain methodology."""
    resp = advisor_post(client, "What is mission readiness?")
    assert resp.status_code == 200
    data = resp.json()
    assert "query" in data
    assert "answer" in data
    assert "knowledge_sources" in data
    assert len(data["knowledge_sources"]) > 0
    assert any("kb-readiness" in k for k in data["knowledge_sources"])
    assert "readiness" in data["answer"].lower() or "mission" in data["answer"].lower()


# ---------------------------------------------------------------------------
# 2. Operational-only question
# ---------------------------------------------------------------------------

def test_operational_only_question(client):
    """Operational query returns live operational numbers and sources."""
    resp = advisor_post(client, "Which depot has lowest stock?")
    assert resp.status_code == 200
    data = resp.json()
    assert "operational_sources" in data
    assert "inventory" in data["operational_sources"]
    assert "stockout" in data["operational_sources"]
    assert len(data["evidence"]) > 0


# ---------------------------------------------------------------------------
# 3. Mixed operational + knowledge question
# ---------------------------------------------------------------------------

def test_mixed_operational_plus_knowledge_question():
    """Mixed query combines current operational numbers with KB methodology explanation."""
    req = AdvisorRequest(query="Why is DEPOT-IMP-SUP high risk?", depot_id="DEPOT-IMP-SUP")
    provider = MockLLMProvider(behavior="operational_plus_knowledge")
    res = AdvisorService.query(req, provider=provider)
    assert res.provider_mode == "mock"
    assert "DEPOT-IMP-SUP" in [e.entity_id for e in res.relevant_entities]
    assert len(res.knowledge_sources) > 0
    assert len(res.operational_sources) > 0


# ---------------------------------------------------------------------------
# 4. Correct KB article attribution
# ---------------------------------------------------------------------------

def test_kb_article_attribution():
    """knowledge_sources field lists article IDs matching retrieved KB articles."""
    req = AdvisorRequest(query="How does environmental risk assessment work?")
    res = AdvisorService.query(req)
    assert isinstance(res.knowledge_sources, list)
    assert len(res.knowledge_sources) > 0
    assert any("environment" in k for k in res.knowledge_sources)


# ---------------------------------------------------------------------------
# 5. Fabricated KB source rejection
# ---------------------------------------------------------------------------

def test_fabricated_kb_source_rejection():
    """If LLM provider returns unretrieved KB source IDs, validation fails and falls back to deterministic."""
    req = AdvisorRequest(query="Explain mission readiness")
    provider = MockLLMProvider(behavior="unsupported_kb_source")
    res = AdvisorService.query(req, provider=provider)
    assert res.provider_mode == "deterministic"
    assert any("failed validation" in lim or "unsupported" in lim.lower() for lim in res.limitations)
    assert "kb-fake-unsupported-999" not in res.knowledge_sources


# ---------------------------------------------------------------------------
# 6. Fabricated operational entity rejection
# ---------------------------------------------------------------------------

def test_fabricated_operational_entity_rejection():
    """If LLM provider returns ungrounded entity ID, validation fails and falls back to deterministic."""
    req = AdvisorRequest(query="Check depot status")
    provider = MockLLMProvider(behavior="unsupported_operational_entity")
    res = AdvisorService.query(req, provider=provider)
    assert res.provider_mode == "deterministic"
    assert not any(e.entity_id == "DEPOT-FAKE-HALLUCINATED-999" for e in res.relevant_entities)


# ---------------------------------------------------------------------------
# 7. Operational values override explanatory knowledge
# ---------------------------------------------------------------------------

def test_operational_values_authoritative():
    """Live operational measurements remain authoritative for current status."""
    ctx = AdvisorContextBuilder.build(query="Current readiness score for DEPOT-TWA-AMM", depot_id="DEPOT-TWA-AMM")
    assert ctx.readiness_assessments is not None
    res = AdvisorReasoningEngine.evaluate(ctx, intent="readiness")
    assert res["priority"] in ("HIGH", "CRITICAL")
    assert "This assessment uses synthetic demonstration data." in res["limitations"]


# ---------------------------------------------------------------------------
# 8. Missing KB results handling
# ---------------------------------------------------------------------------

def test_missing_kb_results_handling():
    """When query yields no KB matches, advisor continues operating normally."""
    req = AdvisorRequest(query="xyz999nonsenseunmatchedquery")
    res = AdvisorService.query(req)
    assert res.provider_mode == "deterministic"
    assert isinstance(res.knowledge_sources, list)
    assert res.query == "xyz999nonsenseunmatchedquery"


# ---------------------------------------------------------------------------
# 9. LLM provider unavailable
# ---------------------------------------------------------------------------

def test_llm_provider_unavailable():
    """When provider is None, fallback to deterministic reasoning engine operates cleanly."""
    req = AdvisorRequest(query="General overview")
    res = AdvisorService.query(req, provider=None)
    assert res.provider_mode == "deterministic"
    assert res.data_source == "synthetic_demo"
    assert res.environment == "demo"


# ---------------------------------------------------------------------------
# 10. LLM provider failure
# ---------------------------------------------------------------------------

def test_llm_provider_failure():
    """When LLM provider raises an exception, system falls back safely to deterministic reasoning."""
    req = AdvisorRequest(query="General status")
    provider = MockLLMProvider(behavior="provider_failure")
    res = AdvisorService.query(req, provider=provider)
    assert res.provider_mode == "deterministic"
    assert any("fell back to deterministic" in lim for lim in res.limitations)


# ---------------------------------------------------------------------------
# 11. Malformed LLM response rejection
# ---------------------------------------------------------------------------

def test_malformed_llm_response_rejection():
    """Invalid priority or out-of-bounds confidence causes validation failure & fallback."""
    req = AdvisorRequest(query="Check risks")
    bad_prio_provider = MockLLMProvider(behavior="malformed_priority")
    res1 = AdvisorService.query(req, provider=bad_prio_provider)
    assert res1.provider_mode == "deterministic"

    bad_conf_provider = MockLLMProvider(behavior="malformed_confidence")
    res2 = AdvisorService.query(req, provider=bad_conf_provider)
    assert res2.provider_mode == "deterministic"


# ---------------------------------------------------------------------------
# 12. Grounded Mock Provider Success
# ---------------------------------------------------------------------------

def test_mock_provider_grounded_success():
    """Valid MockLLMProvider execution returns provider_mode='mock' with valid sources."""
    req = AdvisorRequest(query="Explain readiness for DEPOT-IMP-SUP", depot_id="DEPOT-IMP-SUP")
    provider = MockLLMProvider(behavior="knowledge_grounded")
    res = AdvisorService.query(req, provider=provider)
    assert res.provider_mode == "mock"
    assert "Mock LLM" in res.answer
    assert res.data_source == "synthetic_demo"
    assert res.environment == "demo"


# ---------------------------------------------------------------------------
# 13. Provenance & Schema preservation
# ---------------------------------------------------------------------------

def test_provenance_preservation(client):
    """API responses maintain strict data_source and environment tags."""
    resp = advisor_post(client, "Overview of all bases")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_source"] == "synthetic_demo"
    assert data["environment"] == "demo"
    assert data["provider_mode"] in ("deterministic", "mock", "llm")


# ---------------------------------------------------------------------------
# 14. Operational sources tracking
# ---------------------------------------------------------------------------

def test_operational_sources_tracking():
    """AdvisorResponse includes operational_sources list matching active modules."""
    req = AdvisorRequest(query="Show active inventory and shipments")
    res = AdvisorService.query(req)
    assert isinstance(res.operational_sources, list)
    assert "inventory" in res.operational_sources
    assert "shipments" in res.operational_sources


# ---------------------------------------------------------------------------
# 15. Read-only database safety
# ---------------------------------------------------------------------------

def test_database_read_only_safety(setup_test_db):
    """Advisor query executes without writing or mutating DB state."""
    db_file = setup_test_db
    mtime_before = os.path.getmtime(db_file)
    
    req = AdvisorRequest(query="Full system audit")
    res = AdvisorService.query(req, db_path=db_file)
    assert res is not None

    mtime_after = os.path.getmtime(db_file)
    assert mtime_before == mtime_after
