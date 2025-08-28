"""
Genesis Error Framework

Structured error handling with categorization, context preservation,
and correlation ID tracking.
"""

from .handler import (
    AuthenticationError,
    AuthorizationError,
    ErrorCategory,
    ErrorContext,
    ErrorHandler,
    ErrorSeverity,
    ExternalServiceError,
    GenesisError,
    GenesisTimeoutError,
    InfrastructureError,
    NetworkError,
    RateLimitError,
    ResourceError,
    ValidationError,
    get_error_handler,
    handle_error,
)

__all__ = [
    "ErrorCategory",
    "ErrorSeverity",
    "ErrorContext",
    "GenesisError",
    "InfrastructureError",
    "NetworkError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "GenesisTimeoutError",
    "RateLimitError",
    "ExternalServiceError",
    "ResourceError",
    "ErrorHandler",
    "handle_error",
    "get_error_handler",
]
