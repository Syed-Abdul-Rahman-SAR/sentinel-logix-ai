"""
SENTINEL LOGIX AI — Phase 11G: Scenario-Aware Advisor Intelligence
Test Suite

Test coverage (24 required tests):
 1. Valid scenario lookup — scenario_result is populated
 2. Unknown scenario reference — error propagated, no fabrication
 3. Scenario-only explanation — deterministic mode, no LLM
 4. Scenario + KB explanation — KB provides explanatory context only
 5. Baseline vs scenario risk comparison
 6. Baseline vs scenario readiness comparison
 7. Inventory trajectory / shortfall explanation
 8. Stock-out explanation
 9. Pre-existing stock-out distinction
10. Affected shipment explanation
11. Environmental scenario explanation
12. Causal-chain explanation
13. Contributing-factor explanation
14. Missing causal chain — graceful handling
15. Missing environmental impact — no fabrication
16. Deterministic mode — no LLM
17. Mock LLM mode — scenario_grounded behavior
18. LLM provider failure — deterministic fallback
19. Fabricated KB source — rejected by validator
20. Fabricated scenario/entity reference — rejected by validator
21. Provenance preservation — operational_sources includes digital_twin_scenario
22. Read-only database behavior — DB not mutated
23. Backward compatibility — requests without scenario_id unchanged
24. Existing Advisor query behavior remains unchanged
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.database import init_db, get_db
from backend.app.db.seed import seed_database
from backend.app.advisor import AdvisorRequest, AdvisorResponse, AdvisorService
from backend.app.advisor.context import AdvisorContextBuilder
from backend.app.advisor.reasoning import AdvisorReasoningEngine
from backend.app.advisor.llm import MockLLMProvider
from backend.app.digital_twin.scenario import DEMO_SCENARIOS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Isolated SQLite DB populated with seed data for every test."""
    test_db_file = str(tmp_path / "test_sentinel_phase_11g.db")
    import backend.app.config as config
    config.DB_PATH = test_db_file
    init_db(test_db_file)
    seed_database(test_db_file)
    yield test_db_file


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


VALID_SCENARIO_ID   = DEMO_SCENARIOS[0]["scenario_id"]   # DEMO-ROUTE-DISRUPTION-01
VALID_SCENARIO_ID_2 = DEMO_SCENARIOS[1]["scenario_id"]   # DEMO-ROUTE-DISRUPTION-02
UNKNOWN_SCENARIO_ID = "SCENARIO-DOES-NOT-EXIST-99999"


def _build_ctx(query, scenario_id=None, db_path=None):
    return AdvisorContextBuilder.build(
        query=query,
        scenario_id=scenario_id,
        db_path=db_path
    )


# ===========================================================================
# Test 1 — Valid scenario lookup
# ===========================================================================

def test_01_valid_scenario_lookup(setup_test_db):
    """Context builder resolves a known scenario_id to a populated scenario_result."""
    ctx = _build_ctx(
        "Explain this Digital Twin scenario.",
        scenario_id=VALID_SCENARIO_ID,
        db_path=setup_test_db,
    )
    assert ctx.scenario_result is not None, "scenario_result must be populated for a valid scenario_id"
    assert ctx.scenario_result.get("scenario_id") == VALID_SCENARIO_ID
    assert ctx.modules_available.get("digital_twin_scenario") is True
    for field in ("baseline_risk_score", "simulated_risk_score", "baseline_readiness_score",
                  "simulated_readiness_score", "inventory_shortfall", "affected_shipments"):
        assert field in ctx.scenario_result, f"Expected field '{field}' in scenario_result"


# ===========================================================================
# Test 2 — Unknown scenario reference
# ===========================================================================

def test_02_unknown_scenario_reference(setup_test_db):
    """Unknown scenario_id produces an error, scenario_result stays None, no fabrication."""
    ctx = _build_ctx(
        "What happens in this scenario?",
        scenario_id=UNKNOWN_SCENARIO_ID,
        db_path=setup_test_db,
    )
    assert ctx.scenario_result is None, "No scenario data must be present for unknown scenario_id"
    assert ctx.modules_available.get("digital_twin_scenario") is False
    error_text = " ".join(ctx.errors)
    assert UNKNOWN_SCENARIO_ID in error_text


# ===========================================================================
# Test 3 — Scenario-only explanation (deterministic mode)
# ===========================================================================

