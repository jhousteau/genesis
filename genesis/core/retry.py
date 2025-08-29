"""
Retry and Circuit Breaker - Resilience patterns for distributed systems.

This module provides:
1. **Retry decorator**: Exponential backoff with jitter for transient failures
2. **Circuit Breaker**: Fail-fast pattern to prevent cascading failures
3. **Integration**: Combined retry + circuit breaker for maximum resilience

Basic Usage:
    # Simple retry
    @retry()
    def api_call():
        return requests.get('https://api.example.com')

    # Circuit breaker
    @circuit_breaker()
    def database_query():
        return db.execute('SELECT * FROM table')

    # Combined resilience
    @resilient_call()
    def external_service():
        return service.get_data()

    # Pre-configured patterns
    @resilient_external_service()
    def api_call():
        return requests.get('https://api.example.com')

    @resilient_database()
    def db_call():
        return db.query('SELECT * FROM users')

Circuit Breaker States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit tripped, requests fail fast to prevent cascading failures
    - HALF_OPEN: Testing if service recovered, limited requests allowed

Integration Pattern:
    The resilient_call decorator applies circuit breaker around retry:
    1. Circuit breaker checks if call can proceed
    2. If open, fails fast with CircuitBreakerError (no retry)
    3. If closed/half-open, retry decorator handles transient failures
    4. Circuit tracks success/failure of overall retry attempts

This prevents retry storms against failing services while handling transient failures.
"""

import asyncio
import functools
import inspect
import random
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

from .errors.handler import ErrorCategory, GenesisError

# Type variable for generic functions
F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int
    initial_delay: float
    max_delay: float
    exponential_base: float
    jitter: bool = True
    exceptions: tuple[type[Exception], ...] = (Exception,)

    @classmethod
    def default(cls) -> "RetryConfig":
        """Create RetryConfig with values from environment variables."""
        from genesis.core.constants import RetryDefaults

        return cls(
            max_attempts=RetryDefaults.get_max_attempts(),
            initial_delay=RetryDefaults.get_initial_delay(),
            max_delay=RetryDefaults.get_max_delay(),
            exponential_base=RetryDefaults.get_exponential_base(),
        )

    @classmethod
    def create(
        cls,
        max_attempts: int | None = None,
        initial_delay: float | None = None,
        max_delay: float | None = None,
        exponential_base: float | None = None,
        jitter: bool | None = None,
        exceptions: tuple[type[Exception], ...] | None = None,
    ) -> "RetryConfig":
        """Create RetryConfig with optional parameters, using defaults for missing ones."""
        default_config = cls.default()

        return cls(
            max_attempts=(
                max_attempts
                if max_attempts is not None
                else default_config.max_attempts
            ),
            initial_delay=(
                initial_delay
                if initial_delay is not None
                else default_config.initial_delay
            ),
            max_delay=max_delay if max_delay is not None else default_config.max_delay,
            exponential_base=(
                exponential_base
                if exponential_base is not None
                else default_config.exponential_base
            ),
            jitter=jitter if jitter is not None else default_config.jitter,
            exceptions=(
                exceptions if exceptions is not None else default_config.exceptions
            ),
        )


