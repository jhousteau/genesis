"""Tests for retry functionality."""

import time
from unittest.mock import Mock

import pytest

from shared_core.retry import RetryConfig, retry


class TestRetry:
    def test_retry_success_on_first_attempt(self):
        """Test that successful functions don't retry."""
        mock_func = Mock(return_value="success")
        decorated = retry()(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_failure_then_success(self):
        """Test retry behavior with eventual success."""
        mock_func = Mock(side_effect=[Exception("fail"), Exception("fail"), "success"])
        decorated = retry(RetryConfig(max_attempts=3, initial_delay=0.01))(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_max_attempts_exceeded(self):
        """Test that retry gives up after max attempts."""
        mock_func = Mock(side_effect=Exception("always fail"))
        decorated = retry(RetryConfig(max_attempts=2, initial_delay=0.01))(mock_func)

        with pytest.raises(Exception, match="always fail"):
            decorated()

        assert mock_func.call_count == 2

    def test_retry_specific_exceptions(self):
        """Test retry only catches specified exceptions."""
        mock_func = Mock(side_effect=ValueError("specific error"))
        config = RetryConfig(exceptions=(RuntimeError,), initial_delay=0.01)
        decorated = retry(config)(mock_func)

        # ValueError should not be retried
        with pytest.raises(ValueError, match="specific error"):
            decorated()

        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_success(self):
        """Test async retry functionality."""
        call_count = 0

        async def async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("async fail")
            return "async success"

        decorated = retry(RetryConfig(max_attempts=3, initial_delay=0.01))(async_func)

        result = await decorated()

        assert result == "async success"
        assert call_count == 3

    def test_retry_delay_calculation(self):
        """Test exponential backoff delay calculation."""
        mock_func = Mock(side_effect=[Exception("fail")] * 3)
        config = RetryConfig(
            max_attempts=3, initial_delay=0.1, exponential_base=2.0, jitter=False
        )
        decorated = retry(config)(mock_func)

        start_time = time.time()

        with pytest.raises(Exception, match="fail"):
            decorated()

        # Should have delays of ~0.1s and ~0.2s between attempts
        elapsed = time.time() - start_time
        assert elapsed >= 0.3  # At least the sum of delays
        assert elapsed < 1.0  # But not too much overhead