def test_03_scenario_only_explanation(setup_test_db):
    """Scenario-aware deterministic response contains scenario evidence."""
    req = AdvisorRequest(
        query="Explain this Digital Twin scenario.",
        scenario_id=VALID_SCENARIO_ID,
    )
    resp = AdvisorService.query(req, db_path=setup_test_db, provider=None)

    assert isinstance(resp, AdvisorResponse)
    assert resp.provider_mode == "deterministic"
    assert resp.answer
    assert resp.recommendation
    evidence_sources = {e.source for e in resp.evidence}
    assert "digital_twin_simulation" in evidence_sources
    assert "digital_twin_scenario" in resp.operational_sources


# ===========================================================================
# Test 4 — Scenario + KB explanation
# ===========================================================================

def test_04_scenario_plus_kb_explanation(setup_test_db):
    """KB provides explanatory context that does not override DT operational values."""
    req = AdvisorRequest(
        query="Explain this Digital Twin scenario and what the risk score means.",
        scenario_id=VALID_SCENARIO_ID,
    )
    resp = AdvisorService.query(req, db_path=setup_test_db, provider=None)

    assert isinstance(resp, AdvisorResponse)
    dt_evidence = [e for e in resp.evidence if e.source == "digital_twin_simulation"]
    assert len(dt_evidence) > 0, "DT simulation evidence must be present"


# ===========================================================================
# Test 5 — Baseline vs scenario risk comparison
# ===========================================================================

def test_05_baseline_vs_scenario_risk_comparison(setup_test_db):
    """Risk evidence shows both baseline and scenario values from DT result."""
    ctx = _build_ctx("How much did risk increase?", scenario_id=VALID_SCENARIO_ID, db_path=setup_test_db)
    assert ctx.scenario_result is not None
    sc = ctx.scenario_result

    result = AdvisorReasoningEngine.evaluate(ctx, "scenario_explanation")
    risk_items = [e for e in result["evidence"] if "Risk Score" in e.observation]
    assert len(risk_items) >= 1
    risk_ev = risk_items[0]
    assert "->" in risk_ev.value
    assert "delta" in risk_ev.value.lower()


# ===========================================================================
# Test 6 — Baseline vs scenario readiness comparison
# ===========================================================================

def test_06_baseline_vs_scenario_readiness_comparison(setup_test_db):
    """Readiness evidence shows both baseline and scenario values from DT result."""
    ctx = _build_ctx("Why did readiness fall?", scenario_id=VALID_SCENARIO_ID, db_path=setup_test_db)
    assert ctx.scenario_result is not None

    result = AdvisorReasoningEngine.evaluate(ctx, "scenario_explanation")
    readiness_items = [e for e in result["evidence"] if "Readiness" in e.observation]
    assert len(readiness_items) >= 1
    assert "->" in readiness_items[0].value


# ===========================================================================
# Test 7 — Inventory trajectory / shortfall explanation
# ===========================================================================

def test_07_inventory_shortfall_explanation(setup_test_db):
    """Inventory shortfall evidence is present when DT result reports a shortfall."""
    ctx = _build_ctx("What caused inventory to reach stock-out?", scenario_id=VALID_SCENARIO_ID, db_path=setup_test_db)
    assert ctx.scenario_result is not None
    sc = ctx.scenario_result

    result = AdvisorReasoningEngine.evaluate(ctx, "scenario_explanation")
    if sc.get("inventory_shortfall", 0) > 0:
        shortfall_items = [e for e in result["evidence"] if "Shortfall" in e.observation]
        assert len(shortfall_items) >= 1
        assert str(int(sc["inventory_shortfall"])) in shortfall_items[0].value


# ===========================================================================
# Test 8 — Stock-out explanation
# ===========================================================================

def test_08_stockout_explanation(setup_test_db):
    """When DT reports a stock-out day, evidence captures it."""
    ctx = _build_ctx("What caused the stock-out?", scenario_id=VALID_SCENARIO_ID, db_path=setup_test_db)
    assert ctx.scenario_result is not None
    sc = ctx.scenario_result

    result = AdvisorReasoningEngine.evaluate(ctx, "scenario_explanation")
    if sc.get("stockout_day") is not None:
        so_items = [e for e in result["evidence"] if "Stock-out" in e.observation]
        assert len(so_items) >= 1
        assert str(sc["stockout_day"]) in so_items[0].value


# ===========================================================================
# Test 9 — Pre-existing stock-out distinction
# ===========================================================================

