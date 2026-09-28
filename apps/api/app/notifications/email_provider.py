"""Email provider abstraction — this phase's §4.6: "if included, use a
provider abstraction, safe configuration, bounded retries, and explicit
user preferences. The application must work with email disabled and
must not require paid credentials for ordinary tests." Same pattern as
`app.ai.providers` (Phase 12): a `Protocol`, a plain `httpx` adapter (no
vendor SDK), defaulting to `"none"` so the app builds/boots/tests with
email fully disabled.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from app.core.config import get_settings


class EmailProviderError(RuntimeError):
    """Raised for a provider call failure — callers (`app.notifications.
    delivery`) catch this specifically and record a bounded, observable
    failure, never let it propagate as an unhandled error (this phase's
    "safe failure states" requirement)."""


class EmailProvider(Protocol):
    async def send(self, *, to: str, subject: str, body: str) -> None: ...


class ResendEmailProvider:
    """A plain `httpx` wrapper around Resend's REST API — a common,
    simple, transactional-email HTTP API, chosen the same way Phase
    12 chose OpenAI for embeddings: a stable, well-documented REST
    endpoint, not a reason to add a vendor SDK dependency."""

    def __init__(
        self, *, api_key: str, from_address: str, base_url: str, timeout_seconds: float
    ) -> None:
        self._api_key = api_key
        self._from_address = from_address
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def send(self, *, to: str, subject: str, body: str) -> None:
        payload = {"from": self._from_address, "to": [to], "subject": subject, "text": body}
        headers = {"Authorization": f"Bearer {self._api_key}", "content-type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/emails", json=payload, headers=headers
                )
        except httpx.HTTPError as exc:
            raise EmailProviderError(f"Email request failed: {type(exc).__name__}") from exc

        if response.status_code >= 300:
            raise EmailProviderError(f"Email provider returned HTTP {response.status_code}")


def get_email_provider() -> EmailProvider | None:
    settings = get_settings()
    if settings.email_provider == "none" or not settings.email_api_key:
        return None
    return ResendEmailProvider(
        api_key=settings.email_api_key,
        from_address=settings.email_from_address,
        base_url=settings.email_base_url,
        timeout_seconds=settings.email_timeout_seconds,
    )
