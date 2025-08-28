"""
Genesis Error Framework

Structured error handling with categorization, context preservation,
and correlation ID tracking.
"""

from .handler import (
    ErrorCategory,
    ErrorSeverity,
    ErrorContext,
    GenesisError,
    InfrastructureError,
    NetworkError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    GenesisTimeoutError,
    RateLimitError,
    ExternalServiceError,
    ResourceError,
    ErrorHandler,
    handle_error,
    get_error_handler,
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
