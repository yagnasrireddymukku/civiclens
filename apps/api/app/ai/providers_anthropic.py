"""The one concrete `LLMProvider` implementation — Anthropic's Messages
API, called directly via `httpx` rather than the `anthropic` SDK
(CLAUDE.md rule 13: a plain REST call is a few dozen lines and avoids a
whole extra dependency tree for one endpoint). Nothing outside
`app.ai.providers` ever imports this module directly — always go through
`get_llm_provider()`.
"""

from __future__ import annotations

import httpx

from app.ai.providers import LLMCompletion, LLMProviderError

_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicLLMProvider:
    def __init__(self, *, api_key: str, model: str, base_url: str, timeout_seconds: float) -> None:
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def complete(
        self, *, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> LLMCompletion:
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/v1/messages", json=payload, headers=headers
                )
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Anthropic request failed: {type(exc).__name__}") from exc

        if response.status_code != 200:
            # Never surface the raw provider response body — it can
            # include request-echoing detail this app should not log at
            # the caller's level, let alone return to a client
            # (this phase's "do not leak... internal provider errors").
            raise LLMProviderError(f"Anthropic returned HTTP {response.status_code}")

        try:
            body = response.json()
            content_blocks = body["content"]
            text = "".join(block["text"] for block in content_blocks if block.get("type") == "text")
        except (KeyError, TypeError, ValueError) as exc:
            raise LLMProviderError("Anthropic response was not in the expected shape") from exc

        return LLMCompletion(text=text, model=body.get("model", self.model))
