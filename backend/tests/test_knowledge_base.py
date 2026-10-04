"""
SENTINEL LOGIX AI - Phase 11D: Knowledge Base & Retrieval Foundation Tests

Tests cover:
  - KBArticle and KBSearchResult data models
  - Article loading from the articles/ directory
  - KnowledgeRetriever.search() — relevance ranking, top_k, category filtering, min_relevance
  - KnowledgeRetriever.get_article() — exact article retrieval by ID
  - KnowledgeRetriever.list_categories() — category enumeration
  - KnowledgeRetriever.article_count() — total loaded articles
  - Empty / blank query edge cases
  - KB integration in AdvisorContext (context.kb_excerpts populated)
  - KB context surfaced in AdvisorResponse (kb_context field)
  - KB module_available tracking
  - Grounding prompt includes KB section when excerpts present
  - KnowledgeRetriever.reload() — hot-reload returns a count >= 0
  - Provenance: KB articles never override live operational data signals
  - Phase 11D is backward-compatible (all existing advisor tests still pass)

All tests are read-only; no modifications to production data or article files.
"""

import pytest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# KB Module imports
# ---------------------------------------------------------------------------

from backend.app.advisor.knowledge_base.retriever import (
    KBArticle,
    KBSearchResult,
    KnowledgeRetriever,
    _tokenise,
    _extract_excerpt,
    _parse_frontmatter,
    _parse_tags,
)
from backend.app.advisor.knowledge_base import KnowledgeRetriever as PublicRetriever

# ---------------------------------------------------------------------------
# Advisor integration imports
# ---------------------------------------------------------------------------

from backend.app.advisor.schemas import AdvisorRequest, AdvisorResponse
from backend.app.advisor.context import AdvisorContext, AdvisorContextBuilder
from backend.app.advisor.service import AdvisorService
from backend.app.advisor.llm.base import BaseLLMProvider

# FastAPI test client
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


# ===========================================================================
# 1. Data model tests
# ===========================================================================

class TestKBDataModels:

    def test_kb_article_is_frozen(self):
        """KBArticle is immutable (frozen=True)."""
        article = KBArticle(
            article_id="test-001",
            title="Test Article",
            category="system",
            content="Content here.",
            tags=frozenset(["test", "article"]),
            source_file="test-001.md",
        )
        with pytest.raises((AttributeError, TypeError)):
            article.title = "Changed"  # type: ignore[misc]

    def test_kb_article_tags_are_frozenset(self):
        article = KBArticle(
            article_id="test-002",
            title="Tags Test",
            category="risk",
            content="content",
            tags=frozenset(["risk", "score"]),
            source_file="test-002.md",
        )
        assert isinstance(article.tags, frozenset)
        assert "risk" in article.tags

    def test_kb_search_result_fields(self):
        result = KBSearchResult(
            article_id="kb-risk-001",
            title="Risk Article",
            category="risk",
            relevance=0.75,
            excerpt="Some excerpt text",
            matched_tags=["risk", "score"],
        )
        assert result.article_id == "kb-risk-001"
        assert result.relevance == 0.75
        assert "risk" in result.matched_tags

    def test_kb_search_result_relevance_bounds(self):
        """Relevance is always a float between 0 and 1."""
        result = KBSearchResult(
            article_id="kb-x",
            title="X",
            category="system",
            relevance=0.0,
            excerpt="",
            matched_tags=[],
        )
        assert 0.0 <= result.relevance <= 1.0


# ===========================================================================
# 2. Article loading tests
# ===========================================================================

