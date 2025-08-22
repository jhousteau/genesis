"""
Genesis Structured Logging Foundation

Provides production-ready logging with:
- Structured JSON output
- Log levels and filtering
- Context injection
- Correlation ID tracking
- Cloud Logging integration
- Performance tracking
"""

import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Union


class LogLevel(Enum):
    """Log levels matching standard severity"""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class GenesisLogger:
    """
    Structured logger for Genesis platform

    Features:
    - JSON formatted output
    - Automatic context injection
    - Performance tracking
    - Cloud Logging compatible
    """

    def __init__(
        self,
        name: str,
        level: Union[LogLevel, str] = LogLevel.INFO,
        service: Optional[str] = None,
        environment: Optional[str] = None,
        version: Optional[str] = None,
    ):
        self.name = name
        self.service = service or os.environ.get("GENESIS_SERVICE", "genesis")
        self.environment = environment or os.environ.get("GENESIS_ENV", "development")
        self.version = version or os.environ.get("GENESIS_VERSION", "unknown")

        # Create underlying Python logger
        self.logger = logging.getLogger(name)

        # Set log level
        if isinstance(level, str):
            level = LogLevel[level.upper()]
        self.logger.setLevel(level.value)

        # Remove default handlers
        self.logger.handlers = []

        # Add JSON handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self._get_json_formatter())
        self.logger.addHandler(handler)

        # Context storage
        self._context = {}

    def _get_json_formatter(self):
        """Create JSON formatter for structured logging"""
        return JsonFormatter(
            service=self.service, environment=self.environment, version=self.version
        )

    def with_context(self, **kwargs) -> "GenesisLogger":
        """
        Create a new logger instance with additional context

        Args:
            **kwargs: Context key-value pairs

        Returns:
            New logger instance with merged context
        """
        new_logger = GenesisLogger(
            name=self.name,
            level=LogLevel(self.logger.level),
            service=self.service,
            environment=self.environment,
            version=self.version,
        )
        new_logger._context = {**self._context, **kwargs}
        return new_logger

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message"""
        if error:
            kwargs["error_type"] = type(error).__name__
            kwargs["error_message"] = str(error)
        self._log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log critical message"""
        if error:
            kwargs["error_type"] = type(error).__name__
            kwargs["error_message"] = str(error)
        self._log(LogLevel.CRITICAL, message, **kwargs)

    def _log(self, level: LogLevel, message: str, **kwargs):
        """Internal logging method"""
        # Merge contexts
        log_data = {**self._context, **kwargs, "message": message}

        # Use appropriate logging method
        log_method = getattr(self.logger, level.name.lower())
        log_method(message, extra={"data": log_data})

    @contextmanager
    def timer(self, operation: str, **kwargs):
        """
        Context manager for timing operations

        Usage:
            with logger.timer("database_query", query="SELECT * FROM users"):
                # perform operation
        """
        start_time = time.time()
        self.debug(f"Starting {operation}", operation=operation, **kwargs)

        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.info(
                f"Completed {operation}",
                operation=operation,
                duration_ms=round(duration_ms, 2),
                **kwargs,
            )

    @contextmanager
    def trace(self, trace_id: str, span_id: Optional[str] = None):
        """
        Context manager for distributed tracing

        Usage:
            with logger.trace(trace_id="abc123", span_id="def456"):
                logger.info("Processing request")
        """
        import uuid

        old_context = self._context.copy()
        self._context["trace_id"] = trace_id
        self._context["span_id"] = span_id or str(uuid.uuid4())

        try:
            yield
        finally:
            self._context = old_context


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging

    Produces Cloud Logging compatible JSON output
    """

    def __init__(self, service: str, environment: str, version: str):
        super().__init__()
        self.service = service
        self.environment = environment
        self.version = version

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # Base log structure
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service,
            "environment": self.environment,
            "version": self.version,
        }

        # Add source location
        log_obj["source"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add custom data if present
        if hasattr(record, "data"):
            data = record.data
            # Extract special fields
            for field in [
                "trace_id",
                "span_id",
                "correlation_id",
                "user_id",
                "request_id",
            ]:
                if field in data:
                    log_obj[field] = data.pop(field)

            # Add remaining data
            if data:
                log_obj["data"] = data

        # Add exception info if present
        if record.exc_info:
            import traceback

            log_obj["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_obj)


class LoggerFactory:
    """Factory for creating loggers with consistent configuration"""

    _loggers: Dict[str, GenesisLogger] = {}
    _default_level = LogLevel.INFO
    _service = None
    _environment = None
    _version = None

    @classmethod
    def configure(
        cls,
        service: str,
        environment: str = "development",
        version: str = "unknown",
        default_level: Union[LogLevel, str] = LogLevel.INFO,
    ):
        """
        Configure default settings for all loggers

        Args:
            service: Service name
            environment: Environment (development, staging, production)
            version: Service version
            default_level: Default log level
        """
        cls._service = service
        cls._environment = environment
        cls._version = version

        if isinstance(default_level, str):
            default_level = LogLevel[default_level.upper()]
        cls._default_level = default_level

    @classmethod
    def get_logger(cls, name: str, **kwargs) -> GenesisLogger:
        """
        Get or create a logger instance

        Args:
            name: Logger name (usually __name__)
            **kwargs: Additional logger configuration

        Returns:
            GenesisLogger instance
        """
        if name not in cls._loggers:
            cls._loggers[name] = GenesisLogger(
                name=name,
                level=kwargs.get("level", cls._default_level),
                service=kwargs.get("service", cls._service),
                environment=kwargs.get("environment", cls._environment),
                version=kwargs.get("version", cls._version),
            )

        return cls._loggers[name]


# Convenience function for getting logger
def get_logger(name: str = None, **kwargs) -> GenesisLogger:
    """
    Get a logger instance

    Args:
        name: Logger name (defaults to calling module)
        **kwargs: Additional configuration

    Returns:
        GenesisLogger instance
    """
    if name is None:
        import inspect

        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get("__name__", "genesis")
        else:
            name = "genesis"

    return LoggerFactory.get_logger(name, **kwargs)


# Configure default logger settings from environment
LoggerFactory.configure(
    service=os.environ.get("GENESIS_SERVICE", "genesis"),
    environment=os.environ.get("GENESIS_ENV", "development"),
    version=os.environ.get("GENESIS_VERSION", "0.1.0"),
    default_level=os.environ.get("GENESIS_LOG_LEVEL", "INFO"),
)
