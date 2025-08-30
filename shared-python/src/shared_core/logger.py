"""Lightweight structured logging utility."""

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LogConfig:
    """Configuration for logging behavior."""

    level: str = "INFO"
    format_json: bool = True
    include_timestamp: bool = True
    include_caller: bool = False
    extra_fields: dict[str, Any] = field(default_factory=dict)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, config: LogConfig):
        super().__init__()
        self.config = config

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "message": record.getMessage(),
            "level": record.levelname,
        }

        if self.config.include_timestamp:
            log_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

        if self.config.include_caller:
            log_data["caller"] = f"{record.filename}:{record.lineno}"

        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        log_data.update(self.config.extra_fields)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def get_logger(
    name: str,
    config: LogConfig | None = None,
    handler: logging.Handler | None = None,
) -> logging.Logger:
    """Get configured logger instance.

    Args:
        name: Logger name (typically __name__)
        config: LogConfig instance. Defaults to JSON logging at INFO level.
        handler: Optional custom handler. Defaults to stdout.

    Usage:
        logger = get_logger(__name__)
        logger.info("Simple message")
        logger.info("Message with data", extra={"extra_data": {"key": "value"}})
    """
    if config is None:
        config = LogConfig()

    logger = logging.getLogger(name)

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    if handler is None:
        handler = logging.StreamHandler(sys.stdout)

    if config.format_json:
        formatter = JSONFormatter(config)
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, config.level.upper()))
    logger.propagate = False

    return logger
