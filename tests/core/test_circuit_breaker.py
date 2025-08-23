"""
Comprehensive tests for Genesis circuit breaker using VERIFY methodology.

Test Coverage:
- CircuitBreakerState transitions and validation
- CircuitBreakerError handling and categorization
- CircuitBreakerMetrics calculation and tracking
- CircuitBreaker state management and thread safety
- Synchronous and asynchronous operation handling
- Decorator functionality and integration
- Performance benchmarks and concurrency tests
- Recovery scenarios and edge cases
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch

import pytest

from core.errors.handler import ErrorCategory, GenesisError
from core.retry.circuit_breaker import (CircuitBreaker, CircuitBreakerError,
                                        CircuitBreakerMetrics,
                                        CircuitBreakerState)


class TestCircuitBreakerState:
    """Test CircuitBreakerState enumeration."""

    def test_circuit_breaker_state_values(self):
        """Test all circuit breaker state enum values."""
        assert CircuitBreakerState.CLOSED.value == "closed"
        assert CircuitBreakerState.OPEN.value == "open"
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"

    def test_circuit_breaker_state_from_string(self):
        """Test creating state from string value."""
        assert CircuitBreakerState("closed") == CircuitBreakerState.CLOSED
        assert CircuitBreakerState("open") == CircuitBreakerState.OPEN
        assert CircuitBreakerState("half_open") == CircuitBreakerState.HALF_OPEN


class TestCircuitBreakerError:
    """Test CircuitBreakerError exception handling."""

    def test_circuit_breaker_error_creation(self):
        """Test creating CircuitBreakerError with default values."""
        error = CircuitBreakerError("Circuit is open")

        assert str(error) == "Circuit is open"
        assert error.message == "Circuit is open"
        assert error.circuit_name == "unknown"
        assert error.category == ErrorCategory.UNAVAILABLE
        assert error.details["circuit_name"] == "unknown"
        assert error.details["circuit_state"] == "open"
        assert error.details["error_type"] == "circuit_breaker_open"

    def test_circuit_breaker_error_with_circuit_name(self):
        """Test creating CircuitBreakerError with specific circuit name."""
        error = CircuitBreakerError(
            "Service unavailable", circuit_name="payment-service"
        )

        assert error.message == "Service unavailable"
        assert error.circuit_name == "payment-service"
        assert error.details["circuit_name"] == "payment-service"

    def test_circuit_breaker_error_inheritance(self):
        """Test that CircuitBreakerError inherits from GenesisError."""
        error = CircuitBreakerError("Test error")

        assert isinstance(error, GenesisError)
        assert isinstance(error, Exception)
        assert error.category == ErrorCategory.UNAVAILABLE


class TestCircuitBreakerMetrics:
    """Test CircuitBreakerMetrics data tracking."""

    def test_metrics_initialization(self):
        """Test metrics initialization with default values."""
        metrics = CircuitBreakerMetrics()

        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.open_state_count == 0
        assert metrics.half_open_state_count == 0
        assert metrics.last_failure_time is None
        assert metrics.last_success_time is None
        assert metrics.state_transitions == 0

    def test_metrics_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = CircuitBreakerMetrics()

        # No requests
        assert metrics.success_rate == 0.0

        # All successful
        metrics.total_requests = 10
        metrics.successful_requests = 10
        assert metrics.success_rate == 100.0

        # Partial success
        metrics.successful_requests = 7
        assert metrics.success_rate == 70.0

        # No success
        metrics.successful_requests = 0
        assert metrics.success_rate == 0.0

    def test_metrics_failure_rate_calculation(self):
        """Test failure rate calculation."""
        metrics = CircuitBreakerMetrics()

        # No requests
        assert metrics.failure_rate == 0.0

        # All failed
        metrics.total_requests = 10
        metrics.failed_requests = 10
        assert metrics.failure_rate == 100.0

        # Partial failure
        metrics.failed_requests = 3
        assert metrics.failure_rate == 30.0

        # No failures
        metrics.failed_requests = 0
        assert metrics.failure_rate == 0.0

    def test_metrics_rate_calculations_with_custom_values(self):
        """Test rate calculations with various values."""
        metrics = CircuitBreakerMetrics(
            total_requests=50, successful_requests=35, failed_requests=15
        )

        assert metrics.success_rate == 70.0
        assert metrics.failure_rate == 30.0
        assert (
            metrics.successful_requests + metrics.failed_requests
            == metrics.total_requests
        )


class TestCircuitBreaker:
    """Test CircuitBreaker core functionality."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker with test-friendly configuration."""
        return CircuitBreaker(
            failure_threshold=3,
            timeout=0.1,  # Short timeout for testing
            half_open_max_calls=2,
            success_threshold=1,
            sliding_window_size=5,
            name="test-circuit",
        )

    @pytest.fixture
    def strict_circuit_breaker(self):
        """Create circuit breaker with strict configuration."""
        return CircuitBreaker(
            failure_threshold=1,
            timeout=0.05,
            half_open_max_calls=1,
            success_threshold=2,
            sliding_window_size=3,
            name="strict-circuit",
        )

    def test_circuit_breaker_initialization(self, circuit_breaker):
        """Test circuit breaker initialization."""
        assert circuit_breaker.failure_threshold == 3
        assert circuit_breaker.timeout == 0.1
        assert circuit_breaker.half_open_max_calls == 2
        assert circuit_breaker.success_threshold == 1
        assert circuit_breaker.sliding_window_size == 5
        assert circuit_breaker.name == "test-circuit"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_default_initialization(self):
        """Test circuit breaker with default values."""
        cb = CircuitBreaker()

        assert cb.failure_threshold == 5
        assert cb.timeout == 60.0
        assert cb.half_open_max_calls == 5
        assert cb.success_threshold == 1
        assert cb.sliding_window_size == 10
        assert cb.name == "CircuitBreaker"
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_state_property(self, circuit_breaker):
        """Test state property thread safety."""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        # State should be accessible from multiple threads
        states = []

        def get_state():
            states.append(circuit_breaker.state)

        threads = [threading.Thread(target=get_state) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(states) == 10
        assert all(state == CircuitBreakerState.CLOSED for state in states)

    def test_circuit_breaker_metrics_property(self, circuit_breaker):
        """Test metrics property returns copy."""
        metrics1 = circuit_breaker.metrics
        metrics2 = circuit_breaker.metrics

        # Should be different instances (copies)
        assert metrics1 is not metrics2
        assert metrics1.total_requests == metrics2.total_requests == 0

    def test_successful_call_execution(self, circuit_breaker):
        """Test successful function call through circuit breaker."""
        mock_func = Mock(return_value="success")

        result = circuit_breaker.call(mock_func, "arg1", kwarg1="value1")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        metrics = circuit_breaker.metrics
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0

    def test_failed_call_below_threshold(self, circuit_breaker):
        """Test failed calls below failure threshold."""
        mock_func = Mock(side_effect=ConnectionError("network error"))

        # Two failures (below threshold of 3)
        for _ in range(2):
            with pytest.raises(ConnectionError):
                circuit_breaker.call(mock_func)

        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        metrics = circuit_breaker.metrics
        assert metrics.total_requests == 2
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 2

    def test_circuit_opens_after_threshold_reached(self, circuit_breaker):
        """Test circuit opens after failure threshold is reached."""
        mock_func = Mock(side_effect=RuntimeError("persistent error"))

        # Exceed failure threshold
        for _ in range(3):
            with pytest.raises(RuntimeError):
                circuit_breaker.call(mock_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        metrics = circuit_breaker.metrics
        assert metrics.total_requests == 3
        assert metrics.failed_requests == 3
        assert metrics.open_state_count == 1

    def test_circuit_breaker_error_when_open(self, circuit_breaker):
        """Test CircuitBreakerError is raised when circuit is open."""
        # Force circuit to open state
        mock_func = Mock(side_effect=Exception("error"))
        for _ in range(3):
            with pytest.raises(Exception):
                circuit_breaker.call(mock_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Now calls should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError) as exc_info:
            circuit_breaker.call(lambda: "should not execute")

        error = exc_info.value
        assert "test-circuit" in str(error)
        assert error.circuit_name == "test-circuit"
        assert "open" in str(error)

    def test_circuit_transitions_to_half_open(self, circuit_breaker):
        """Test circuit transitions from open to half-open after timeout."""
        # Force circuit to open
        mock_func = Mock(side_effect=Exception("error"))
        for _ in range(3):
            with pytest.raises(Exception):
                circuit_breaker.call(mock_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(0.11)  # Slightly longer than timeout

        # Next call should transition to half-open
        mock_func = Mock(return_value="success")
        result = circuit_breaker.call(mock_func)

        assert result == "success"
        assert (
            circuit_breaker.state == CircuitBreakerState.CLOSED
        )  # Should close on success

    def test_half_open_state_behavior(self, circuit_breaker):
        """Test behavior in half-open state."""
        # Force circuit to open
        for _ in range(3):
            with pytest.raises(Exception):
                circuit_breaker.call(lambda: exec('raise Exception("error")'))

        # Wait for timeout and transition to half-open
        time.sleep(0.11)

        # First call in half-open should be allowed
        mock_func = Mock(return_value="test1")
        result1 = circuit_breaker.call(mock_func)
        assert result1 == "test1"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_half_open_failure_reopens_circuit(self, circuit_breaker):
        """Test that failure in half-open state reopens circuit."""
        # Force circuit to open
        for _ in range(3):
            with pytest.raises(Exception):
                circuit_breaker.call(lambda: exec('raise Exception("error")'))

        # Wait for timeout
        time.sleep(0.11)

        # Fail in half-open state
        with pytest.raises(Exception):
            circuit_breaker.call(lambda: exec('raise Exception("half-open error")'))

        assert circuit_breaker.state == CircuitBreakerState.OPEN

    def test_half_open_max_calls_limit(self):
        """Test half-open max calls limit and transition to closed."""
        cb = CircuitBreaker(
            failure_threshold=1,
            timeout=0.05,
            half_open_max_calls=2,
            success_threshold=2,
            name="limited-half-open",
        )

        # Force to open
        with pytest.raises(Exception):
            cb.call(lambda: exec('raise Exception("error")'))

        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(0.06)

        # Should allow limited calls in half-open, then transition to closed
        results = []
        for i in range(3):
            try:
                result = cb.call(lambda x=i: f"call-{x}")
                results.append(result)
            except CircuitBreakerError:
                results.append("blocked")

        # All calls should succeed: first 2 in half-open (triggering transition to closed), third in closed state
        assert len(results) == 3
        assert results[0] == "call-0"
        assert results[1] == "call-1"
        assert results[2] == "call-2"

        # Circuit should be closed after successful calls
        assert cb.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_async_call_execution(self, circuit_breaker):
        """Test asynchronous function execution."""

        async def async_func(arg, kwarg=None):
            await asyncio.sleep(0.001)
            return f"async-{arg}-{kwarg}"

        result = await circuit_breaker.call_async(async_func, "test", kwarg="value")

        assert result == "async-test-value"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        metrics = circuit_breaker.metrics
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1

    @pytest.mark.asyncio
    async def test_async_call_failure(self, circuit_breaker):
        """Test asynchronous function failure handling."""

        async def failing_func():
            await asyncio.sleep(0.001)
            raise ValueError("async error")

        with pytest.raises(ValueError, match="async error"):
            await circuit_breaker.call_async(failing_func)

        metrics = circuit_breaker.metrics
        assert metrics.total_requests == 1
        assert metrics.failed_requests == 1

    @pytest.mark.asyncio
    async def test_async_circuit_opens(self, circuit_breaker):
        """Test circuit opening with async calls."""

        async def failing_func():
            raise ConnectionError("async network error")

        # Trigger failures to open circuit
        for _ in range(3):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call_async(failing_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call_async(lambda: "should not execute")

    def test_decorator_sync_function(self, circuit_breaker):
        """Test decorator with synchronous function."""
        call_count = 0

        @circuit_breaker.decorator
        def decorated_func(arg):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError(f"failure {call_count}")
            return f"success-{arg}"

        result = decorated_func("test")

        assert result == "success-test"
        assert call_count == 3
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_decorator_async_function(self, circuit_breaker):
        """Test decorator with asynchronous function."""
        call_count = 0

        @circuit_breaker.decorator
        async def decorated_async_func(arg):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.001)
            if call_count <= 1:
                raise ConnectionError(f"async failure {call_count}")
            return f"async-success-{arg}"

        result = await decorated_async_func("test")

        assert result == "async-success-test"
        assert call_count == 2

    def test_manual_reset(self, circuit_breaker):
        """Test manual circuit reset functionality."""
        # Force circuit to open
        for _ in range(3):
            with pytest.raises(Exception):
                circuit_breaker.call(lambda: exec('raise Exception("error")'))

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Manually reset
        circuit_breaker.reset()

        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        # Should work normally after reset
        result = circuit_breaker.call(lambda: "reset success")
        assert result == "reset success"

    def test_get_status(self, circuit_breaker):
        """Test get_status method returns comprehensive information."""
        # Execute some operations
        circuit_breaker.call(lambda: "success1")
        circuit_breaker.call(lambda: "success2")

        try:
            circuit_breaker.call(lambda: exec('raise Exception("error")'))
        except:
            pass

        status = circuit_breaker.get_status()

        assert status["name"] == "test-circuit"
        assert status["state"] == "closed"
        assert status["failure_threshold"] == 3
        assert status["timeout"] == 0.1

        metrics = status["metrics"]
        assert metrics["total_requests"] == 3
        assert metrics["successful_requests"] == 2
        assert metrics["failed_requests"] == 1
        assert metrics["success_rate"] == 66.67
        assert metrics["failure_rate"] == 33.33

        config = status["config"]
        assert config["half_open_max_calls"] == 2
        assert config["success_threshold"] == 1
        assert config["sliding_window_size"] == 5


class TestCircuitBreakerThreadSafety:
    """Test circuit breaker thread safety and concurrent usage."""

    def test_concurrent_successful_calls(self):
        """Test concurrent successful calls."""
        cb = CircuitBreaker(name="concurrent-test")

        def make_call(thread_id):
            return cb.call(lambda: f"result-{thread_id}")

        # Execute concurrent calls
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_call, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]

        assert len(results) == 10
        for i in range(10):
            assert f"result-{i}" in results

        metrics = cb.metrics
        assert metrics.total_requests == 10
        assert metrics.successful_requests == 10
        assert metrics.failed_requests == 0

    def test_concurrent_mixed_calls(self):
        """Test concurrent calls with mixed success/failure."""
        cb = CircuitBreaker(failure_threshold=20, name="mixed-test")  # High threshold

        def make_call(thread_id):
            if thread_id % 3 == 0:  # Every third call fails
                try:
                    return cb.call(lambda: exec('raise Exception("planned failure")'))
                except:
                    return f"failed-{thread_id}"
            else:
                return cb.call(lambda: f"success-{thread_id}")

        # Execute concurrent calls
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(make_call, i) for i in range(15)]
            results = [future.result() for future in as_completed(futures)]

        assert len(results) == 15

        success_count = len([r for r in results if r.startswith("success")])
        failure_count = len([r for r in results if r.startswith("failed")])

        assert success_count == 10  # 2/3 of calls
        assert failure_count == 5  # 1/3 of calls

    def test_concurrent_state_transitions(self):
        """Test thread safety during state transitions."""
        cb = CircuitBreaker(failure_threshold=3, timeout=0.05, name="transition-test")

        results = []
        lock = threading.Lock()

        def failing_calls():
            """Generate failing calls to trigger state transition."""
            for _ in range(3):
                try:
                    cb.call(lambda: exec('raise Exception("error")'))
                except:
                    pass

            with lock:
                results.append(("failed", cb.state))

        def checking_calls():
            """Check circuit state during transitions."""
            time.sleep(0.01)  # Small delay
            with lock:
                results.append(("check", cb.state))

        def recovery_calls():
            """Attempt recovery after timeout."""
            time.sleep(0.06)  # Wait for timeout
            try:
                result = cb.call(lambda: "recovery")
                with lock:
                    results.append(("recovery", result, cb.state))
            except Exception as e:
                with lock:
                    results.append(("recovery_failed", type(e).__name__))

        # Start concurrent operations
        threads = [
            threading.Thread(target=failing_calls),
            threading.Thread(target=checking_calls),
            threading.Thread(target=recovery_calls),
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify thread safety - no race conditions
        assert len(results) >= 3

        # Check that we have expected result types
        result_types = [r[0] for r in results]
        assert "failed" in result_types
        assert "check" in result_types

    def test_metrics_thread_safety(self):
        """Test metrics updates are thread-safe."""
        cb = CircuitBreaker(name="metrics-test")

        def update_metrics(thread_id):
            # Mix of success and failure
            try:
                cb.call(
                    lambda: (
                        "success"
                        if thread_id % 2 == 0
                        else exec('raise Exception("error")')
                    )
                )
            except:
                pass

        # Concurrent metric updates
        threads = [
            threading.Thread(target=update_metrics, args=(i,)) for i in range(20)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        metrics = cb.metrics
        assert metrics.total_requests == 20
        assert metrics.successful_requests + metrics.failed_requests == 20
        assert 0 <= metrics.success_rate <= 100
        assert 0 <= metrics.failure_rate <= 100


class TestCircuitBreakerPerformance:
    """Test circuit breaker performance characteristics."""

    def test_successful_call_performance(self):
        """Test performance overhead of successful calls."""
        cb = CircuitBreaker(name="perf-test")

        def simple_function():
            return "result"

        # Measure execution time
        start_time = time.time()
        for _ in range(1000):
            cb.call(simple_function)
        duration = time.time() - start_time

        # Should complete quickly with minimal overhead
        assert duration < 1.0  # Less than 1 second for 1000 calls

        metrics = cb.metrics
        assert metrics.total_requests == 1000
        assert metrics.successful_requests == 1000

    @pytest.mark.asyncio
    async def test_async_call_performance(self):
        """Test performance of async calls."""
        cb = CircuitBreaker(name="async-perf-test")

        async def simple_async_function():
            return "async_result"

        # Measure execution time
        start_time = time.time()
        for _ in range(500):
            await cb.call_async(simple_async_function)
        duration = time.time() - start_time

        # Should complete reasonably quickly
        assert duration < 2.0  # Less than 2 seconds for 500 async calls

        metrics = cb.metrics
        assert metrics.total_requests == 500
        assert metrics.successful_requests == 500

    def test_state_check_performance(self):
        """Test performance of state checking."""
        cb = CircuitBreaker(name="state-perf-test")

        # Measure state check performance
        start_time = time.time()
        for _ in range(10000):
            _ = cb.state
        duration = time.time() - start_time

        # State checks should be very fast
        assert duration < 0.1  # Less than 100ms for 10000 checks

    def test_metrics_calculation_performance(self):
        """Test performance of metrics calculations."""
        cb = CircuitBreaker(name="metrics-perf-test")

        # Populate with some data
        for i in range(100):
            try:
                cb.call(
                    lambda x=i: (
                        "success" if x % 2 == 0 else exec('raise Exception("error")')
                    )
                )
            except:
                pass

        # Measure metrics access performance
        start_time = time.time()
        for _ in range(1000):
            _ = cb.metrics
        duration = time.time() - start_time

        # Metrics access should be fast
        assert duration < 0.5  # Less than 500ms for 1000 accesses


class TestCircuitBreakerEdgeCases:
    """Test circuit breaker edge cases and error conditions."""

    def test_zero_failure_threshold(self):
        """Test circuit breaker with zero failure threshold."""
        # This should work but immediately open on any failure
        cb = CircuitBreaker(failure_threshold=0, name="zero-threshold")

        # First failure should immediately open circuit
        with pytest.raises(Exception):
            cb.call(lambda: exec('raise Exception("immediate failure")'))

        # Circuit should be open
        assert cb.state == CircuitBreakerState.OPEN

        # Next call should be blocked
        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: "should not execute")

    def test_very_short_timeout(self):
        """Test circuit breaker with very short timeout."""
        cb = CircuitBreaker(
            failure_threshold=1,
            timeout=0.001,
            name="short-timeout",  # 1ms timeout
        )

        # Force to open
        with pytest.raises(Exception):
            cb.call(lambda: exec('raise Exception("error")'))

        assert cb.state == CircuitBreakerState.OPEN

        # Wait minimal time
        time.sleep(0.002)  # 2ms

        # Should transition to half-open
        result = cb.call(lambda: "recovered")
        assert result == "recovered"
        assert cb.state == CircuitBreakerState.CLOSED

    def test_very_large_sliding_window(self):
        """Test circuit breaker with large sliding window."""
        cb = CircuitBreaker(
            failure_threshold=5, sliding_window_size=1000, name="large-window"
        )

        # Should handle large window without issues
        for i in range(10):
            try:
                cb.call(
                    lambda x=i: (
                        "success" if x % 2 == 0 else exec('raise Exception("error")')
                    )
                )
            except:
                pass

        metrics = cb.metrics
        assert metrics.total_requests == 10
        assert cb.state == CircuitBreakerState.CLOSED  # Under threshold

    def test_function_returning_complex_objects(self):
        """Test circuit breaker with functions returning complex objects."""
        cb = CircuitBreaker(name="complex-return")

        def complex_function():
            return {
                "data": [1, 2, 3],
                "nested": {"value": "test", "items": {"a": 1, "b": 2}},
                "timestamp": time.time(),
            }

        result = cb.call(complex_function)

        assert result["data"] == [1, 2, 3]
        assert result["nested"]["value"] == "test"
        assert result["nested"]["items"]["a"] == 1
        assert "timestamp" in result

    def test_exception_in_function_with_complex_state(self):
        """Test exception handling with complex state."""
        cb = CircuitBreaker(failure_threshold=2, name="complex-exception")

        # First successful call
        cb.call(lambda: "success")

        # Then failure
        with pytest.raises(ValueError):
            cb.call(lambda: exec('raise ValueError("custom error")'))

        # Then success again
        cb.call(lambda: "success2")

        # Then another failure
        with pytest.raises(RuntimeError):
            cb.call(lambda: exec('raise RuntimeError("different error")'))

        # Should still be closed (only 2 failures, threshold is 2, but not consecutive in window)
        assert cb.state == CircuitBreakerState.CLOSED

        metrics = cb.metrics
        assert metrics.total_requests == 4
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 2


class TestCircuitBreakerRecoveryScenarios:
    """Test various recovery scenarios."""

    def test_gradual_recovery(self):
        """Test gradual recovery from failure state."""
        cb = CircuitBreaker(
            failure_threshold=2,
            timeout=0.05,
            half_open_max_calls=3,
            success_threshold=2,
            name="gradual-recovery",
        )

        # Force to open state
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(lambda: exec('raise Exception("error")'))

        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(0.06)

        # Partial recovery - one success, one failure
        cb.call(lambda: "success1")

        # Circuit might be closed or half-open depending on success_threshold
        # Let's test the actual behavior
        current_state = cb.state
        assert current_state in [
            CircuitBreakerState.CLOSED,
            CircuitBreakerState.HALF_OPEN,
        ]

    def test_recovery_with_immediate_failure(self):
        """Test recovery attempt with immediate failure."""
        cb = CircuitBreaker(
            failure_threshold=1, timeout=0.05, name="immediate-failure-recovery"
        )

        # Force to open
        with pytest.raises(Exception):
            cb.call(lambda: exec('raise Exception("error")'))

        # Wait for timeout
        time.sleep(0.06)

        # Immediate failure on recovery attempt
        with pytest.raises(Exception):
            cb.call(lambda: exec('raise Exception("recovery failed")'))

        # Should be open again
        assert cb.state == CircuitBreakerState.OPEN

    def test_multiple_recovery_cycles(self):
        """Test multiple recovery cycles."""
        cb = CircuitBreaker(failure_threshold=1, timeout=0.03, name="multiple-recovery")

        recovery_attempts = 0

        for cycle in range(3):
            # Force to open
            with pytest.raises(Exception):
                cb.call(lambda: exec('raise Exception(f"error cycle {cycle}")'))

            assert cb.state == CircuitBreakerState.OPEN

            # Wait and recover
            time.sleep(0.04)

            try:
                result = cb.call(lambda: f"recovery {cycle}")
                recovery_attempts += 1
                assert result == f"recovery {cycle}"
            except CircuitBreakerError:
                # Circuit might still be open due to timing
                pass

        # Should have at least some successful recoveries
        assert recovery_attempts > 0


@pytest.mark.integration
class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker functionality."""

    def test_circuit_breaker_with_retry_simulation(self):
        """Test circuit breaker with simulated retry scenarios."""
        cb = CircuitBreaker(failure_threshold=3, timeout=0.1, name="retry-integration")

        call_count = 0

        def unreliable_service():
            nonlocal call_count
            call_count += 1

            # Fail first 3 calls
            if call_count <= 3:
                raise ConnectionError(f"Service unavailable (attempt {call_count})")

            # Then succeed
            return f"Service response (attempt {call_count})"

        # First 3 calls should fail and open circuit
        for i in range(3):
            with pytest.raises(ConnectionError):
                cb.call(unreliable_service)

        assert cb.state == CircuitBreakerState.OPEN

        # Immediate call should be blocked
        with pytest.raises(CircuitBreakerError):
            cb.call(unreliable_service)

        # Wait for recovery
        time.sleep(0.11)

        # Recovery call should succeed
        result = cb.call(unreliable_service)
        assert result == "Service response (attempt 4)"
        assert cb.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_async_services(self):
        """Test circuit breaker with async service calls."""
        cb = CircuitBreaker(
            failure_threshold=2, timeout=0.05, name="async-service-integration"
        )

        call_count = 0

        async def async_external_service(data):
            nonlocal call_count
            call_count += 1

            # Simulate async processing
            await asyncio.sleep(0.001)

            if call_count <= 2:
                raise TimeoutError(f"Async service timeout (call {call_count})")

            return {"processed": data, "call": call_count}

        # Trigger failures
        for i in range(2):
            with pytest.raises(TimeoutError):
                await cb.call_async(async_external_service, f"data-{i}")

        assert cb.state == CircuitBreakerState.OPEN

        # Wait and recover
        await asyncio.sleep(0.06)

        # Should recover
        result = await cb.call_async(async_external_service, "recovery-data")
        assert result["processed"] == "recovery-data"
        assert result["call"] == 3

    def test_circuit_breaker_with_mixed_exception_types(self):
        """Test circuit breaker handling various exception types."""
        cb = CircuitBreaker(failure_threshold=5, name="mixed-exceptions")

        exceptions = [
            ConnectionError("Network issue"),
            TimeoutError("Request timeout"),
            ValueError("Validation error"),
            RuntimeError("Runtime issue"),
            KeyError("Missing key"),
        ]

        # All exceptions should be counted as failures
        for exc in exceptions:
            with pytest.raises(type(exc)):
                cb.call(lambda e=exc: exec("raise e"))

        assert cb.state == CircuitBreakerState.OPEN

        metrics = cb.metrics
        assert metrics.failed_requests == 5
        assert metrics.total_requests == 5

    def test_circuit_breaker_logging_integration(self):
        """Test circuit breaker logging integration."""
        cb = CircuitBreaker(name="logging-test")

        # Mock the logger to verify logging calls
        with patch.object(cb._logger, "info") as mock_info:
            # Trigger state transition
            for _ in range(5):
                try:
                    cb.call(lambda: exec('raise Exception("logged error")'))
                except:
                    pass

            # Verify logging was called for state transition
            assert mock_info.call_count > 0

            # Check that transition was logged
            log_calls = [call.args[0] for call in mock_info.call_args_list]
            transition_logs = [log for log in log_calls if "state transition" in log]
            assert len(transition_logs) > 0
