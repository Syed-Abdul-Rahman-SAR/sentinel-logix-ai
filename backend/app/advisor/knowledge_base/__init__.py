"""
SENTINEL LOGIX AI - Advisor Knowledge Base
Phase 11D: Knowledge Base & Retrieval Foundation

Exposes the primary retrieval entry point:
    KnowledgeRetriever — searches local KB articles and returns relevant excerpts
                         ranked by keyword overlap.

The KB is a local, version-controlled collection of trusted articles about
SENTINEL itself.  It is NOT a live-data source; live operational values always
come from the existing service layer (inventory, risk, readiness, environment,
digital_twin).
"""

from .retriever import KnowledgeRetriever, KBArticle, KBSearchResult

__all__ = ["KnowledgeRetriever", "KBArticle", "KBSearchResult"]
