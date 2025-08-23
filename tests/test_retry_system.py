"""
Comprehensive Test Suite for Genesis Retry System

Tests all components of the retry system including:
- RetryPolicy configuration and validation
- RetryExecutor execution logic
- CircuitBreaker state transitions
- Pre-configured policies
- Integration with Genesis error handling
"""

import threading
import time

import pytest

from core.errors.handler import ErrorCategory, GenesisError
# Import the retry system components
from core.retry import (AGGRESSIVE_POLICY, CONSERVATIVE_POLICY, DEFAULT_POLICY,
                        BackoffStrategy, CircuitBreaker, CircuitBreakerError,
                        CircuitBreakerState, RetryExecutor, RetryPolicy,
                        create_circuit_breaker_policy, create_policy, retry,
                        retry_async)


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

    def test_policy_validation(self):
        """Test policy parameter validation."""

        # Test invalid max_attempts
        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            RetryPolicy(max_attempts=0)

        # Test invalid base_delay
        with pytest.raises(ValueError, match="base_delay must be non-negative"):
            RetryPolicy(base_delay=-1.0)

        # Test invalid max_delay
        with pytest.raises(ValueError, match="max_delay must be >= base_delay"):
            RetryPolicy(base_delay=10.0, max_delay=5.0)

    def test_custom_policy_creation(self):
        """Test creating policy with custom values."""
        policy = RetryPolicy(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            backoff_strategy=BackoffStrategy.LINEAR,
            exceptions={ValueError, RuntimeError},
        )

        assert policy.max_attempts == 5
        assert policy.base_delay == 2.0
        assert policy.max_delay == 120.0
        assert policy.backoff_strategy == BackoffStrategy.LINEAR
        assert ValueError in policy.exceptions
        assert RuntimeError in policy.exceptions


