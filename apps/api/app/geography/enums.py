import enum


class StateStatus(enum.StrEnum):
    """Whether a state is publicly launched — data, not a code branch.
    See docs/ARCHITECTURE.md §3 (state-agnostic design)."""

    ACTIVE = "active"
    PLANNED = "planned"


class ConstituencyType(enum.StrEnum):
    ASSEMBLY = "assembly"
    PARLIAMENTARY = "parliamentary"
