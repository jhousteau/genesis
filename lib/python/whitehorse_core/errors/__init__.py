"""
Error Handling Module

Comprehensive error handling with recovery mechanisms, structured error logging,
and integration with monitoring systems.
"""

import functools
import sys
import time
import traceback
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

from ..logging import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error category types."""

    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NETWORK = "network"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    CONFIGURATION = "configuration"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """
    Error context information for better debugging and monitoring.
    """

    error_id: str
    timestamp: float
    severity: ErrorSeverity
    category: ErrorCategory
    service: str
    operation: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        result = asdict(self)
        result["severity"] = self.severity.value
        result["category"] = self.category.value
        return result


class WhitehorseError(Exception):
    """
    Base exception class for all Whitehorse-related errors.
    Includes structured error information and context.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        recoverable: bool = False,
        user_message: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.severity = severity
        self.category = category
        self.context = context
        self.cause = cause
        self.recoverable = recoverable
        self.user_message = user_message or message
        self.additional_data = kwargs
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging and monitoring."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp,
            "context": self.context.to_dict() if self.context else None,
            "cause": str(self.cause) if self.cause else None,
            "additional_data": self.additional_data,
        }


class ValidationError(WhitehorseError):
    """Data validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            **kwargs,
        )
        self.field = field


class AuthenticationError(WhitehorseError):
    """Authentication failures."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.AUTHENTICATION,
            **kwargs,
        )


class AuthorizationError(WhitehorseError):
    """Authorization failures."""

    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.AUTHORIZATION,
            **kwargs,
        )


class NetworkError(WhitehorseError):
    """Network-related errors."""

    def __init__(self, message: str, url: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            recoverable=True,
            **kwargs,
        )
        self.url = url


class DatabaseError(WhitehorseError):
    """Database-related errors."""

    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATABASE,
            **kwargs,
        )
        self.query = query


class ExternalServiceError(WhitehorseError):
    """External service integration errors."""

    def __init__(self, message: str, service: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.EXTERNAL_SERVICE,
            recoverable=True,
            **kwargs,
        )
        self.service = service


class ConfigurationError(WhitehorseError):
    """Configuration-related errors."""

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.CONFIGURATION,
            **kwargs,
        )
        self.config_key = config_key


class BusinessLogicError(WhitehorseError):
    """Business logic violation errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.BUSINESS_LOGIC,
            **kwargs,
        )


class SystemError(WhitehorseError):
    """System-level errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.SYSTEM,
            **kwargs,
        )


