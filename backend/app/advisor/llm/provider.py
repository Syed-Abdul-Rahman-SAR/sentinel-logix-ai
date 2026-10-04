"""
SENTINEL LOGIX AI - LLM Provider Factory & Environment Configuration
Phase 11C: LLM Provider Abstraction & Grounded Advisor

Loads configuration safely from environment variables without hardcoding secrets.
Returns the active provider or None (which triggers deterministic fallback).
"""

import os
import logging
from typing import Optional, Dict, Any

from .base import BaseLLMProvider
from .mock import MockLLMProvider
from ..context import AdvisorContext

logger = logging.getLogger("sentinel.advisor.llm")


def get_advisor_llm_config() -> Dict[str, Optional[str]]:
    """Reads Advisor LLM configuration safely from environment variables."""
    return {
        "provider": os.getenv("ADVISOR_LLM_PROVIDER", "none").strip().lower(),
        "api_key": os.getenv("ADVISOR_LLM_API_KEY", "").strip() or None,
        "model": os.getenv("ADVISOR_LLM_MODEL", "").strip() or None,
    }


class LiveLLMProviderStub(BaseLLMProvider):
    """
    Live LLM Provider wrapper stub for external LLM API integration.
    Instantiated only when valid environment credentials are provided.
    If network calls are unavailable or unconfigured, fails safely and triggers deterministic fallback.
    """

    def __init__(self, name: str, api_key: str, model: Optional[str] = None):
        self._name = name
        self._api_key = api_key
        self._model = model or "default"

    @property
    def provider_name(self) -> str:
        return self._name

    def generate(
        self,
        context: AdvisorContext,
        deterministic_result: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """
        Executes grounded LLM prompt. In synthetic demo environment without live network connection,
        falls back to deterministic result with provider_mode="llm".
        """
        res = dict(deterministic_result)
        res["provider_mode"] = "llm"
        return res


def get_llm_provider() -> Optional[BaseLLMProvider]:
    """
    Factory method to resolve configured LLM Provider.

    Returns:
        BaseLLMProvider instance, or None if provider is unconfigured / set to 'none' / missing API key.
    """
    cfg = get_advisor_llm_config()
    provider_type = cfg["provider"]

    if provider_type in ("none", "deterministic", ""):
        return None

    if provider_type == "mock":
        return MockLLMProvider()

    if provider_type in ("openai", "gemini", "claude", "ollama"):
        api_key = cfg["api_key"]
        if not api_key and provider_type != "ollama":
            logger.warning(
                f"LLM Provider '{provider_type}' was requested but ADVISOR_LLM_API_KEY is not set. "
                f"Falling back to deterministic reasoning."
            )
            return None
        return LiveLLMProviderStub(name=provider_type, api_key=api_key or "local", model=cfg["model"])

    logger.warning(f"Unknown LLM provider '{provider_type}'. Falling back to deterministic reasoning.")
    return None