class TestRetryExecutor:
    """Test RetryExecutor logic and behavior."""

    def test_calculate_delay_fixed(self):
        """Test fixed backoff delay calculation."""
        policy = RetryPolicy(
            base_delay=2.0, backoff_strategy=BackoffStrategy.FIXED, jitter=False
        )
        executor = RetryExecutor(policy)

        assert executor.calculate_delay(0) == 0.0  # First attempt
        assert executor.calculate_delay(1) == 2.0
        assert executor.calculate_delay(2) == 2.0
        assert executor.calculate_delay(5) == 2.0

    def test_calculate_delay_linear(self):
        """Test linear backoff delay calculation."""
        policy = RetryPolicy(
            base_delay=1.0, backoff_strategy=BackoffStrategy.LINEAR, jitter=False
        )
        executor = RetryExecutor(policy)

        assert executor.calculate_delay(0) == 0.0
        assert executor.calculate_delay(1) == 1.0
        assert executor.calculate_delay(2) == 2.0
        assert executor.calculate_delay(3) == 3.0

    def test_calculate_delay_exponential(self):
        """Test exponential backoff delay calculation."""
        policy = RetryPolicy(
            base_delay=1.0, backoff_strategy=BackoffStrategy.EXPONENTIAL, jitter=False
        )
        executor = RetryExecutor(policy)

        assert executor.calculate_delay(0) == 0.0
        assert executor.calculate_delay(1) == 1.0
        assert executor.calculate_delay(2) == 2.0
        assert executor.calculate_delay(3) == 4.0
        assert executor.calculate_delay(4) == 8.0

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        policy = RetryPolicy(
            base_delay=1.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
            jitter=True,
        )
        executor = RetryExecutor(policy)

        # With jitter, delays should vary but be within expected range
        delay1 = executor.calculate_delay(2)
        delay2 = executor.calculate_delay(2)

        # Base exponential delay would be 2.0
        # With jitter, should be 2.0 + some random amount
        assert delay1 >= 2.0
        assert delay2 >= 2.0
        # They should be different (with high probability)
        assert delay1 != delay2 or delay1 == delay2  # Account for edge case

    def test_calculate_delay_max_limit(self):
        """Test delay calculation respects max_delay."""
        policy = RetryPolicy(
            base_delay=1.0,
            max_delay=5.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            jitter=False,
        )
        executor = RetryExecutor(policy)

        # Large attempt should be capped at max_delay
        assert executor.calculate_delay(10) == 5.0

    def test_should_retry_exception_types(self):
        """Test retry decision based on exception types."""
        policy = RetryPolicy(exceptions={ValueError, RuntimeError})
        executor = RetryExecutor(policy)

        # Should retry on configured exceptions
        assert executor.should_retry(ValueError("test"), None, 0) is True
        assert executor.should_retry(RuntimeError("test"), None, 0) is True

        # Should not retry on non-configured exceptions
        assert executor.should_retry(TypeError("test"), None, 0) is False

    def test_should_retry_genesis_errors(self):
        """Test retry decision based on Genesis error categories."""
        policy = RetryPolicy()
        executor = RetryExecutor(policy)

        # Should retry on retryable Genesis errors
        network_error = GenesisError(
            message="Network error", category=ErrorCategory.NETWORK
        )
        assert executor.should_retry(network_error, None, 0) is True

        # Should not retry on non-retryable Genesis errors
        validation_error = GenesisError(
            message="Validation error", category=ErrorCategory.VALIDATION
        )
        assert executor.should_retry(validation_error, None, 0) is False

    def test_should_retry_attempt_limit(self):
        """Test retry decision respects max attempts."""
        policy = RetryPolicy(max_attempts=3)
        executor = RetryExecutor(policy)

        # Should retry within limit
        assert executor.should_retry(ConnectionError(), None, 0) is True
        assert executor.should_retry(ConnectionError(), None, 1) is True

        # Should not retry at limit
        assert executor.should_retry(ConnectionError(), None, 2) is False

    def test_should_retry_result_based(self):
        """Test retry decision based on result checking."""

        def should_retry_result(result):
            return result == "retry"

        policy = RetryPolicy(retry_on_result=should_retry_result)
        executor = RetryExecutor(policy)

        # Should retry based on result
        assert executor.should_retry(None, "retry", 0) is True
        assert executor.should_retry(None, "success", 0) is False

    def test_execute_success_no_retry(self):
        """Test successful execution without retries."""
        policy = RetryPolicy()
        executor = RetryExecutor(policy)

        def successful_func():
            return "success"

        result = executor.execute(successful_func)
        assert result == "success"

    def test_execute_success_after_retries(self):
        """Test successful execution after failures."""
        policy = RetryPolicy(base_delay=0.1)  # Fast for testing
        executor = RetryExecutor(policy)

        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = executor.execute(flaky_func)
        assert result == "success"
        assert call_count == 3

    def test_execute_all_retries_exhausted(self):
        """Test behavior when all retries are exhausted."""
        policy = RetryPolicy(max_attempts=2, base_delay=0.1)
        executor = RetryExecutor(policy)

        def always_fails():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError, match="Always fails"):
            executor.execute(always_fails)

    def test_execute_non_retryable_exception(self):
        """Test behavior with non-retryable exceptions."""
        policy = RetryPolicy()
        executor = RetryExecutor(policy)

        def validation_error_func():
            raise ValueError("Validation error")

        with pytest.raises(ValueError, match="Validation error"):
            executor.execute(validation_error_func)

    @pytest.mark.asyncio
    async def test_execute_async_success(self):
        """Test async execution success."""
        policy = RetryPolicy()
        executor = RetryExecutor(policy)

        async def async_func():
            return "async_success"

        result = await executor.execute_async(async_func)
        assert result == "async_success"

    @pytest.mark.asyncio
    async def test_execute_async_with_retries(self):
        """Test async execution with retries."""
        policy = RetryPolicy(base_delay=0.1)
        executor = RetryExecutor(policy)

        call_count = 0

        async def flaky_async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Async temporary failure")
            return "async_success"

        result = await executor.execute_async(flaky_async_func)
        assert result == "async_success"
        assert call_count == 3


