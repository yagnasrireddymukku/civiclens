import enum


class UserRole(enum.StrEnum):
    """See ADR-009 and docs/SECURITY.md §4 — three roles, no per-resource
    ACL system planned at this scale."""

    USER = "user"
    EDITOR = "editor"
    ADMIN = "admin"
