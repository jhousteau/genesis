"""Tests for circuit breaker functionality in retry module."""

import threading
import time

import pytest

from genesis.core.retry import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerMetrics,
    CircuitBreakerState,
    RetryConfig,
    circuit_breaker,
    resilient_call,
    resilient_database,
    resilient_external_service,
)


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig.default()
        assert config.failure_threshold == 5
        assert config.timeout == 60.0
        assert config.half_open_max_calls == 5
        assert config.success_threshold == 1
        assert config.sliding_window_size == 10
        assert config.name == "CircuitBreaker"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig.create(
            failure_threshold=3,
            timeout=30.0,
            half_open_max_calls=2,
            success_threshold=2,
            sliding_window_size=5,
            name="TestCircuit",
        )
        assert config.failure_threshold == 3
        assert config.timeout == 30.0
        assert config.half_open_max_calls == 2
        assert config.success_threshold == 2
        assert config.sliding_window_size == 5
        assert config.name == "TestCircuit"


class TestCircuitBreakerMetrics:
    """Test CircuitBreakerMetrics class."""

    def test_empty_metrics(self):
        """Test metrics with no requests."""
        metrics = CircuitBreakerMetrics()
        assert metrics.success_rate == 0.0
        assert metrics.failure_rate == 0.0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = CircuitBreakerMetrics(
            total_requests=10, successful_requests=7, failed_requests=3
        )
        assert metrics.success_rate == 70.0
        assert metrics.failure_rate == 30.0

    def test_all_successful(self):
        """Test metrics with all successful requests."""
        metrics = CircuitBreakerMetrics(
            total_requests=5, successful_requests=5, failed_requests=0
        )
        assert metrics.success_rate == 100.0
        assert metrics.failure_rate == 0.0

    def test_all_failed(self):
        """Test metrics with all failed requests."""
        metrics = CircuitBreakerMetrics(
            total_requests=5, successful_requests=0, failed_requests=5
        )
        assert metrics.success_rate == 0.0
        assert metrics.failure_rate == 100.0


class TestCircuitBreakerError:
    """Test CircuitBreakerError exception."""

    def test_default_error(self):
        """Test error creation requires circuit name."""
        error = CircuitBreakerError("Circuit is open", "test_circuit")
        assert str(error) == "Circuit is open"
        assert error.circuit_name == "test_circuit"
        assert error.code == "CIRCUIT_BREAKER_OPEN"

    def test_error_with_circuit_name(self):
        """Test error with circuit name."""
        error = CircuitBreakerError("Circuit is open", "TestCircuit")
        assert error.circuit_name == "TestCircuit"
        assert error.details["circuit_name"] == "TestCircuit"
        assert error.details["circuit_state"] == "open"


