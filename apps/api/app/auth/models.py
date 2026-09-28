"""`RefreshToken` — the server-side half of ADR-009's refresh-rotation
design (docs/SECURITY.md §2: "rotated on every use... a replayed
already-rotated token signals compromise and revokes its whole token
family").

Only the SHA-256 hash of a refresh token is ever stored (see
`app.auth.security.hash_refresh_token`) — never the raw value, matching
SECURITY.md §2's explicit "never plaintext" requirement. `family_id` is
shared across every token in one rotation chain (starting at login,
carried forward on every successful `/auth/refresh`); when a token whose
`revoked_at` is already set is presented again, the entire family is
revoked (`app.auth.service.rotate_refresh_token`), not just that one row.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
