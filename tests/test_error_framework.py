"""
Comprehensive tests for Genesis error framework.
"""

import json
import pytest
from datetime import datetime
from unittest.mock import patch

from genesis.core.errors import (
    ErrorCategory,
    ErrorSeverity, 
    ErrorContext,
    GenesisError,
    InfrastructureError,
    NetworkError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    GenesisTimeoutError,
    RateLimitError,
    ExternalServiceError,
    ResourceError,
    handle_error,
    get_error_handler,
)


class TestErrorContext:
    """Test ErrorContext functionality."""

    def test_create_default_context(self):
        """Test creating default error context."""
        with patch.dict('os.environ', {'GENESIS_SERVICE': 'test-service', 'GENESIS_ENV': 'test'}):
            context = ErrorContext.create_default()
            
            assert context.service == 'test-service'
            assert context.environment == 'test'
            assert context.correlation_id is not None
            assert isinstance(context.timestamp, datetime)

    def test_context_to_dict(self):
        """Test error context serialization."""
        context = ErrorContext.create_default(service="test", environment="test")
        context_dict = context.to_dict()
        
        assert 'correlation_id' in context_dict
        assert 'timestamp' in context_dict
        assert context_dict['service'] == 'test'
        assert context_dict['environment'] == 'test'
        assert context_dict['metadata'] == {}

    def test_context_with_metadata(self):
        """Test error context with metadata."""
        context = ErrorContext.create_default()
        context.user_id = "user123"
        context.request_id = "req456"
        context.metadata = {"key": "value"}
        
        context_dict = context.to_dict()
        assert context_dict['user_id'] == "user123"
        assert context_dict['request_id'] == "req456"
        assert context_dict['metadata'] == {"key": "value"}


class TestGenesisError:
    """Test GenesisError base class functionality."""

    def test_basic_genesis_error(self):
        """Test basic GenesisError creation."""
        error = GenesisError("Test error")
        
        assert error.message == "Test error"
        assert error.code == "GENESIS_ERROR"
        assert error.category == ErrorCategory.UNKNOWN
        assert error.severity == ErrorSeverity.ERROR
        assert error.recoverable is True
        assert error.context is not None
        assert len(error.stack_trace) > 0

    def test_genesis_error_with_all_params(self):
        """Test GenesisError with all parameters."""
        context = ErrorContext.create_default()
        details = {"field": "username", "value": "invalid"}
        cause = ValueError("Original error")
        
        error = GenesisError(
            message="Custom error",
            code="CUSTOM_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            context=context,
            cause=cause,
            details=details,
            retry_after=30,
            recoverable=False
        )
        
        assert error.message == "Custom error"
        assert error.code == "CUSTOM_ERROR"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.WARNING
        assert error.context == context
        assert error.cause == cause
        assert error.details == details
        assert error.retry_after == 30
        assert error.recoverable is False

    def test_genesis_error_serialization(self):
        """Test GenesisError to_dict serialization."""
        error = GenesisError(
            "Test error",
            code="TEST_ERROR",
            details={"key": "value"}
        )
        
        error_dict = error.to_dict()
        
        assert 'error' in error_dict
        assert 'context' in error_dict
        assert 'details' in error_dict
        
        assert error_dict['error']['message'] == "Test error"
        assert error_dict['error']['code'] == "TEST_ERROR"
        assert error_dict['error']['category'] == ErrorCategory.UNKNOWN.value
        assert error_dict['error']['severity'] == ErrorSeverity.ERROR.value
        assert error_dict['details'] == {"key": "value"}

    def test_genesis_error_json_serialization(self):
        """Test GenesisError JSON serialization."""
        error = GenesisError("Test error")
        json_str = error.to_json()
        
        # Should be valid JSON
        error_data = json.loads(json_str)
        assert error_data['error']['message'] == "Test error"

    def test_stack_trace_inclusion(self):
        """Test stack trace inclusion based on severity."""
        # ERROR severity should include stack trace
        error_with_trace = GenesisError("Error", severity=ErrorSeverity.ERROR)
        error_dict = error_with_trace.to_dict()
        assert 'stack_trace' in error_dict['error']
        
        # WARNING severity should not include stack trace
        warning_error = GenesisError("Warning", severity=ErrorSeverity.WARNING)
        warning_dict = warning_error.to_dict()
        assert 'stack_trace' not in warning_dict['error']


