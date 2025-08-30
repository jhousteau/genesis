"""Tests for logging functionality."""

import json
import logging
from io import StringIO

from shared_core.logger import LogConfig, get_logger


class TestLogger:
    def test_json_logger_basic(self):
        """Test basic JSON logging."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger = get_logger("test", LogConfig(level="INFO"), handler)

        logger.info("test message")

        output = stream.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["message"] == "test message"
        assert log_data["level"] == "INFO"
        assert "timestamp" in log_data

    def test_logger_with_extra_data(self):
        """Test logging with additional structured data."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger = get_logger("test", LogConfig(), handler)

        logger.info("test with data", extra={"extra_data": {"key": "value"}})

        output = stream.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["message"] == "test with data"
        assert log_data["key"] == "value"

    def test_logger_config_options(self):
        """Test various logger configuration options."""
        config = LogConfig(
            level="DEBUG", include_caller=True, extra_fields={"service": "test-service"}
        )
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger = get_logger("test", config, handler)

        logger.debug("debug message")

        output = stream.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["level"] == "DEBUG"
        assert log_data["service"] == "test-service"
        assert "caller" in log_data

    def test_non_json_formatter(self):
        """Test plain text logging format."""
        config = LogConfig(format_json=False)
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger = get_logger("test", config, handler)

        logger.info("plain text message")

        output = stream.getvalue().strip()

        # Should contain typical log format elements
        assert "test" in output  # logger name
        assert "INFO" in output  # level
        assert "plain text message" in output  # message

    def test_logger_level_filtering(self):
        """Test that log level filtering works correctly."""
        config = LogConfig(level="WARNING")
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger = get_logger("test", config, handler)

        logger.info("info message")  # Should be filtered out
        logger.warning("warning message")  # Should appear

        output = stream.getvalue().strip()

        assert "info message" not in output
        assert "warning message" in output
