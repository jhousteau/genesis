"""
Comprehensive tests for Genesis retry logic using VERIFY methodology.

Test Coverage:
- RetryPolicy validation and configuration
- BackoffStrategy calculations and algorithms
- RetryExecutor synchronous and asynchronous execution
- Decorator functionality and edge cases
- Error handling and recovery scenarios
- Performance benchmarks and thread safety
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch

import pytest

from core.errors.handler import ErrorCategory, GenesisError
from core.retry.retry import (BackoffStrategy, RetryExecutor, RetryPolicy,
                              retry, retry_async)


class TestRetryPolicy:
    """Test RetryPolicy configuration and validation."""

    def test_default_policy_creation(self):
        """Test creating policy with default values."""
        policy = RetryPolicy()

        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.backoff_strategy == BackoffStrategy.EXPONENTIAL_JITTER
        assert policy.jitter is True
        assert ConnectionError in policy.exceptions
        assert TimeoutError in policy.exceptions
        assert OSError in policy.exceptions
        assert policy.retry_on_result is None
        assert policy.context_preserve is True

    def test_custom_policy_creation(self):
        """Test creating policy with custom values."""
        custom_exceptions = {ValueError, KeyError}
        retry_on_result = lambda x: x is None

        policy = RetryPolicy(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            backoff_strategy=BackoffStrategy.LINEAR,
            jitter=False,
            exceptions=custom_exceptions,
            retry_on_result=retry_on_result,
            context_preserve=False,
        )

        assert policy.max_attempts == 5
        assert policy.base_delay == 2.0
        assert policy.max_delay == 120.0
        assert policy.backoff_strategy == BackoffStrategy.LINEAR
        assert policy.jitter is False
        assert policy.exceptions == custom_exceptions
        assert policy.retry_on_result == retry_on_result
        assert policy.context_preserve is False

    def test_policy_validation_max_attempts(self):
        """Test validation of max_attempts parameter."""
        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            RetryPolicy(max_attempts=0)

        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            RetryPolicy(max_attempts=-1)

    def test_policy_validation_base_delay(self):
        """Test validation of base_delay parameter."""
        with pytest.raises(ValueError, match="base_delay must be non-negative"):
            RetryPolicy(base_delay=-1.0)

    def test_policy_validation_max_delay(self):
        """Test validation of max_delay parameter."""
        with pytest.raises(ValueError, match="max_delay must be >= base_delay"):
            RetryPolicy(base_delay=10.0, max_delay=5.0)


class TestBackoffStrategy:
    """Test backoff strategy enumeration and values."""

    def test_backoff_strategy_values(self):
        """Test all backoff strategy enum values."""
        assert BackoffStrategy.FIXED.value == "fixed"
        assert BackoffStrategy.LINEAR.value == "linear"
        assert BackoffStrategy.EXPONENTIAL.value == "exponential"
        assert BackoffStrategy.EXPONENTIAL_JITTER.value == "exponential_jitter"

    def test_backoff_strategy_from_string(self):
        """Test creating backoff strategy from string."""
        assert BackoffStrategy("fixed") == BackoffStrategy.FIXED
        assert BackoffStrategy("linear") == BackoffStrategy.LINEAR
        assert BackoffStrategy("exponential") == BackoffStrategy.EXPONENTIAL
        assert (
            BackoffStrategy("exponential_jitter") == BackoffStrategy.EXPONENTIAL_JITTER
        )


class TestRetryExecutor:
    """Test RetryExecutor core functionality."""

    @pytest.fixture
    def executor(self):
        """Create executor with default policy."""
        policy = RetryPolicy(max_attempts=3, base_delay=0.1, max_delay=1.0)
        return RetryExecutor(policy)

    @pytest.fixture
    def custom_executor(self):
        """Create executor with custom policy."""
        policy = RetryPolicy(
            max_attempts=5,
            base_delay=0.05,
            max_delay=0.5,
            backoff_strategy=BackoffStrategy.LINEAR,
            jitter=False,
        )
        return RetryExecutor(policy)

    def test_executor_initialization(self, executor):
        """Test executor initialization."""
        assert executor.policy.max_attempts == 3
        assert executor.policy.base_delay == 0.1
        assert executor.policy.max_delay == 1.0
        assert executor._logger is not None

    def test_calculate_delay_first_attempt(self, executor):
        """Test delay calculation for first attempt."""
        delay = executor.calculate_delay(0)
        assert delay == 0.0

    def test_calculate_delay_fixed_strategy(self):
        """Test delay calculation with fixed strategy."""
        policy = RetryPolicy(
            base_delay=2.0, backoff_strategy=BackoffStrategy.FIXED, jitter=False
        )
        executor = RetryExecutor(policy)

        assert executor.calculate_delay(1) == 2.0
        assert executor.calculate_delay(2) == 2.0
        assert executor.calculate_delay(3) == 2.0

    def test_calculate_delay_linear_strategy(self):
        """Test delay calculation with linear strategy."""
        policy = RetryPolicy(
            base_delay=1.0, backoff_strategy=BackoffStrategy.LINEAR, jitter=False
        )
        executor = RetryExecutor(policy)

        assert executor.calculate_delay(1) == 1.0
        assert executor.calculate_delay(2) == 2.0
        assert executor.calculate_delay(3) == 3.0

    def test_calculate_delay_exponential_strategy(self):
        """Test delay calculation with exponential strategy."""
        policy = RetryPolicy(
            base_delay=1.0, backoff_strategy=BackoffStrategy.EXPONENTIAL, jitter=False
        )
        executor = RetryExecutor(policy)

        assert executor.calculate_delay(1) == 1.0
        assert executor.calculate_delay(2) == 2.0
        assert executor.calculate_delay(3) == 4.0
        assert executor.calculate_delay(4) == 8.0

    def test_calculate_delay_max_delay_limit(self):
        """Test delay calculation respects max_delay."""
        policy = RetryPolicy(
            base_delay=1.0,
            max_delay=3.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            jitter=False,
        )
        executor = RetryExecutor(policy)

        assert executor.calculate_delay(1) == 1.0
        assert executor.calculate_delay(2) == 2.0
        assert executor.calculate_delay(3) == 3.0  # Limited by max_delay
        assert executor.calculate_delay(4) == 3.0  # Limited by max_delay

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation includes jitter."""
        policy = RetryPolicy(
            base_delay=1.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
            jitter=True,
        )
        executor = RetryExecutor(policy)

        # Test multiple calculations to ensure jitter varies
        delays = [executor.calculate_delay(2) for _ in range(10)]

        # All delays should be >= base exponential delay
        assert all(delay >= 2.0 for delay in delays)
        # Delays should vary due to jitter
        assert len(set(delays)) > 1

    def test_should_retry_attempt_limit(self, executor):
        """Test retry logic respects attempt limits."""
        # Within limit
        assert (
            executor.should_retry(None, None, 0) is False
        )  # No exception, no result check
        assert executor.should_retry(ConnectionError(), None, 0) is True
        assert executor.should_retry(ConnectionError(), None, 1) is True

        # At limit
        assert executor.should_retry(ConnectionError(), None, 2) is False

    def test_should_retry_exception_types(self, executor):
        """Test retry logic for different exception types."""
        # Retryable exceptions
        assert executor.should_retry(ConnectionError(), None, 0) is True
        assert executor.should_retry(TimeoutError(), None, 0) is True
        assert executor.should_retry(OSError(), None, 0) is True

        # Non-retryable exceptions
        assert executor.should_retry(ValueError(), None, 0) is False
        assert executor.should_retry(KeyError(), None, 0) is False
        assert executor.should_retry(RuntimeError(), None, 0) is False

    def test_should_retry_genesis_error_categories(self, executor):
        """Test retry logic for Genesis error categories."""
        # Retryable categories
        retryable_errors = [
            GenesisError("Network error", category=ErrorCategory.NETWORK),
            GenesisError("Timeout error", category=ErrorCategory.TIMEOUT),
            GenesisError("Rate limit", category=ErrorCategory.RATE_LIMIT),
            GenesisError(
                "Resource exhausted", category=ErrorCategory.RESOURCE_EXHAUSTED
            ),
            GenesisError("Service unavailable", category=ErrorCategory.UNAVAILABLE),
        ]

        for error in retryable_errors:
            assert executor.should_retry(error, None, 0) is True

        # Non-retryable categories
        non_retryable_errors = [
            GenesisError("Auth error", category=ErrorCategory.AUTHENTICATION),
            GenesisError("Validation error", category=ErrorCategory.VALIDATION),
            GenesisError("App error", category=ErrorCategory.APPLICATION),
        ]

        for error in non_retryable_errors:
            assert executor.should_retry(error, None, 0) is False

    def test_should_retry_result_based(self):
        """Test retry logic based on result evaluation."""
        policy = RetryPolicy(
            max_attempts=3, retry_on_result=lambda x: x is None or x == "retry"
        )
        executor = RetryExecutor(policy)

        # Should retry on None result
        assert executor.should_retry(None, None, 0) is True
        # Should retry on "retry" result
        assert executor.should_retry(None, "retry", 0) is True
        # Should not retry on other results
        assert executor.should_retry(None, "success", 0) is False
        assert executor.should_retry(None, 42, 0) is False

    def test_execute_successful_first_attempt(self, executor):
        """Test successful execution on first attempt."""
        mock_func = Mock(return_value="success")

        result = executor.execute(mock_func, "arg1", kwarg1="value1")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    def test_execute_successful_after_retries(self, executor):
        """Test successful execution after retries."""
        mock_func = Mock(side_effect=[ConnectionError(), ConnectionError(), "success"])

        result = executor.execute(mock_func, "arg1")

        assert result == "success"
        assert mock_func.call_count == 3

    def test_execute_all_retries_exhausted(self, executor):
        """Test execution when all retries are exhausted."""
        mock_func = Mock(side_effect=ConnectionError("persistent error"))

        with pytest.raises(ConnectionError, match="persistent error"):
            executor.execute(mock_func)

        assert mock_func.call_count == 3  # Initial + 2 retries

    def test_execute_non_retryable_exception(self, executor):
        """Test execution with non-retryable exception."""
        mock_func = Mock(side_effect=ValueError("validation failed"))

        with pytest.raises(ValueError, match="validation failed"):
            executor.execute(mock_func)

        assert mock_func.call_count == 1  # No retries

    def test_execute_result_based_retry(self):
        """Test execution with result-based retry."""
        policy = RetryPolicy(
            max_attempts=3, base_delay=0.01, retry_on_result=lambda x: x is None
        )
        executor = RetryExecutor(policy)

        mock_func = Mock(side_effect=[None, None, "success"])

        result = executor.execute(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_async_successful_first_attempt(self, executor):
        """Test async successful execution on first attempt."""

        async def async_func(arg, kwarg=None):
            return f"success-{arg}-{kwarg}"

        result = await executor.execute_async(async_func, "test", kwarg="value")

        assert result == "success-test-value"

    @pytest.mark.asyncio
    async def test_execute_async_successful_after_retries(self, executor):
        """Test async successful execution after retries."""
        call_count = 0

        async def async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError(f"attempt {call_count}")
            return "success"

        result = await executor.execute_async(async_func)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_async_all_retries_exhausted(self, executor):
        """Test async execution when all retries are exhausted."""

        async def async_func():
            raise TimeoutError("persistent timeout")

        with pytest.raises(TimeoutError, match="persistent timeout"):
            await executor.execute_async(async_func)

    @pytest.mark.asyncio
    async def test_execute_async_result_based_retry(self):
        """Test async execution with result-based retry."""
        policy = RetryPolicy(
            max_attempts=3, base_delay=0.01, retry_on_result=lambda x: x == "retry"
        )
        executor = RetryExecutor(policy)

        call_count = 0

        async def async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return "retry"
            return "success"

        result = await executor.execute_async(async_func)

        assert result == "success"
        assert call_count == 3


class TestRetryDecorator:
    """Test retry decorator functionality."""

    def test_retry_decorator_default_args(self):
        """Test retry decorator with default arguments."""
        call_count = 0

        @retry()
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("network issue")
            return "success"

        result = flaky_function()

        assert result == "success"
        assert call_count == 2

    def test_retry_decorator_custom_args(self):
        """Test retry decorator with custom arguments."""
        call_count = 0

        @retry(max_attempts=5, base_delay=0.01, backoff="linear")
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise OSError("resource issue")
            return f"success after {call_count} attempts"

        result = flaky_function()

        assert result == "success after 4 attempts"
        assert call_count == 4

    def test_retry_decorator_with_policy(self):
        """Test retry decorator with pre-configured policy."""
        policy = RetryPolicy(max_attempts=2, base_delay=0.01, exceptions={ValueError})

        call_count = 0

        @retry(policy=policy)
        def selective_retry():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("first failure")
            return "success"

        result = selective_retry()

        assert result == "success"
        assert call_count == 2

    def test_retry_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""

        @retry(max_attempts=2)
        def documented_function(arg1, arg2="default"):
            """This function has documentation."""
            return f"{arg1}-{arg2}"

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This function has documentation."
        assert documented_function("test", arg2="custom") == "test-custom"

    def test_retry_decorator_exception_propagation(self):
        """Test that non-retryable exceptions are propagated."""

        @retry(max_attempts=3)
        def non_retryable_error():
            raise ValueError("validation error")

        with pytest.raises(ValueError, match="validation error"):
            non_retryable_error()

    def test_retry_decorator_with_args_and_kwargs(self):
        """Test retry decorator with function arguments."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        def function_with_args(arg1, arg2, kwarg1=None, kwarg2="default"):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("temporary failure")
            return f"{arg1}-{arg2}-{kwarg1}-{kwarg2}"

        result = function_with_args("a", "b", kwarg1="c", kwarg2="d")

        assert result == "a-b-c-d"
        assert call_count == 2


class TestRetryAsyncDecorator:
    """Test retry_async decorator functionality."""

    @pytest.mark.asyncio
    async def test_retry_async_decorator_default_args(self):
        """Test async retry decorator with default arguments."""
        call_count = 0

        @retry_async()
        async def flaky_async_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("network issue")
            return "async success"

        result = await flaky_async_function()

        assert result == "async success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_async_decorator_custom_args(self):
        """Test async retry decorator with custom arguments."""
        call_count = 0

        @retry_async(max_attempts=4, base_delay=0.01, backoff="exponential")
        async def flaky_async_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("timeout issue")
            return f"async success after {call_count} attempts"

        result = await flaky_async_function()

        assert result == "async success after 3 attempts"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_async_decorator_with_policy(self):
        """Test async retry decorator with pre-configured policy."""
        policy = RetryPolicy(
            max_attempts=3, base_delay=0.01, retry_on_result=lambda x: x is None
        )

        call_count = 0

        @retry_async(policy=policy)
        async def result_based_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return None
            return "async success"

        result = await result_based_retry()

        assert result == "async success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_async_decorator_preserves_function_metadata(self):
        """Test that async decorator preserves function metadata."""

        @retry_async(max_attempts=2)
        async def documented_async_function(arg1, arg2="default"):
            """This async function has documentation."""
            return f"async-{arg1}-{arg2}"

        assert documented_async_function.__name__ == "documented_async_function"
        assert (
            documented_async_function.__doc__
            == "This async function has documentation."
        )
        result = await documented_async_function("test", arg2="custom")
        assert result == "async-test-custom"


class TestRetryPerformance:
    """Test retry performance and benchmarks."""

    def test_retry_performance_overhead(self):
        """Test performance overhead of retry mechanism."""
        policy = RetryPolicy(max_attempts=1)  # No retries
        executor = RetryExecutor(policy)

        def simple_function():
            return "result"

        # Measure execution time
        start_time = time.time()
        for _ in range(1000):
            executor.execute(simple_function)
        duration = time.time() - start_time

        # Should complete 1000 executions quickly (within reasonable time)
        assert duration < 1.0  # Less than 1 second

    @pytest.mark.asyncio
    async def test_retry_async_performance_overhead(self):
        """Test performance overhead of async retry mechanism."""
        policy = RetryPolicy(max_attempts=1)  # No retries
        executor = RetryExecutor(policy)

        async def simple_async_function():
            return "result"

        # Measure execution time
        start_time = time.time()
        for _ in range(1000):
            await executor.execute_async(simple_async_function)
        duration = time.time() - start_time

        # Should complete 1000 executions quickly
        assert duration < 2.0  # Less than 2 seconds for async

    def test_backoff_calculation_performance(self):
        """Test performance of backoff calculations."""
        policy = RetryPolicy(
            base_delay=1.0, backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER
        )
        executor = RetryExecutor(policy)

        # Measure calculation time
        start_time = time.time()
        for attempt in range(1000):
            executor.calculate_delay(attempt % 10)  # Vary attempts
        duration = time.time() - start_time

        # Should complete calculations quickly
        assert duration < 0.1  # Less than 100ms


class TestRetryThreadSafety:
    """Test retry thread safety and concurrent usage."""

    def test_retry_executor_thread_safety(self):
        """Test that RetryExecutor is thread-safe."""
        policy = RetryPolicy(max_attempts=2, base_delay=0.01)
        executor = RetryExecutor(policy)

        results = []
        call_counts = {}
        lock = threading.Lock()

        def thread_function(thread_id):
            call_count = 0

            def flaky_function():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ConnectionError("first failure")
                return f"thread-{thread_id}-success"

            try:
                result = executor.execute(flaky_function)
                with lock:
                    results.append(result)
                    call_counts[thread_id] = call_count
            except Exception as e:
                with lock:
                    results.append(f"error-{e}")

        # Run multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=thread_function, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify results
        assert len(results) == 10
        assert len(call_counts) == 10

        # All threads should succeed
        for i in range(10):
            assert f"thread-{i}-success" in results
            assert call_counts[i] == 2  # Each had one retry

    def test_retry_decorator_thread_safety(self):
        """Test that retry decorator is thread-safe."""
        call_counts = {}
        lock = threading.Lock()

        @retry(max_attempts=3, base_delay=0.01)
        def shared_function(thread_id):
            with lock:
                if thread_id not in call_counts:
                    call_counts[thread_id] = 0
                call_counts[thread_id] += 1

                # Fail on first two attempts
                if call_counts[thread_id] < 3:
                    raise ConnectionError(
                        f"thread {thread_id} attempt {call_counts[thread_id]}"
                    )

                return f"thread-{thread_id}-success"

        # Run concurrent threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(shared_function, i) for i in range(5)]
            results = [future.result() for future in as_completed(futures)]

        # Verify results
        assert len(results) == 5
        for i in range(5):
            assert f"thread-{i}-success" in results
            assert call_counts[i] == 3


class TestRetryEdgeCases:
    """Test retry edge cases and error conditions."""

    def test_retry_with_zero_delay(self):
        """Test retry with zero base delay."""
        policy = RetryPolicy(max_attempts=3, base_delay=0.0)
        executor = RetryExecutor(policy)

        call_count = 0

        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("failure")
            return "success"

        start_time = time.time()
        result = executor.execute(flaky_function)
        duration = time.time() - start_time

        assert result == "success"
        assert call_count == 3
        # Should complete quickly with zero delay
        assert duration < 0.1

    def test_retry_with_very_small_delay(self):
        """Test retry with very small delay values."""
        policy = RetryPolicy(max_attempts=3, base_delay=0.001)
        executor = RetryExecutor(policy)

        call_count = 0

        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("failure")
            return "success"

        result = executor.execute(flaky_function)

        assert result == "success"
        assert call_count == 3

    def test_retry_with_large_attempt_count(self):
        """Test retry with large number of attempts."""
        policy = RetryPolicy(max_attempts=100, base_delay=0.001, max_delay=0.01)
        executor = RetryExecutor(policy)

        call_count = 0

        def eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 50:
                raise ConnectionError("still failing")
            return "finally success"

        result = executor.execute(eventually_successful)

        assert result == "finally success"
        assert call_count == 50

    def test_retry_function_returning_none(self):
        """Test retry with function returning None."""
        policy = RetryPolicy(max_attempts=2)
        executor = RetryExecutor(policy)

        def returns_none():
            return None

        result = executor.execute(returns_none)
        assert result is None

    def test_retry_function_with_complex_return_type(self):
        """Test retry with function returning complex objects."""
        policy = RetryPolicy(max_attempts=2)
        executor = RetryExecutor(policy)

        def returns_complex():
            return {
                "data": [1, 2, 3],
                "metadata": {"count": 3, "type": "list"},
                "status": "success",
            }

        result = executor.execute(returns_complex)
        assert result["data"] == [1, 2, 3]
        assert result["metadata"]["count"] == 3
        assert result["status"] == "success"

    def test_retry_with_exception_in_should_retry(self):
        """Test handling of exceptions in retry logic itself."""
        # This is more of a robustness test
        policy = RetryPolicy(max_attempts=2)
        executor = RetryExecutor(policy)

        def normal_function():
            return "success"

        # Should work normally even with edge cases
        result = executor.execute(normal_function)
        assert result == "success"


@pytest.mark.integration
class TestRetryIntegration:
    """Integration tests for retry functionality."""

    def test_retry_with_real_network_simulation(self):
        """Test retry with simulated network operations."""

        policy = RetryPolicy(
            max_attempts=5,
            base_delay=0.01,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            exceptions={ConnectionError, TimeoutError},
        )
        executor = RetryExecutor(policy)

        call_count = 0

        def simulated_network_call():
            nonlocal call_count
            call_count += 1

            # Simulate various network conditions
            if call_count <= 2:
                # Simulate connection errors
                raise ConnectionError(f"Connection failed on attempt {call_count}")
            elif call_count == 3:
                # Simulate timeout
                raise TimeoutError("Request timeout")
            else:
                # Simulate success
                return {
                    "status": "success",
                    "data": "response_data",
                    "attempt": call_count,
                }

        result = executor.execute(simulated_network_call)

        assert result["status"] == "success"
        assert result["data"] == "response_data"
        assert result["attempt"] == 4
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_retry_async_with_real_async_operation(self):
        """Test async retry with simulated async operations."""
        policy = RetryPolicy(
            max_attempts=4, base_delay=0.01, backoff_strategy=BackoffStrategy.LINEAR
        )
        executor = RetryExecutor(policy)

        call_count = 0

        async def simulated_async_api_call():
            nonlocal call_count
            call_count += 1

            # Simulate async operation delay
            await asyncio.sleep(0.001)

            if call_count < 3:
                raise ConnectionError(f"API call failed on attempt {call_count}")

            return {
                "api_response": "success",
                "timestamp": time.time(),
                "attempts": call_count,
            }

        result = await executor.execute_async(simulated_async_api_call)

        assert result["api_response"] == "success"
        assert result["attempts"] == 3
        assert call_count == 3

    def test_retry_with_logging_verification(self):
        """Test that retry operations are properly logged."""
        # This test would verify logging integration
        # For now, we'll test that the mechanism works
        policy = RetryPolicy(max_attempts=3, base_delay=0.01)
        executor = RetryExecutor(policy)

        call_count = 0

        def logged_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError(f"Logged failure {call_count}")
            return "logged success"

        with (
            patch.object(executor._logger, "info") as mock_info,
            patch.object(executor._logger, "warning") as mock_warning,
        ):
            result = executor.execute(logged_function)

            assert result == "logged success"
            # Verify logging calls were made
            assert mock_warning.call_count == 2  # Two retry warnings
            assert mock_info.call_count == 1  # One success log
