"""
Genesis Error Handling Module

Provides structured error handling with categorization, context preservation,
and automatic error reporting.
"""

from .handler import (
    ErrorCategory,
    ErrorContext,
    ErrorHandler,
    ErrorSeverity,
    GenesisError,
    InfrastructureError,
    NetworkError,
    RateLimitError,
    TimeoutError,
    ValidationError,
    get_error_handler,
    handle_error,
)

__all__ = [
    "ErrorCategory",
    "ErrorContext",
    "ErrorHandler",
    "ErrorSeverity",
    "GenesisError",
    "InfrastructureError",
    "NetworkError",
    "RateLimitError",
    "TimeoutError",
    "ValidationError",
    "get_error_handler",
    "handle_error",
]
