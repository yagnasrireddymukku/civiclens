"""The one concrete `EmbeddingProvider` implementation — OpenAI's
Embeddings API via plain `httpx` (see `providers_anthropic.py`'s
docstring for the same "no vendor SDK" rationale). Anthropic does not
offer a public embeddings endpoint; OpenAI's is a common, stable,
independently-configurable choice — this is a second, separate provider
credential from the LLM one, matching the kickoff's own two distinct
abstractions (`LLMProvider`, `EmbeddingProvider`), not a hidden coupling
to "the same vendor."
"""

from __future__ import annotations

import httpx

from app.ai.providers import EmbeddingProviderError, EmbeddingResult


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        expected_dimensions: int,
        base_url: str,
        timeout_seconds: float,
    ) -> None:
        self.model = model
        self.dimensions = expected_dimensions
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(vectors=[], model=self.model, dimensions=self.dimensions)

        payload = {"model": self.model, "input": texts}
        headers = {"Authorization": f"Bearer {self._api_key}", "content-type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/v1/embeddings", json=payload, headers=headers
                )
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError(f"OpenAI request failed: {type(exc).__name__}") from exc

        if response.status_code != 200:
            raise EmbeddingProviderError(f"OpenAI returned HTTP {response.status_code}")

        try:
            body = response.json()
            # The API does not guarantee response order matches request
            # order — each item carries its own `index`, so sort by it
            # rather than trusting array position (a real, documented
            # OpenAI API behavior, not defensive paranoia).
            ordered = sorted(body["data"], key=lambda item: item["index"])
            vectors = [item["embedding"] for item in ordered]
        except (KeyError, TypeError, ValueError) as exc:
            raise EmbeddingProviderError("OpenAI response was not in the expected shape") from exc

        # Safe compatibility check (this phase's §5): a configured
        # dimensions mismatch against what the provider actually
        # returned must fail loudly here, not silently write a
        # wrong-shaped vector that later corrupts similarity math.
        for vector in vectors:
            if len(vector) != self.dimensions:
                raise EmbeddingProviderError(
                    f"OpenAI returned {len(vector)}-dimensional embeddings, expected "
                    f"{self.dimensions} (configured AI_EMBEDDING_DIMENSIONS) — check that "
                    f"AI_EMBEDDING_MODEL={self.model!r} actually matches the configured "
                    "dimensions."
                )

        return EmbeddingResult(vectors=vectors, model=self.model, dimensions=self.dimensions)