class TestCircuitBreaker:
    """Test CircuitBreaker class."""

    def test_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.metrics.total_requests == 0

    def test_successful_call(self):
        """Test successful function call."""
        cb = CircuitBreaker()

        def successful_function():
            return "success"

        result = cb.call(successful_function)
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.metrics.successful_requests == 1
        assert cb.metrics.total_requests == 1

    def test_failed_call(self):
        """Test failed function call."""
        cb = CircuitBreaker()

        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            cb.call(failing_function)

        assert (
            cb.state == CircuitBreakerState.CLOSED
        )  # Still closed, need more failures
        assert cb.metrics.failed_requests == 1
        assert cb.metrics.total_requests == 1

    def test_circuit_opens_after_failures(self):
        """Test circuit opens after failure threshold is reached."""
        config = CircuitBreakerConfig.create(failure_threshold=3, sliding_window_size=5)
        cb = CircuitBreaker(config)

        def failing_function():
            raise ValueError("Test error")

        # First 2 failures should keep circuit closed
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_function)
        assert cb.state == CircuitBreakerState.CLOSED

        # Third failure should open the circuit
        with pytest.raises(ValueError):
            cb.call(failing_function)
        assert cb.state == CircuitBreakerState.OPEN

    def test_circuit_rejects_calls_when_open(self):
        """Test circuit rejects calls when open."""
        config = CircuitBreakerConfig.create(failure_threshold=1)
        cb = CircuitBreaker(config)

        def failing_function():
            raise ValueError("Test error")

        # Trip the circuit
        with pytest.raises(ValueError):
            cb.call(failing_function)
        assert cb.state == CircuitBreakerState.OPEN

        # Further calls should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError) as exc_info:
            cb.call(failing_function)
        assert "Circuit breaker" in str(exc_info.value)

    def test_circuit_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        config = CircuitBreakerConfig.create(failure_threshold=1, timeout=0.1)
        cb = CircuitBreaker(config)

        def failing_function():
            raise ValueError("Test error")

        def successful_function():
            return "success"

        # Trip the circuit
        with pytest.raises(ValueError):
            cb.call(failing_function)
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(0.2)

        # Next call should work and transition to HALF_OPEN then CLOSED
        result = cb.call(successful_function)
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_closes_after_success_in_half_open(self):
        """Test circuit closes after successful calls in HALF_OPEN state."""
        config = CircuitBreakerConfig.create(
            failure_threshold=1, timeout=0.1, success_threshold=2, half_open_max_calls=3
        )
        cb = CircuitBreaker(config)

        def failing_function():
            raise ValueError("Test error")

        def successful_function():
            return "success"

        # Trip the circuit
        with pytest.raises(ValueError):
            cb.call(failing_function)
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(0.2)

        # First successful call transitions to HALF_OPEN
        result = cb.call(successful_function)
        assert result == "success"
        # Need 2 successes to close, so should still be HALF_OPEN
        # But since success_threshold is 2, we need another success

        # Force transition to HALF_OPEN for testing
        cb._transition_to_state(CircuitBreakerState.HALF_OPEN)
        cb._half_open_calls = 0
        cb._half_open_successes = 0

        # First success in HALF_OPEN
        result = cb.call(successful_function)
        assert result == "success"

        # Second success should close the circuit
        result = cb.call(successful_function)
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_reopens_on_failure_in_half_open(self):
        """Test circuit reopens on failure while in HALF_OPEN state."""
        config = CircuitBreakerConfig.create(failure_threshold=1, timeout=0.1)
        cb = CircuitBreaker(config)

        def failing_function():
            raise ValueError("Test error")

        # Trip the circuit
        with pytest.raises(ValueError):
            cb.call(failing_function)
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout and force HALF_OPEN state
        time.sleep(0.2)
        cb._transition_to_state(CircuitBreakerState.HALF_OPEN)

        # Failure in HALF_OPEN should reopen circuit
        with pytest.raises(ValueError):
            cb.call(failing_function)
        assert cb.state == CircuitBreakerState.OPEN

    def test_half_open_call_limit(self):
        """Test HALF_OPEN state respects call limit."""
        config = CircuitBreakerConfig.create(
            failure_threshold=1,
            timeout=0.1,
            half_open_max_calls=2,
            success_threshold=3,  # Need 3 successes to close, more than max_calls
        )
        cb = CircuitBreaker(config)

        def slow_function():
            return "success"

        # Trip circuit and force HALF_OPEN state
        cb._transition_to_state(CircuitBreakerState.OPEN)
        cb._last_failure_time = time.time() - 0.2  # Make it eligible for reset
        cb._transition_to_state(CircuitBreakerState.HALF_OPEN)
        cb._half_open_calls = 0  # Reset call count

        # First two calls should work (but circuit stays HALF_OPEN)
        result1 = cb.call(slow_function)
        result2 = cb.call(slow_function)
        assert result1 == "success"
        assert result2 == "success"
        assert cb.state == CircuitBreakerState.HALF_OPEN  # Still half open

        # Third call should be rejected due to call limit
        with pytest.raises(CircuitBreakerError):
            cb.call(slow_function)

    def test_reset_functionality(self):
        """Test manual reset functionality."""
        config = CircuitBreakerConfig.create(failure_threshold=1)
        cb = CircuitBreaker(config)

        def failing_function():
            raise ValueError("Test error")

        # Trip the circuit
        with pytest.raises(ValueError):
            cb.call(failing_function)
        assert cb.state == CircuitBreakerState.OPEN

        # Reset the circuit
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.metrics.total_requests == 1  # Reset doesn't clear metrics

    def test_get_status(self):
        """Test status information retrieval."""
        config = CircuitBreakerConfig.create(name="TestCircuit")
        cb = CircuitBreaker(config)

        status = cb.get_status()
        assert status["name"] == "TestCircuit"
        assert status["state"] == "closed"
        assert "metrics" in status
        assert "config" in status

    def test_thread_safety(self):
        """Test thread safety of circuit breaker."""
        cb = CircuitBreaker()
        results = []
        errors = []

        def worker_successful():
            try:
                result = cb.call(lambda: "success")
                results.append(result)
            except Exception as e:
                errors.append(e)

        def worker_failing():
            try:
                cb.call(lambda: exec('raise ValueError("error")'))
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker_successful)
            threads.append(thread)
            thread.start()

        for _ in range(3):
            thread = threading.Thread(target=worker_failing)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(results) == 5  # All successful calls completed
        assert len([e for e in errors if isinstance(e, ValueError)]) == 3

    @pytest.mark.asyncio
    async def test_async_calls(self):
        """Test async function calls."""
        cb = CircuitBreaker()

        async def async_successful():
            return "async success"

        async def async_failing():
            raise ValueError("Async error")

        # Test successful async call
        result = await cb.call_async(async_successful)
        assert result == "async success"

        # Test failing async call
        with pytest.raises(ValueError):
            await cb.call_async(async_failing)


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator functionality."""

    def test_decorator_sync_function(self):
        """Test decorator with synchronous function."""
        config = CircuitBreakerConfig.create(failure_threshold=2, name="DecoratorTest")
        cb = CircuitBreaker(config)

        @cb.decorator
        def test_function(value):
            if value == "fail":
                raise ValueError("Test error")
            return f"success: {value}"

        # Test successful call
        result = test_function("good")
        assert result == "success: good"

        # Test failing calls
        with pytest.raises(ValueError):
            test_function("fail")

        with pytest.raises(ValueError):
            test_function("fail")

        # Circuit should be open now
        assert cb.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_decorator_async_function(self):
        """Test decorator with asynchronous function."""
        config = CircuitBreakerConfig.create(
            failure_threshold=1, name="AsyncDecoratorTest"
        )
        cb = CircuitBreaker(config)

        @cb.decorator
        async def async_test_function(value):
            if value == "fail":
                raise ValueError("Async test error")
            return f"async success: {value}"

        # Test successful call
        result = await async_test_function("good")
        assert result == "async success: good"

        # Test failing call
        with pytest.raises(ValueError):
            await async_test_function("fail")

        # Circuit should be open now
        assert cb.state == CircuitBreakerState.OPEN

    def test_factory_decorator(self):
        """Test circuit_breaker factory decorator."""
        config = CircuitBreakerConfig.create(failure_threshold=1, name="FactoryTest")

        @circuit_breaker(config)
        def test_function():
            raise ValueError("Always fails")

        # First call should fail normally
        with pytest.raises(ValueError):
            test_function()

        # Second call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            test_function()


class TestResilientIntegration:
    """Test integration of retry and circuit breaker."""

    def test_resilient_call_decorator(self):
        """Test resilient_call decorator combining retry and circuit breaker."""
        call_count = 0

        @resilient_call(
            retry_config=RetryConfig.create(max_attempts=2, initial_delay=0.01),
            circuit_config=CircuitBreakerConfig.create(
                failure_threshold=2, name="ResilientTest"
            ),
        )
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 6:  # Fail first 6 calls
                raise ValueError("Test error")
            return "success"

        # First attempt: 2 calls (1 + 1 retry), both fail - creates 1 circuit failure
        with pytest.raises(ValueError):
            test_function()
        assert call_count == 2

        # Second attempt: 2 more calls, both fail - creates 2nd circuit failure, opens circuit
        with pytest.raises(ValueError):
            test_function()
        assert call_count == 4

        # Third attempt: Circuit is open, no retry attempts
        with pytest.raises(CircuitBreakerError):
            test_function()
        assert call_count == 4  # No additional calls made

    def test_resilient_external_service(self):
        """Test resilient_external_service convenience decorator."""
        call_count = 0

        @resilient_external_service(max_attempts=2, failure_threshold=2)
        def external_api():
            nonlocal call_count
            call_count += 1
            if call_count <= 6:  # Always fail to ensure circuit opens
                raise ConnectionError("Connection failed")
            return {"status": "ok"}

        # First attempt fails with retries (2 calls total)
        with pytest.raises(ConnectionError):
            external_api()
        assert call_count == 2

        # Second attempt fails with retries (4 calls total, circuit opens)
        with pytest.raises(ConnectionError):
            external_api()
        assert call_count == 4

    def test_resilient_database(self):
        """Test resilient_database convenience decorator."""
        call_count = 0

        @resilient_database(max_attempts=2, failure_threshold=2)
        def database_query():
            nonlocal call_count
            call_count += 1
            if call_count <= 6:  # Always fail to ensure circuit opens
                raise ConnectionError("DB connection failed")
            return [{"id": 1, "name": "test"}]

        # First attempt fails with retries (2 calls total)
        with pytest.raises(ConnectionError):
            database_query()
        assert call_count == 2

        # Second attempt fails with retries (4 calls total, circuit opens)
        with pytest.raises(ConnectionError):
            database_query()
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_resilient_call_async(self):
        """Test resilient_call with async functions."""
        call_count = 0

        @resilient_call(
            retry_config=RetryConfig.create(max_attempts=2, initial_delay=0.01),
            circuit_config=CircuitBreakerConfig.create(failure_threshold=2),
        )
        async def async_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 6:  # Always fail to ensure circuit opens
                raise ValueError("Async test error")
            return "async success"

        # First attempt: fails after retries (2 calls total)
        with pytest.raises(ValueError):
            await async_function()
        assert call_count == 2

        # Second attempt: fails after retries (4 calls total, circuit opens)
        with pytest.raises(ValueError):
            await async_function()
        assert call_count == 4


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_failure_threshold(self):
        """Test behavior with zero failure threshold."""
        config = CircuitBreakerConfig.create(failure_threshold=0)
        cb = CircuitBreaker(config)

        def failing_function():
            raise ValueError("Test error")

        # Should never open circuit with zero threshold
        for _ in range(10):
            with pytest.raises(ValueError):
                cb.call(failing_function)

        assert cb.state == CircuitBreakerState.CLOSED

    def test_very_short_timeout(self):
        """Test behavior with very short timeout."""
        config = CircuitBreakerConfig.create(failure_threshold=1, timeout=0.001)
        cb = CircuitBreaker(config)

        # Trip circuit
        with pytest.raises(ValueError):
            cb.call(lambda: exec('raise ValueError("error")'))

        # Wait for timeout
        time.sleep(0.01)

        # Should be able to make calls again
        result = cb.call(lambda: "success")
        assert result == "success"

    def test_large_sliding_window(self):
        """Test behavior with large sliding window."""
        config = CircuitBreakerConfig.create(
            failure_threshold=5, sliding_window_size=1000
        )
        cb = CircuitBreaker(config)

        # Add many successful calls
        for _ in range(100):
            cb.call(lambda: "success")

        # Add some failures (not enough to trip circuit)
        for _ in range(4):
            with pytest.raises(ValueError):
                cb.call(lambda: exec('raise ValueError("error")'))

        assert cb.state == CircuitBreakerState.CLOSED

        # One more failure should trip it
        with pytest.raises(ValueError):
            cb.call(lambda: exec('raise ValueError("error")'))
        assert cb.state == CircuitBreakerState.OPEN

    def test_metrics_thread_safety(self):
        """Test that metrics are thread-safe."""
        cb = CircuitBreaker()

        def worker():
            for _ in range(10):
                try:
                    cb.call(lambda: "success")
                except:
                    pass

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Check that metrics are consistent
        metrics = cb.metrics
        assert metrics.total_requests == 100
        assert metrics.successful_requests == 100
        assert metrics.failed_requests == 0