class TestArticleLoading:

    def test_article_count_is_positive(self):
        """At least some articles should be loaded from the articles/ dir."""
        count = KnowledgeRetriever.article_count()
        assert count >= 10, f"Expected >= 10 articles, got {count}"

    def test_categories_are_non_empty(self):
        cats = KnowledgeRetriever.list_categories()
        assert len(cats) > 0

    def test_expected_categories_present(self):
        cats = KnowledgeRetriever.list_categories()
        for expected in ("risk", "inventory", "readiness", "environment", "digital_twin", "logistics", "system"):
            assert expected in cats, f"Category '{expected}' not found in {cats}"

    def test_all_articles_have_ids(self):
        """All loaded articles must have non-empty article_id."""
        for article in KnowledgeRetriever._get():
            assert article.article_id, f"Article missing ID: {article}"

    def test_all_articles_have_titles(self):
        for article in KnowledgeRetriever._get():
            assert article.title, f"Article missing title: {article}"

    def test_all_articles_have_content(self):
        for article in KnowledgeRetriever._get():
            assert article.content.strip(), f"Article has empty content: {article.article_id}"

    def test_article_ids_are_unique(self):
        ids = [a.article_id for a in KnowledgeRetriever._get()]
        assert len(ids) == len(set(ids)), "Duplicate article IDs found"

    def test_known_article_ids_present(self):
        """Specific Phase 11D articles must be present."""
        known_ids = {
            "kb-system-001",
            "kb-risk-001",
            "kb-stockout-001",
            "kb-readiness-001",
            "kb-environment-001",
            "kb-digital-twin-001",
            "kb-logistics-001",
            "kb-advisor-001",
            "kb-forecasting-001",
            "kb-replenishment-001",
        }
        loaded_ids = {a.article_id for a in KnowledgeRetriever._get()}
        missing = known_ids - loaded_ids
        assert not missing, f"Missing expected KB articles: {missing}"


# ===========================================================================
# 3. KnowledgeRetriever.get_article() tests
# ===========================================================================

class TestGetArticle:

    def test_get_article_known_id(self):
        article = KnowledgeRetriever.get_article("kb-risk-001")
        assert article is not None
        assert article.article_id == "kb-risk-001"
        assert article.category == "risk"

    def test_get_article_system(self):
        article = KnowledgeRetriever.get_article("kb-system-001")
        assert article is not None
        assert "SENTINEL" in article.title

    def test_get_article_unknown_returns_none(self):
        result = KnowledgeRetriever.get_article("kb-nonexistent-999")
        assert result is None

    def test_get_article_empty_id_returns_none(self):
        result = KnowledgeRetriever.get_article("")
        assert result is None

    def test_get_article_content_not_empty(self):
        for article_id in ("kb-risk-001", "kb-readiness-001", "kb-environment-001"):
            article = KnowledgeRetriever.get_article(article_id)
            assert article is not None
            assert len(article.content) > 100, f"Article {article_id} content too short"


# ===========================================================================
# 4. KnowledgeRetriever.search() tests
# ===========================================================================

class TestKBSearch:

    def test_search_risk_query(self):
        results = KnowledgeRetriever.search("what causes high risk scores?")
        assert len(results) > 0
        # Risk article should be near the top
        top_ids = [r.article_id for r in results[:3]]
        assert "kb-risk-001" in top_ids, f"Risk article not in top 3: {top_ids}"

    def test_search_stockout_query(self):
        results = KnowledgeRetriever.search("how is days until stockout calculated?")
        assert len(results) > 0
        top_ids = [r.article_id for r in results[:3]]
        assert "kb-stockout-001" in top_ids, f"Stockout article not in top 3: {top_ids}"

    def test_search_readiness_query(self):
        results = KnowledgeRetriever.search("what is mission readiness status?")
        assert len(results) > 0
        top_ids = [r.article_id for r in results[:3]]
        assert "kb-readiness-001" in top_ids

    def test_search_environment_query(self):
        results = KnowledgeRetriever.search("route weather terrain risk environmental")
        assert len(results) > 0
        top_ids = [r.article_id for r in results[:3]]
        assert "kb-environment-001" in top_ids

    def test_search_digital_twin_query(self):
        results = KnowledgeRetriever.search("scenario simulation digital twin what if")
        assert len(results) > 0
        top_ids = [r.article_id for r in results[:3]]
        assert "kb-digital-twin-001" in top_ids

    def test_search_returns_sorted_by_relevance(self):
        results = KnowledgeRetriever.search("risk critical high depot inventory")
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].relevance >= results[i + 1].relevance, \
                    "Results not sorted by descending relevance"

    def test_search_top_k_respected(self):
        results = KnowledgeRetriever.search("depot inventory risk readiness route", top_k=2)
        assert len(results) <= 2

    def test_search_top_k_default_is_5(self):
        results = KnowledgeRetriever.search("risk depot readiness inventory route")
        assert len(results) <= 5

    def test_search_category_filter_risk(self):
        results = KnowledgeRetriever.search("risk score", category_filter="risk")
        for r in results:
            assert r.category == "risk", f"Expected category 'risk', got '{r.category}'"

    def test_search_category_filter_system(self):
        results = KnowledgeRetriever.search("sentinel system overview", category_filter="system")
        for r in results:
            assert r.category == "system"

    def test_search_category_filter_nonexistent_returns_empty(self):
        results = KnowledgeRetriever.search("anything", category_filter="nonexistent_category_xyz")
        assert results == []

    def test_search_blank_query_returns_empty(self):
        assert KnowledgeRetriever.search("") == []

    def test_search_whitespace_only_query_returns_empty(self):
        assert KnowledgeRetriever.search("   ") == []

    def test_search_stopwords_only_query_returns_empty(self):
        # After stop-word filtering, "is the a and" has no meaningful tokens
        results = KnowledgeRetriever.search("is the a and or to of")
        # Should return empty or very low relevance results
        # Allow empty or very few results (stop-word queries should not produce high-confidence matches)
        for r in results:
            assert r.relevance < 0.2, f"Stop-word query produced suspiciously high relevance: {r.relevance}"

    def test_search_result_has_excerpt(self):
        results = KnowledgeRetriever.search("risk critical depot")
        for r in results:
            assert isinstance(r.excerpt, str)

    def test_search_result_has_matched_tags(self):
        results = KnowledgeRetriever.search("risk score critical")
        assert any(len(r.matched_tags) > 0 for r in results), \
            "No results had matched tags"

    def test_search_min_relevance_filters_low_scores(self):
        results_strict = KnowledgeRetriever.search("risk", min_relevance=0.3)
        results_loose = KnowledgeRetriever.search("risk", min_relevance=0.01)
        # Strict should return <= count from loose
        assert len(results_strict) <= len(results_loose)
        for r in results_strict:
            assert r.relevance >= 0.3


