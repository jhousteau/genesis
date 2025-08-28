"""Lightweight structured logging utility."""

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .context import get_context


@dataclass
class LogConfig:
    """Configuration for logging behavior."""

    level: str
    format_json: bool
    include_timestamp: bool
    include_caller: bool
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

        # Include context information automatically
        context = get_context()
        if context:
            log_data.update(context.get_logger_context())

        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        log_data.update(self.config.extra_fields)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def get_logger(
    name: str,
    config: Optional[LogConfig] = None,
    handler: Optional[logging.Handler] = None,
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
        from genesis.core.constants import LoggerConfig
        config = LogConfig(
            level=LoggerConfig.get_level(),
            format_json=LoggerConfig.should_format_json(),
            include_timestamp=LoggerConfig.should_include_timestamp(),
            include_caller=LoggerConfig.should_include_caller(),
        )

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
