"""
Genesis Error Handling - Simplified and Enhanced

Provides structured error handling with:
- 14 error categories for proper classification
- Correlation ID tracking for request tracing
- Context preservation across operations
- Automatic error enrichment
"""

import json
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ErrorSeverity(Enum):
    """Error severity levels for logging and alerting."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification and handling."""

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


@dataclass
class ErrorContext:
    """Context information attached to errors for tracing and debugging."""

    correlation_id: str
    timestamp: datetime
    service: str
    environment: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "service": self.service,
            "environment": self.environment,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "metadata": self.metadata or {},
        }

    @classmethod
    def create_default(
        cls, service: Optional[str] = None, environment: Optional[str] = None
    ) -> "ErrorContext":
        """
        Create a default error context with proper service and environment detection.

        Args:
            service: Optional service name override
            environment: Optional environment override

        Returns:
            ErrorContext instance

        Raises:
            ValueError: If service or environment cannot be determined
        """
        if service is None or environment is None:
            from genesis.core.constants import get_environment, get_service_name

            if service is None:
                service = get_service_name()
            if environment is None:
                environment = get_environment()

        return cls(
            correlation_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            service=service,
            environment=environment,
        )


class GenesisError(Exception):
    """
    Base exception class for all Genesis errors.

    Provides structured error information including category, severity,
    context, and automatic correlation ID generation.
    """

    def __init__(
        self,
        message: str,
        code: str = "SYSTEM_ERROR",
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        details: Optional[dict[str, Any]] = None,
        retry_after: Optional[int] = None,
        recoverable: bool = True,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.severity = severity
        self.context = context or self._create_default_context()
        self.cause = cause
        self.details = details or {}
        self.retry_after = retry_after
        self.recoverable = recoverable
        self.stack_trace = self._capture_stack_trace()

    def _create_default_context(self) -> ErrorContext:
        """Create default error context with proper detection."""
        return ErrorContext.create_default()

    def _capture_stack_trace(self) -> list[str]:
        """Capture current stack trace for debugging."""
        return traceback.format_stack()[:-1]

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        error_dict = {
            "error": {
                "message": self.message,
                "code": self.code,
                "category": self.category.value,
                "severity": self.severity.value,
                "recoverable": self.recoverable,
                "timestamp": datetime.utcnow().isoformat(),
            },
            "context": self.context.to_dict() if self.context else {},
            "details": self.details,
        }

        if self.retry_after:
            error_dict["error"]["retry_after"] = self.retry_after

        if self.cause:
            error_dict["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause),
            }

        # Include stack trace for errors and critical issues
        if self.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            error_dict["error"]["stack_trace"] = self.stack_trace[
                -10:
            ]  # Last 10 frames

        return error_dict

    def to_json(self) -> str:
        """Convert error to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# Specific error classes for different categories
class InfrastructureError(GenesisError):
    """Infrastructure and platform-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code="INFRASTRUCTURE_ERROR",
            category=ErrorCategory.INFRASTRUCTURE,
            **kwargs,
        )


class NetworkError(GenesisError):
    """Network connectivity and communication errors."""

    def __init__(self, message: str, endpoint: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if endpoint:
            details["endpoint"] = endpoint
        kwargs["details"] = details
        super().__init__(
            message, code="NETWORK_ERROR", category=ErrorCategory.NETWORK, **kwargs
        )


class ValidationError(GenesisError):
    """Data validation and format errors."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        kwargs["details"] = details
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            **kwargs,
        )


class AuthenticationError(GenesisError):
    """Authentication failures."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code="AUTHENTICATION_ERROR",
            category=ErrorCategory.AUTHENTICATION,
            recoverable=False,
            **kwargs,
        )