# ===========================================================================
# 5. Tokeniser and excerpt helper tests
# ===========================================================================

class TestHelpers:

    def test_tokenise_removes_stop_words(self):
        tokens = _tokenise("the risk is high and critical")
        assert "the" not in tokens
        assert "is" not in tokens
        assert "and" not in tokens
        assert "risk" in tokens
        assert "high" in tokens
        assert "critical" in tokens

    def test_tokenise_lowercases(self):
        tokens = _tokenise("RISK CRITICAL DEPOT")
        assert "risk" in tokens
        assert "RISK" not in tokens

    def test_tokenise_empty_string(self):
        assert _tokenise("") == set()

    def test_extract_excerpt_returns_string(self):
        content = "First paragraph about risk.\n\nSecond paragraph about stockout.\n\nThird about readiness."
        excerpt = _extract_excerpt(content, {"risk"})
        assert isinstance(excerpt, str)
        assert len(excerpt) > 0

    def test_extract_excerpt_max_length(self):
        content = "x" * 1000
        excerpt = _extract_excerpt(content, {"x"}, max_length=100)
        assert len(excerpt) <= 100

    def test_parse_frontmatter_extracts_fields(self):
        raw = "---\nid: test-001\ntitle: Test Title\ncategory: risk\ntags: [risk, test]\n---\nBody content here.\n"
        meta, body = _parse_frontmatter(raw)
        assert meta["id"] == "test-001"
        assert meta["title"] == "Test Title"
        assert meta["category"] == "risk"
        assert "Body content here" in body

    def test_parse_frontmatter_no_frontmatter(self):
        raw = "Just body content with no frontmatter."
        meta, body = _parse_frontmatter(raw)
        assert meta == {}
        assert "Just body" in body

    def test_parse_tags_bracket_format(self):
        tags = _parse_tags("[risk, stockout, critical]")
        assert "risk" in tags
        assert "stockout" in tags
        assert "critical" in tags

    def test_parse_tags_comma_format(self):
        tags = _parse_tags("risk, stockout, critical")
        assert "risk" in tags
        assert "stockout" in tags

    def test_parse_tags_lowercased(self):
        tags = _parse_tags("[RISK, Stockout]")
        assert "risk" in tags
        assert "stockout" in tags


# ===========================================================================
# 6. Public package interface tests
# ===========================================================================

class TestPublicInterface:

    def test_public_import_works(self):
        """KnowledgeRetriever importable from knowledge_base package."""
        assert PublicRetriever is KnowledgeRetriever

    def test_reload_returns_count(self):
        count = KnowledgeRetriever.reload()
        assert isinstance(count, int)
        assert count >= 10

    def test_article_count_consistent_with_reload(self):
        count_before = KnowledgeRetriever.article_count()
        count_after = KnowledgeRetriever.reload()
        assert count_before == count_after


# ===========================================================================
# 7. AdvisorContext KB integration tests
# ===========================================================================

