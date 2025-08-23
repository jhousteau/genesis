"""
Genesis Retry Logic Implementation

Provides production-ready retry mechanisms with exponential backoff, jitter,
and configurable policies. Supports both synchronous and asynchronous operations
with comprehensive logging and error handling.

Classes:
    RetryPolicy: Configuration for retry behavior
    BackoffStrategy: Different backoff algorithms
    RetryExecutor: Core retry execution engine

Decorators:
    @retry: Synchronous retry decorator
    @retry_async: Asynchronous retry decorator
"""

import asyncio
import functools
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import (Any, Awaitable, Callable, Optional, Set, Type, TypeVar,
                    Union)

from ..errors.handler import ErrorCategory, GenesisError
# Import Genesis core components
from ..logging.logger import GenesisLogger

# Type variables for generic functions
F = TypeVar("F", bound=Callable[..., Any])
AF = TypeVar("AF", bound=Callable[..., Awaitable[Any]])

# Module logger
logger = GenesisLogger(__name__)


class BackoffStrategy(Enum):
    """Available backoff strategies for retry operations."""

    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"


@dataclass
class RetryPolicy:
    """
    Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of retry attempts (including initial)
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_strategy: Algorithm for calculating delays
        jitter: Whether to add randomization to delays
        exceptions: Exception types that should trigger retries
        retry_on_result: Function to check if result should trigger retry
        context_preserve: Whether to preserve context across retries
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER
    jitter: bool = True
    exceptions: Set[Type[Exception]] = field(
        default_factory=lambda: {
            ConnectionError,
            TimeoutError,
            OSError,
        }
    )
    retry_on_result: Optional[Callable[[Any], bool]] = None
    context_preserve: bool = True

    def __post_init__(self):
        """Validate policy configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")


