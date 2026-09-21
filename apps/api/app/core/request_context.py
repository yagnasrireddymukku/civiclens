"""Per-request correlation id, shared by the logging formatter and the
request-id middleware without coupling either to the other."""

from contextvars import ContextVar

_request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return _request_id_ctx_var.get()


def set_request_id(request_id: str) -> None:
    _request_id_ctx_var.set(request_id)
