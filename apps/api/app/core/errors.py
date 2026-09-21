"""Standard error response envelope — see docs/API.md §7.

Every non-2xx response uses:

    {"error": {"code": "...", "message": "...", "details": [...]}}

`code` is a stable, machine-readable string a frontend can branch on;
`message` is human-readable and never leaks internals (stack traces, SQL,
file paths — see docs/SECURITY.md). Internal errors are logged with full
detail server-side and returned to the client as a generic message only.
"""

import logging

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

logger = logging.getLogger("civiclens.api.errors")

_STATUS_TO_CODE: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "VALIDATION_ERROR",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
}


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    error_body: dict[str, object] = {"code": code, "message": message}
    if details:
        error_body["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error_body})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"field": ".".join(str(part) for part in error["loc"]), "issue": error["msg"]}
            for error in exc.errors()
        ]
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "VALIDATION_ERROR",
            "The request could not be validated.",
            details,
        )

    # Registered on starlette.exceptions.HTTPException (not fastapi's
    # HTTPException, which is a *subclass* of it) so this also catches
    # routing-level exceptions Starlette raises directly for 404/405 —
    # a handler registered only on the FastAPI subclass would miss those,
    # since exception-handler lookup walks the raised exception's own MRO,
    # not the registered class's subclasses.
    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        code = _STATUS_TO_CODE.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return _error_response(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception while processing request", exc_info=exc)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
        )
