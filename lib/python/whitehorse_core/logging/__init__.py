"""
Logging Module

Provides structured logging with GCP Cloud Logging integration,
correlation IDs, and consistent formatting across all projects.
"""

import json
import logging
import sys
import threading
import traceback
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    from google.cloud import logging as cloud_logging
    from google.cloud.logging.handlers import CloudLoggingHandler

    HAS_GCP_LOGGING = True
except ImportError:
    HAS_GCP_LOGGING = False

# Thread-local storage for correlation IDs
_thread_local = threading.local()


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs with consistent fields.
    """

    def __init__(self, service_name: str = "whitehorse-service"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
        }

        # Add correlation ID if available
        correlation_id = get_correlation_id()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                extra_fields[key] = value

        if extra_fields:
            log_entry["extra"] = extra_fields

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class WhitehorseLogger:
    """
    Enhanced logger with correlation ID support and structured logging.
    """

    def __init__(self, name: str, service_name: str = "whitehorse-service"):
        self.logger = logging.getLogger(name)
        self.service_name = service_name

    def debug(self, message: str, **kwargs):
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, exc_info: bool = True, **kwargs):
        self.logger.error(message, exc_info=exc_info, extra=kwargs)

    def critical(self, message: str, exc_info: bool = True, **kwargs):
        self.logger.critical(message, exc_info=exc_info, extra=kwargs)

    def exception(self, message: str, **kwargs):
        self.logger.exception(message, extra=kwargs)

    @contextmanager
    def correlation_id(self, correlation_id: Optional[str] = None):
        """Context manager to set correlation ID for current thread."""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())

        old_id = get_correlation_id()
        set_correlation_id(correlation_id)
        try:
            self.info("Started operation", operation_id=correlation_id)
            yield correlation_id
        finally:
            self.info("Completed operation", operation_id=correlation_id)
            set_correlation_id(old_id)


def setup_logging(
    service_name: str = "whitehorse-service",
    level: str = "INFO",
    enable_gcp: bool = True,
    gcp_project: Optional[str] = None,
    log_file: Optional[Union[str, Path]] = None,
    console_output: bool = True,
) -> None:
    """
    Setup structured logging with optional GCP Cloud Logging integration.

    Args:
        service_name: Name of the service for log identification
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_gcp: Whether to enable GCP Cloud Logging
        gcp_project: GCP project ID (auto-detected if not provided)
        log_file: Optional file path for file logging
        console_output: Whether to output logs to console
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    formatter = StructuredFormatter(service_name)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # GCP Cloud Logging handler
    if enable_gcp and HAS_GCP_LOGGING:
        try:
            client = cloud_logging.Client(project=gcp_project)
            gcp_handler = CloudLoggingHandler(client, name=service_name)
            root_logger.addHandler(gcp_handler)
        except Exception as e:
            # Fallback to console if GCP logging fails
            console_logger = logging.getLogger(__name__)
            console_logger.warning(f"Failed to setup GCP logging: {e}")


def get_logger(name: str, service_name: str = "whitehorse-service") -> WhitehorseLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)
        service_name: Service name for log identification

    Returns:
        WhitehorseLogger instance
    """
    return WhitehorseLogger(name, service_name)


def set_correlation_id(correlation_id: Optional[str]) -> None:
    """Set correlation ID for current thread."""
    _thread_local.correlation_id = correlation_id


def get_correlation_id() -> Optional[str]:
    """Get correlation ID for current thread."""
    return getattr(_thread_local, "correlation_id", None)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


# Convenience functions
def log_performance(func):
    """Decorator to log function performance."""
    import functools
    import time

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()

        logger.info(
            f"Starting {func.__name__}", function=func.__name__, module=func.__module__
        )

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(
                f"Completed {func.__name__}",
                function=func.__name__,
                module=func.__module__,
                duration_seconds=duration,
                success=True,
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Failed {func.__name__}: {str(e)}",
                function=func.__name__,
                module=func.__module__,
                duration_seconds=duration,
                success=False,
                error=str(e),
            )
            raise

    return wrapper
