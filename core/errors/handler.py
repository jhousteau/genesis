"""
Genesis Error Handling Foundation

Provides structured error handling with:
- Error categorization and codes
- Stack trace management
- Correlation ID tracking
- Context preservation
- Automatic error reporting
"""

import json
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


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
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for errors"""

    correlation_id: str
    timestamp: datetime
    service: str
    environment: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
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


class GenesisError(Exception):
    """
    Base error class for Genesis platform

    All Genesis errors should inherit from this class
    """

    def __init__(
        self,
        message: str,
        code: str = "GENESIS_ERROR",
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
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
        """Create default error context"""
        import os

        return ErrorContext(
            correlation_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            service=os.environ.get("GENESIS_SERVICE", "unknown"),
            environment=os.environ.get("GENESIS_ENV", "development"),
        )

    def _capture_stack_trace(self) -> List[str]:
        """Capture current stack trace"""
        return traceback.format_stack()[:-1]

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization"""
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

        if self.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            error_dict["stack_trace"] = self.stack_trace

        return error_dict

    def to_json(self) -> str:
        """Convert error to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class InfrastructureError(GenesisError):
    """Infrastructure-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code="INFRASTRUCTURE_ERROR",
            category=ErrorCategory.INFRASTRUCTURE,
            **kwargs,
        )


class ValidationError(GenesisError):
    """Validation errors"""

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


class NetworkError(GenesisError):
    """Network-related errors"""

    def __init__(self, message: str, endpoint: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if endpoint:
            details["endpoint"] = endpoint
        kwargs["details"] = details
        super().__init__(
            message, code="NETWORK_ERROR", category=ErrorCategory.NETWORK, **kwargs
        )


class TimeoutError(GenesisError):
    """Timeout errors"""

    def __init__(self, message: str, timeout_seconds: Optional[int] = None, **kwargs):
        details = kwargs.get("details", {})
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        kwargs["details"] = details
        super().__init__(
            message, code="TIMEOUT_ERROR", category=ErrorCategory.TIMEOUT, **kwargs
        )


class RateLimitError(GenesisError):
    """Rate limiting errors"""

    def __init__(
        self,
        message: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if limit:
            details["limit"] = limit
        if window:
            details["window_seconds"] = window
        kwargs["details"] = details
        super().__init__(
            message,
            code="RATE_LIMIT_ERROR",
            category=ErrorCategory.RATE_LIMIT,
            recoverable=True,
            **kwargs,
        )


class ErrorHandler:
    """
    Central error handler for Genesis platform

    Manages error processing, reporting, and recovery
    """

    def __init__(self, service_name: str, environment: str = "development"):
        self.service_name = service_name
        self.environment = environment
        self.handlers = []

    def handle(
        self, error: Exception, context: Optional[ErrorContext] = None
    ) -> GenesisError:
        """
        Handle any error and convert to GenesisError

        Args:
            error: The error to handle
            context: Optional error context

        Returns:
            GenesisError instance
        """
        if isinstance(error, GenesisError):
            if context:
                error.context = context
            return error

        # Convert standard exceptions to GenesisError
        genesis_error = self._convert_to_genesis_error(error, context)

        # Process through handlers
        for handler in self.handlers:
            handler(genesis_error)

        return genesis_error

    def _convert_to_genesis_error(
        self, error: Exception, context: Optional[ErrorContext] = None
    ) -> GenesisError:
        """Convert standard exception to GenesisError"""
        error_map = {
            ConnectionError: (NetworkError, ErrorCategory.NETWORK),
            TimeoutError: (TimeoutError, ErrorCategory.TIMEOUT),
            PermissionError: (GenesisError, ErrorCategory.AUTHORIZATION),
            FileNotFoundError: (GenesisError, ErrorCategory.RESOURCE),
            ValueError: (ValidationError, ErrorCategory.VALIDATION),
            KeyError: (ValidationError, ErrorCategory.VALIDATION),
        }

        error_class = GenesisError
        category = ErrorCategory.UNKNOWN

        for exc_type, (genesis_class, error_category) in error_map.items():
            if isinstance(error, exc_type):
                error_class = genesis_class
                category = error_category
                break

        return error_class(
            message=str(error), category=category, context=context, cause=error
        )

    def add_handler(self, handler):
        """Add an error handler function"""
        self.handlers.append(handler)

    def log_error(self, error: GenesisError):
        """Log error to configured logging system"""
        # This will be integrated with the logging module
        print(f"[{error.severity.value.upper()}] {error.code}: {error.message}")
        if error.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            print(f"Stack trace: {''.join(error.stack_trace[-5:])}")


# Global error handler instance
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance"""
    global _error_handler
    if _error_handler is None:
        import os

        _error_handler = ErrorHandler(
            service_name=os.environ.get("GENESIS_SERVICE", "genesis"),
            environment=os.environ.get("GENESIS_ENV", "development"),
        )
    return _error_handler


def handle_error(
    error: Exception, context: Optional[ErrorContext] = None
) -> GenesisError:
    """
    Convenience function to handle errors

    Args:
        error: The error to handle
        context: Optional error context

    Returns:
        GenesisError instance
    """
    return get_error_handler().handle(error, context)
