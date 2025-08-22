"""
Universal Structured Logger
Provides consistent, structured logging across all platform applications.
"""

import json
import logging
import logging.config
import os
import sys
import traceback
import uuid
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from google.cloud import logging as gcp_logging
    from google.cloud.logging.handlers import CloudLoggingHandler

    GCP_LOGGING_AVAILABLE = True
except ImportError:
    GCP_LOGGING_AVAILABLE = False

try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


# Context variables for request correlation
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")
user_id: ContextVar[str] = ContextVar("user_id", default="")
session_id: ContextVar[str] = ContextVar("session_id", default="")
trace_id: ContextVar[str] = ContextVar("trace_id", default="")


@dataclass
class LogContext:
    """Context information for structured logging."""

    service_name: str
    service_version: str = "1.0.0"
    environment: str = "development"
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    region: str = field(default_factory=lambda: os.getenv("REGION", "unknown"))
    project_id: str = field(default_factory=lambda: os.getenv("GCP_PROJECT", "unknown"))
    namespace: str = field(default_factory=lambda: os.getenv("NAMESPACE", "default"))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LogEntry:
    """Structured log entry format."""

    timestamp: str
    level: str
    message: str
    service: Dict[str, Any]
    request: Dict[str, Any] = field(default_factory=dict)
    user: Dict[str, Any] = field(default_factory=dict)
    error: Dict[str, Any] = field(default_factory=dict)
    performance: Dict[str, Any] = field(default_factory=dict)
    business: Dict[str, Any] = field(default_factory=dict)
    security: Dict[str, Any] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":"))


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""

    def __init__(self, context: LogContext):
        super().__init__()
        self.context = context

    def format(self, record: logging.LogRecord) -> str:
        # Extract exception information if present
        error_info = {}
        if record.exc_info:
            error_info = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Build request context
        request_info = {
            "correlation_id": correlation_id.get(""),
            "trace_id": trace_id.get(""),
            "span_id": getattr(record, "span_id", ""),
        }

        # Build user context
        user_info = {
            "user_id": user_id.get(""),
            "session_id": session_id.get(""),
        }

        # Extract performance metrics if present
        performance_info = {}
        if hasattr(record, "duration"):
            performance_info["duration_ms"] = record.duration
        if hasattr(record, "memory_usage"):
            performance_info["memory_mb"] = record.memory_usage

        # Extract business context if present
        business_info = {}
        if hasattr(record, "business_event"):
            business_info["event"] = record.business_event
        if hasattr(record, "business_value"):
            business_info["value"] = record.business_value

        # Extract security context if present
        security_info = {}
        if hasattr(record, "security_event"):
            security_info["event"] = record.security_event
        if hasattr(record, "threat_level"):
            security_info["threat_level"] = record.threat_level

        # Build labels from extra attributes
        labels = {}
        for key, value in record.__dict__.items():
            if key.startswith("label_"):
                labels[key[6:]] = str(value)

        # Create structured log entry
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=record.levelname,
            message=record.getMessage(),
            service=self.context.to_dict(),
            request=request_info,
            user=user_info,
            error=error_info,
            performance=performance_info,
            business=business_info,
            security=security_info,
            labels=labels,
        )

        return log_entry.to_json()