class TestContextKBIntegration:

    def test_context_has_kb_excerpts_field(self):
        """AdvisorContext has kb_excerpts list field."""
        ctx = AdvisorContext()
        assert hasattr(ctx, "kb_excerpts")
        assert isinstance(ctx.kb_excerpts, list)

    def test_context_builder_populates_kb_excerpts(self):
        """AdvisorContextBuilder.build() populates kb_excerpts."""
        ctx = AdvisorContextBuilder.build(query="what is the risk score?")
        assert isinstance(ctx.kb_excerpts, list)
        # Should find risk-related articles
        assert len(ctx.kb_excerpts) >= 1

    def test_context_builder_kb_module_available(self):
        ctx = AdvisorContextBuilder.build(query="risk depot inventory")
        assert ctx.modules_available.get("knowledge_base") is True

    def test_context_builder_kb_excerpts_are_kb_search_results(self):
        ctx = AdvisorContextBuilder.build(query="risk critical depot")
        for item in ctx.kb_excerpts:
            assert isinstance(item, KBSearchResult)

    def test_context_builder_kb_fail_safe(self):
        """If KB retrieval fails, context.errors is updated but no exception raised."""
        with patch("backend.app.advisor.context.KnowledgeRetriever.search",
                   side_effect=RuntimeError("KB test failure")):
            ctx = AdvisorContextBuilder.build(query="risk query")
        assert ctx.modules_available.get("knowledge_base") is False
        assert any("knowledge_base" in e.lower() or "knowledge base" in e.lower()
                   for e in ctx.errors)

    def test_context_kb_excerpts_empty_for_stopword_query(self):
        """Queries with only stop words produce no or few KB excerpts."""
        ctx = AdvisorContextBuilder.build(query="the is a and to of")
        # Result should be empty or at least have very low relevance
        for item in ctx.kb_excerpts:
            assert item.relevance < 0.2


# ===========================================================================
# 8. AdvisorResponse KB context field tests
# ===========================================================================

class TestResponseKBContext:

    def test_advisor_response_has_kb_context_field(self):
        """AdvisorResponse schema has kb_context field."""
        resp = AdvisorResponse(
            query="test",
            answer="test answer",
            recommendation="test rec",
            priority="LOW",
            confidence=50,
        )
        assert hasattr(resp, "kb_context")
        assert isinstance(resp.kb_context, list)

    def test_service_query_populates_kb_context(self):
        """AdvisorService.query() populates kb_context with article titles."""
        request = AdvisorRequest(query="what causes critical risk?")
        response = AdvisorService.query(request)
        assert hasattr(response, "kb_context")
        assert isinstance(response.kb_context, list)

    def test_service_query_kb_context_contains_relevant_titles(self):
        """kb_context entries contain article IDs in bracket notation."""
        request = AdvisorRequest(query="how is risk score calculated?")
        response = AdvisorService.query(request)
        # All kb_context entries should have a bracket-enclosed ID
        for entry in response.kb_context:
            assert "[" in entry and "]" in entry, \
                f"KB context entry missing article ID brackets: {entry}"

    def test_api_response_includes_kb_context(self):
        """POST /api/advisor/query response JSON includes kb_context field."""
        res = client.post("/api/advisor/query", json={
            "query": "what items are at risk of stockout?"
        })
        assert res.status_code == 200
        data = res.json()
        assert "kb_context" in data, "Response JSON missing 'kb_context' field"
        assert isinstance(data["kb_context"], list)

    def test_api_kb_context_for_environment_query(self):
        res = client.post("/api/advisor/query", json={
            "query": "what are the route weather and terrain conditions?"
        })
        assert res.status_code == 200
        data = res.json()
        assert "kb_context" in data
        # Should have found environment or route-related articles
        context_text = " ".join(data["kb_context"]).lower()
        assert any(kw in context_text for kw in ("environment", "route", "terrain", "weather")), \
            f"Expected environment-related KB context, got: {data['kb_context']}"

    def test_api_kb_context_for_readiness_query(self):
        res = client.post("/api/advisor/query", json={
            "query": "what is the mission readiness status?"
        })
        assert res.status_code == 200
        data = res.json()
        assert "kb_context" in data

    def test_api_backward_compatible_schema(self):
        """Existing required response fields still present alongside new kb_context."""
        res = client.post("/api/advisor/query", json={"query": "general logistics query"})
        assert res.status_code == 200
        data = res.json()
        for field in ("query", "answer", "recommendation", "priority", "confidence",
                      "evidence", "supporting_factors", "relevant_entities",
                      "provider_mode", "data_source", "environment", "kb_context"):
            assert field in data, f"Missing required field: {field}"


