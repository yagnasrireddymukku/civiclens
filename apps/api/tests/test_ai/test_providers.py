"""Provider-adapter tests — no live credentials required (this phase's
explicit testing requirement): `httpx.AsyncClient` itself is faked so
these exercise real request/response-shape handling (including error
paths) without any network call.
"""

import asyncio

import httpx
import pytest

from app.ai import providers_anthropic, providers_openai
from app.ai.providers import (
    EmbeddingProviderError,
    LLMProviderError,
    get_embedding_provider,
    get_llm_provider,
)
from app.core.config import Settings


def _sync(coro):
    return asyncio.run(coro)


class _FakeResponse:
    def __init__(self, status_code: int, json_body: object) -> None:
        self.status_code = status_code
        self._json_body = json_body

    def json(self) -> object:
        return self._json_body


class _FakeAsyncClient:
    def __init__(self, response: _FakeResponse | Exception, *, captured: list) -> None:
        self._response = response
        self._captured = captured

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, *, json: dict, headers: dict) -> _FakeResponse:
        self._captured.append({"url": url, "json": json, "headers": headers})
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class _FakeHttpxModule:
    """Stands in for the `httpx` name inside a provider module — a
    plain object with the two attributes that module actually uses
    (`AsyncClient`, `HTTPError`), avoiding any class/instance method-
    binding subtlety a dynamically-built class would risk."""

    HTTPError = httpx.HTTPError

    def __init__(self, response: _FakeResponse | Exception, captured: list) -> None:
        self._response = response
        self._captured = captured

    def AsyncClient(self, *, timeout: float) -> _FakeAsyncClient:  # noqa: N802 - matches httpx's real name
        return _FakeAsyncClient(self._response, captured=self._captured)


def _patch_client(monkeypatch: pytest.MonkeyPatch, module, response, captured: list) -> None:
    monkeypatch.setattr(module, "httpx", _FakeHttpxModule(response, captured))


class TestProviderFactories:
    def test_get_llm_provider_returns_none_by_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.ai.providers.get_settings", lambda: Settings(ai_llm_provider="none")
        )
        assert get_llm_provider() is None

    def test_get_llm_provider_returns_none_without_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.ai.providers.get_settings",
            lambda: Settings(ai_llm_provider="anthropic", ai_llm_api_key=None),
        )
        assert get_llm_provider() is None

    def test_get_llm_provider_returns_anthropic_adapter_when_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.ai.providers.get_settings",
            lambda: Settings(ai_llm_provider="anthropic", ai_llm_api_key="sk-fake"),
        )
        provider = get_llm_provider()
        assert provider is not None
        assert provider.model

    def test_get_embedding_provider_returns_none_by_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.ai.providers.get_settings", lambda: Settings(ai_embedding_provider="none")
        )
        assert get_embedding_provider() is None


class TestAnthropicLLMProvider:
    def _provider(self) -> providers_anthropic.AnthropicLLMProvider:
        return providers_anthropic.AnthropicLLMProvider(
            api_key="sk-fake",
            model="claude-haiku-4-5-20251001",
            base_url="https://api.anthropic.com",
            timeout_seconds=5.0,
        )

    def test_parses_a_successful_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: list = []
        response = _FakeResponse(
            200,
            {
                "content": [
                    {"type": "text", "text": "Hello, "},
                    {"type": "text", "text": "world."},
                ],
                "model": "claude-haiku-4-5-20251001",
            },
        )
        _patch_client(monkeypatch, providers_anthropic, response, captured)

        result = _sync(
            self._provider().complete(system_prompt="sys", user_prompt="hi", max_tokens=100)
        )

        assert result.text == "Hello, world."
        assert captured[0]["json"]["system"] == "sys"
        assert captured[0]["json"]["messages"] == [{"role": "user", "content": "hi"}]
        assert captured[0]["headers"]["x-api-key"] == "sk-fake"

    def test_raises_on_non_200(self, monkeypatch: pytest.MonkeyPatch) -> None:
        response = _FakeResponse(500, {"error": "boom"})
        _patch_client(monkeypatch, providers_anthropic, response, [])

        with pytest.raises(LLMProviderError):
            _sync(self._provider().complete(system_prompt="sys", user_prompt="hi", max_tokens=100))

    def test_raises_on_malformed_body(self, monkeypatch: pytest.MonkeyPatch) -> None:
        response = _FakeResponse(200, {"unexpected": "shape"})
        _patch_client(monkeypatch, providers_anthropic, response, [])

        with pytest.raises(LLMProviderError):
            _sync(self._provider().complete(system_prompt="sys", user_prompt="hi", max_tokens=100))

    def test_raises_on_transport_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, providers_anthropic, httpx.ConnectTimeout("timed out"), [])

        with pytest.raises(LLMProviderError):
            _sync(self._provider().complete(system_prompt="sys", user_prompt="hi", max_tokens=100))


class TestOpenAIEmbeddingProvider:
    def _provider(self) -> providers_openai.OpenAIEmbeddingProvider:
        return providers_openai.OpenAIEmbeddingProvider(
            api_key="sk-fake",
            model="text-embedding-3-small",
            expected_dimensions=3,
            base_url="https://api.openai.com",
            timeout_seconds=5.0,
        )

    def test_parses_and_reorders_by_index(self, monkeypatch: pytest.MonkeyPatch) -> None:
        response = _FakeResponse(
            200,
            {
                "data": [
                    {"index": 1, "embedding": [0.4, 0.5, 0.6]},
                    {"index": 0, "embedding": [0.1, 0.2, 0.3]},
                ]
            },
        )
        _patch_client(monkeypatch, providers_openai, response, [])

        result = _sync(self._provider().embed(["first", "second"]))

        assert result.vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        assert result.dimensions == 3

    def test_empty_input_never_calls_the_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: list = []
        _patch_client(monkeypatch, providers_openai, _FakeResponse(200, {"data": []}), captured)

        result = _sync(self._provider().embed([]))

        assert result.vectors == []
        assert captured == []

    def test_raises_on_dimension_mismatch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        response = _FakeResponse(200, {"data": [{"index": 0, "embedding": [0.1, 0.2]}]})
        _patch_client(monkeypatch, providers_openai, response, [])

        with pytest.raises(EmbeddingProviderError):
            _sync(self._provider().embed(["text"]))

    def test_raises_on_non_200(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, providers_openai, _FakeResponse(500, {}), [])

        with pytest.raises(EmbeddingProviderError):
            _sync(self._provider().embed(["text"]))