class AuthorizationError(GenesisError):
    """Authorization and permission errors."""

    def __init__(self, message: str, resource: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if resource:
            details["resource"] = resource
        kwargs["details"] = details
        super().__init__(
            message,
            code="AUTHORIZATION_ERROR",
            category=ErrorCategory.AUTHORIZATION,
            recoverable=False,
            **kwargs,
        )


class GenesisTimeoutError(GenesisError):
    """Timeout and deadline exceeded errors."""

    def __init__(
        self, message: str, timeout_duration: Optional[float] = None, **kwargs
    ):
        details = kwargs.get("details", {})
        if timeout_duration:
            details["timeout_duration"] = timeout_duration
        kwargs["details"] = details
        super().__init__(
            message, code="TIMEOUT_ERROR", category=ErrorCategory.TIMEOUT, **kwargs
        )


class RateLimitError(GenesisError):
    """Rate limiting and throttling errors."""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(
            message,
            code="RATE_LIMIT_ERROR",
            category=ErrorCategory.RATE_LIMIT,
            retry_after=retry_after,
            **kwargs,
        )


class ExternalServiceError(GenesisError):
    """External service and API errors."""

    def __init__(self, message: str, service_name: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if service_name:
            details["service_name"] = service_name
        kwargs["details"] = details
        super().__init__(
            message,
            code="EXTERNAL_SERVICE_ERROR",
            category=ErrorCategory.EXTERNAL_SERVICE,
            **kwargs,
        )


class ResourceError(GenesisError):
    """Resource not found or access errors."""

    def __init__(self, message: str, resource_type: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        kwargs["details"] = details
        super().__init__(
            message, code="RESOURCE_ERROR", category=ErrorCategory.RESOURCE, **kwargs
        )


class ErrorHandler:
    """
    Central error handler for processing and converting exceptions.

    Manages error processing, categorization, and context enrichment.
    """

    def __init__(self, service_name: str, environment: str):
        """
        Initialize error handler with required service and environment info.

        Args:
            service_name: Name of the service (required)
            environment: Environment name (required)
        """
        if not service_name or not service_name.strip():
            raise ValueError("service_name is required and cannot be empty")
        if not environment or not environment.strip():
            raise ValueError("environment is required and cannot be empty")

        self.service_name = service_name.strip()
        self.environment = environment.strip()
        self.handlers: list[Callable[[GenesisError], None]] = []

    def handle(
        self, error: Exception, context: Optional[ErrorContext] = None
    ) -> GenesisError:
        """
        Handle any error and convert to GenesisError with enriched context.

        Args:
            error: The error to handle
            context: Optional error context to attach

        Returns:
            GenesisError instance with proper categorization
        """
        # If already a GenesisError, enrich with context if provided
        if isinstance(error, GenesisError):
            if context:
                error.context = context
            return error

        # Convert standard exceptions to GenesisError
        genesis_error = self._convert_to_genesis_error(error, context)

        # Process through registered handlers
        for handler in self.handlers:
            try:
                handler(genesis_error)
            except Exception:
                # Don't let handler errors break error handling
                pass

        return genesis_error

    def _convert_to_genesis_error(
        self, error: Exception, context: Optional[ErrorContext] = None
    ) -> GenesisError:
        """Convert standard exception to appropriate GenesisError subclass."""

        # Mapping of standard exceptions to Genesis error types
        error_mappings = {
            ConnectionError: NetworkError,
            TimeoutError: GenesisTimeoutError,
            PermissionError: AuthorizationError,
            FileNotFoundError: ResourceError,
            ValueError: ValidationError,
            KeyError: ValidationError,
            AttributeError: ValidationError,
        }

        # Find appropriate Genesis error class
        genesis_error_class = GenesisError
        for exc_type, error_class in error_mappings.items():
            if isinstance(error, exc_type):
                genesis_error_class = error_class
                break

        # Create context if not provided
        if context is None:
            context = ErrorContext.create_default(
                service=self.service_name, environment=self.environment
            )

        return genesis_error_class(message=str(error), context=context, cause=error)

    def add_handler(self, handler: Callable[[GenesisError], None]) -> None:
        """Add a handler function to process errors."""
        self.handlers.append(handler)


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """
    Get the global error handler instance.

    Returns:
        ErrorHandler instance with properly configured service and environment

    Raises:
        ValueError: If service name or environment cannot be determined
    """
    global _error_handler
    if _error_handler is None:
        from genesis.core.constants import get_environment, get_service_name

        _error_handler = ErrorHandler(
            service_name=get_service_name(),
            environment=get_environment(),
        )
    return _error_handler


def handle_error(
    error: Exception, context: Optional[ErrorContext] = None
) -> GenesisError:
    """
    Convenience function to handle errors with the global handler.

    Args:
        error: The error to handle
        context: Optional error context

    Returns:
        GenesisError instance with proper categorization and context
    """
    return get_error_handler().handle(error, context)
