"""
SENTINEL LOGIX AI - Knowledge Base Retriever
Phase 11D: Knowledge Base & Retrieval Foundation

Provides lightweight, local keyword-based retrieval over a static collection of
trusted KB articles about SENTINEL concepts.

Architecture:
  - KBArticle: typed dataclass for each knowledge article.
  - KBSearchResult: typed retrieval result with relevance score and excerpts.
  - KnowledgeRetriever: main retrieval interface.

Design constraints:
  - No vector database, embeddings, external network calls, or RAG.
  - No live operational data stored here. Live facts come from SENTINEL services.
  - Retrieval is purely keyword/token overlap (deterministic, reproducible).
  - Articles are loaded from the local `articles/` directory at import time.
  - The retriever is read-only; it never writes to any data source.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Set

logger = logging.getLogger("sentinel.advisor.knowledge_base")

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KBArticle:
    """
    A single knowledge base article.

    Attributes:
        article_id:  Unique stable identifier, e.g. 'kb-risk-001'.
        title:       Short human-readable title.
        category:    Thematic grouping ('risk', 'readiness', 'inventory',
                     'environment', 'digital_twin', 'logistics', 'system').
        content:     Full markdown article text.
        tags:        Set of lowercase keyword tags used for retrieval.
        source_file: Relative path of the .md file from the articles/ directory.
    """
    article_id: str
    title: str
    category: str
    content: str
    tags: frozenset
    source_file: str


@dataclass
class KBSearchResult:
    """
    A single retrieval result.

    Attributes:
        article_id:   ID of the matched article.
        title:        Article title.
        category:     Article category.
        relevance:    Float 0.0–1.0 indicating keyword overlap proportion.
        excerpt:      Snippet (first 500 chars of content, or matched paragraph).
        matched_tags: Tags that matched the query tokens.
    """
    article_id: str
    title: str
    category: str
    relevance: float
    excerpt: str
    matched_tags: List[str]


# ---------------------------------------------------------------------------
# Article loader
# ---------------------------------------------------------------------------

_ARTICLES_DIR = Path(__file__).parent / "articles"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FIELD_RE = re.compile(r"^(\w+):\s*(.+)$", re.MULTILINE)
_TAG_RE = re.compile(r"\[([^\]]+)\]")          # tags: [tag1, tag2, tag3]


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    """
    Extract YAML-like frontmatter from a markdown file.
    Returns (metadata_dict, body_text).
    """
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw

    meta_block = m.group(1)
    body = raw[m.end():]
    meta: dict = {}
    for fm in _FIELD_RE.finditer(meta_block):
        key = fm.group(1).strip()
        val = fm.group(2).strip()
        meta[key] = val
    return meta, body


def _parse_tags(tag_str: str) -> frozenset:
    """
    Parse a tags string like '[risk, stockout, critical]' into a frozenset of lowercase tokens.
    Falls back to splitting by comma if no brackets found.
    """
    bracket_m = _TAG_RE.search(tag_str)
    if bracket_m:
        raw_tags = bracket_m.group(1)
    else:
        raw_tags = tag_str

    return frozenset(t.strip().lower() for t in raw_tags.split(",") if t.strip())


def _load_articles() -> List[KBArticle]:
    """
    Load all .md files from the articles/ directory.
    Each file must have YAML-like frontmatter:

        ---
        id: kb-xxx-001
        title: Article Title
        category: risk
        tags: [tag1, tag2]
        ---
        ... markdown body ...

    Silently skips malformed files and logs a warning.
    """
    articles: List[KBArticle] = []

    if not _ARTICLES_DIR.exists():
        logger.warning(
            f"Knowledge base articles directory not found: {_ARTICLES_DIR}. "
            "Knowledge retrieval will return no results."
        )
        return articles

    for md_file in sorted(_ARTICLES_DIR.glob("*.md")):
        try:
            raw = md_file.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
            meta, body = _parse_frontmatter(raw)

            article_id = meta.get("id", "").strip()
            title = meta.get("title", "").strip()
            category = meta.get("category", "general").strip()
            tags_raw = meta.get("tags", "")
            tags = _parse_tags(tags_raw)

            if not article_id or not title:
                logger.warning(f"Skipping KB file missing 'id' or 'title': {md_file.name}")
                continue

            articles.append(KBArticle(
                article_id=article_id,
                title=title,
                category=category,
                content=body.strip(),
                tags=tags,
                source_file=md_file.name,
            ))
        except Exception as exc:
            logger.warning(f"Error loading KB article {md_file.name}: {exc}")

    logger.info(f"Knowledge base loaded {len(articles)} article(s) from {_ARTICLES_DIR}")
    return articles


# Module-level cache: None means not yet loaded; populated lazily on first access.
_KB_ARTICLES: Optional[List[KBArticle]] = None


def _get_articles() -> List[KBArticle]:
    """Return the lazily-loaded module-level article cache."""
    global _KB_ARTICLES
    if _KB_ARTICLES is None:
        _KB_ARTICLES = _load_articles()
    return _KB_ARTICLES


# ---------------------------------------------------------------------------
# Tokeniser helpers
# ---------------------------------------------------------------------------

_STOP_WORDS: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "on", "at", "by", "for", "with", "about",
    "from", "into", "through", "during", "before", "after", "above",
    "below", "between", "out", "and", "or", "but", "not", "so", "if",
    "then", "than", "that", "this", "these", "those", "what", "which",
    "who", "how", "when", "where", "why", "it", "its", "my", "we",
    "our", "you", "your", "they", "their", "i", "me", "him", "her",
    "us", "am",
}


def _tokenise(text: str) -> Set[str]:
    """Lowercase, strip punctuation, split into tokens, removing stop words."""
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {t for t in tokens if t not in _STOP_WORDS and len(t) > 1}


def _extract_excerpt(content: str, query_tokens: Set[str], max_length: int = 500) -> str:
    """
    Return a relevant excerpt.
    Prefers the first paragraph that contains a query token; falls back to the
    first `max_length` characters of the content.
    """
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    for para in paragraphs:
        para_tokens = _tokenise(para)
        if para_tokens & query_tokens:
            return para[:max_length]
    return content[:max_length] if content else ""


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class KnowledgeRetriever:
    """
    Lightweight, deterministic keyword-retriever over the local SENTINEL KB.

    Usage:
        results = KnowledgeRetriever.search("what causes high stockout risk?", top_k=3)

    Returns a list of KBSearchResult sorted by relevance (descending).
    All retrieval is pure in-memory keyword matching over the pre-loaded article corpus.
    No external calls, no embeddings, no vector DB.
    """

    @classmethod
    def _get(cls) -> List[KBArticle]:
        """Return the lazily-loaded article list."""
        return _get_articles()

    @classmethod
    def search(
        cls,
        query: str,
        *,
        top_k: int = 5,
        category_filter: Optional[str] = None,
        min_relevance: float = 0.10,
    ) -> List[KBSearchResult]:
        """
        Search the knowledge base for articles relevant to `query`.

        Args:
            query:           Natural-language query string.
            top_k:           Maximum number of results to return (default 5).
            category_filter: If given, restrict to articles of this category.
            min_relevance:   Minimum relevance score to include in results (0–1).

        Returns:
            List of KBSearchResult, sorted by relevance descending.
        """
        if not query or not query.strip():
            return []

        query_tokens = _tokenise(query)
        if not query_tokens:
            return []

        results: List[KBSearchResult] = []

        articles_to_search = cls._get()
        if category_filter:
            articles_to_search = [a for a in cls._get() if a.category == category_filter]

        for article in articles_to_search:
            # Combine tag tokens + body tokens for matching
            article_tokens = set(article.tags) | _tokenise(article.title) | _tokenise(article.content)
            matched = query_tokens & article_tokens
            matched_tags = [t for t in matched if t in article.tags]

            if not matched:
                continue

            # Relevance scoring: query-centric blend
            #   - Base: query recall = matched_tokens / total_query_tokens
            #     This is 1.0 when ALL query tokens appear in the article.
            #     It does NOT penalize large articles (Jaccard would).
            #   - Bonus: tag precision = matched_tags / total_query_tokens (×0.5 weight)
            #     Rewards articles whose declared tags directly match the query.
            n_query = len(query_tokens) or 1
            recall = len(matched) / n_query
            tag_precision = len(matched_tags) / n_query
            relevance = round(min(1.0, recall * 0.6 + tag_precision * 0.5), 4)

            if relevance < min_relevance:
                continue

            excerpt = _extract_excerpt(article.content, query_tokens)

            results.append(KBSearchResult(
                article_id=article.article_id,
                title=article.title,
                category=article.category,
                relevance=relevance,
                excerpt=excerpt,
                matched_tags=sorted(matched_tags),
            ))

        results.sort(key=lambda r: r.relevance, reverse=True)
        return results[:top_k]

    @classmethod
    def get_article(cls, article_id: str) -> Optional[KBArticle]:
        """
        Retrieve a single article by its stable ID.
        Returns None if not found.
        """
        for article in cls._get():
            if article.article_id == article_id:
                return article
        return None

    @classmethod
    def list_categories(cls) -> List[str]:
        """Return a sorted list of unique article categories."""
        return sorted({a.category for a in cls._get()})

    @classmethod
    def article_count(cls) -> int:
        """Return total number of loaded KB articles."""
        return len(cls._get())

    @classmethod
    def reload(cls) -> int:
        """
        Reload articles from disk (useful for hot-reload in development).
        Returns the new article count.
        """
        global _KB_ARTICLES
        _KB_ARTICLES = _load_articles()
        return len(_KB_ARTICLES)