def retry(config: RetryConfig | None = None) -> Callable:
    """Retry decorator with exponential backoff.

    Args:
        config: RetryConfig instance. Defaults to basic configuration.

    Usage:
        @retry()
        def unreliable_function():
            # May fail, will be retried
            pass

        @retry(RetryConfig.default())
        async def async_function():
            # Async functions supported
            pass
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            return _async_retry_wrapper(func, config)
        else:
            return _sync_retry_wrapper(func, config)

    return decorator


def _sync_retry_wrapper(func: Callable, config: RetryConfig) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        last_exception = None

        for attempt in range(config.max_attempts):
            try:
                return func(*args, **kwargs)
            except config.exceptions as e:
                last_exception = e
                if attempt == config.max_attempts - 1:
                    break

                delay = min(
                    config.initial_delay * (config.exponential_base**attempt),
                    config.max_delay,
                )
                if config.jitter:
                    delay *= random.uniform(0.5, 1.5)

                time.sleep(delay)

        raise last_exception

    return wrapper


def _async_retry_wrapper(func: Callable, config: RetryConfig) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        last_exception = None

        for attempt in range(config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except config.exceptions as e:
                last_exception = e
                if attempt == config.max_attempts - 1:
                    break

                delay = min(
                    config.initial_delay * (config.exponential_base**attempt),
                    config.max_delay,
                )
                if config.jitter:
                    delay *= random.uniform(0.5, 1.5)

                await asyncio.sleep(delay)

        raise last_exception

    return wrapper


# Circuit Breaker Implementation
class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Circuit tripped, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(GenesisError):
    """Exception raised when circuit breaker is open."""

    def __init__(self, message: str, circuit_name: str):
        super().__init__(
            message=message,
            code="CIRCUIT_BREAKER_OPEN",
            category=ErrorCategory.UNAVAILABLE,
            details={
                "circuit_name": circuit_name,
                "circuit_state": "open",
                "error_type": "circuit_breaker_open",
            },
        )
        self.circuit_name = circuit_name


@dataclass
class CircuitBreakerMetrics:
    """Metrics tracked by the circuit breaker."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    open_state_count: int = 0
    half_open_state_count: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    state_transitions: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100.0

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100.0


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int
    timeout: float
    half_open_max_calls: int
    success_threshold: int
    sliding_window_size: int
    name: str

    @classmethod
    def default(cls, name: str | None = None) -> "CircuitBreakerConfig":
        """Create CircuitBreakerConfig with values from environment variables."""
        from genesis.core.constants import CircuitBreakerDefaults

        return cls(
            failure_threshold=CircuitBreakerDefaults.get_failure_threshold(),
            timeout=CircuitBreakerDefaults.get_timeout(),
            half_open_max_calls=CircuitBreakerDefaults.get_half_open_max_calls(),
            success_threshold=CircuitBreakerDefaults.get_success_threshold(),
            sliding_window_size=CircuitBreakerDefaults.get_sliding_window_size(),
            name=name or "CircuitBreaker",
        )

    @classmethod
    def create(
        cls,
        failure_threshold: int | None = None,
        timeout: float | None = None,
        half_open_max_calls: int | None = None,
        success_threshold: int | None = None,
        sliding_window_size: int | None = None,
        name: str | None = None,
    ) -> "CircuitBreakerConfig":
        """Create CircuitBreakerConfig with optional parameters, using defaults for missing ones."""
        default_config = cls.default()

        return cls(
            failure_threshold=(
                failure_threshold
                if failure_threshold is not None
                else default_config.failure_threshold
            ),
            timeout=timeout if timeout is not None else default_config.timeout,
            half_open_max_calls=(
                half_open_max_calls
                if half_open_max_calls is not None
                else default_config.half_open_max_calls
            ),
            success_threshold=(
                success_threshold
                if success_threshold is not None
                else default_config.success_threshold
            ),
            sliding_window_size=(
                sliding_window_size
                if sliding_window_size is not None
                else default_config.sliding_window_size
            ),
            name=name if name is not None else default_config.name,
        )


