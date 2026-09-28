"""Provider abstraction — the one boundary any vendor SDK/HTTP call is
confined to (docs/AI_ARCHITECTURE.md §5, docs/SECURITY.md §11: "the LLM
provider API key is confined to the single `LLMProvider` interface, not
scattered across the codebase"). No module outside this file and
`providers_anthropic.py`/`providers_openai.py` ever imports `httpx` to
talk to an LLM/embedding vendor.

Both `get_llm_provider()`/`get_embedding_provider()` return `None` when
unconfigured (`ai_llm_provider`/`ai_embedding_provider` settings default
to `"none"`) — every caller in this module must handle `None` explicitly
rather than assume a provider exists, since the app is required to
build, boot, and run its full test suite with both fully disabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings


class LLMProviderError(RuntimeError):
    """Raised for a provider call failure (timeout, non-2xx, malformed
    response) — callers catch this specifically and degrade to
    `GroundingStatus.PROVIDER_UNAVAILABLE`/
    `EligibilityExplanationStatus.PROVIDER_UNAVAILABLE`, never let it
    propagate as an unhandled 500 with a raw provider error message
    (this phase's explicit "do not leak... internal provider errors")."""


class EmbeddingProviderError(RuntimeError):
    """See `LLMProviderError` — the embedding-path equivalent."""


@dataclass(frozen=True, slots=True)
class LLMCompletion:
    text: str
    model: str


class LLMProvider(Protocol):
    """`complete` takes the system prompt and user-facing prompt as
    separate arguments (never concatenated by the caller) — keeping the
    system/user boundary explicit all the way down to the actual
    provider call is part of this phase's prompt-injection defense
    (docs/AI_ARCHITECTURE.md §7): a provider adapter sends them as
    distinct fields in the underlying API's own request shape, never as
    one blended string a clever piece of retrieved content could blur
    the edges of.
    """

    model: str

    async def complete(
        self, *, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> LLMCompletion: ...


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vectors: list[list[float]]
    model: str
    dimensions: int


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int

    async def embed(self, texts: list[str]) -> EmbeddingResult: ...


def get_llm_provider() -> LLMProvider | None:
    settings = get_settings()
    if settings.ai_llm_provider == "none" or not settings.ai_llm_api_key:
        return None
    if settings.ai_llm_provider == "anthropic":
        from app.ai.providers_anthropic import AnthropicLLMProvider

        return AnthropicLLMProvider(
            api_key=settings.ai_llm_api_key,
            model=settings.ai_llm_model,
            base_url=settings.ai_llm_base_url,
            timeout_seconds=settings.ai_llm_timeout_seconds,
        )
    raise AssertionError(
        f"unreachable ai_llm_provider {settings.ai_llm_provider!r}"
    )  # pragma: no cover


def get_embedding_provider() -> EmbeddingProvider | None:
    settings = get_settings()
    if settings.ai_embedding_provider == "none" or not settings.ai_embedding_api_key:
        return None
    if settings.ai_embedding_provider == "openai":
        from app.ai.providers_openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(
            api_key=settings.ai_embedding_api_key,
            model=settings.ai_embedding_model,
            expected_dimensions=settings.ai_embedding_dimensions,
            base_url=settings.ai_embedding_base_url,
            timeout_seconds=settings.ai_embedding_timeout_seconds,
        )
    raise AssertionError(  # pragma: no cover
        f"unreachable ai_embedding_provider {settings.ai_embedding_provider!r}"
    )
