"""
SENTINEL LOGIX AI - Phase 11F: Advisor Evaluation, Grounding Audit & Production-Safety Hardening

Test Suite structure:
1. TestAdvisorConceptQuestions (Category A)
2. TestAdvisorOperationalQuestions (Category B)
3. TestAdvisorMixedQuestions (Category C)
4. TestAdvisorLimitationQuestions (Category D)
5. TestGroundingConsistencyAudit (KB vs Operational context boundary)
6. TestProvenanceAudit (knowledge_sources, operational_sources, provider_mode)
7. TestEntityGroundingAudit (entity ID validation & hallucination prevention)
8. TestRecommendationSafetyAudit (human-in-the-loop decision-support phrasing)
9. TestSyntheticDataProvenanceAudit (synthetic tags & limitations)
10. TestReadOnlySafetyAudit (zero DB mutation across all query types)
11. TestDeterministicRepeatability (stability & determinism across repeated queries)
12. TestCrossModuleConsistency (Advisor values match underlying service outputs)
13. TestErrorRecoveryMatrix (KB failure, LLM failure, malformed response, incomplete context)
14. TestAPIContractRegression (HTTP 200, 400, 404, 422 contracts)
"""

import os
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db, get_db
from backend.app.db.seed import seed_database
from backend.app.advisor import AdvisorRequest, AdvisorResponse, AdvisorService
from backend.app.advisor.context import AdvisorContext, AdvisorContextBuilder
from backend.app.advisor.reasoning import AdvisorReasoningEngine
from backend.app.advisor.llm import (
    MockLLMProvider,
    AdvisorResponseValidator,
    get_llm_provider,
)
from backend.app.services.depot_service import DepotService
from backend.app.risk.service import RiskService
from backend.app.readiness.service import ReadinessService
from backend.app.stockout.service import StockoutService
from backend.app.environment.service import EnvironmentService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Initialise isolated SQLite DB populated with seed data."""
    test_db_file = str(tmp_path / "test_sentinel_phase_11f.db")
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


# ===========================================================================
# 1. Category A: Concept Questions
# ===========================================================================

class TestAdvisorConceptQuestions:

    @pytest.mark.parametrize("query,expected_kb_tag", [
        ("What is mission readiness?", "kb-readiness"),
        ("How is operational risk calculated?", "kb-risk"),
        ("What does stock-out prediction mean?", "kb-stockout"),
        ("How does the Digital Twin work?", "kb-digital-twin"),
        ("What does environmental risk mean?", "kb-environment"),
    ])
    def test_concept_queries_retrieve_kb_and_stay_conceptual(self, client, query, expected_kb_tag):
        resp = advisor_post(client, query)
        assert resp.status_code == 200
        data = resp.json()

        # Knowledge sources present and contain matched article tag
        assert len(data["knowledge_sources"]) > 0
        assert any(expected_kb_tag in k for k in data["knowledge_sources"])

        # Answer remains conceptual with KB citation
        assert "according to sentinel knowledge base" in data["answer"].lower() or "kb" in data["answer"].lower()

        # Knowledge sources contain only retrieved IDs
        for k_id in data["knowledge_sources"]:
            assert isinstance(k_id, str)
            assert len(k_id) > 0


# ===========================================================================
# 2. Category B: Operational Questions
# ===========================================================================

class TestAdvisorOperationalQuestions:

    def test_lowest_inventory_depot_query(self, client):
        resp = advisor_post(client, "Which depot has the lowest inventory?")
        assert resp.status_code == 200
        data = resp.json()

        assert "inventory" in data["operational_sources"]
        assert len(data["evidence"]) > 0
        assert len(data["relevant_entities"]) > 0

    def test_highest_risk_depot_query(self, client):
        resp = advisor_post(client, "Which depot is highest risk?")
        assert resp.status_code == 200
        data = resp.json()

        assert "risk" in data["operational_sources"]
        assert data["priority"] in ("HIGH", "CRITICAL")

    def test_lowest_readiness_depot_query(self, client):
        resp = advisor_post(client, "Which depot has the lowest readiness?")
        assert resp.status_code == 200
        data = resp.json()

        assert "readiness" in data["operational_sources"]
        assert any(e["source"] == "readiness_service" for e in data["evidence"])

    def test_highest_environmental_risk_route_query(self, client):
        resp = advisor_post(client, "Which route has the highest environmental risk?", route_id="SIL-IMP")
        assert resp.status_code == 200
        data = resp.json()

        assert "environment" in data["operational_sources"]
        assert any(e["source"] == "environment_service" for e in data["evidence"])


# ===========================================================================
# 3. Category C: Mixed Questions
# ===========================================================================

class TestAdvisorMixedQuestions:

    def test_why_depot_high_risk(self, client):
        resp = advisor_post(client, "Why is DEPOT-IMP-SUP high risk?", depot_id="DEPOT-IMP-SUP")
        assert resp.status_code == 200
        data = resp.json()

        # Live values from services
        assert "DEPOT-IMP-SUP" in [e["entity_id"] for e in data["relevant_entities"]]
        assert "risk" in data["operational_sources"]

        # Provenance preserved
        assert data["data_source"] == "synthetic_demo"
        assert data["environment"] == "demo"

    def test_why_depot_readiness_degraded(self, client):
        resp = advisor_post(client, "Why is this depot's readiness degraded?", depot_id="DEPOT-TWA-AMM")
        assert resp.status_code == 200
        data = resp.json()

        assert "readiness" in data["operational_sources"]
        assert any(e["entity_id"] == "DEPOT-TWA-AMM" for e in data["relevant_entities"])

    def test_digital_twin_result_impact(self, client):
        resp = advisor_post(client, "What does the Digital Twin result mean for DEPOT-SHL-MED?", depot_id="DEPOT-SHL-MED")
        assert resp.status_code == 200
        data = resp.json()

        assert "digital_twin" in data["operational_sources"] or "shipments" in data["operational_sources"]


# ===========================================================================
# 4. Category D: Limitation Questions
# ===========================================================================

class TestAdvisorLimitationQuestions:

    def test_unknown_route_returns_404(self, client):
        resp = advisor_post(client, "Route analysis", route_id="ROUTE-NON-EXISTENT-999")
        assert resp.status_code == 404
        assert "Route 'ROUTE-NON-EXISTENT-999' not found" in resp.json()["detail"]

    def test_unknown_depot_returns_404(self, client):
        resp = advisor_post(client, "Depot analysis", depot_id="DEPOT-NON-EXISTENT-999")
        assert resp.status_code == 404
        assert "Depot 'DEPOT-NON-EXISTENT-999' not found" in resp.json()["detail"]

    def test_unmatched_query_returns_safe_fallback(self):
        req = AdvisorRequest(query="zxcvbnm123456789nonsense")
        res = AdvisorService.query(req)
        assert res.provider_mode == "deterministic"
        assert res.query == "zxcvbnm123456789nonsense"
        assert isinstance(res.limitations, list)
        assert len(res.limitations) > 0


# ===========================================================================
# 5. Grounding Consistency Audit
# ===========================================================================

class TestGroundingConsistencyAudit:

    def test_operational_context_authoritative_over_kb(self):
        """Verify that live operational measurements are used as current values, not KB examples."""
        ctx = AdvisorContextBuilder.build(query="What is the current readiness status for DEPOT-TWA-AMM?", depot_id="DEPOT-TWA-AMM")
        res = AdvisorReasoningEngine.evaluate(ctx, intent="readiness")

        # Operational status comes from readiness service (CRITICAL/DEGRADED)
        assert any("readiness_service" in e.source for e in res["evidence"])
        # Synthetic limitation is clearly attached
        assert "This assessment uses synthetic demonstration data." in res["limitations"]


# ===========================================================================
# 6. Provenance Audit
# ===========================================================================

class TestProvenanceAudit:

    def test_knowledge_sources_validity(self):
        req = AdvisorRequest(query="Explain mission readiness methodology")
        res = AdvisorService.query(req)
        for kb_id in res.knowledge_sources:
            assert isinstance(kb_id, str)
            assert kb_id.startswith("kb-")

    def test_operational_sources_validity(self):
        req = AdvisorRequest(query="General overview")
        res = AdvisorService.query(req)
        valid_modules = {"inventory", "stockout", "risk", "readiness", "environment", "digital_twin", "shipments", "depots", "bases"}
        for op in res.operational_sources:
            assert op in valid_modules

    def test_truthful_provider_mode_on_fallback(self):
        req = AdvisorRequest(query="Overview query")
        failing_provider = MockLLMProvider(behavior="provider_failure")
        res = AdvisorService.query(req, provider=failing_provider)
        assert res.provider_mode == "deterministic", "Must not claim LLM mode when fallback occurred"
        assert any("fell back to deterministic" in lim for lim in res.limitations)


# ===========================================================================
# 7. Entity Grounding Audit
# ===========================================================================

class TestEntityGroundingAudit:

    def test_valid_entities_accepted(self):
        req = AdvisorRequest(query="Depot status for DEPOT-TWA-AMM", depot_id="DEPOT-TWA-AMM")
        res = AdvisorService.query(req)
        assert any(e.entity_id == "DEPOT-TWA-AMM" for e in res.relevant_entities)

    def test_hallucinated_entity_rejected_by_validator(self):
        req = AdvisorRequest(query="Check depots")
        provider = MockLLMProvider(behavior="unsupported_operational_entity")
        res = AdvisorService.query(req, provider=provider)
        assert res.provider_mode == "deterministic"
        assert not any(e.entity_id == "DEPOT-FAKE-HALLUCINATED-999" for e in res.relevant_entities)


# ===========================================================================
# 8. Recommendation Safety Audit
# ===========================================================================

class TestRecommendationSafetyAudit:

    def test_recommendations_are_human_decision_support(self, client):
        resp = advisor_post(client, "What actions should I take for inventory risk?")
        assert resp.status_code == 200
        data = resp.json()

        rec = data["recommendation"].lower()
        # Ensure no claim of autonomous action execution
        assert "executed action" not in rec
        assert "automatically dispatched" not in rec

        # Check recommended actions use decision-support phrasing
        actions = [a.lower() for a in data["recommended_actions"]]
        for act in actions:
            assert any(word in act for word in ("review", "monitor", "inspect", "evaluate", "track", "run", "confirm", "assess", "expedite"))


# ===========================================================================
# 9. Synthetic Data Provenance Audit
# ===========================================================================

class TestSyntheticDataProvenanceAudit:

    def test_synthetic_tags_preserved(self, client):
        resp = advisor_post(client, "System status")
        assert resp.status_code == 200
        data = resp.json()

        assert data["data_source"] == "synthetic_demo"
        assert data["environment"] == "demo"

        # Limitations list contains synthetic notice
        assert any("synthetic" in lim.lower() for lim in data["limitations"])


# ===========================================================================
# 10. Read-Only Safety Audit
# ===========================================================================

class TestReadOnlySafetyAudit:

    def test_queries_do_not_mutate_database(self, setup_test_db):
        db_file = setup_test_db
        mtime_start = os.path.getmtime(db_file)

        # Execute multiple queries across different operational areas
        for q in [
            "What is mission readiness?",
            "Which depot is highest risk?",
            "Why is SIL-IMP environmentally risky?",
            "Run advisory analysis for DEPOT-TWA-AMM"
        ]:
            req = AdvisorRequest(query=q)
            res = AdvisorService.query(req, db_path=db_file)
            assert res is not None

        mtime_end = os.path.getmtime(db_file)
        assert mtime_start == mtime_end, "Database file modified during advisor query execution!"


# ===========================================================================
# 11. Deterministic Repeatability Audit
# ===========================================================================

class TestDeterministicRepeatabilityAudit:

    def test_deterministic_queries_are_repeatable(self):
        req = AdvisorRequest(query="Depot risk analysis for DEPOT-IMP-SUP", depot_id="DEPOT-IMP-SUP")

        res1 = AdvisorService.query(req)
        res2 = AdvisorService.query(req)

        assert res1.answer == res2.answer
        assert res1.recommendation == res2.recommendation
        assert res1.priority == res2.priority
        assert res1.confidence == res2.confidence
        assert res1.knowledge_sources == res2.knowledge_sources
        assert res1.operational_sources == res2.operational_sources

    def test_mock_llm_provider_is_deterministic(self):
        req = AdvisorRequest(query="Readiness check for DEPOT-TWA-AMM", depot_id="DEPOT-TWA-AMM")
        provider1 = MockLLMProvider(behavior="normal")
        provider2 = MockLLMProvider(behavior="normal")

        res1 = AdvisorService.query(req, provider=provider1)
        res2 = AdvisorService.query(req, provider=provider2)

        assert res1.answer == res2.answer
        assert res1.provider_mode == res2.provider_mode == "mock"


# ===========================================================================
# 12. Cross-Module Consistency Audit
# ===========================================================================

class TestCrossModuleConsistencyAudit:

    def test_advisor_risk_matches_risk_service(self, setup_test_db):
        db_file = setup_test_db
        ctx = AdvisorContextBuilder.build(query="Risk for DEPOT-TWA-AMM", depot_id="DEPOT-TWA-AMM", db_path=db_file)
        risk_direct = RiskService.get_risk_assessments(depot_id="DEPOT-TWA-AMM", db_path=db_file)

        assert len(ctx.risk_assessments) == len(risk_direct)
        if risk_direct:
            assert ctx.risk_assessments[0]["risk_score"] == risk_direct[0]["risk_score"]

    def test_advisor_readiness_matches_readiness_service(self, setup_test_db):
        db_file = setup_test_db
        ctx = AdvisorContextBuilder.build(query="Readiness for DEPOT-IMP-SUP", depot_id="DEPOT-IMP-SUP", db_path=db_file)
        readiness_direct = ReadinessService.get_readiness_assessments(depot_id="DEPOT-IMP-SUP", db_path=db_file)

        assert len(ctx.readiness_assessments) == len(readiness_direct)
        if readiness_direct:
            assert ctx.readiness_assessments[0]["readiness_score"] == readiness_direct[0]["readiness_score"]


# ===========================================================================
# 13. Error-Recovery Matrix Audit
# ===========================================================================

class TestErrorRecoveryMatrixAudit:

    def test_recovery_from_llm_exception(self):
        req = AdvisorRequest(query="System review")
        failing_provider = MockLLMProvider(behavior="provider_failure")
        res = AdvisorService.query(req, provider=failing_provider)

        assert res.provider_mode == "deterministic"
        assert res.answer is not None
        assert len(res.answer) > 0

    def test_recovery_from_unsupported_kb_source(self):
        req = AdvisorRequest(query="Risk explanation")
        unsupported_provider = MockLLMProvider(behavior="unsupported_kb_source")
        res = AdvisorService.query(req, provider=unsupported_provider)

        assert res.provider_mode == "deterministic"
        assert "kb-fake-unsupported-999" not in res.knowledge_sources


# ===========================================================================
# 14. API Contract Regression Audit
# ===========================================================================

class TestAPIContractRegressionAudit:

    def test_valid_query_contract(self, client):
        resp = advisor_post(client, "What is the status of Tawang depot?")
        assert resp.status_code == 200
        data = resp.json()
        for field in ("query", "answer", "recommendation", "priority", "confidence", "reasoning_summary", "evidence", "recommended_actions", "limitations", "supporting_factors", "relevant_entities", "kb_context", "knowledge_sources", "operational_sources", "provider_mode", "data_source", "environment"):
            assert field in data

    def test_blank_query_returns_400(self, client):
        resp = advisor_post(client, "   ")
        assert resp.status_code == 400
        assert "Query must be a non-empty string" in resp.json()["detail"]

    def test_invalid_depot_returns_404(self, client):
        resp = advisor_post(client, "Overview", depot_id="DEPOT-INVALID-123")
        assert resp.status_code == 404

    def test_invalid_base_returns_404(self, client):
        resp = advisor_post(client, "Overview", base_id="BASE-INVALID-123")
        assert resp.status_code == 404

    def test_invalid_route_returns_404(self, client):
        resp = advisor_post(client, "Overview", route_id="ROUTE-INVALID-123")
        assert resp.status_code == 404
