"""Genesis shared Python utilities.

Provides essential utilities for retry logic, logging, configuration, health checks,
error handling, and context management.
All utilities are designed to be lightweight and dependency-free.
"""

from .config import ConfigLoader, load_config
from .context import (
    ContextManager,
    RequestContext,
    TraceContext,
    clear_context,
    context_span,
    context_span_async,
    create_request_context,
    create_trace_context,
    get_context,
    get_correlation_id,
    get_request_id,
    get_trace_id,
    set_context,
)
from .errors import (
    AuthenticationError,
    AuthorizationError,
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    ExternalServiceError,
    GenesisError,
    InfrastructureError,
    NetworkError,
    RateLimitError,
    ResourceError,
    TimeoutError,
    ValidationError,
    create_error_context,
    handle_error,
)
from .health import HealthCheck, HealthStatus
from .logger import LogConfig, get_logger
from .retry import RetryConfig, retry

__version__ = "0.1.0"
__all__ = [
    # Retry utilities
    "retry",
    "RetryConfig",
    # Logging utilities
    "get_logger",
    "LogConfig",
    # Config utilities
    "load_config",
    "ConfigLoader",
    # Health check utilities
    "HealthCheck",
    "HealthStatus",
    # Context management
    "RequestContext",
    "TraceContext",
    "ContextManager",
    "get_context",
    "set_context",
    "clear_context",
    "context_span",
    "context_span_async",
    "get_correlation_id",
    "get_request_id",
    "get_trace_id",
    "create_request_context",
    "create_trace_context",
    # Error handling
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorContext",
    "GenesisError",
    "InfrastructureError",
    "NetworkError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "TimeoutError",
    "RateLimitError",
    "ExternalServiceError",
    "ResourceError",
    "handle_error",
    "create_error_context",
]
