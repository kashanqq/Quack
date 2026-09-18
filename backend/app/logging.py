"""Structured JSON logging with request context and secret masking."""

import logging
from typing import Any

import structlog

_SECRET_PARTS = ("password", "secret", "token", "api_key", "authorization")


def _mask_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if any(part in str(key).lower() for part in _SECRET_PARTS)
            else _mask_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_mask_value(item) for item in value]
    return value


def mask_secrets(
    _logger: Any, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Redact secret-bearing fields, including nested structured fields."""
    return _mask_value(event_dict)


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level.upper(), format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            mask_secrets,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
