import enum


class SearchSortOption(enum.StrEnum):
    """The only sortable dimensions at this phase — an explicit allow-list
    per docs/API.md §6, never an arbitrary client-supplied column name."""

    RELEVANCE = "relevance"
    LAST_VERIFIED = "last_verified"