class RetryExecutor:
    """
    Core retry execution engine.

    Handles the actual retry logic with comprehensive logging,
    error handling, and context preservation.
    """

    def __init__(self, policy: RetryPolicy):
        """Initialize with a retry policy."""
        self.policy = policy
        self._logger = GenesisLogger(f"{__name__}.RetryExecutor")

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt number.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        if attempt == 0:
            return 0.0

        base = self.policy.base_delay

        if self.policy.backoff_strategy == BackoffStrategy.FIXED:
            delay = base
        elif self.policy.backoff_strategy == BackoffStrategy.LINEAR:
            delay = base * attempt
        elif self.policy.backoff_strategy in (
            BackoffStrategy.EXPONENTIAL,
            BackoffStrategy.EXPONENTIAL_JITTER,
        ):
            delay = base * (2 ** (attempt - 1))
        else:
            delay = base

        # Apply maximum delay limit
        delay = min(delay, self.policy.max_delay)

        # Add jitter if enabled
        if (
            self.policy.jitter
            or self.policy.backoff_strategy == BackoffStrategy.EXPONENTIAL_JITTER
        ):
            # Add up to 100% jitter
            jitter_amount = random.uniform(0, min(delay, base))
            delay += jitter_amount

        return delay

    def should_retry(self, exception: Exception, result: Any, attempt: int) -> bool:
        """
        Determine if operation should be retried.

        Args:
            exception: Exception that occurred (None if no exception)
            result: Result from operation (None if exception occurred)
            attempt: Current attempt number (0-based)

        Returns:
            True if should retry, False otherwise
        """
        # Check attempt limit
        if attempt >= self.policy.max_attempts - 1:
            return False

        # Check exception-based retry
        if exception is not None:
            # Check if exception type is retryable
            for exc_type in self.policy.exceptions:
                if isinstance(exception, exc_type):
                    return True

            # Check Genesis error categories for intelligent retry
            if isinstance(exception, GenesisError):
                retryable_categories = {
                    ErrorCategory.NETWORK,
                    ErrorCategory.TIMEOUT,
                    ErrorCategory.RATE_LIMIT,
                    ErrorCategory.RESOURCE_EXHAUSTED,
                    ErrorCategory.UNAVAILABLE,
                    ErrorCategory.EXTERNAL_SERVICE,
                }
                if exception.category in retryable_categories:
                    return True

            return False

        # Check result-based retry
        if self.policy.retry_on_result is not None:
            return self.policy.retry_on_result(result)

        return False

    def execute(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result from successful function execution

        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None

        for attempt in range(self.policy.max_attempts):
            try:
                # Log retry attempt
                if attempt > 0:
                    func_name = getattr(func, "__name__", "unknown_function")
                    self._logger.info(
                        f"Retry attempt {attempt + 1}/{self.policy.max_attempts}",
                        extra={
                            "function": func_name,
                            "attempt": attempt + 1,
                            "max_attempts": self.policy.max_attempts,
                        },
                    )

                # Execute function
                result = func(*args, **kwargs)

                # Check if result indicates retry needed
                if self.should_retry(None, result, attempt):
                    delay = self.calculate_delay(attempt)
                    func_name = getattr(func, "__name__", "unknown_function")
                    self._logger.warning(
                        f"Result-based retry needed, waiting {delay:.2f}s",
                        extra={
                            "function": func_name,
                            "attempt": attempt + 1,
                            "delay": delay,
                            "result": str(result)[:100],  # Truncate for logging
                        },
                    )
                    if delay > 0:
                        time.sleep(delay)
                    continue

                # Success!
                if attempt > 0:
                    func_name = getattr(func, "__name__", "unknown_function")
                    self._logger.info(
                        f"Retry succeeded on attempt {attempt + 1}",
                        extra={
                            "function": func_name,
                            "attempt": attempt + 1,
                            "total_attempts": attempt + 1,
                        },
                    )

                return result

            except Exception as e:
                last_exception = e

                # Check if should retry
                if not self.should_retry(e, None, attempt):
                    func_name = getattr(func, "__name__", "unknown_function")
                    self._logger.error(
                        f"Non-retryable exception in {func_name}",
                        extra={
                            "function": func_name,
                            "attempt": attempt + 1,
                            "exception_type": type(e).__name__,
                            "exception_message": str(e),
                        },
                    )
                    raise

                # Calculate delay for next attempt
                delay = self.calculate_delay(attempt + 1)

                # Log retry
                func_name = getattr(func, "__name__", "unknown_function")
                self._logger.warning(
                    f"Exception in {func_name}, retrying in {delay:.2f}s",
                    extra={
                        "function": func_name,
                        "attempt": attempt + 1,
                        "max_attempts": self.policy.max_attempts,
                        "delay": delay,
                        "exception_type": type(e).__name__,
                        "exception_message": str(e),
                    },
                )

                # Wait before retry
                if delay > 0:
                    time.sleep(delay)

        # All retries exhausted
        self._logger.error(
            f"All retries exhausted for {func.__name__}",
            extra={
                "function": func.__name__,
                "total_attempts": self.policy.max_attempts,
                "final_exception": str(last_exception),
            },
        )

        # Re-raise the last exception
        if last_exception:
            raise last_exception

    async def execute_async(
        self, func: Callable[..., Awaitable[Any]], *args, **kwargs
    ) -> Any:
        """
        Execute async function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result from successful function execution

        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None

        for attempt in range(self.policy.max_attempts):
            try:
                # Log retry attempt
                if attempt > 0:
                    self._logger.info(
                        f"Async retry attempt {attempt + 1}/{self.policy.max_attempts}",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_attempts": self.policy.max_attempts,
                        },
                    )

                # Execute async function
                result = await func(*args, **kwargs)

                # Check if result indicates retry needed
                if self.should_retry(None, result, attempt):
                    delay = self.calculate_delay(attempt)
                    self._logger.warning(
                        f"Async result-based retry needed, waiting {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "delay": delay,
                        },
                    )
                    if delay > 0:
                        await asyncio.sleep(delay)
                    continue

                # Success!
                if attempt > 0:
                    self._logger.info(
                        f"Async retry succeeded on attempt {attempt + 1}",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "total_attempts": attempt + 1,
                        },
                    )

                return result

            except Exception as e:
                last_exception = e

                # Check if should retry
                if not self.should_retry(e, None, attempt):
                    self._logger.error(
                        f"Non-retryable exception in async {func.__name__}",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "exception_type": type(e).__name__,
                            "exception_message": str(e),
                        },
                    )
                    raise

                # Calculate delay for next attempt
                delay = self.calculate_delay(attempt + 1)

                # Log retry
                self._logger.warning(
                    f"Exception in async {func.__name__}, retrying in {delay:.2f}s",
                    extra={
                        "function": func.__name__,
                        "attempt": attempt + 1,
                        "max_attempts": self.policy.max_attempts,
                        "delay": delay,
                        "exception_type": type(e).__name__,
                        "exception_message": str(e),
                    },
                )

                # Wait before retry
                if delay > 0:
                    await asyncio.sleep(delay)

        # All retries exhausted
        self._logger.error(
            f"All async retries exhausted for {func.__name__}",
            extra={
                "function": func.__name__,
                "total_attempts": self.policy.max_attempts,
                "final_exception": str(last_exception),
            },
        )

        # Re-raise the last exception
        if last_exception:
            raise last_exception


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff: Union[str, BackoffStrategy] = BackoffStrategy.EXPONENTIAL_JITTER,
    exceptions: Optional[Set[Type[Exception]]] = None,
    retry_on_result: Optional[Callable[[Any], bool]] = None,
    policy: Optional[RetryPolicy] = None,
) -> Callable[[F], F]:
    """
    Decorator for adding retry logic to synchronous functions.

    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries
        backoff: Backoff strategy ('fixed', 'linear', 'exponential', or BackoffStrategy enum)
        exceptions: Exception types to retry on
        retry_on_result: Function to check if result should trigger retry
        policy: Pre-configured RetryPolicy (overrides other args)

    Returns:
        Decorated function with retry logic

    Example:
        @retry(max_attempts=5, base_delay=2.0)
        def unreliable_operation():
            # Your code here
            pass
    """

    def decorator(func: F) -> F:
        # Create policy from arguments or use provided policy
        if policy is not None:
            retry_policy = policy
        else:
            # Convert string backoff to enum
            if isinstance(backoff, str):
                backoff_strategy = BackoffStrategy(backoff.lower())
            else:
                backoff_strategy = backoff

            retry_policy = RetryPolicy(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                backoff_strategy=backoff_strategy,
                exceptions=exceptions or {ConnectionError, TimeoutError, OSError},
                retry_on_result=retry_on_result,
            )

        # Create executor
        executor = RetryExecutor(retry_policy)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return executor.execute(func, *args, **kwargs)

        return wrapper

    return decorator


def retry_async(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff: Union[str, BackoffStrategy] = BackoffStrategy.EXPONENTIAL_JITTER,
    exceptions: Optional[Set[Type[Exception]]] = None,
    retry_on_result: Optional[Callable[[Any], bool]] = None,
    policy: Optional[RetryPolicy] = None,
) -> Callable[[AF], AF]:
    """
    Decorator for adding retry logic to asynchronous functions.

    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries
        backoff: Backoff strategy ('fixed', 'linear', 'exponential', or BackoffStrategy enum)
        exceptions: Exception types to retry on
        retry_on_result: Function to check if result should trigger retry
        policy: Pre-configured RetryPolicy (overrides other args)

    Returns:
        Decorated async function with retry logic

    Example:
        @retry_async(max_attempts=5, base_delay=2.0)
        async def unreliable_async_operation():
            # Your async code here
            pass
    """

    def decorator(func: AF) -> AF:
        # Create policy from arguments or use provided policy
        if policy is not None:
            retry_policy = policy
        else:
            # Convert string backoff to enum
            if isinstance(backoff, str):
                backoff_strategy = BackoffStrategy(backoff.lower())
            else:
                backoff_strategy = backoff

            retry_policy = RetryPolicy(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                backoff_strategy=backoff_strategy,
                exceptions=exceptions or {ConnectionError, TimeoutError, OSError},
                retry_on_result=retry_on_result,
            )

        # Create executor
        executor = RetryExecutor(retry_policy)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await executor.execute_async(func, *args, **kwargs)

        return wrapper

    return decorator