# ===========================================================================
# 9. Grounding prompt KB integration tests
# ===========================================================================

class TestGroundingPromptKB:

    def _make_ctx_with_kb(self) -> AdvisorContext:
        ctx = AdvisorContext()
        ctx.kb_excerpts = [
            KBSearchResult(
                article_id="kb-risk-001",
                title="Understanding Operational Risk Scores in SENTINEL",
                category="risk",
                relevance=0.75,
                excerpt="Risk score is derived from multiple contributing factors including days until stockout.",
                matched_tags=["risk", "score"],
            ),
            KBSearchResult(
                article_id="kb-stockout-001",
                title="Stock-out Prediction",
                category="inventory",
                relevance=0.45,
                excerpt="Days until stockout = current quantity / average daily consumption rate.",
                matched_tags=["stockout", "days_until_stockout"],
            ),
        ]
        return ctx

    def test_grounding_prompt_includes_kb_section(self):
        """build_grounding_prompt() includes KB section header when excerpts present."""
        from backend.app.advisor.llm.base import BaseLLMProvider

        class _DummyProvider(BaseLLMProvider):
            @property
            def provider_name(self): return "dummy"
            def generate(self, context, deterministic_result, query): return {}

        provider = _DummyProvider()
        ctx = self._make_ctx_with_kb()
        prompt = provider.build_grounding_prompt(ctx, "why is risk high?")
        assert "SENTINEL KNOWLEDGE BASE" in prompt.upper(), \
            "Grounding prompt missing KB section header"

    def test_grounding_prompt_includes_article_titles(self):
        from backend.app.advisor.llm.base import BaseLLMProvider

        class _DummyProvider(BaseLLMProvider):
            @property
            def provider_name(self): return "dummy"
            def generate(self, context, deterministic_result, query): return {}

        provider = _DummyProvider()
        ctx = self._make_ctx_with_kb()
        prompt = provider.build_grounding_prompt(ctx, "risk score question")
        assert "kb-risk-001" in prompt
        assert "Understanding Operational Risk Scores" in prompt

    def test_grounding_prompt_no_kb_section_when_empty(self):
        """Grounding prompt omits KB section when no excerpts available."""
        from backend.app.advisor.llm.base import BaseLLMProvider

        class _DummyProvider(BaseLLMProvider):
            @property
            def provider_name(self): return "dummy"
            def generate(self, context, deterministic_result, query): return {}

        provider = _DummyProvider()
        ctx = AdvisorContext()  # Empty kb_excerpts
        prompt = provider.build_grounding_prompt(ctx, "any query")
        assert "KNOWLEDGE BASE" not in prompt.upper()


# ===========================================================================
# 10. Provenance and safety tests
# ===========================================================================

class TestProvenanceAndSafety:

    def test_kb_does_not_override_live_data(self):
        """
        The kb_excerpts in context must never be mistaken for live operational data.
        They are static articles — live values come from service layers only.
        """
        ctx = AdvisorContextBuilder.build(query="risk inventory depot")
        # KB articles should not contain actual inventory quantity data
        for item in ctx.kb_excerpts:
            # Excerpts should be explanatory text, not synthetic data blobs
            assert isinstance(item.excerpt, str)
            # Excerpts do not contain data_source/environment tags (those are live response tags)
            assert "synthetic_demo" not in item.excerpt.lower()

    def test_response_data_source_unchanged(self):
        """KB integration must not change data_source or environment provenance tags."""
        response = AdvisorService.query(AdvisorRequest(query="risk stockout critical"))
        assert response.data_source == "synthetic_demo"
        assert response.environment == "demo"

    def test_response_provider_mode_deterministic(self):
        """Without a configured LLM provider, mode stays deterministic."""
        response = AdvisorService.query(AdvisorRequest(query="readiness depot"))
        assert response.provider_mode == "deterministic"

    def test_kb_context_does_not_contain_real_quantities(self):
        """KB article titles/IDs in kb_context are explanatory labels, not numeric operational data."""
        response = AdvisorService.query(AdvisorRequest(query="risk score factors"))
        for entry in response.kb_context:
            # Should be article title + ID notation, not a number string
            assert any(c.isalpha() for c in entry), \
                f"KB context entry appears to be purely numeric data: {entry}"
