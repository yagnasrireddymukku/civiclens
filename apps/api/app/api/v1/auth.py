"""POST /api/v1/auth/register, /login, /refresh, /logout,
GET /api/v1/auth/me, PATCH /api/v1/auth/me — see docs/API.md.

Implements ADR-009's already-accepted design (JWT access+refresh,
email/password baseline, httpOnly cookies, refresh rotation with
family-wide revocation on replay) — the first real authentication in
this codebase; every other private route from this phase onward sits
behind `app.auth.dependencies.get_current_user`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.cookies import clear_auth_cookies, set_auth_cookies
from app.auth.dependencies import get_current_user, verify_csrf
from app.auth.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UpdateNotificationPreferenceRequest,
    UserSummary,
)
from app.core.config import get_settings
from app.core.db.session import get_db
from app.users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_summary(user: User) -> UserSummary:
    return UserSummary(
        id=user.id,
        email=user.email,
        role=user.role,
        email_notifications_enabled=user.email_notifications_enabled,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest, response: Response, db: Session = Depends(get_db)
) -> AuthResponse:
    try:
        user = service.register_user(db, email=payload.email, password=payload.password)
    except service.EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An account with this email already exists."
        ) from exc

    settings = get_settings()
    tokens = service.issue_token_pair(db, settings=settings, user=user)
    csrf_token = set_auth_cookies(
        response,
        settings=settings,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )
    return AuthResponse(user=_user_summary(user), csrf_token=csrf_token)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    user = service.authenticate_user(db, email=payload.email, password=payload.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")

    settings = get_settings()
    tokens = service.issue_token_pair(db, settings=settings, user=user)
    csrf_token = set_auth_cookies(
        response,
        settings=settings,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )
    return AuthResponse(user=_user_summary(user), csrf_token=csrf_token)


@router.post("/refresh", response_model=AuthResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    settings = get_settings()
    raw_refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if raw_refresh_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.")

    try:
        user, tokens = service.rotate_refresh_token(
            db, settings=settings, raw_refresh_token=raw_refresh_token
        )
    except service.RefreshTokenError as exc:
        clear_auth_cookies(response, settings=settings)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.") from exc

    csrf_token = set_auth_cookies(
        response,
        settings=settings,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )
    return AuthResponse(user=_user_summary(user), csrf_token=csrf_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_csrf)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    settings = get_settings()
    raw_refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if raw_refresh_token is not None:
        service.revoke_refresh_token(db, raw_refresh_token=raw_refresh_token)
    clear_auth_cookies(response, settings=settings)


@router.get("/me", response_model=UserSummary)
def me(current_user: User = Depends(get_current_user)) -> UserSummary:
    return _user_summary(current_user)


@router.patch("/me", response_model=UserSummary, dependencies=[Depends(verify_csrf)])
def update_preferences(
    payload: UpdateNotificationPreferenceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSummary:
    current_user.email_notifications_enabled = payload.email_notifications_enabled
    db.flush()
    return _user_summary(current_user)
