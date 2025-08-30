"""Genesis Error Handling - Python Implementation

Provides structured error handling with:
- 14 error categories for proper classification
- Correlation ID tracking for request tracing
- Context preservation across operations
- Automatic error enrichment
"""

import os
import traceback
import uuid
from datetime import datetime
from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Error severity levels"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""

    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    EXTERNAL_SERVICE = "external_service"
    RESOURCE = "resource"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ErrorContext:
    """Error context for tracking"""

    def __init__(
        self,
        correlation_id: str,
        timestamp: datetime,
        service: str,
        environment: str,
        user_id: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.correlation_id = correlation_id
        self.timestamp = timestamp
        self.service = service
        self.environment = environment
        self.user_id = user_id
        self.request_id = request_id
        self.trace_id = trace_id
        self.span_id = span_id
        self.metadata = metadata or {}


def create_error_context(
    service: str | None = None, environment: str | None = None
) -> ErrorContext:
    """Create default error context"""
    return ErrorContext(
        correlation_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        service=service or os.environ.get("SERVICE", "genesis"),
        environment=environment or os.environ.get("ENV", "development"),
    )


class GenesisError(Exception):
    """Base exception class for all Genesis errors"""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
        details: dict[str, Any] | None = None,
        retry_after: int | None = None,
        recoverable: bool = True,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or "GENESIS_ERROR"
        self.category = category
        self.severity = severity
        self.context = context or self._create_default_context()
        self.cause = cause
        self.details = details or {}
        self.retry_after = retry_after
        self.recoverable = recoverable
        self.stack_trace = self._capture_stack_trace()

    def _create_default_context(self) -> ErrorContext:
        """Create default error context"""
        return create_error_context()

    def _capture_stack_trace(self) -> list[str]:
        """Capture current stack trace"""
        return traceback.format_tb(self.__traceback__) if self.__traceback__ else []

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary"""
        error_data = {
            "error": {
                "message": self.message,
                "code": self.code,
                "category": self.category.value,
                "severity": self.severity.value,
                "recoverable": self.recoverable,
                "timestamp": datetime.utcnow().isoformat(),
            },
            "context": {
                "correlation_id": self.context.correlation_id,
                "timestamp": self.context.timestamp.isoformat(),
                "service": self.context.service,
                "environment": self.context.environment,
                "user_id": self.context.user_id,
                "request_id": self.context.request_id,
                "trace_id": self.context.trace_id,
                "span_id": self.context.span_id,
                "metadata": self.context.metadata,
            },
            "details": self.details,
        }

        if self.retry_after:
            error_data["error"]["retry_after"] = self.retry_after

        if self.cause:
            error_data["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause),
            }

        return error_data

    def to_json(self) -> dict[str, Any]:
        """Alias for to_dict for TypeScript compatibility"""
        return self.to_dict()


class InfrastructureError(GenesisError):
    """Infrastructure-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message, category=ErrorCategory.INFRASTRUCTURE, **kwargs
        )


class NetworkError(GenesisError):
    """Network-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message=message, category=ErrorCategory.NETWORK, **kwargs)


class ValidationError(GenesisError):
    """Validation errors"""

    def __init__(self, message: str, field: str | None = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field

        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            details=details,
            **kwargs,
        )


class AuthenticationError(GenesisError):
    """Authentication errors"""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            recoverable=False,
            **kwargs,
        )


class AuthorizationError(GenesisError):
    """Authorization errors"""

    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTHORIZATION,
            recoverable=False,
            **kwargs,
        )


class TimeoutError(GenesisError):
    """Timeout errors"""

    def __init__(self, message: str, timeout_seconds: float | None = None, **kwargs):
        details = kwargs.get("details", {})
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds

        super().__init__(
            message=message, category=ErrorCategory.TIMEOUT, details=details, **kwargs
        )


class RateLimitError(GenesisError):
    """Rate limit errors"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.RATE_LIMIT,
            retry_after=retry_after,
            **kwargs,
        )


class ExternalServiceError(GenesisError):
    """External service errors"""

    def __init__(self, message: str, service_name: str | None = None, **kwargs):
        details = kwargs.get("details", {})
        if service_name:
            details["service_name"] = service_name

        super().__init__(
            message=message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            details=details,
            **kwargs,
        )


class ResourceError(GenesisError):
    """Resource-related errors"""

    def __init__(self, message: str, resource_type: str | None = None, **kwargs):
        details = kwargs.get("details", {})
        if resource_type:
            details["resource_type"] = resource_type

        super().__init__(
            message=message, category=ErrorCategory.RESOURCE, details=details, **kwargs
        )


class ErrorHandler:
    """Error handling utilities"""

    @staticmethod
    def handle_error(error: Exception) -> GenesisError:
        """Convert any exception to GenesisError"""
        if isinstance(error, GenesisError):
            return error

        # Map common Python exceptions to Genesis errors
        if isinstance(error, ValueError):
            return ValidationError(str(error), cause=error)
        elif isinstance(error, ConnectionError):
            return NetworkError(str(error), cause=error)
        elif isinstance(error, TimeoutError):
            return TimeoutError(str(error), cause=error)
        elif isinstance(error, PermissionError):
            return AuthorizationError(str(error), cause=error)
        else:
            return GenesisError(
                message=str(error), category=ErrorCategory.UNKNOWN, cause=error
            )


def get_error_handler() -> ErrorHandler:
    """Get error handler instance"""
    return ErrorHandler()


def handle_error(error: Exception) -> GenesisError:
    """Convenience function to handle any error"""
    return ErrorHandler.handle_error(error)
