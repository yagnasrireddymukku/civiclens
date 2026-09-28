"""Sets/clears the three auth cookies — the one place `Response.set_cookie`
is called for auth, so every cookie's flags stay consistent
(docs/SECURITY.md §3: httpOnly + Secure + SameSite=Lax for the token
cookies; the CSRF cookie is deliberately *not* httpOnly, since the
frontend must be able to read it to echo it back in the `X-CSRF-Token`
header).
"""

from __future__ import annotations

from fastapi import Response

from app.auth.security import generate_csrf_token
from app.core.config import Settings


def set_auth_cookies(
    response: Response,
    *,
    settings: Settings,
    access_token: str,
    refresh_token: str,
) -> str:
    """Returns the new CSRF token so the caller can also expose it in
    the JSON response body for a first-load SPA that hasn't parsed
    cookies yet (never a secret — its only job is to prove the request
    came from a page that could read this cookie, i.e. same-site)."""

    response.set_cookie(
        settings.access_cookie_name,
        access_token,
        max_age=settings.access_token_ttl_minutes * 60,
        httponly=True,
        secure=settings.cookies_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.refresh_cookie_name,
        refresh_token,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookies_secure,
        samesite="lax",
        path="/",
    )
    csrf_token = generate_csrf_token()
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        httponly=False,
        secure=settings.cookies_secure,
        samesite="lax",
        path="/",
    )
    return csrf_token


def clear_auth_cookies(response: Response, *, settings: Settings) -> None:
    for name in (
        settings.access_cookie_name,
        settings.refresh_cookie_name,
        settings.csrf_cookie_name,
    ):
        response.delete_cookie(name, path="/")