class RetryPolicy:
    """
    Retry policy configuration for error recovery.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retriable_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retriable_exceptions = retriable_exceptions or [
            NetworkError,
            ExternalServiceError,
            SystemError,
        ]

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random

            delay *= 0.5 + random.random() * 0.5  # 50-100% of calculated delay

        return delay

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if exception should be retried."""
        if attempt >= self.max_attempts:
            return False

        if isinstance(exception, WhitehorseError):
            if not exception.recoverable:
                return False

            return any(
                isinstance(exception, exc_type)
                for exc_type in self.retriable_exceptions
            )

        return any(
            isinstance(exception, exc_type) for exc_type in self.retriable_exceptions
        )


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def __call__(self, func: Callable) -> Callable:
        """Circuit breaker decorator."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half-open"
                else:
                    raise SystemError(
                        f"Circuit breaker open for {func.__name__}", recoverable=True
                    )

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception:
                self._on_failure()
                raise

        return wrapper

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        return (
            self.last_failure_time
            and time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class ErrorHandler:
    """
    Central error handler with recovery mechanisms and monitoring integration.
    """

    def __init__(self, service_name: str = "whitehorse-service"):
        self.service_name = service_name
        self.error_count = 0
        self.error_history: List[Dict[str, Any]] = []

    def handle_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        notify: bool = True,
    ) -> None:
        """
        Handle error with logging, monitoring, and notifications.

        Args:
            error: The exception that occurred
            context: Additional error context
            notify: Whether to send notifications for this error
        """
        self.error_count += 1

        # Create structured error information
        if isinstance(error, WhitehorseError):
            error_info = error.to_dict()
        else:
            error_info = {
                "error_code": error.__class__.__name__,
                "message": str(error),
                "severity": ErrorSeverity.MEDIUM.value,
                "category": ErrorCategory.UNKNOWN.value,
                "timestamp": time.time(),
            }

        # Add context if provided
        if context:
            error_info["context"] = context.to_dict()

        # Add traceback
        error_info["traceback"] = traceback.format_exc()

        # Log the error
        logger.error(
            f"Error handled: {error_info['message']}",
            error_info=error_info,
            service=self.service_name,
        )

        # Store in history (keep last 100 errors)
        self.error_history.append(error_info)
        if len(self.error_history) > 100:
            self.error_history.pop(0)

        # Send notifications if requested and severity is high enough
        if notify and error_info.get("severity") in ["high", "critical"]:
            self._send_notification(error_info)

    def _send_notification(self, error_info: Dict[str, Any]) -> None:
        """Send error notification (placeholder for integration)."""
        # This would integrate with alerting systems like PagerDuty, Slack, etc.
        logger.critical(
            "Critical error notification",
            error_code=error_info.get("error_code"),
            message=error_info.get("message"),
            service=self.service_name,
        )

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        recent_errors = [
            e
            for e in self.error_history
            if time.time() - e["timestamp"] < 3600  # Last hour
        ]

        severity_counts = {}
        category_counts = {}

        for error in recent_errors:
            severity = error.get("severity", "unknown")
            category = error.get("category", "unknown")

            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1

        return {
            "total_errors": self.error_count,
            "recent_errors": len(recent_errors),
            "severity_distribution": severity_counts,
            "category_distribution": category_counts,
            "error_rate": len(recent_errors) / 60,  # errors per minute
        }


# Decorators for error handling


def retry(policy: Optional[RetryPolicy] = None):
    """
    Retry decorator with configurable policy.

    Args:
        policy: Retry policy configuration
    """
    if policy is None:
        policy = RetryPolicy()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, policy.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not policy.should_retry(e, attempt):
                        break

                    delay = policy.calculate_delay(attempt)
                    logger.warning(
                        f"Retrying {func.__name__} (attempt {attempt}/{policy.max_attempts}) after {delay:.2f}s",
                        function=func.__name__,
                        attempt=attempt,
                        delay=delay,
                        error=str(e),
                    )

                    time.sleep(delay)

            # All retries exhausted
            logger.error(
                f"All retry attempts exhausted for {func.__name__}",
                function=func.__name__,
                attempts=policy.max_attempts,
                final_error=str(last_exception),
            )
            raise last_exception

        return wrapper

    return decorator


def handle_errors(error_handler: Optional[ErrorHandler] = None):
    """
    Error handling decorator.

    Args:
        error_handler: ErrorHandler instance
    """
    if error_handler is None:
        error_handler = ErrorHandler()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(e)
                raise

        return wrapper

    return decorator


@contextmanager
def error_context(
    operation: str,
    user_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None,
):
    """
    Context manager for providing error context.

    Args:
        operation: Name of the operation being performed
        user_id: User ID if applicable
        additional_data: Additional context data
    """
    import uuid

    from ..logging import get_correlation_id

    context = ErrorContext(
        error_id=str(uuid.uuid4()),
        timestamp=time.time(),
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.UNKNOWN,
        service="whitehorse-service",
        operation=operation,
        user_id=user_id,
        correlation_id=get_correlation_id(),
        additional_data=additional_data,
    )

    try:
        yield context
    except Exception as e:
        if isinstance(e, WhitehorseError):
            e.context = context
        raise


# Global error handler instance
global_error_handler = ErrorHandler()