class UniversalLogger:
    """Universal structured logger for all platform applications."""

    def __init__(self, context: LogContext, enable_cloud_logging: bool = True):
        self.context = context
        self.logger = logging.getLogger(context.service_name)
        self.logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Set up structured formatter
        formatter = StructuredFormatter(context)

        # Console handler with structured output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Google Cloud Logging handler if available and enabled
        if enable_cloud_logging and GCP_LOGGING_AVAILABLE:
            try:
                client = gcp_logging.Client(project=context.project_id)
                cloud_handler = CloudLoggingHandler(client)
                cloud_handler.setFormatter(formatter)
                self.logger.addHandler(cloud_handler)
            except Exception as e:
                self.logger.warning(f"Failed to setup Cloud Logging: {e}")

        # File handler for local development
        if context.environment == "development":
            file_handler = logging.FileHandler("application.log")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _log_with_context(self, level: str, message: str, **kwargs):
        """Log with additional context information."""
        extra = {}

        # Add performance metrics
        if "duration" in kwargs:
            extra["duration"] = kwargs.pop("duration")
        if "memory_usage" in kwargs:
            extra["memory_usage"] = kwargs.pop("memory_usage")

        # Add business context
        if "business_event" in kwargs:
            extra["business_event"] = kwargs.pop("business_event")
        if "business_value" in kwargs:
            extra["business_value"] = kwargs.pop("business_value")

        # Add security context
        if "security_event" in kwargs:
            extra["security_event"] = kwargs.pop("security_event")
        if "threat_level" in kwargs:
            extra["threat_level"] = kwargs.pop("threat_level")

        # Add labels
        for key, value in kwargs.items():
            if key.startswith("label_"):
                extra[key] = value

        # Get the appropriate log method
        log_method = getattr(self.logger, level.lower())
        log_method(message, extra=extra)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log_with_context("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log_with_context("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log_with_context("WARNING", message, **kwargs)

    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message with optional exception."""
        if exception:
            self.logger.error(message, exc_info=exception, extra=kwargs)
        else:
            self._log_with_context("ERROR", message, **kwargs)

    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log critical message with optional exception."""
        if exception:
            self.logger.critical(message, exc_info=exception, extra=kwargs)
        else:
            self._log_with_context("CRITICAL", message, **kwargs)

    def access_log(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        user_id: str = "",
        **kwargs,
    ):
        """Log HTTP access information."""
        self.info(
            f"{method} {path} - {status_code}",
            duration=duration,
            label_http_method=method,
            label_http_path=path,
            label_http_status=str(status_code),
            label_user_id=user_id,
            **kwargs,
        )

    def security_log(
        self,
        event: str,
        threat_level: str = "low",
        user_id: str = "",
        details: Dict[str, Any] = None,
        **kwargs,
    ):
        """Log security events."""
        details = details or {}
        self.warning(
            f"Security event: {event}",
            security_event=event,
            threat_level=threat_level,
            label_user_id=user_id,
            **{f"label_{k}": v for k, v in details.items()},
            **kwargs,
        )

    def business_log(
        self,
        event: str,
        value: Optional[float] = None,
        user_id: str = "",
        details: Dict[str, Any] = None,
        **kwargs,
    ):
        """Log business events."""
        details = details or {}
        self.info(
            f"Business event: {event}",
            business_event=event,
            business_value=value,
            label_user_id=user_id,
            **{f"label_{k}": v for k, v in details.items()},
            **kwargs,
        )

    def performance_log(
        self,
        operation: str,
        duration: float,
        memory_usage: Optional[float] = None,
        **kwargs,
    ):
        """Log performance metrics."""
        self.info(
            f"Performance: {operation}",
            duration=duration,
            memory_usage=memory_usage,
            label_operation=operation,
            **kwargs,
        )

    def audit_log(
        self,
        action: str,
        resource: str,
        user_id: str,
        result: str,
        details: Dict[str, Any] = None,
        **kwargs,
    ):
        """Log audit events for compliance."""
        details = details or {}
        self.info(
            f"Audit: {action} on {resource} by {user_id} - {result}",
            label_audit_action=action,
            label_audit_resource=resource,
            label_audit_user=user_id,
            label_audit_result=result,
            **{f"label_{k}": v for k, v in details.items()},
            **kwargs,
        )


# Context managers for request correlation
class RequestContext:
    """Context manager for request correlation."""

    def __init__(
        self,
        correlation_id: str = None,
        user_id: str = "",
        session_id: str = "",
        trace_id: str = "",
    ):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id
        self.trace_id = trace_id
        self.tokens = []

    def __enter__(self):
        self.tokens.append(correlation_id.set(self.correlation_id))
        self.tokens.append(user_id.set(self.user_id))
        self.tokens.append(session_id.set(self.session_id))
        self.tokens.append(trace_id.set(self.trace_id))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for token in reversed(self.tokens):
            token.reset()


# Global logger instance
_global_logger = None


def get_logger(context: Optional[LogContext] = None) -> UniversalLogger:
    """Get the global logger instance."""
    global _global_logger
    if _global_logger is None:
        if context is None:
            context = LogContext(
                service_name=os.getenv("SERVICE_NAME", "unknown-service"),
                service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
                environment=os.getenv("ENVIRONMENT", "development"),
                project_id=os.getenv("GCP_PROJECT", "unknown"),
            )
        _global_logger = UniversalLogger(context)
    return _global_logger


# Convenience functions
def debug(message: str, **kwargs):
    """Convenience function for debug logging."""
    get_logger().debug(message, **kwargs)


def info(message: str, **kwargs):
    """Convenience function for info logging."""
    get_logger().info(message, **kwargs)


def warning(message: str, **kwargs):
    """Convenience function for warning logging."""
    get_logger().warning(message, **kwargs)


def error(message: str, exception: Optional[Exception] = None, **kwargs):
    """Convenience function for error logging."""
    get_logger().error(message, exception=exception, **kwargs)


def critical(message: str, exception: Optional[Exception] = None, **kwargs):
    """Convenience function for critical logging."""
    get_logger().critical(message, exception=exception, **kwargs)