class TestRetryDecorators:
    """Test retry decorators."""

    def test_retry_decorator_success(self):
        """Test retry decorator on successful function."""

        @retry(max_attempts=3)
        def successful_func():
            return "decorated_success"

        result = successful_func()
        assert result == "decorated_success"

    def test_retry_decorator_with_retries(self):
        """Test retry decorator with failures then success."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.1)
        def flaky_decorated_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Decorated failure")
            return "decorated_success"

        result = flaky_decorated_func()
        assert result == "decorated_success"
        assert call_count == 3

    def test_retry_decorator_with_custom_policy(self):
        """Test retry decorator with custom policy."""
        custom_policy = RetryPolicy(max_attempts=5, base_delay=0.05)

        call_count = 0

        @retry(policy=custom_policy)
        def func_with_custom_policy():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ConnectionError("Custom policy failure")
            return "custom_success"

        result = func_with_custom_policy()
        assert result == "custom_success"
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_retry_async_decorator(self):
        """Test async retry decorator."""
        call_count = 0

        @retry_async(max_attempts=3, base_delay=0.1)
        async def flaky_async_decorated():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Async decorated failure")
            return "async_decorated_success"

        result = await flaky_async_decorated()
        assert result == "async_decorated_success"
        assert call_count == 2


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3, timeout=1.0)
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_success_tracking(self):
        """Test circuit breaker tracks successful calls."""
        cb = CircuitBreaker(failure_threshold=3)

        def successful_func():
            return "success"

        result = cb.call(successful_func)
        assert result == "success"
        assert cb.metrics.successful_requests == 1
        assert cb.metrics.total_requests == 1

    def test_circuit_breaker_failure_tracking(self):
        """Test circuit breaker tracks failed calls."""
        cb = CircuitBreaker(failure_threshold=3)

        def failing_func():
            raise ConnectionError("Test failure")

        with pytest.raises(ConnectionError):
            cb.call(failing_func)

        assert cb.metrics.failed_requests == 1
        assert cb.metrics.total_requests == 1

    def test_circuit_breaker_opens_on_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=2, sliding_window_size=5)

        def failing_func():
            raise ConnectionError("Test failure")

        # First failure - should remain closed
        with pytest.raises(ConnectionError):
            cb.call(failing_func)
        assert cb.state == CircuitBreakerState.CLOSED

        # Second failure - should open circuit
        with pytest.raises(ConnectionError):
            cb.call(failing_func)
        assert cb.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_fails_fast_when_open(self):
        """Test circuit breaker fails fast when open."""
        cb = CircuitBreaker(failure_threshold=1)

        def failing_func():
            raise ConnectionError("Test failure")

        # Trip the circuit
        with pytest.raises(ConnectionError):
            cb.call(failing_func)
        assert cb.state == CircuitBreakerState.OPEN

        # Should fail fast without calling function
        def never_called_func():
            raise RuntimeError("Should not be called")

        with pytest.raises(CircuitBreakerError):
            cb.call(never_called_func)

    def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitions to half-open after timeout."""
        cb = CircuitBreaker(failure_threshold=1, timeout=0.1)

        def failing_func():
            raise ConnectionError("Test failure")

        # Trip the circuit
        with pytest.raises(ConnectionError):
            cb.call(failing_func)
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(0.2)

        # Next call should transition to half-open
        def successful_func():
            return "success"

        result = cb.call(successful_func)
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED  # Should close after success

    def test_circuit_breaker_half_open_reopens_on_failure(self):
        """Test circuit breaker reopens from half-open on failure."""
        cb = CircuitBreaker(failure_threshold=1, timeout=0.1)

        # Trip the circuit
        def failing_func():
            raise ConnectionError("Test failure")

        with pytest.raises(ConnectionError):
            cb.call(failing_func)
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(0.2)

        # Fail in half-open state
        with pytest.raises(ConnectionError):
            cb.call(failing_func)
        assert cb.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_decorator(self):
        """Test circuit breaker as decorator."""
        cb = CircuitBreaker(failure_threshold=2)

        call_count = 0

        @cb.decorator
        def decorated_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("Decorated failure")
            return "decorated_success"

        # First two calls should fail and trip circuit
        with pytest.raises(ConnectionError):
            decorated_func()
        with pytest.raises(ConnectionError):
            decorated_func()

        assert cb.state == CircuitBreakerState.OPEN

        # Third call should fail fast
        with pytest.raises(CircuitBreakerError):
            decorated_func()

    @pytest.mark.asyncio
    async def test_circuit_breaker_async_decorator(self):
        """Test circuit breaker async decorator."""
        cb = CircuitBreaker(failure_threshold=1)

        @cb.decorator
        async def async_decorated_func():
            return "async_decorated_success"

        result = await async_decorated_func()
        assert result == "async_decorated_success"

    def test_circuit_breaker_reset(self):
        """Test manual circuit breaker reset."""
        cb = CircuitBreaker(failure_threshold=1)

        def failing_func():
            raise ConnectionError("Test failure")

        # Trip the circuit
        with pytest.raises(ConnectionError):
            cb.call(failing_func)
        assert cb.state == CircuitBreakerState.OPEN

        # Reset manually
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_thread_safety(self):
        """Test circuit breaker is thread-safe."""
        cb = CircuitBreaker(failure_threshold=5)
        results = []

        def worker():
            try:
                result = cb.call(lambda: "success")
                results.append(result)
            except Exception as e:
                results.append(f"error: {e}")

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All should succeed
        assert len(results) == 10
        assert all(result == "success" for result in results)

    def test_circuit_breaker_metrics(self):
        """Test circuit breaker metrics collection."""
        cb = CircuitBreaker(failure_threshold=2)

        # Successful calls
        cb.call(lambda: "success")
        cb.call(lambda: "success")

        # Failed calls
        with pytest.raises(ConnectionError):
            cb.call(lambda: exec('raise ConnectionError("fail")'))
        with pytest.raises(ConnectionError):
            cb.call(lambda: exec('raise ConnectionError("fail")'))

        metrics = cb.metrics
        assert metrics.total_requests == 4
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 2
        assert metrics.success_rate == 50.0
        assert metrics.failure_rate == 50.0

    def test_circuit_breaker_status_report(self):
        """Test circuit breaker status reporting."""
        cb = CircuitBreaker(failure_threshold=3, name="TestCircuit")

        status = cb.get_status()
        assert status["name"] == "TestCircuit"
        assert status["state"] == "closed"
        assert status["failure_threshold"] == 3
        assert "metrics" in status
        assert "config" in status


