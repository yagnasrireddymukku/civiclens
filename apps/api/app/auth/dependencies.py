"""FastAPI dependencies: `get_current_user` (the auth boundary every
private route in this phase sits behind) and `verify_csrf` (the
double-submit check for state-changing requests, docs/SECURITY.md §3).
"""

from __future__ import annotations

import hmac

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.core.config import get_settings
from app.core.db.session import get_db
from app.users.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Reads the access token from its httpOnly cookie (never a header a
    client-side script could read or a query parameter that could leak
    into logs/Referer). `401` for every failure mode — missing cookie,
    invalid/expired token, or a user that no longer exists — never
    distinguishing which (fail closed, SECURITY.md §1)."""

    settings = get_settings()
    token = request.cookies.get(settings.access_cookie_name)
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.")

    claims = decode_access_token(settings=settings, token=token)
    if claims is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.")

    user = db.get(User, claims.user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.")
    return user


def verify_csrf(request: Request) -> None:
    """Double-submit CSRF check (docs/SECURITY.md §3) — required on
    every state-changing (`POST`/`PATCH`/`DELETE`) route behind
    `get_current_user`. Because cookies are sent automatically by the
    browser but a cross-site page cannot read this cookie's value to
    echo it back in the header, the two must match."""

    settings = get_settings()
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get("X-CSRF-Token")
    if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid CSRF token.")
