"""
Genesis Circuit Breaker Implementation

Provides a thread-safe circuit breaker pattern with three states (CLOSED, OPEN, HALF_OPEN)
for handling failures in distributed systems. Prevents cascading failures by stopping
requests to failing services and allowing automatic recovery.

Classes:
    CircuitBreakerState: Enumeration of circuit breaker states
    CircuitBreakerError: Exception raised when circuit is open
    CircuitBreaker: Main circuit breaker implementation

Usage:
    cb = CircuitBreaker(failure_threshold=5, timeout=60)

    @cb.decorator
    def external_service_call():
        # Your code here
        pass

    # Or use directly
    result = cb.call(external_service_call)
"""

import functools
import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Deque, Optional, TypeVar

from ..errors.handler import ErrorCategory, GenesisError
# Import Genesis core components
from ..logging.logger import GenesisLogger

# Type variable for generic functions
F = TypeVar("F", bound=Callable[..., Any])

# Module logger
logger = GenesisLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Circuit tripped, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(GenesisError):
    """Exception raised when circuit breaker is open."""

    def __init__(self, message: str, circuit_name: str = "unknown"):
        super().__init__(
            message=message,
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
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
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


class CircuitBreaker:
    """
    Thread-safe circuit breaker implementation.

    The circuit breaker monitors failures and prevents requests to a failing
    service. It has three states:
    - CLOSED: Normal operation
    - OPEN: Service is failing, requests fail fast
    - HALF_OPEN: Testing if service recovered

    Args:
        failure_threshold: Number of failures before opening circuit
        timeout: Time to wait before transitioning from OPEN to HALF_OPEN
        half_open_max_calls: Max calls to allow in HALF_OPEN state
        success_threshold: Successes needed in HALF_OPEN to close circuit
        sliding_window_size: Size of failure tracking window
        name: Name for logging and identification
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        half_open_max_calls: int = 5,
        success_threshold: int = 1,
        sliding_window_size: int = 10,
        name: str = "CircuitBreaker",
    ):
        # Configuration
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold
        self.sliding_window_size = sliding_window_size
        self.name = name

        # State management
        self._state = CircuitBreakerState.CLOSED
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._half_open_successes = 0

        # Sliding window for tracking recent calls
        self._call_results: Deque[bool] = deque(maxlen=sliding_window_size)

        # Thread safety
        self._lock = threading.RLock()

        # Metrics
        self._metrics = CircuitBreakerMetrics()

        # Logger
        self._logger = GenesisLogger(f"{__name__}.{name}")

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        with self._lock:
            return self._state

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        """Get current metrics."""
        with self._lock:
            # Create a copy to avoid race conditions
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
        """Transition to a new state with logging."""
        if new_state == self._state:
            return

        old_state = self._state
        self._state = new_state
        self._metrics.state_transitions += 1

        # State-specific initialization
        if new_state == CircuitBreakerState.HALF_OPEN:
            self._half_open_calls = 0
            self._half_open_successes = 0
            self._metrics.half_open_state_count += 1
        elif new_state == CircuitBreakerState.OPEN:
            self._metrics.open_state_count += 1

        # Log state transition
        self._logger.info(
            f"Circuit breaker state transition: {old_state.value} -> {new_state.value}",
            extra={
                "circuit_name": self.name,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "failure_threshold": self.failure_threshold,
                "success_rate": self._metrics.success_rate,
                "failure_rate": self._metrics.failure_rate,
            },
        )

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

                if recent_failures >= self.failure_threshold:
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
        """
        Execute a function through the circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result from function execution

        Raises:
            CircuitBreakerError: If circuit is open
            Any exception: Raised by the wrapped function
        """
        # Check if we can execute
        if not self._can_execute():
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is open. "
                f"Last failure: {self._last_failure_time}, "
                f"Failure rate: {self._metrics.failure_rate:.1f}%",
                circuit_name=self.name,
            )

        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise

    async def call_async(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute an async function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result from function execution

        Raises:
            CircuitBreakerError: If circuit is open
            Any exception: Raised by the wrapped function
        """
        # Check if we can execute
        if not self._can_execute():
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is open. "
                f"Last failure: {self._last_failure_time}, "
                f"Failure rate: {self._metrics.failure_rate:.1f}%",
                circuit_name=self.name,
            )

        # Execute the async function
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise

    def decorator(self, func: F) -> F:
        """
        Decorator for wrapping functions with circuit breaker.

        Args:
            func: Function to wrap

        Returns:
            Wrapped function

        Example:
            cb = CircuitBreaker(failure_threshold=3)

            @cb.decorator
            def external_service():
                # Your code here
                pass
        """
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
        """
        Manually reset the circuit breaker to CLOSED state.

        This can be useful for testing or manual recovery.
        """
        with self._lock:
            self._transition_to_state(CircuitBreakerState.CLOSED)
            self._call_results.clear()
            self._half_open_calls = 0
            self._half_open_successes = 0

            self._logger.info(
                f"Circuit breaker '{self.name}' manually reset",
                extra={"circuit_name": self.name},
            )

    def get_status(self) -> dict:
        """
        Get detailed status information.

        Returns:
            Dictionary with current status and metrics
        """
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


# Import asyncio for async/await detection
import inspect