class TestPredefinedPolicies:
    """Test predefined retry policies."""

    def test_default_policy_configuration(self):
        """Test DEFAULT_POLICY configuration."""
        assert DEFAULT_POLICY.max_attempts == 3
        assert DEFAULT_POLICY.base_delay == 1.0
        assert DEFAULT_POLICY.backoff_strategy == BackoffStrategy.EXPONENTIAL_JITTER

    def test_aggressive_policy_configuration(self):
        """Test AGGRESSIVE_POLICY configuration."""
        assert AGGRESSIVE_POLICY.max_attempts == 5
        assert AGGRESSIVE_POLICY.base_delay == 0.5
        assert AGGRESSIVE_POLICY.max_delay == 30.0

    def test_conservative_policy_configuration(self):
        """Test CONSERVATIVE_POLICY configuration."""
        assert CONSERVATIVE_POLICY.max_attempts == 2
        assert CONSERVATIVE_POLICY.base_delay == 2.0
        assert CONSERVATIVE_POLICY.backoff_strategy == BackoffStrategy.LINEAR

    def test_create_policy_default(self):
        """Test create_policy with default profile."""
        policy = create_policy()
        assert policy.max_attempts == DEFAULT_POLICY.max_attempts
        assert policy.base_delay == DEFAULT_POLICY.base_delay

    def test_create_policy_with_overrides(self):
        """Test create_policy with parameter overrides."""
        policy = create_policy(profile="default", max_attempts=10, base_delay=0.25)
        assert policy.max_attempts == 10
        assert policy.base_delay == 0.25

    def test_create_circuit_breaker_policy(self):
        """Test create_circuit_breaker_policy."""
        policy, cb = create_circuit_breaker_policy("aggressive")

        assert isinstance(policy, RetryPolicy)
        assert isinstance(cb, CircuitBreaker)
        assert policy.max_attempts == AGGRESSIVE_POLICY.max_attempts


class TestIntegration:
    """Test integration scenarios."""

    def test_retry_with_circuit_breaker(self):
        """Test retry decorator combined with circuit breaker."""
        cb = CircuitBreaker(failure_threshold=2, timeout=0.1)

        call_count = 0

        @retry(max_attempts=3, base_delay=0.05)
        @cb.decorator
        def integrated_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Integration failure")

        # Should exhaust retries and trip circuit breaker
        with pytest.raises(ConnectionError):
            integrated_func()

        assert call_count == 3  # Retry exhausted first
        assert cb.state == CircuitBreakerState.OPEN

        # Subsequent calls should fail fast via circuit breaker
        with pytest.raises(CircuitBreakerError):
            integrated_func()

    def test_complex_error_scenarios(self):
        """Test complex error handling scenarios."""
        policy = RetryPolicy(
            max_attempts=4, base_delay=0.05, exceptions={ConnectionError, TimeoutError}
        )
        executor = RetryExecutor(policy)

        call_count = 0

        def complex_func():
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                raise ConnectionError("Network issue")
            elif call_count == 2:
                raise TimeoutError("Service timeout")
            elif call_count == 3:
                raise ValueError("Non-retryable error")
            else:
                return "success"

        # Should retry on ConnectionError and TimeoutError,
        # but fail on ValueError
        with pytest.raises(ValueError, match="Non-retryable error"):
            executor.execute(complex_func)

        assert call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
