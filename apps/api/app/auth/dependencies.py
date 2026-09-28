"""FastAPI dependencies: `get_current_user` (the auth boundary every
private route in this phase sits behind), `verify_csrf` (the
double-submit check for state-changing requests, docs/SECURITY.md §3),
and `require_role` (the RBAC boundary privileged routes sit behind,
Admin Intelligence Center).
"""

from __future__ import annotations

import hmac
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.core.config import get_settings
from app.core.db.session import get_db
from app.users.enums import UserRole
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


def require_role(*allowed_roles: UserRole) -> Callable[..., User]:
    """Returns a dependency that 403s unless `current_user.role` is one
    of `allowed_roles` — the role is always read from the `User` row
    `get_current_user` just loaded fresh from the database (never from
    the JWT's own claims), so a role change takes effect on the very
    next request rather than waiting for the (already short-lived, ~15
    min) access token to expire. Composes with `get_current_user`
    rather than duplicating its cookie/token logic — every route using
    this is still subject to the identical 401-on-no-session behavior
    first."""

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this action.")
        return current_user

    return _dependency