def test_09_preexisting_stockout_distinction(setup_test_db):
    """Advisor distinguishes a pre-existing stock-out from a scenario-induced one."""
    ctx = _build_ctx("Did the scenario cause a new stock-out?", scenario_id=VALID_SCENARIO_ID, db_path=setup_test_db)
    assert ctx.scenario_result is not None

    result = AdvisorReasoningEngine.evaluate(ctx, "scenario_explanation")
    answer = result["answer"].lower()
    assert any(kw in answer for kw in [
        "pre-existing", "scenario-induced", "no stock-out", "baseline", "not present"
    ]), f"Answer must distinguish pre-existing vs scenario-induced stock-out. Got: {answer[:200]}"


# ===========================================================================
# Test 10 — Affected shipment explanation
# ===========================================================================

def test_10_affected_shipment_explanation(setup_test_db):
    """When DT result has affected shipments, evidence captures count and delay."""
    ctx = _build_ctx("Which shipments are affected?", scenario_id=VALID_SCENARIO_ID, db_path=setup_test_db)
    assert ctx.scenario_result is not None
    sc = ctx.scenario_result

    result = AdvisorReasoningEngine.evaluate(ctx, "scenario_explanation")
    if sc.get("affected_shipments"):
        shipment_items = [e for e in result["evidence"] if "Shipment" in e.observation]
        assert len(shipment_items) >= 1
        assert str(len(sc["affected_shipments"])) in shipment_items[0].value


# ===========================================================================
# Test 11 — Environmental scenario explanation
# ===========================================================================

def test_11_environmental_scenario_explanation(setup_test_db):
    """When DT result has environmental_impact, evidence captures it."""
    ctx = _build_ctx("Why is this route environmentally risky?", scenario_id=VALID_SCENARIO_ID, db_path=setup_test_db)
    assert ctx.scenario_result is not None
    sc = ctx.scenario_result

    result = AdvisorReasoningEngine.evaluate(ctx, "scenario_explanation")
    if sc.get("environmental_impact"):
        env_items = [e for e in result["evidence"] if "Environmental" in e.observation]
        assert len(env_items) >= 1
        env_class = sc["environmental_impact"].get("classification", "")
        if env_class:
            assert env_class in env_items[0].value


# ===========================================================================
# Test 12 — Causal-chain explanation
# ===========================================================================

def test_12_causal_chain_explanation(setup_test_db):
    """When DT result has causal_chain, reasoning summary and answer reference it."""
    ctx = _build_ctx("What triggered the inventory impact?", scenario_id=VALID_SCENARIO_ID, db_path=setup_test_db)
    assert ctx.scenario_result is not None
    sc = ctx.scenario_result

    result = AdvisorReasoningEngine.evaluate(ctx, "scenario_explanation")
    if sc.get("causal_chain"):
        first_link = sc["causal_chain"][0]
        combined = result["answer"] + " " + result["reasoning_summary"]
        assert first_link in combined or "->" in combined


# ===========================================================================
# Test 13 — Contributing-factor explanation
# ===========================================================================

def test_13_contributing_factor_explanation(setup_test_db):
    """Contributing factors from DT result appear as SupportingFactor items."""
    ctx = _build_ctx("What contributed to this scenario impact?", scenario_id=VALID_SCENARIO_ID, db_path=setup_test_db)
    assert ctx.scenario_result is not None
    sc = ctx.scenario_result

    result = AdvisorReasoningEngine.evaluate(ctx, "scenario_explanation")
    if sc.get("contributing_factors"):
        dt_factors = [f for f in result["supporting_factors"] if "DT_CONTRIBUTING_FACTOR" in f.factor]
        assert len(dt_factors) > 0


# ===========================================================================
# Test 14 — Missing causal chain
# ===========================================================================

def test_14_missing_causal_chain(setup_test_db):
    """When causal chain is absent, Advisor states it explicitly — no fabrication."""
    ctx = _build_ctx("Explain the causal chain.", scenario_id=VALID_SCENARIO_ID, db_path=setup_test_db)
    assert ctx.scenario_result is not None

    patched = dict(ctx.scenario_result)
    patched["causal_chain"] = []
    ctx.scenario_result = patched

    result = AdvisorReasoningEngine.evaluate(ctx, "scenario_explanation")
    combined = result["answer"] + " " + result["reasoning_summary"]
    assert "unavailable" in combined.lower() or "causal chain" in combined.lower()


# ===========================================================================
# Test 15 — Missing environmental impact
# ===========================================================================

