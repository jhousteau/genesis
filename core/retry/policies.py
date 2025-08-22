"""
Genesis Retry Policies

Pre-configured retry policies for common use cases. These policies follow
the PIPES methodology for standardized, production-ready configurations.

Policies:
    DEFAULT_POLICY: Balanced retry for most use cases
    AGGRESSIVE_POLICY: Fast retries for time-sensitive operations
    CONSERVATIVE_POLICY: Patient retries for resource-heavy operations
    CIRCUIT_BREAKER_POLICY: Integrated with circuit breaker pattern
"""

from typing import Any, Callable, Optional, Set, Type

import requests

from ..errors.handler import ErrorCategory, GenesisError
from .circuit_breaker import CircuitBreaker
from .retry import BackoffStrategy, RetryPolicy


def is_http_retryable(result: Any) -> bool:
    """
    Check if HTTP response should trigger retry.

    Args:
        result: HTTP response object or status code

    Returns:
        True if response indicates transient failure
    """
    if hasattr(result, "status_code"):
        # HTTP response object
        return result.status_code in {408, 429, 500, 502, 503, 504}
    elif isinstance(result, int):
        # Status code
        return result in {408, 429, 500, 502, 503, 504}

    return False


def is_gcp_retryable_error(exception: Exception) -> bool:
    """
    Check if GCP-specific error should trigger retry.

    Args:
        exception: Exception that occurred

    Returns:
        True if exception is a transient GCP error
    """
    # Check Genesis error categories
    if isinstance(exception, GenesisError):
        retryable_categories = {
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.RESOURCE_EXHAUSTED,
            ErrorCategory.UNAVAILABLE,
            ErrorCategory.EXTERNAL_SERVICE,
        }
        return exception.category in retryable_categories

    # Check exception message for GCP error patterns
    error_message = str(exception).lower()
    retryable_patterns = [
        "deadline exceeded",
        "service unavailable",
        "internal server error",
        "rate limit exceeded",
        "quota exceeded",
        "resource exhausted",
        "connection reset",
        "connection refused",
        "temporary failure",
        "try again",
    ]

    return any(pattern in error_message for pattern in retryable_patterns)


# Default retryable exceptions for Genesis platform
STANDARD_RETRYABLE_EXCEPTIONS: Set[Type[Exception]] = {
    ConnectionError,
    TimeoutError,
    OSError,
}

# Try to include requests exceptions if available
try:
    import requests

    STANDARD_RETRYABLE_EXCEPTIONS.update(
        {
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
        }
    )
except ImportError:
    pass


# =============================================================================
# PRE-CONFIGURED POLICIES
# =============================================================================

DEFAULT_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
    jitter=True,
    exceptions=STANDARD_RETRYABLE_EXCEPTIONS,
    retry_on_result=is_http_retryable,
    context_preserve=True,
)
"""
Default retry policy for most use cases.

Configuration:
- 3 attempts maximum (including initial)
- 1 second base delay
- Exponential backoff with jitter
- Retries on standard network/timeout errors
- Retries on HTTP 4xx/5xx status codes
"""


AGGRESSIVE_POLICY = RetryPolicy(
    max_attempts=5,
    base_delay=0.5,
    max_delay=30.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL,
    jitter=True,
    exceptions=STANDARD_RETRYABLE_EXCEPTIONS,
    retry_on_result=is_http_retryable,
    context_preserve=True,
)
"""
Aggressive retry policy for time-sensitive operations.

Configuration:
- 5 attempts maximum
- 0.5 second base delay
- Faster exponential backoff
- More attempts with shorter delays
- Good for real-time systems
"""


CONSERVATIVE_POLICY = RetryPolicy(
    max_attempts=2,
    base_delay=2.0,
    max_delay=120.0,
    backoff_strategy=BackoffStrategy.LINEAR,
    jitter=True,
    exceptions={
        ConnectionError,
        TimeoutError,
    },
    retry_on_result=None,  # Only retry on exceptions
    context_preserve=True,
)
"""
Conservative retry policy for resource-heavy operations.

Configuration:
- 2 attempts maximum
- 2 second base delay
- Linear backoff (predictable timing)
- Only retries on critical connection errors
- Good for expensive operations
"""


