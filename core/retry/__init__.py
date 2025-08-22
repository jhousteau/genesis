"""
Genesis Core Retry Module

Provides production-ready retry logic and circuit breaker patterns for resilient
cloud-native applications. Implements exponential backoff with jitter, configurable
retry policies, and thread-safe circuit breakers.

Components:
    - RetryPolicy: Configurable retry strategies
    - RetryExecutor: Executes operations with retry logic
    - CircuitBreaker: Three-state circuit breaker pattern
    - BackoffStrategy: Various backoff algorithms

Example:
    >>> from core.retry import retry, CircuitBreaker
    >>>
    >>> @retry(max_attempts=3, backoff='exponential')
    >>> def unreliable_operation():
    >>>     # Your code here
    >>>     pass
    >>>
    >>> cb = CircuitBreaker(failure_threshold=5, timeout=60)
    >>> result = cb.call(unreliable_operation)
"""

import logging

from .circuit_breaker import CircuitBreaker, CircuitBreakerError, CircuitBreakerState
from .policies import (
    AGGRESSIVE_POLICY,
    CONSERVATIVE_POLICY,
    DEFAULT_POLICY,
    create_policy,
)

# Import main components (will be implemented)
from .retry import BackoffStrategy, RetryExecutor, RetryPolicy, retry, retry_async

# Version information
__version__ = "1.0.0"
__author__ = "Genesis Core Team"

# Public API exports
__all__ = [
    # Retry functionality
    "RetryPolicy",
    "RetryExecutor",
    "BackoffStrategy",
    "retry",
    "retry_async",
    # Circuit breaker functionality
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerError",
    # Pre-configured policies
    "DEFAULT_POLICY",
    "AGGRESSIVE_POLICY",
    "CONSERVATIVE_POLICY",
    "create_policy",
]

# Module-level logger
logger = logging.getLogger(__name__)
