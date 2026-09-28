"""`Notification`/`NotificationDeliveryAttempt` — see docs/DATABASE.md
§18.

**`entity_type`/`entity_id` are polymorphic (no FK)**, unlike
`app.tracking.models.TrackedItem`'s four real FKs — deliberately the
opposite choice, for the opposite reason Phase 11 gave for the same
choice `search_documents`/`ai_knowledge_chunks` made: a notification is
a durable, audit-trail-like historical record (matching
`app.sources.models.ChangeRecord`'s own polymorphic convention exactly)
that should survive even after the entity it was about is deleted —
"this job was removed" is itself meaningful information a cascading FK
would destroy along with the row.

**Deduplication is enforced at the database layer**
(`UNIQUE (user_id, dedup_key)`), not only in application code — this
phase's explicit "enforce notification deduplication at the database
level when feasible." `dedup_key` is built deterministically per
notification type (see `app.notifications.generation`) so the exact
same underlying event can never produce two rows for the same user,
even under concurrent sweep runs.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.notifications.enums import DeliveryChannel, DeliveryStatus, NotificationType


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "dedup_key", name="uq_notifications_user_dedup_key"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", native_enum=True),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Polymorphic — see module docstring. Nullable in principle (not
    # every notification need be entity-scoped), always set in practice
    # today since all three current notification types are.
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)

    # Provenance — never required (a deadline reminder isn't "caused" by
    # a change record), but recorded whenever a real one exists.
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    change_record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("change_records.id", ondelete="SET NULL"), nullable=True
    )

    dedup_key: Mapped[str] = mapped_column(String(300), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    delivery_attempts: Mapped[list[NotificationDeliveryAttempt]] = relationship(
        back_populates="notification", cascade="all, delete-orphan"
    )


class NotificationDeliveryAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_delivery_attempts"

    notification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[DeliveryChannel] = mapped_column(
        Enum(DeliveryChannel, name="delivery_channel", native_enum=True), nullable=False
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status", native_enum=True),
        nullable=False,
        default=DeliveryStatus.PENDING,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    notification: Mapped[Notification] = relationship(back_populates="delivery_attempts")