class TestSpecificErrorTypes:
    """Test specific error type implementations."""

    def test_infrastructure_error(self):
        """Test InfrastructureError."""
        error = InfrastructureError("Database connection failed")
        
        assert error.code == "INFRASTRUCTURE_ERROR"
        assert error.category == ErrorCategory.INFRASTRUCTURE
        assert error.message == "Database connection failed"

    def test_network_error(self):
        """Test NetworkError with endpoint."""
        error = NetworkError("Connection timeout", endpoint="https://api.example.com")
        
        assert error.code == "NETWORK_ERROR"
        assert error.category == ErrorCategory.NETWORK
        assert error.details['endpoint'] == "https://api.example.com"

    def test_validation_error(self):
        """Test ValidationError with field."""
        error = ValidationError("Invalid email format", field="email")
        
        assert error.code == "VALIDATION_ERROR"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.WARNING
        assert error.details['field'] == "email"

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Invalid credentials")
        
        assert error.code == "AUTHENTICATION_ERROR"
        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.recoverable is False

    def test_authorization_error(self):
        """Test AuthorizationError with resource."""
        error = AuthorizationError("Access denied", resource="/admin/users")
        
        assert error.code == "AUTHORIZATION_ERROR"
        assert error.category == ErrorCategory.AUTHORIZATION
        assert error.recoverable is False
        assert error.details['resource'] == "/admin/users"

    def test_timeout_error(self):
        """Test GenesisTimeoutError with duration."""
        error = GenesisTimeoutError("Operation timeout", timeout_duration=30.0)
        
        assert error.code == "TIMEOUT_ERROR"
        assert error.category == ErrorCategory.TIMEOUT
        assert error.details['timeout_duration'] == 30.0

    def test_rate_limit_error(self):
        """Test RateLimitError with retry_after."""
        error = RateLimitError("Rate limit exceeded", retry_after=60)
        
        assert error.code == "RATE_LIMIT_ERROR"
        assert error.category == ErrorCategory.RATE_LIMIT
        assert error.retry_after == 60

    def test_external_service_error(self):
        """Test ExternalServiceError with service name."""
        error = ExternalServiceError("Payment service unavailable", service_name="stripe")
        
        assert error.code == "EXTERNAL_SERVICE_ERROR"
        assert error.category == ErrorCategory.EXTERNAL_SERVICE
        assert error.details['service_name'] == "stripe"

    def test_resource_error(self):
        """Test ResourceError with resource type."""
        error = ResourceError("File not found", resource_type="config")
        
        assert error.code == "RESOURCE_ERROR"
        assert error.category == ErrorCategory.RESOURCE
        assert error.details['resource_type'] == "config"