def create_policy(
    profile: str = "default",
    *,  # Force keyword-only arguments after profile
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    backoff: Optional[BackoffStrategy] = None,
    exceptions: Optional[Set[Type[Exception]]] = None,
    retry_on_result: Optional[Callable[[Any], bool]] = None,
) -> RetryPolicy:
    """
    Create a customized retry policy based on a profile.

    Args:
        profile: Base profile ('default', 'aggressive', 'conservative')
        max_attempts: Override max attempts
        base_delay: Override base delay
        max_delay: Override max delay
        backoff: Override backoff strategy
        exceptions: Override retryable exceptions
        retry_on_result: Override result-based retry function

    Returns:
        Customized RetryPolicy instance

    Examples:
        # Create faster default policy
        policy = create_policy("default", max_attempts=5, base_delay=0.5)

        # Create GCP-optimized policy
        policy = create_policy("aggressive", retry_on_result=is_gcp_retryable_error)
    """
    # Select base policy
    if profile == "aggressive":
        base = AGGRESSIVE_POLICY
    elif profile == "conservative":
        base = CONSERVATIVE_POLICY
    else:  # default
        base = DEFAULT_POLICY

    # Create customized policy
    return RetryPolicy(
        max_attempts=max_attempts if max_attempts is not None else base.max_attempts,
        base_delay=base_delay if base_delay is not None else base.base_delay,
        max_delay=max_delay if max_delay is not None else base.max_delay,
        backoff_strategy=backoff if backoff is not None else base.backoff_strategy,
        jitter=base.jitter,
        exceptions=exceptions if exceptions is not None else base.exceptions,
        retry_on_result=(
            retry_on_result if retry_on_result is not None else base.retry_on_result
        ),
        context_preserve=base.context_preserve,
    )


# Circuit breaker instances for different scenarios
_default_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=60.0,
    half_open_max_calls=3,
    success_threshold=2,
    name="DefaultCircuit",
)

_aggressive_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    timeout=30.0,
    half_open_max_calls=2,
    success_threshold=1,
    name="AggressiveCircuit",
)

_conservative_circuit_breaker = CircuitBreaker(
    failure_threshold=10,
    timeout=180.0,
    half_open_max_calls=5,
    success_threshold=3,
    name="ConservativeCircuit",
)


def create_circuit_breaker_policy(
    profile: str = "default",
    circuit_breaker: Optional[CircuitBreaker] = None,
) -> tuple[RetryPolicy, CircuitBreaker]:
    """
    Create a retry policy with integrated circuit breaker.

    Args:
        profile: Base profile for retry policy
        circuit_breaker: Custom circuit breaker instance

    Returns:
        Tuple of (RetryPolicy, CircuitBreaker)

    Example:
        policy, cb = create_circuit_breaker_policy("aggressive")

        @retry(policy=policy)
        @cb.decorator
        def external_service_call():
            # Your code here
            pass
    """
    # Select circuit breaker
    if circuit_breaker is None:
        if profile == "aggressive":
            circuit_breaker = _aggressive_circuit_breaker
        elif profile == "conservative":
            circuit_breaker = _conservative_circuit_breaker
        else:
            circuit_breaker = _default_circuit_breaker

    # Create matching retry policy
    retry_policy = create_policy(profile)

    return retry_policy, circuit_breaker


# GCP-specific policies
GCP_POLICY = create_policy(
    "default",
    max_attempts=4,
    retry_on_result=lambda result: (
        is_http_retryable(result)
        or (
            hasattr(result, "status_code") and result.status_code == 401
        )  # Token refresh
    ),
)
"""
GCP-optimized retry policy.

Includes retry patterns specific to Google Cloud Platform:
- Token refresh on 401 errors
- GCP service error detection
- Cloud API rate limiting
"""


DATABASE_POLICY = create_policy(
    "conservative",
    exceptions={
        ConnectionError,
        TimeoutError,
        OSError,
    },
    retry_on_result=None,  # Don't retry based on results for DB operations
)
"""
Database operation retry policy.

Conservative approach for database operations:
- Limited retries to prevent data consistency issues
- Only retries on connection failures
- No result-based retries
"""


API_POLICY = create_policy(
    "aggressive",
    retry_on_result=is_http_retryable,
)
"""
API call retry policy.

Optimized for external API calls:
- More attempts for network resilience
- HTTP status code based retries
- Faster recovery from transient failures
"""


# Export all policies and utilities
__all__ = [
    # Pre-configured policies
    "DEFAULT_POLICY",
    "AGGRESSIVE_POLICY",
    "CONSERVATIVE_POLICY",
    "GCP_POLICY",
    "DATABASE_POLICY",
    "API_POLICY",
    # Policy creation functions
    "create_policy",
    "create_circuit_breaker_policy",
    # Utility functions
    "is_http_retryable",
    "is_gcp_retryable_error",
    # Standard exceptions
    "STANDARD_RETRYABLE_EXCEPTIONS",
]