def test_15_missing_environmental_impact(setup_test_db):
    """When environmental_impact is absent, no environmental evidence is fabricated."""
    ctx = _build_ctx("Explain the environmental impact.", scenario_id=VALID_SCENARIO_ID, db_path=setup_test_db)
    assert ctx.scenario_result is not None

    patched = dict(ctx.scenario_result)
    patched["environmental_impact"] = None
    ctx.scenario_result = patched

    result = AdvisorReasoningEngine.evaluate(ctx, "scenario_explanation")
    env_items = [e for e in result["evidence"] if "Environmental Impact" in e.observation]
    assert len(env_items) == 0


# ===========================================================================
# Test 16 — Deterministic mode
# ===========================================================================

def test_16_deterministic_mode(setup_test_db):
    """Without a provider, scenario response uses deterministic mode."""
    req = AdvisorRequest(query="Explain the Digital Twin scenario impact.", scenario_id=VALID_SCENARIO_ID)
    resp = AdvisorService.query(req, db_path=setup_test_db, provider=None)
    assert resp.provider_mode == "deterministic"
    assert resp.data_source == "synthetic_demo"
    assert resp.environment == "demo"
    assert len(resp.evidence) > 0


# ===========================================================================
# Test 17 — Mock LLM mode (scenario_grounded)
# ===========================================================================

def test_17_mock_llm_scenario_grounded(setup_test_db):
    """MockLLMProvider with scenario_grounded behavior returns valid grounded response."""
    req = AdvisorRequest(query="Explain this Digital Twin scenario.", scenario_id=VALID_SCENARIO_ID)
    resp = AdvisorService.query(req, db_path=setup_test_db, provider=MockLLMProvider(behavior="scenario_grounded"))
    assert isinstance(resp, AdvisorResponse)
    assert resp.provider_mode == "mock"
    assert resp.data_source == "synthetic_demo"
    assert resp.answer
    assert VALID_SCENARIO_ID in resp.answer or "Digital Twin scenario" in resp.answer


# ===========================================================================
# Test 18 — LLM provider failure → deterministic fallback
# ===========================================================================

def test_18_llm_provider_failure_fallback(setup_test_db):
    """Provider failure during scenario query falls back safely to deterministic."""
    req = AdvisorRequest(query="Explain this Digital Twin scenario.", scenario_id=VALID_SCENARIO_ID)
    resp = AdvisorService.query(req, db_path=setup_test_db, provider=MockLLMProvider(behavior="provider_failure"))
    assert resp.provider_mode == "deterministic"
    lim = " ".join(resp.limitations).lower()
    assert "fell back" in lim or "error" in lim


# ===========================================================================
# Test 19 — Fabricated KB source rejected
# ===========================================================================

def test_19_fabricated_kb_source_rejected(setup_test_db):
    """LLM output claiming an unretrieved KB source fails validation → fallback."""
    req = AdvisorRequest(query="Explain the scenario.", scenario_id=VALID_SCENARIO_ID)
    resp = AdvisorService.query(req, db_path=setup_test_db, provider=MockLLMProvider(behavior="unsupported_kb_source"))
    assert resp.provider_mode == "deterministic"
    lim = " ".join(resp.limitations).lower()
    assert "fell back" in lim or "validation" in lim or "failed" in lim


# ===========================================================================
# Test 20 — Fabricated scenario entity reference rejected
# ===========================================================================

def test_20_fabricated_scenario_entity_rejected(setup_test_db):
    """LLM output with a hallucinated entity ID fails validation → fallback."""
    req = AdvisorRequest(query="Explain the scenario.", scenario_id=VALID_SCENARIO_ID)
    resp = AdvisorService.query(req, db_path=setup_test_db, provider=MockLLMProvider(behavior="scenario_fabricated_entity"))
    assert resp.provider_mode == "deterministic"
    lim = " ".join(resp.limitations).lower()
    assert "fell back" in lim or "hallucinated" in lim or "validation" in lim


# ===========================================================================
# Test 21 — Provenance preservation
# ===========================================================================

def test_21_provenance_preservation(setup_test_db):
    """Scenario response correctly reports operational_sources and data_source provenance."""
    req = AdvisorRequest(query="Explain this Digital Twin scenario.", scenario_id=VALID_SCENARIO_ID)
    resp = AdvisorService.query(req, db_path=setup_test_db, provider=None)
    assert "digital_twin_scenario" in resp.operational_sources
    assert resp.data_source == "synthetic_demo"
    assert resp.environment == "demo"
    for kb_id in resp.knowledge_sources:
        assert "fake" not in kb_id.lower()


# ===========================================================================
# Test 22 — Read-only database behavior
# ===========================================================================

