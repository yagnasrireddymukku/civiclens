"""Structured logging foundation.

Emits one JSON object per log line (timestamp, level, logger name, message,
plus the current request id when available — see `middleware.py`). This is
the Phase 1 foundation for docs/OBSERVABILITY.md's structured-logging and
correlation-id requirements; it intentionally has no external dependency
(no structlog/vendor SDK) until a real need is documented.
"""

import json
import logging
import sys
from datetime import UTC, datetime

from app.core.config import Settings
from app.core.request_context import get_request_id

# Fields that must never be logged, even if accidentally passed as `extra`
# — see docs/SECURITY.md (no secrets in logs) and docs/PRIVACY.md (no full
# profile data in logs).
_FORBIDDEN_LOG_FIELDS = {"password", "token", "authorization", "secret"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = get_request_id()
        if request_id is not None:
            payload["request_id"] = request_id

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key in _FORBIDDEN_LOG_FIELDS:
                continue
            if key.startswith("civiclens_"):
                payload[key.removeprefix("civiclens_")] = value

        return json.dumps(payload, default=str)


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(settings.log_level)
