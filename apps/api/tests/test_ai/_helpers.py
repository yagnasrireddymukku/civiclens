"""Shared fakes/helpers for Civic AI tests — plain functions/classes, not
pytest fixtures, mirroring every other domain's `_helpers.py` pattern.
No test in this package requires a live provider credential (this
phase's explicit testing requirement) — `FakeLLMProvider`/
`FakeEmbeddingProvider` implement the same `LLMProvider`/
`EmbeddingProvider` protocols `app.ai.providers` defines, deterministically.
"""

from __future__ import annotations

import hashlib

from app.ai.providers import EmbeddingResult, LLMCompletion, LLMProviderError


class FakeLLMProvider:
    model = "fake-llm-1"

    def __init__(self, response_text: str, *, raise_error: bool = False) -> None:
        self._response_text = response_text
        self._raise_error = raise_error
        self.calls: list[tuple[str, str]] = []

    async def complete(
        self, *, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> LLMCompletion:
        self.calls.append((system_prompt, user_prompt))
        if self._raise_error:
            raise LLMProviderError("fake provider failure")
        return LLMCompletion(text=self._response_text, model=self.model)


def deterministic_fake_vector(text: str, dimensions: int) -> list[float]:
    """A stable, reproducible pseudo-embedding derived from the text's
    own bytes — not a real semantic embedding, but deterministic and
    sufficient to exercise cosine-similarity ranking/ordering in tests
    without a live provider."""

    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [((digest[i % len(digest)] / 255.0) * 2) - 1 for i in range(dimensions)]


class FakeEmbeddingProvider:
    def __init__(
        self, *, dimensions: int = 8, model: str = "fake-embed-1", raise_error: bool = False
    ) -> None:
        self.model = model
        self.dimensions = dimensions
        self._raise_error = raise_error
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        self.calls.append(texts)
        if self._raise_error:
            from app.ai.providers import EmbeddingProviderError

            raise EmbeddingProviderError("fake provider failure")
        vectors = [deterministic_fake_vector(text, self.dimensions) for text in texts]
        return EmbeddingResult(vectors=vectors, model=self.model, dimensions=self.dimensions)