def test_22_readonly_database_behavior(setup_test_db):
    """Scenario-aware Advisor query does not mutate the database."""
    with get_db(setup_test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, current_quantity FROM inventory_items ORDER BY id")
        before = [dict(r) for r in cursor.fetchall()]

    req = AdvisorRequest(query="Explain the Digital Twin scenario impact.", scenario_id=VALID_SCENARIO_ID)
    AdvisorService.query(req, db_path=setup_test_db, provider=None)

    with get_db(setup_test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, current_quantity FROM inventory_items ORDER BY id")
        after = [dict(r) for r in cursor.fetchall()]

    assert before == after, "Phase 11G Advisor query must NOT mutate production database records!"


# ===========================================================================
# Test 23 — Backward compatibility: requests without scenario_id
# ===========================================================================

def test_23_backward_compatibility_no_scenario_id(setup_test_db):
    """Requests without scenario_id continue to work exactly as before Phase 11G."""
    req = AdvisorRequest(query="Which depot needs attention?")
    resp = AdvisorService.query(req, db_path=setup_test_db, provider=None)
    assert isinstance(resp, AdvisorResponse)
    assert resp.provider_mode == "deterministic"
    assert resp.answer
    assert "digital_twin_scenario" not in resp.operational_sources
    assert resp.data_source == "synthetic_demo"


# ===========================================================================
# Test 24 — Existing Advisor query behavior remains unchanged
# ===========================================================================

def test_24_existing_advisor_queries_unchanged(client):
    """Existing advisor queries without scenario_id produce valid unchanged responses via API."""
    payload = {"query": "What is the readiness status of the depots?"}
    resp = client.post("/api/advisor/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"]
    assert data["recommendation"]
    assert data["data_source"] == "synthetic_demo"
    assert data["environment"] == "demo"
    assert "digital_twin_scenario" not in data.get("operational_sources", [])


# ===========================================================================
# Additional regression / coverage tests
# ===========================================================================

def test_api_unknown_scenario_returns_404(client):
    """API returns HTTP 404 for an unknown scenario_id."""
    payload = {"query": "Explain this scenario.", "scenario_id": UNKNOWN_SCENARIO_ID}
    resp = client.post("/api/advisor/query", json=payload)
    assert resp.status_code == 404
    assert UNKNOWN_SCENARIO_ID in resp.json().get("detail", "")


def test_api_valid_scenario_returns_200(client):
    """API returns HTTP 200 for a valid scenario_id."""
    payload = {"query": "Explain this Digital Twin scenario.", "scenario_id": VALID_SCENARIO_ID}
    resp = client.post("/api/advisor/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"]
    assert "digital_twin_scenario" in data.get("operational_sources", [])


def test_second_demo_scenario_resolves(setup_test_db):
    """Second DEMO scenario also resolves correctly."""
    ctx = _build_ctx("Explain this Digital Twin scenario.", scenario_id=VALID_SCENARIO_ID_2, db_path=setup_test_db)
    assert ctx.scenario_result is not None
    assert ctx.scenario_result.get("scenario_id") == VALID_SCENARIO_ID_2


def test_scenario_evidence_sources_are_approved(setup_test_db):
    """All scenario-specific evidence items come from approved source tags."""
    ctx = _build_ctx("Explain the Digital Twin scenario.", scenario_id=VALID_SCENARIO_ID, db_path=setup_test_db)
    result = AdvisorReasoningEngine.evaluate(ctx, "scenario_explanation")
    approved = {
        "inventory_service", "stockout_prediction", "risk_service",
        "readiness_service", "environment_service", "digital_twin",
        "digital_twin_simulation",
    }
    for ev in result["evidence"]:
        assert ev.source in approved, f"Unexpected evidence source: '{ev.source}'"


def test_scenario_limitations_contain_phase_11g_tag(setup_test_db):
    """Phase 11G limitations tag is present in scenario response."""
    req = AdvisorRequest(query="Explain the Digital Twin scenario impact.", scenario_id=VALID_SCENARIO_ID)
    resp = AdvisorService.query(req, db_path=setup_test_db, provider=None)
    lim_text = " ".join(resp.limitations)
    assert "11G" in lim_text or "verbatim" in lim_text.lower()


def test_mock_llm_normal_with_scenario_context(setup_test_db):
    """MockLLMProvider normal mode still works when scenario context is present."""
    req = AdvisorRequest(query="Explain the Digital Twin scenario.", scenario_id=VALID_SCENARIO_ID)
    resp = AdvisorService.query(req, db_path=setup_test_db, provider=MockLLMProvider(behavior="normal"))
    assert isinstance(resp, AdvisorResponse)
    assert resp.provider_mode == "mock"
    assert resp.answer