class CircuitBreaker:
    """
    Thread-safe circuit breaker implementation.

    The circuit breaker monitors failures and prevents requests to a failing
    service. It has three states:
    - CLOSED: Normal operation
    - OPEN: Service is failing, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, config: CircuitBreakerConfig | None = None):
        if config is None:
            config = CircuitBreakerConfig.default()

        # Configuration
        self.failure_threshold = config.failure_threshold
        self.timeout = config.timeout
        self.half_open_max_calls = config.half_open_max_calls
        self.success_threshold = config.success_threshold
        self.sliding_window_size = config.sliding_window_size
        self.name = config.name

        # State management
        self._state = CircuitBreakerState.CLOSED
        self._last_failure_time: float | None = None
        self._half_open_calls = 0
        self._half_open_successes = 0

        # Sliding window for tracking recent calls
        self._call_results: deque[bool] = deque(maxlen=config.sliding_window_size)

        # Thread safety
        self._lock = threading.RLock()

        # Metrics
        self._metrics = CircuitBreakerMetrics()

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        with self._lock:
            return self._state

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        """Get current metrics (thread-safe copy)."""
        with self._lock:
            return CircuitBreakerMetrics(
                total_requests=self._metrics.total_requests,
                successful_requests=self._metrics.successful_requests,
                failed_requests=self._metrics.failed_requests,
                open_state_count=self._metrics.open_state_count,
                half_open_state_count=self._metrics.half_open_state_count,
                last_failure_time=self._metrics.last_failure_time,
                last_success_time=self._metrics.last_success_time,
                state_transitions=self._metrics.state_transitions,
            )

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset from OPEN to HALF_OPEN."""
        if self._state != CircuitBreakerState.OPEN:
            return False
        if self._last_failure_time is None:
            return False
        return time.time() - self._last_failure_time >= self.timeout

    def _transition_to_state(self, new_state: CircuitBreakerState) -> None:
        """Transition to a new state."""
        if new_state == self._state:
            return

        self._state = new_state
        self._metrics.state_transitions += 1

        # State-specific initialization
        if new_state == CircuitBreakerState.HALF_OPEN:
            self._half_open_calls = 0
            self._half_open_successes = 0
            self._metrics.half_open_state_count += 1
        elif new_state == CircuitBreakerState.OPEN:
            self._metrics.open_state_count += 1

    def _record_success(self) -> None:
        """Record a successful call."""
        current_time = time.time()

        with self._lock:
            self._call_results.append(True)
            self._metrics.total_requests += 1
            self._metrics.successful_requests += 1
            self._metrics.last_success_time = current_time

            # Handle success in different states
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._half_open_successes += 1

                # Check if we can close the circuit
                if self._half_open_successes >= self.success_threshold:
                    self._transition_to_state(CircuitBreakerState.CLOSED)

    def _record_failure(self, exception: Exception) -> None:
        """Record a failed call."""
        current_time = time.time()

        with self._lock:
            self._call_results.append(False)
            self._metrics.total_requests += 1
            self._metrics.failed_requests += 1
            self._metrics.last_failure_time = current_time
            self._last_failure_time = current_time

            # Check if we should open the circuit
            if self._state == CircuitBreakerState.CLOSED:
                # Count recent failures
                recent_failures = sum(1 for result in self._call_results if not result)

                if (
                    self.failure_threshold > 0
                    and recent_failures >= self.failure_threshold
                ):
                    self._transition_to_state(CircuitBreakerState.OPEN)

            elif self._state == CircuitBreakerState.HALF_OPEN:
                # Any failure in half-open state reopens the circuit
                self._transition_to_state(CircuitBreakerState.OPEN)

    def _can_execute(self) -> bool:
        """Check if a call can be executed."""
        with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True
            elif self._state == CircuitBreakerState.OPEN:
                # Check if we should try to reset
                if self._should_attempt_reset():
                    self._transition_to_state(CircuitBreakerState.HALF_OPEN)
                    self._half_open_calls = 1  # Count the call we're about to make
                    return True
                return False
            elif self._state == CircuitBreakerState.HALF_OPEN:
                # Allow limited calls in half-open state
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            return False

    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute a function through the circuit breaker."""
        if not self._can_execute():
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is open. "
                f"Failure rate: {self._metrics.failure_rate:.1f}%",
                circuit_name=self.name,
            )

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise

    async def call_async(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute an async function through the circuit breaker."""
        if not self._can_execute():
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is open. "
                f"Failure rate: {self._metrics.failure_rate:.1f}%",
                circuit_name=self.name,
            )

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise

    def decorator(self, func: F) -> F:
        """Decorator for wrapping functions with circuit breaker."""
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.call_async(func, *args, **kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self.call(func, *args, **kwargs)

            return sync_wrapper

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        with self._lock:
            self._transition_to_state(CircuitBreakerState.CLOSED)
            self._call_results.clear()
            self._half_open_calls = 0
            self._half_open_successes = 0

    def get_status(self) -> dict:
        """Get detailed status information."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_threshold": self.failure_threshold,
                "timeout": self.timeout,
                "metrics": {
                    "total_requests": self._metrics.total_requests,
                    "successful_requests": self._metrics.successful_requests,
                    "failed_requests": self._metrics.failed_requests,
                    "success_rate": round(self._metrics.success_rate, 2),
                    "failure_rate": round(self._metrics.failure_rate, 2),
                    "last_failure_time": self._metrics.last_failure_time,
                    "last_success_time": self._metrics.last_success_time,
                    "state_transitions": self._metrics.state_transitions,
                },
                "config": {
                    "half_open_max_calls": self.half_open_max_calls,
                    "success_threshold": self.success_threshold,
                    "sliding_window_size": self.sliding_window_size,
                },
            }


def circuit_breaker(config: CircuitBreakerConfig | None = None) -> Callable:
    """Circuit breaker decorator factory."""
    cb = CircuitBreaker(config)
    return cb.decorator


# Integration: Retry + Circuit Breaker
def resilient_call(
    retry_config: RetryConfig | None = None,
    circuit_config: CircuitBreakerConfig | None = None,
) -> Callable:
    """
    Combined retry and circuit breaker decorator.

    Circuit breaker wraps retry - if circuit is open, no retry attempts are made.
    This prevents retry storms against failing services.

    Args:
        retry_config: Configuration for retry behavior
        circuit_config: Configuration for circuit breaker

    Usage:
        @resilient_call()
        def external_api_call():
            return requests.get('https://api.example.com')

        @resilient_call(
            retry_config=RetryConfig.default(),
            circuit_config=CircuitBreakerConfig.default()
        )
        def database_call():
            return db.query("SELECT * FROM table")
    """

    def decorator(func: Callable) -> Callable:
        # Apply retry decorator first
        retried_func = retry(retry_config)(func)

        # Then wrap with circuit breaker
        cb = CircuitBreaker(circuit_config)
        return cb.decorator(retried_func)

    return decorator


# Convenience functions
def resilient_external_service(
    max_attempts: int | None = None,
    failure_threshold: int | None = None,
    timeout: float | None = None,
    name: str | None = None,
) -> Callable:
    """
    Pre-configured resilient decorator for external service calls.

    Optimized for typical external service patterns:
    - More aggressive retry (3 attempts with exponential backoff)
    - Lower failure threshold (5 failures opens circuit)
    - Moderate timeout (60 seconds)
    """
    return resilient_call(
        retry_config=RetryConfig.create(
            max_attempts=max_attempts,
        ),
        circuit_config=CircuitBreakerConfig.create(
            failure_threshold=failure_threshold,
            timeout=timeout,
            name=name,
        ),
    )


def resilient_database(
    max_attempts: int | None = None,
    failure_threshold: int | None = None,
    timeout: float | None = None,
    name: str | None = None,
) -> Callable:
    """
    Pre-configured resilient decorator for database calls.

    Optimized for database patterns:
    - Conservative retry (2 attempts to avoid long delays)
    - Aggressive circuit breaker (3 failures opens circuit)
    - Shorter timeout (30 seconds for faster recovery)
    """
    return resilient_call(
        retry_config=RetryConfig.create(
            max_attempts=max_attempts,
        ),
        circuit_config=CircuitBreakerConfig.create(
            failure_threshold=failure_threshold,
            timeout=timeout,
            name=name,
        ),
    )