class TestErrorHandler:
    """Test ErrorHandler functionality."""

    def test_handle_genesis_error(self):
        """Test handling existing GenesisError."""
        original_error = ValidationError("Invalid input")
        handler = get_error_handler()
        
        handled_error = handler.handle(original_error)
        
        assert handled_error is original_error
        assert isinstance(handled_error, ValidationError)

    def test_handle_standard_exception(self):
        """Test converting standard exceptions to GenesisError."""
        handler = get_error_handler()
        
        # Test ValueError conversion
        value_error = ValueError("Invalid value")
        handled = handler.handle(value_error)
        
        assert isinstance(handled, ValidationError)
        assert handled.cause is value_error
        assert handled.category == ErrorCategory.VALIDATION

    def test_handle_connection_error(self):
        """Test NetworkError conversion from ConnectionError."""
        handler = get_error_handler()
        
        conn_error = ConnectionError("Network unreachable")
        handled = handler.handle(conn_error)
        
        assert isinstance(handled, NetworkError)
        assert handled.cause is conn_error
        assert handled.category == ErrorCategory.NETWORK

    def test_handle_timeout_error(self):
        """Test GenesisTimeoutError conversion."""
        handler = get_error_handler()
        
        timeout = TimeoutError("Request timeout")
        handled = handler.handle(timeout)
        
        assert isinstance(handled, GenesisTimeoutError)
        assert handled.cause is timeout
        assert handled.category == ErrorCategory.TIMEOUT

    def test_handle_permission_error(self):
        """Test AuthorizationError conversion from PermissionError."""
        handler = get_error_handler()
        
        perm_error = PermissionError("Permission denied")
        handled = handler.handle(perm_error)
        
        assert isinstance(handled, GenesisError)  # Base class for this mapping
        assert handled.cause is perm_error
        assert handled.category == ErrorCategory.AUTHORIZATION

    def test_handle_file_not_found_error(self):
        """Test ResourceError conversion from FileNotFoundError."""
        handler = get_error_handler()
        
        file_error = FileNotFoundError("File not found")
        handled = handler.handle(file_error)
        
        assert isinstance(handled, GenesisError)  # Base class for this mapping
        assert handled.cause is file_error
        assert handled.category == ErrorCategory.RESOURCE

    def test_handle_unknown_error(self):
        """Test handling unknown error types."""
        handler = get_error_handler()
        
        unknown_error = RuntimeError("Unknown error")
        handled = handler.handle(unknown_error)
        
        assert isinstance(handled, GenesisError)
        assert handled.cause is unknown_error
        assert handled.category == ErrorCategory.UNKNOWN

    def test_error_handler_with_context(self):
        """Test error handling with provided context."""
        handler = get_error_handler()
        context = ErrorContext.create_default()
        context.user_id = "test_user"
        
        error = ValueError("Test error")
        handled = handler.handle(error, context)
        
        assert handled.context == context
        assert handled.context.user_id == "test_user"

    def test_error_handler_callbacks(self):
        """Test error handler callbacks."""
        handler = get_error_handler()
        callback_called = False
        callback_error = None
        
        def error_callback(error: GenesisError):
            nonlocal callback_called, callback_error
            callback_called = True
            callback_error = error
        
        handler.add_handler(error_callback)
        
        test_error = ValueError("Test error")
        handled = handler.handle(test_error)
        
        assert callback_called
        assert callback_error is handled


class TestErrorHandlingConvenience:
    """Test convenience functions for error handling."""

    def test_handle_error_function(self):
        """Test global handle_error function."""
        error = ValueError("Test error")
        handled = handle_error(error)
        
        assert isinstance(handled, ValidationError)
        assert handled.cause is error

    def test_handle_error_with_context(self):
        """Test handle_error with context."""
        context = ErrorContext.create_default()
        error = NetworkError("Connection failed")
        handled = handle_error(error, context)
        
        assert handled.context == context
        assert isinstance(handled, NetworkError)

    def test_global_error_handler_singleton(self):
        """Test that get_error_handler returns singleton."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        
        assert handler1 is handler2


class TestErrorCategoriesAndSeverities:
    """Test all error categories and severities."""

    def test_all_error_categories(self):
        """Test all error categories are defined."""
        expected_categories = [
            "infrastructure", "application", "network", "authentication",
            "authorization", "validation", "configuration", "external_service",
            "resource", "resource_exhausted", "timeout", "rate_limit",
            "unavailable", "unknown"
        ]
        
        actual_categories = [category.value for category in ErrorCategory]
        
        for expected in expected_categories:
            assert expected in actual_categories

    def test_all_error_severities(self):
        """Test all error severities are defined."""
        expected_severities = ["debug", "info", "warning", "error", "critical"]
        actual_severities = [severity.value for severity in ErrorSeverity]
        
        for expected in expected_severities:
            assert expected in actual_severities

    def test_error_hierarchy(self):
        """Test that all custom errors inherit from GenesisError."""
        error_classes = [
            InfrastructureError,
            NetworkError,
            ValidationError,
            AuthenticationError,
            AuthorizationError,
            GenesisTimeoutError,
            RateLimitError,
            ExternalServiceError,
            ResourceError,
        ]
        
        for error_class in error_classes:
            error_instance = error_class("Test message")
            assert isinstance(error_instance, GenesisError)
            assert isinstance(error_instance, Exception)