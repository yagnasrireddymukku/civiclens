"""Notification domain vocabulary — see docs/DATABASE.md §18."""

import enum


class NotificationType(enum.StrEnum):
    """Deliberately three, matching exactly what this phase's kickoff
    asks tracking/notifications to distinguish — not a generic
    open-ended "event type" string."""

    DEADLINE_REMINDER = "DEADLINE_REMINDER"
    CHANGE_DETECTED = "CHANGE_DETECTED"
    ENTITY_NO_LONGER_AVAILABLE = "ENTITY_NO_LONGER_AVAILABLE"


class DeliveryChannel(enum.StrEnum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"


class DeliveryStatus(enum.StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
