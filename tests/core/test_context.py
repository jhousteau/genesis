"""
Comprehensive tests for Genesis Context Management using VERIFY methodology

Following VERIFY methodology:
- Validate: Test context propagation, correlation IDs, threading
- Execute: Comprehensive test coverage across all components
- Report: Clear test names and detailed error reporting
- Integrate: Thread safety and async operation validation
- Fix: Edge cases and error handling scenarios
- Yield: Performance metrics and quality validation

Test Categories:
- CorrelationID validation and serialization
- UserContext role/permission management
- TraceContext distributed tracing support
- RequestContext complete context aggregation
- ContextManager thread-safe operations
- Context propagation across async/threading boundaries
- Header propagation for service-to-service communication
- Performance benchmarks for critical context operations
"""

import asyncio
import pytest
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from unittest.mock import Mock, patch

from core.context.manager import (
    # Core classes
    CorrelationID,
    UserContext,
    TraceContext,
    RequestContext,
    ContextManager,
    # ID generation functions
    generate_correlation_id,
    generate_trace_id,
    generate_span_id,
    # Context access functions
    get_correlation_id,
    set_correlation_id,
    get_request_id,
    set_request_id,
    get_user_id,
    set_user_id,
    get_session_id,
    set_session_id,
    get_trace_id,
    set_trace_id,
    get_span_id,
    set_span_id,
    get_parent_span_id,
    set_parent_span_id,
    get_baggage,
    set_baggage,
    add_baggage,
    get_metadata,
    set_metadata,
    add_metadata,
    # Convenience functions
    get_current_context,
    set_user_context,
    get_user_context,
    set_trace_context,
    get_trace_context,
    # Header propagation functions
    propagate_headers,
    extract_headers,
    # Global context manager
    get_context_manager,
)
from core.errors.handler import GenesisError, ErrorCategory


class TestCorrelationID:
    """Test CorrelationID class functionality"""

    def test_correlation_id_creation(self):
        """Test CorrelationID creation with default values"""
        correlation_id = CorrelationID(id="test-123")

        assert correlation_id.id == "test-123"
        assert isinstance(correlation_id.timestamp, datetime)
        assert correlation_id.service == "genesis"  # Default from env
        assert correlation_id.environment == "development"  # Default from env

    def test_correlation_id_creation_with_custom_values(self):
        """Test CorrelationID creation with custom service and environment"""
        correlation_id = CorrelationID(
            id="custom-456", service="auth-service", environment="production"
        )

        assert correlation_id.id == "custom-456"
        assert correlation_id.service == "auth-service"
        assert correlation_id.environment == "production"

    def test_correlation_id_to_dict(self):
        """Test CorrelationID serialization to dictionary"""
        test_time = datetime(2023, 1, 1, 12, 0, 0)
        correlation_id = CorrelationID(
            id="serialize-789",
            timestamp=test_time,
            service="test-service",
            environment="staging",
        )

        result = correlation_id.to_dict()

        expected = {
            "id": "serialize-789",
            "timestamp": "2023-01-01T12:00:00Z",
            "service": "test-service",
            "environment": "staging",
        }
        assert result == expected

    def test_correlation_id_timestamp_auto_generation(self):
        """Test that timestamp is automatically generated"""
        before = datetime.utcnow()
        correlation_id = CorrelationID(id="timestamp-test")
        after = datetime.utcnow()

        assert before <= correlation_id.timestamp <= after


class TestUserContext:
    """Test UserContext class functionality"""

    def test_user_context_creation_minimal(self):
        """Test UserContext creation with minimal required fields"""
        user_context = UserContext(user_id="user-123")

        assert user_context.user_id == "user-123"
        assert user_context.session_id is None
        assert user_context.roles is None
        assert user_context.permissions is None
        assert user_context.tenant_id is None
        assert user_context.organization_id is None
        assert user_context.metadata == {}

    def test_user_context_creation_full(self):
        """Test UserContext creation with all fields"""
        metadata = {"department": "engineering", "level": "senior"}
        user_context = UserContext(
            user_id="user-456",
            session_id="session-789",
            roles=["admin", "user"],
            permissions=["read", "write", "delete"],
            tenant_id="tenant-001",
            organization_id="org-001",
            metadata=metadata,
        )

        assert user_context.user_id == "user-456"
        assert user_context.session_id == "session-789"
        assert user_context.roles == ["admin", "user"]
        assert user_context.permissions == ["read", "write", "delete"]
        assert user_context.tenant_id == "tenant-001"
        assert user_context.organization_id == "org-001"
        assert user_context.metadata == metadata

    def test_user_context_has_role(self):
        """Test role checking functionality"""
        user_context = UserContext(user_id="user-789", roles=["admin", "moderator"])

        assert user_context.has_role("admin") is True
        assert user_context.has_role("moderator") is True
        assert user_context.has_role("user") is False
        assert user_context.has_role("guest") is False

        # Test with no roles
        user_context_no_roles = UserContext(user_id="user-empty")
        assert user_context_no_roles.has_role("admin") is False

    def test_user_context_has_permission(self):
        """Test permission checking functionality"""
        user_context = UserContext(
            user_id="user-perm", permissions=["read", "write", "admin:delete"]
        )

        assert user_context.has_permission("read") is True
        assert user_context.has_permission("write") is True
        assert user_context.has_permission("admin:delete") is True
        assert user_context.has_permission("execute") is False

        # Test with no permissions
        user_context_no_perms = UserContext(user_id="user-empty")
        assert user_context_no_perms.has_permission("read") is False

    def test_user_context_to_dict(self):
        """Test UserContext serialization to dictionary"""
        user_context = UserContext(
            user_id="serialize-user",
            session_id="serialize-session",
            roles=["admin"],
            permissions=["all"],
            tenant_id="tenant-serialize",
            organization_id="org-serialize",
            metadata={"custom": "value"},
        )

        result = user_context.to_dict()

        expected = {
            "user_id": "serialize-user",
            "session_id": "serialize-session",
            "roles": ["admin"],
            "permissions": ["all"],
            "tenant_id": "tenant-serialize",
            "organization_id": "org-serialize",
            "metadata": {"custom": "value"},
        }
        assert result == expected

    def test_user_context_to_dict_empty_lists(self):
        """Test UserContext serialization with None roles/permissions"""
        user_context = UserContext(user_id="empty-user")
        result = user_context.to_dict()

        assert result["roles"] == []
        assert result["permissions"] == []


class TestTraceContext:
    """Test TraceContext class functionality"""

    def test_trace_context_creation_minimal(self):
        """Test TraceContext creation with minimal required fields"""
        trace_context = TraceContext(trace_id="trace-123", span_id="span-456")

        assert trace_context.trace_id == "trace-123"
        assert trace_context.span_id == "span-456"
        assert trace_context.parent_span_id is None
        assert trace_context.trace_flags == 0
        assert trace_context.trace_state is None
        assert trace_context.baggage == {}

    def test_trace_context_creation_full(self):
        """Test TraceContext creation with all fields"""
        baggage = {"key1": "value1", "key2": "value2"}
        trace_context = TraceContext(
            trace_id="full-trace",
            span_id="full-span",
            parent_span_id="parent-span",
            trace_flags=1,
            trace_state="congo=t61rcWkgMzE",
            baggage=baggage,
        )

        assert trace_context.trace_id == "full-trace"
        assert trace_context.span_id == "full-span"
        assert trace_context.parent_span_id == "parent-span"
        assert trace_context.trace_flags == 1
        assert trace_context.trace_state == "congo=t61rcWkgMzE"
        assert trace_context.baggage == baggage

    def test_trace_context_to_dict(self):
        """Test TraceContext serialization to dictionary"""
        trace_context = TraceContext(
            trace_id="dict-trace",
            span_id="dict-span",
            parent_span_id="dict-parent",
            trace_flags=1,
            trace_state="vendor=state",
            baggage={"env": "test"},
        )

        result = trace_context.to_dict()

        expected = {
            "trace_id": "dict-trace",
            "span_id": "dict-span",
            "parent_span_id": "dict-parent",
            "trace_flags": 1,
            "trace_state": "vendor=state",
            "baggage": {"env": "test"},
        }
        assert result == expected

    def test_trace_context_create_child_span(self):
        """Test creating child span from existing trace context"""
        parent_trace = TraceContext(
            trace_id="parent-trace",
            span_id="parent-span",
            trace_flags=1,
            trace_state="vendor=data",
            baggage={"env": "production"},
        )

        child_trace = parent_trace.create_child_span()

        # Verify inheritance
        assert child_trace.trace_id == "parent-trace"
        assert child_trace.parent_span_id == "parent-span"
        assert child_trace.trace_flags == 1
        assert child_trace.trace_state == "vendor=data"
        assert child_trace.baggage == {"env": "production"}

        # Verify new span ID
        assert child_trace.span_id != "parent-span"
        assert len(child_trace.span_id) == 16  # OpenTelemetry span ID format

    def test_trace_context_baggage_independence(self):
        """Test that baggage modifications don't affect original"""
        original_baggage = {"key": "value"}
        trace_context = TraceContext(
            trace_id="baggage-test", span_id="baggage-span", baggage=original_baggage
        )

        child_trace = trace_context.create_child_span()
        child_trace.baggage["new_key"] = "new_value"

        # Original should be unchanged
        assert trace_context.baggage == {"key": "value"}
        assert child_trace.baggage == {"key": "value", "new_key": "new_value"}


class TestRequestContext:
    """Test RequestContext class functionality"""

    def test_request_context_creation_minimal(self):
        """Test RequestContext creation with minimal required fields"""
        request_context = RequestContext(correlation_id="req-123", request_id="req-456")

        assert request_context.correlation_id == "req-123"
        assert request_context.request_id == "req-456"
        assert isinstance(request_context.timestamp, datetime)
        assert request_context.user_context is None
        assert request_context.trace_context is None
        assert request_context.service == "genesis"
        assert request_context.environment == "development"
        assert request_context.metadata == {}

    def test_request_context_creation_full(self):
        """Test RequestContext creation with all components"""
        user_context = UserContext(user_id="test-user", roles=["admin"])
        trace_context = TraceContext(trace_id="test-trace", span_id="test-span")
        metadata = {"version": "1.0", "feature": "auth"}

        request_context = RequestContext(
            correlation_id="full-req",
            request_id="full-req-id",
            user_context=user_context,
            trace_context=trace_context,
            service="test-service",
            environment="staging",
            metadata=metadata,
        )

        assert request_context.correlation_id == "full-req"
        assert request_context.request_id == "full-req-id"
        assert request_context.user_context == user_context
        assert request_context.trace_context == trace_context
        assert request_context.service == "test-service"
        assert request_context.environment == "staging"
        assert request_context.metadata == metadata

    def test_request_context_to_dict_minimal(self):
        """Test RequestContext serialization without optional components"""
        request_context = RequestContext(
            correlation_id="minimal-req",
            request_id="minimal-req-id",
            service="minimal-service",
            environment="test",
        )

        result = request_context.to_dict()

        # Should not contain user or trace keys
        assert "user" not in result
        assert "trace" not in result
        assert result["correlation_id"] == "minimal-req"
        assert result["request_id"] == "minimal-req-id"
        assert result["service"] == "minimal-service"
        assert result["environment"] == "test"

    def test_request_context_to_dict_full(self):
        """Test RequestContext serialization with all components"""
        user_context = UserContext(user_id="dict-user")
        trace_context = TraceContext(trace_id="dict-trace", span_id="dict-span")

        request_context = RequestContext(
            correlation_id="dict-req",
            request_id="dict-req-id",
            user_context=user_context,
            trace_context=trace_context,
            metadata={"key": "value"},
        )

        result = request_context.to_dict()

        assert "user" in result
        assert "trace" in result
        assert result["user"]["user_id"] == "dict-user"
        assert result["trace"]["trace_id"] == "dict-trace"
        assert result["metadata"] == {"key": "value"}

    def test_request_context_get_logger_context(self):
        """Test logger context extraction"""
        user_context = UserContext(user_id="log-user", session_id="log-session")
        trace_context = TraceContext(
            trace_id="log-trace", span_id="log-span", parent_span_id="log-parent"
        )

        request_context = RequestContext(
            correlation_id="log-req",
            request_id="log-req-id",
            user_context=user_context,
            trace_context=trace_context,
        )

        logger_context = request_context.get_logger_context()

        expected = {
            "correlation_id": "log-req",
            "request_id": "log-req-id",
            "user_id": "log-user",
            "session_id": "log-session",
            "trace_id": "log-trace",
            "span_id": "log-span",
            "parent_span_id": "log-parent",
        }
        assert logger_context == expected

    def test_request_context_get_logger_context_partial(self):
        """Test logger context extraction with missing components"""
        request_context = RequestContext(
            correlation_id="partial-req", request_id="partial-req-id"
        )

        logger_context = request_context.get_logger_context()

        expected = {"correlation_id": "partial-req", "request_id": "partial-req-id"}
        assert logger_context == expected


class TestIDGeneration:
    """Test ID generation functions"""

    def test_generate_correlation_id_format(self):
        """Test correlation ID generation format"""
        correlation_id = generate_correlation_id()

        # Should start with "req_"
        assert correlation_id.startswith("req_")

        # Should have timestamp and UUID parts
        parts = correlation_id.split("_")
        assert len(parts) == 3
        assert parts[0] == "req"

        # Timestamp should be numeric
        timestamp_part = parts[1]
        assert timestamp_part.isdigit()

        # UUID part should be 16 hex characters
        uuid_part = parts[2]
        assert len(uuid_part) == 16
        assert all(c in "0123456789abcdef" for c in uuid_part)

    def test_generate_correlation_id_uniqueness(self):
        """Test correlation ID uniqueness"""
        ids = [generate_correlation_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All should be unique

    def test_generate_trace_id_format(self):
        """Test trace ID generation format"""
        trace_id = generate_trace_id()

        # Should be 32 hex characters (OpenTelemetry format)
        assert len(trace_id) == 32
        assert all(c in "0123456789abcdef" for c in trace_id)

    def test_generate_trace_id_uniqueness(self):
        """Test trace ID uniqueness"""
        ids = [generate_trace_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All should be unique

    def test_generate_span_id_format(self):
        """Test span ID generation format"""
        span_id = generate_span_id()

        # Should be 16 hex characters (OpenTelemetry format)
        assert len(span_id) == 16
        assert all(c in "0123456789abcdef" for c in span_id)

    def test_generate_span_id_uniqueness(self):
        """Test span ID uniqueness"""
        ids = [generate_span_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All should be unique


class TestContextAccessFunctions:
    """Test context variable access functions"""

    def setup_method(self):
        """Clear context before each test"""
        get_context_manager().clear_context()

    def teardown_method(self):
        """Clear context after each test"""
        get_context_manager().clear_context()

    def test_correlation_id_get_set(self):
        """Test correlation ID get/set functions"""
        assert get_correlation_id() is None

        set_correlation_id("test-correlation")
        assert get_correlation_id() == "test-correlation"

    def test_request_id_get_set(self):
        """Test request ID get/set functions"""
        assert get_request_id() is None

        set_request_id("test-request")
        assert get_request_id() == "test-request"

    def test_user_id_get_set(self):
        """Test user ID get/set functions"""
        assert get_user_id() is None

        set_user_id("test-user")
        assert get_user_id() == "test-user"

    def test_session_id_get_set(self):
        """Test session ID get/set functions"""
        assert get_session_id() is None

        set_session_id("test-session")
        assert get_session_id() == "test-session"

    def test_trace_id_get_set(self):
        """Test trace ID get/set functions"""
        assert get_trace_id() is None

        set_trace_id("test-trace")
        assert get_trace_id() == "test-trace"

    def test_span_id_get_set(self):
        """Test span ID get/set functions"""
        assert get_span_id() is None

        set_span_id("test-span")
        assert get_span_id() == "test-span"

    def test_parent_span_id_get_set(self):
        """Test parent span ID get/set functions"""
        assert get_parent_span_id() is None

        set_parent_span_id("test-parent-span")
        assert get_parent_span_id() == "test-parent-span"

    def test_baggage_get_set(self):
        """Test baggage get/set functions"""
        assert get_baggage() == {}

        test_baggage = {"key1": "value1", "key2": "value2"}
        set_baggage(test_baggage)

        result = get_baggage()
        assert result == test_baggage

        # Verify independence (copies)
        result["key3"] = "value3"
        assert get_baggage() == test_baggage  # Original unchanged

    def test_baggage_add(self):
        """Test adding individual baggage items"""
        add_baggage("first", "value1")
        assert get_baggage() == {"first": "value1"}

        add_baggage("second", "value2")
        assert get_baggage() == {"first": "value1", "second": "value2"}

        # Overwrite existing
        add_baggage("first", "new_value")
        assert get_baggage() == {"first": "new_value", "second": "value2"}

    def test_metadata_get_set(self):
        """Test metadata get/set functions"""
        assert get_metadata() == {}

        test_metadata = {"version": "1.0", "feature": "auth"}
        set_metadata(test_metadata)

        result = get_metadata()
        assert result == test_metadata

        # Verify independence (copies)
        result["new_key"] = "new_value"
        assert get_metadata() == test_metadata  # Original unchanged

    def test_metadata_add(self):
        """Test adding individual metadata items"""
        add_metadata("version", "1.0")
        assert get_metadata() == {"version": "1.0"}

        add_metadata("feature", "auth")
        assert get_metadata() == {"version": "1.0", "feature": "auth"}

        # Overwrite existing
        add_metadata("version", "2.0")
        assert get_metadata() == {"version": "2.0", "feature": "auth"}


class TestConvenienceFunctions:
    """Test convenience functions for context management"""

    def setup_method(self):
        """Clear context before each test"""
        get_context_manager().clear_context()

    def teardown_method(self):
        """Clear context after each test"""
        get_context_manager().clear_context()

    def test_set_user_context_basic(self):
        """Test basic user context setting"""
        set_user_context("test-user")

        assert get_user_id() == "test-user"
        user_context = get_user_context()
        assert user_context.user_id == "test-user"
        assert user_context.session_id is None

    def test_set_user_context_full(self):
        """Test user context setting with all parameters"""
        set_user_context(
            user_id="full-user",
            session_id="full-session",
            roles=["admin", "user"],
            permissions=["read", "write"],
            tenant_id="tenant-123",
            organization_id="org-456",
            department="engineering",
            level="senior",
        )

        user_context = get_user_context()
        assert user_context.user_id == "full-user"
        assert user_context.session_id == "full-session"
        assert user_context.roles == ["admin", "user"]
        assert user_context.permissions == ["read", "write"]
        assert user_context.tenant_id == "tenant-123"
        assert user_context.organization_id == "org-456"
        assert user_context.metadata["department"] == "engineering"
        assert user_context.metadata["level"] == "senior"

    def test_get_user_context_none(self):
        """Test getting user context when none is set"""
        assert get_user_context() is None

    def test_set_trace_context_basic(self):
        """Test basic trace context setting"""
        set_trace_context("test-trace", "test-span")

        assert get_trace_id() == "test-trace"
        assert get_span_id() == "test-span"

        trace_context = get_trace_context()
        assert trace_context.trace_id == "test-trace"
        assert trace_context.span_id == "test-span"
        assert trace_context.parent_span_id is None

    def test_set_trace_context_full(self):
        """Test trace context setting with all parameters"""
        baggage = {"env": "test", "version": "1.0"}
        set_trace_context(
            trace_id="full-trace",
            span_id="full-span",
            parent_span_id="parent-span",
            baggage=baggage,
        )

        trace_context = get_trace_context()
        assert trace_context.trace_id == "full-trace"
        assert trace_context.span_id == "full-span"
        assert trace_context.parent_span_id == "parent-span"
        assert trace_context.baggage == baggage

    def test_get_trace_context_none(self):
        """Test getting trace context when none is set"""
        assert get_trace_context() is None

    def test_get_current_context_none(self):
        """Test getting current context when none is set"""
        assert get_current_context() is None

    def test_get_current_context_with_correlation_only(self):
        """Test getting current context with minimal setup"""
        set_correlation_id("context-test")

        context = get_current_context()
        assert context is not None
        assert context.correlation_id == "context-test"
        assert context.request_id == "context-test"  # Falls back to correlation_id
        assert context.user_context is None
        assert context.trace_context is None


class TestContextManager:
    """Test ContextManager class functionality"""

    def setup_method(self):
        """Clear context before each test"""
        get_context_manager().clear_context()

    def teardown_method(self):
        """Clear context after each test"""
        get_context_manager().clear_context()

    def test_context_manager_initialization_default(self):
        """Test ContextManager initialization with defaults"""
        manager = ContextManager()

        assert manager.service_name == "genesis"
        assert manager.environment == "development"
        assert manager.auto_generate_ids is True

    def test_context_manager_initialization_custom(self):
        """Test ContextManager initialization with custom values"""
        manager = ContextManager(
            service_name="custom-service",
            environment="production",
            auto_generate_ids=False,
        )

        assert manager.service_name == "custom-service"
        assert manager.environment == "production"
        assert manager.auto_generate_ids is False

    @pytest.mark.asyncio
    async def test_request_context_basic(self):
        """Test basic request context usage"""
        manager = ContextManager()

        async with manager.request_context(correlation_id="async-test"):
            # Context should be set within the async context
            assert get_correlation_id() == "async-test"
            context = manager.get_current_context()
            assert context.correlation_id == "async-test"

        # Context should be cleared after exiting
        assert get_correlation_id() is None

    @pytest.mark.asyncio
    async def test_request_context_auto_generation(self):
        """Test request context with auto ID generation"""
        manager = ContextManager(auto_generate_ids=True)

        async with manager.request_context() as context:
            # IDs should be auto-generated
            assert context.correlation_id is not None
            assert context.request_id is not None
            assert context.correlation_id.startswith("req_")

    @pytest.mark.asyncio
    async def test_request_context_full_parameters(self):
        """Test request context with all parameters"""
        manager = ContextManager()
        metadata = {"version": "1.0", "endpoint": "/api/test"}

        async with manager.request_context(
            correlation_id="full-corr",
            request_id="full-req",
            user_id="full-user",
            session_id="full-session",
            trace_id="full-trace",
            span_id="full-span",
            parent_span_id="full-parent",
            metadata=metadata,
        ) as context:
            assert context.correlation_id == "full-corr"
            assert context.request_id == "full-req"
            assert context.user_context.user_id == "full-user"
            assert context.user_context.session_id == "full-session"
            assert context.trace_context.trace_id == "full-trace"
            assert context.trace_context.span_id == "full-span"
            assert context.trace_context.parent_span_id == "full-parent"
            assert "version" in context.metadata

    @pytest.mark.asyncio
    async def test_request_context_nesting(self):
        """Test nested request contexts"""
        manager = ContextManager()

        async with manager.request_context(correlation_id="outer"):
            assert get_correlation_id() == "outer"

            async with manager.request_context(correlation_id="inner"):
                assert get_correlation_id() == "inner"

            # Should restore outer context
            assert get_correlation_id() == "outer"

        # Should be cleared completely
        assert get_correlation_id() is None

    def test_trace_span_basic(self):
        """Test basic trace span functionality"""
        manager = ContextManager()

        # Set up trace context first
        set_trace_id("span-test-trace")
        set_span_id("parent-span")

        with manager.trace_span("test_operation") as span_context:
            assert span_context.trace_id == "span-test-trace"
            assert span_context.span_id != "parent-span"  # New span ID
            assert span_context.parent_span_id == "parent-span"

            # Current context should be updated
            assert get_span_id() == span_context.span_id
            assert get_parent_span_id() == "parent-span"

        # Should restore previous span context
        assert get_span_id() == "parent-span"

    def test_trace_span_auto_generation(self):
        """Test trace span with auto trace ID generation"""
        manager = ContextManager(auto_generate_ids=True)

        with manager.trace_span("auto_trace_operation") as span_context:
            assert span_context.trace_id is not None
            assert len(span_context.trace_id) == 32  # OpenTelemetry format
            assert span_context.span_id is not None
            assert len(span_context.span_id) == 16  # OpenTelemetry format

    def test_trace_span_no_auto_generation_error(self):
        """Test trace span error when no trace ID and auto-generation disabled"""
        manager = ContextManager(auto_generate_ids=False)

        with pytest.raises(GenesisError) as exc_info:
            with manager.trace_span("error_operation"):
                pass

        assert exc_info.value.code == "TRACE_CONTEXT_MISSING"
        assert exc_info.value.category == ErrorCategory.CONFIGURATION

    def test_trace_span_metadata(self):
        """Test trace span with metadata"""
        manager = ContextManager()
        set_trace_id("metadata-trace")

        span_metadata = {"operation": "database", "table": "users"}

        with manager.trace_span("db_operation", metadata=span_metadata):
            current_metadata = get_metadata()
            assert current_metadata["span.operation"] == "database"
            assert current_metadata["span.table"] == "users"

    def test_trace_span_nesting(self):
        """Test nested trace spans"""
        manager = ContextManager()
        set_trace_id("nested-trace")
        set_span_id("root-span")

        with manager.trace_span("parent_operation") as parent_span:
            parent_span_id = parent_span.span_id

            with manager.trace_span("child_operation") as child_span:
                assert child_span.trace_id == "nested-trace"
                assert child_span.parent_span_id == parent_span_id
                assert child_span.span_id != parent_span_id

                # Current context should be child
                assert get_span_id() == child_span.span_id
                assert get_parent_span_id() == parent_span_id

            # Should restore parent span context
            assert get_span_id() == parent_span_id

    def test_get_current_context_complete(self):
        """Test getting complete current context"""
        manager = ContextManager()

        # Set up complete context
        set_correlation_id("complete-corr")
        set_request_id("complete-req")
        set_user_context("complete-user", session_id="complete-session")
        set_trace_context("complete-trace", "complete-span", baggage={"env": "test"})
        add_metadata("feature", "context_test")

        context = manager.get_current_context()

        assert context.correlation_id == "complete-corr"
        assert context.request_id == "complete-req"
        assert context.user_context.user_id == "complete-user"
        assert context.user_context.session_id == "complete-session"
        assert context.trace_context.trace_id == "complete-trace"
        assert context.trace_context.span_id == "complete-span"
        assert context.trace_context.baggage == {"env": "test"}
        assert context.metadata["feature"] == "context_test"

    def test_copy_context(self):
        """Test context copying for threading"""
        manager = ContextManager()

        set_correlation_id("copy-test")
        set_user_id("copy-user")

        # Copy current context
        context_copy = manager.copy_context()

        # Clear current context
        manager.clear_context()
        assert get_correlation_id() is None

        # Run in copied context
        def verify_context():
            assert get_correlation_id() == "copy-test"
            assert get_user_id() == "copy-user"

        context_copy.run(verify_context)

        # Original context should still be cleared
        assert get_correlation_id() is None

    def test_clear_context(self):
        """Test clearing all context variables"""
        manager = ContextManager()

        # Set up various context variables
        set_correlation_id("clear-test")
        set_user_id("clear-user")
        set_trace_id("clear-trace")
        add_baggage("key", "value")
        add_metadata("test", "data")

        # Verify they're set
        assert get_correlation_id() == "clear-test"
        assert get_user_id() == "clear-user"
        assert get_trace_id() == "clear-trace"
        assert get_baggage() == {"key": "value"}
        assert get_metadata() == {"test": "data"}

        # Clear context
        manager.clear_context()

        # Verify all cleared
        assert get_correlation_id() is None
        assert get_user_id() is None
        assert get_trace_id() is None
        assert get_baggage() == {}
        assert get_metadata() == {}


class TestHeaderPropagation:
    """Test header propagation functionality"""

    def setup_method(self):
        """Clear context before each test"""
        get_context_manager().clear_context()

    def teardown_method(self):
        """Clear context after each test"""
        get_context_manager().clear_context()

    def test_propagate_headers_empty(self):
        """Test header propagation with no context"""
        headers = propagate_headers()
        assert headers == {}

    def test_propagate_headers_correlation_only(self):
        """Test header propagation with correlation ID only"""
        set_correlation_id("header-corr")
        set_request_id("header-req")

        headers = propagate_headers()

        expected = {"X-Correlation-ID": "header-corr", "X-Request-ID": "header-req"}
        assert headers == expected

    def test_propagate_headers_user_context(self):
        """Test header propagation with user context"""
        set_correlation_id("user-corr")
        set_user_id("user-123")
        set_session_id("session-456")

        headers = propagate_headers()

        expected = {
            "X-Correlation-ID": "user-corr",
            "X-Request-ID": "user-corr",
            "X-User-ID": "user-123",
            "X-Session-ID": "session-456",
        }
        assert headers == expected

    def test_propagate_headers_trace_context(self):
        """Test header propagation with trace context"""
        set_correlation_id("trace-corr")
        set_trace_id("0123456789abcdef0123456789abcdef")
        set_span_id("0123456789abcdef")
        set_baggage({"env": "test", "version": "1.0"})

        headers = propagate_headers()

        assert headers["X-Correlation-ID"] == "trace-corr"
        assert (
            headers["traceparent"]
            == "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
        )

        # Baggage header should contain both keys
        baggage_header = headers["baggage"]
        assert "env=test" in baggage_header
        assert "version=1.0" in baggage_header

    def test_propagate_headers_complete(self):
        """Test header propagation with complete context"""
        set_correlation_id("complete-corr")
        set_request_id("complete-req")
        set_user_id("complete-user")
        set_session_id("complete-session")
        set_trace_id("1234567890abcdef1234567890abcdef")
        set_span_id("1234567890abcdef")
        set_baggage({"service": "auth"})

        headers = propagate_headers()

        expected = {
            "X-Correlation-ID": "complete-corr",
            "X-Request-ID": "complete-req",
            "X-User-ID": "complete-user",
            "X-Session-ID": "complete-session",
            "traceparent": "00-1234567890abcdef1234567890abcdef-1234567890abcdef-01",
            "baggage": "service=auth",
        }
        assert headers == expected

    def test_extract_headers_empty(self):
        """Test header extraction from empty headers"""
        result = extract_headers({})

        expected = {
            "correlation_id": None,
            "request_id": None,
            "user_id": None,
            "session_id": None,
            "trace_id": None,
            "span_id": None,
            "parent_span_id": None,
            "baggage": {},
        }
        assert result == expected

    def test_extract_headers_correlation(self):
        """Test header extraction for correlation headers"""
        headers = {"X-Correlation-ID": "extract-corr", "X-Request-ID": "extract-req"}

        result = extract_headers(headers)

        assert result["correlation_id"] == "extract-corr"
        assert result["request_id"] == "extract-req"

    def test_extract_headers_case_insensitive(self):
        """Test header extraction is case insensitive"""
        headers = {
            "x-correlation-id": "lower-corr",
            "X-USER-ID": "upper-user",
            "X-Session-Id": "mixed-session",
        }

        result = extract_headers(headers)

        assert result["correlation_id"] == "lower-corr"
        assert result["user_id"] == "upper-user"
        assert result["session_id"] == "mixed-session"

    def test_extract_headers_traceparent(self):
        """Test header extraction for OpenTelemetry traceparent"""
        headers = {
            "traceparent": "00-abcdef1234567890abcdef1234567890-1234567890abcdef-01"
        }

        result = extract_headers(headers)

        assert result["trace_id"] == "abcdef1234567890abcdef1234567890"
        assert result["span_id"] == "1234567890abcdef"
        assert result["parent_span_id"] == "1234567890abcdef"

    def test_extract_headers_baggage(self):
        """Test header extraction for baggage"""
        headers = {"baggage": "env=production,version=2.0,feature=auth"}

        result = extract_headers(headers)

        expected_baggage = {"env": "production", "version": "2.0", "feature": "auth"}
        assert result["baggage"] == expected_baggage

    def test_extract_headers_baggage_malformed(self):
        """Test header extraction handles malformed baggage"""
        headers = {"baggage": "env=production,invalid_item,key=value"}

        result = extract_headers(headers)

        # Should only extract valid key=value pairs
        expected_baggage = {"env": "production", "key": "value"}
        assert result["baggage"] == expected_baggage

    def test_extract_headers_complete(self):
        """Test header extraction with all header types"""
        headers = {
            "X-Correlation-ID": "all-corr",
            "X-Request-ID": "all-req",
            "X-User-ID": "all-user",
            "X-Session-ID": "all-session",
            "traceparent": "00-fedcba0987654321fedcba0987654321-fedcba0987654321-00",
            "baggage": "service=gateway,region=us-east-1",
        }

        result = extract_headers(headers)

        expected = {
            "correlation_id": "all-corr",
            "request_id": "all-req",
            "user_id": "all-user",
            "session_id": "all-session",
            "trace_id": "fedcba0987654321fedcba0987654321",
            "span_id": "fedcba0987654321",
            "parent_span_id": "fedcba0987654321",
            "baggage": {"service": "gateway", "region": "us-east-1"},
        }
        assert result == expected


class TestContextThreadSafety:
    """Test context thread safety and isolation"""

    def setup_method(self):
        """Clear context before each test"""
        get_context_manager().clear_context()

    def teardown_method(self):
        """Clear context after each test"""
        get_context_manager().clear_context()

    def test_context_isolation_between_threads(self):
        """Test that context is isolated between threads"""
        results = {}

        def set_and_verify_context(thread_id):
            correlation_id = f"thread-{thread_id}"
            user_id = f"user-{thread_id}"

            set_correlation_id(correlation_id)
            set_user_id(user_id)

            # Small delay to allow race conditions to manifest
            time.sleep(0.01)

            # Verify context is still correct
            results[thread_id] = {
                "correlation_id": get_correlation_id(),
                "user_id": get_user_id(),
            }

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=set_and_verify_context, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify each thread had its own context
        for i in range(10):
            assert results[i]["correlation_id"] == f"thread-{i}"
            assert results[i]["user_id"] == f"user-{i}"

    def test_context_propagation_with_threadpool(self):
        """Test context propagation using ThreadPoolExecutor"""
        manager = ContextManager()

        def worker_function():
            return {
                "correlation_id": get_correlation_id(),
                "user_id": get_user_id(),
                "trace_id": get_trace_id(),
            }

        # Set up context in main thread
        set_correlation_id("main-thread")
        set_user_id("main-user")
        set_trace_id("main-trace")

        # Copy context for propagation
        context_copy = manager.copy_context()

        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit work with context propagation
            futures = [
                executor.submit(context_copy.run, worker_function) for _ in range(5)
            ]

            results = [future.result() for future in futures]

        # Verify all workers had the same context
        for result in results:
            assert result["correlation_id"] == "main-thread"
            assert result["user_id"] == "main-user"
            assert result["trace_id"] == "main-trace"

    def test_context_independence_after_propagation(self):
        """Test that propagated context changes don't affect original"""
        manager = ContextManager()

        # Set up original context
        set_correlation_id("original")
        set_user_id("original-user")

        context_copy = manager.copy_context()

        def modify_context():
            # Modify context in copied context
            set_correlation_id("modified")
            set_user_id("modified-user")
            add_metadata("modified", "true")

            return {
                "correlation_id": get_correlation_id(),
                "user_id": get_user_id(),
                "metadata": get_metadata(),
            }

        # Run in copied context
        result = context_copy.run(modify_context)

        # Verify modifications in copied context
        assert result["correlation_id"] == "modified"
        assert result["user_id"] == "modified-user"
        assert result["metadata"]["modified"] == "true"

        # Verify original context unchanged
        assert get_correlation_id() == "original"
        assert get_user_id() == "original-user"
        assert "modified" not in get_metadata()

    @pytest.mark.asyncio
    async def test_async_context_isolation(self):
        """Test context isolation in async operations"""
        manager = ContextManager()

        async def async_worker(worker_id):
            async with manager.request_context(
                correlation_id=f"async-{worker_id}", user_id=f"async-user-{worker_id}"
            ):
                # Simulate async work
                await asyncio.sleep(0.01)

                return {
                    "worker_id": worker_id,
                    "correlation_id": get_correlation_id(),
                    "user_id": get_user_id(),
                }

        # Run multiple async workers concurrently
        tasks = [async_worker(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Verify each worker had correct isolated context
        for result in results:
            worker_id = result["worker_id"]
            assert result["correlation_id"] == f"async-{worker_id}"
            assert result["user_id"] == f"async-user-{worker_id}"

    @pytest.mark.asyncio
    async def test_nested_async_context_isolation(self):
        """Test nested async context managers maintain isolation"""
        manager = ContextManager()

        async with manager.request_context(correlation_id="outer"):
            outer_correlation = get_correlation_id()

            async def inner_async_operation():
                async with manager.request_context(correlation_id="inner"):
                    inner_correlation = get_correlation_id()
                    await asyncio.sleep(0.01)  # Simulate async work
                    return inner_correlation

                # Should be restored to outer context
                return get_correlation_id()

            inner_result = await inner_async_operation()
            final_correlation = get_correlation_id()

            assert outer_correlation == "outer"
            assert inner_result == "outer"  # Restored after inner context
            assert final_correlation == "outer"


class TestContextPerformance:
    """Test context management performance"""

    def setup_method(self):
        """Clear context before each test"""
        get_context_manager().clear_context()

    def teardown_method(self):
        """Clear context after each test"""
        get_context_manager().clear_context()

    def test_context_access_performance(self):
        """Test performance of context variable access"""
        # Set up context
        set_correlation_id("perf-test")
        set_user_id("perf-user")
        set_trace_id("perf-trace")
        set_metadata({"key1": "value1", "key2": "value2"})

        # Measure access performance
        start_time = time.time()

        for _ in range(10000):
            correlation_id = get_correlation_id()
            user_id = get_user_id()
            trace_id = get_trace_id()
            metadata = get_metadata()

        elapsed_time = time.time() - start_time

        # Should complete quickly (< 0.1 seconds for 10k iterations)
        assert elapsed_time < 0.1

        # Verify data is still correct
        assert get_correlation_id() == "perf-test"
        assert get_user_id() == "perf-user"
        assert get_trace_id() == "perf-trace"

    def test_id_generation_performance(self):
        """Test performance of ID generation functions"""
        start_time = time.time()

        # Generate many IDs
        correlation_ids = [generate_correlation_id() for _ in range(1000)]
        trace_ids = [generate_trace_id() for _ in range(1000)]
        span_ids = [generate_span_id() for _ in range(1000)]

        elapsed_time = time.time() - start_time

        # Should complete quickly (< 0.1 seconds)
        assert elapsed_time < 0.1

        # Verify uniqueness
        assert len(set(correlation_ids)) == 1000
        assert len(set(trace_ids)) == 1000
        assert len(set(span_ids)) == 1000

    @pytest.mark.asyncio
    async def test_async_context_performance(self):
        """Test performance of async context operations"""
        manager = ContextManager()

        start_time = time.time()

        # Create many async contexts
        async def create_context(i):
            async with manager.request_context(
                correlation_id=f"perf-{i}", user_id=f"user-{i}"
            ):
                return get_correlation_id()

        tasks = [create_context(i) for i in range(100)]
        results = await asyncio.gather(*tasks)

        elapsed_time = time.time() - start_time

        # Should complete quickly (< 0.5 seconds for 100 contexts)
        assert elapsed_time < 0.5

        # Verify all contexts were created correctly
        for i, result in enumerate(results):
            assert result == f"perf-{i}"

    def test_header_propagation_performance(self):
        """Test performance of header propagation operations"""
        # Set up complete context
        set_correlation_id("header-perf")
        set_user_id("header-user")
        set_trace_id("1234567890abcdef1234567890abcdef")
        set_span_id("1234567890abcdef")
        set_baggage({"key1": "value1", "key2": "value2", "key3": "value3"})

        start_time = time.time()

        # Generate and extract headers many times
        for _ in range(1000):
            headers = propagate_headers()
            extracted = extract_headers(headers)

        elapsed_time = time.time() - start_time

        # Should complete quickly (< 0.1 seconds)
        assert elapsed_time < 0.1


class TestContextEdgeCases:
    """Test edge cases and error conditions"""

    def setup_method(self):
        """Clear context before each test"""
        get_context_manager().clear_context()

    def teardown_method(self):
        """Clear context after each test"""
        get_context_manager().clear_context()

    def test_context_with_none_values(self):
        """Test context handling with None values"""
        # Set some values to None explicitly
        set_correlation_id("test")
        set_user_id(None)  # This shouldn't actually set None
        set_session_id(None)

        # Only correlation_id should be set
        assert get_correlation_id() == "test"
        assert get_user_id() is None
        assert get_session_id() is None

    def test_context_with_empty_strings(self):
        """Test context handling with empty strings"""
        set_correlation_id("")
        set_user_id("")

        # Empty strings should be set as-is
        assert get_correlation_id() == ""
        assert get_user_id() == ""

    def test_baggage_with_empty_dict(self):
        """Test baggage handling with empty dictionary"""
        set_baggage({})
        assert get_baggage() == {}

        # Adding to empty baggage
        add_baggage("key", "value")
        assert get_baggage() == {"key": "value"}

    def test_metadata_with_complex_types(self):
        """Test metadata with complex data types"""
        complex_metadata = {
            "string": "value",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "none": None,
        }

        set_metadata(complex_metadata)
        result = get_metadata()

        assert result == complex_metadata

    def test_trace_context_with_invalid_traceparent(self):
        """Test header extraction with invalid traceparent format"""
        headers = {"traceparent": "invalid-format"}

        result = extract_headers(headers)

        # Should handle gracefully with no extracted trace info
        assert result["trace_id"] is None
        assert result["span_id"] is None
        assert result["parent_span_id"] is None

    def test_trace_context_with_short_traceparent(self):
        """Test header extraction with short traceparent"""
        headers = {"traceparent": "00-123"}  # Too short

        result = extract_headers(headers)

        # Should handle gracefully
        assert result["trace_id"] is None
        assert result["span_id"] is None

    @pytest.mark.asyncio
    async def test_request_context_exception_handling(self):
        """Test request context cleanup on exceptions"""
        manager = ContextManager()

        # Verify context is cleared even if exception occurs
        with pytest.raises(ValueError):
            async with manager.request_context(correlation_id="exception-test"):
                assert get_correlation_id() == "exception-test"
                raise ValueError("Test exception")

        # Context should be cleared despite exception
        assert get_correlation_id() is None

    def test_trace_span_exception_handling(self):
        """Test trace span cleanup on exceptions"""
        manager = ContextManager()
        set_trace_id("exception-trace")
        set_span_id("original-span")

        original_span = get_span_id()

        with pytest.raises(RuntimeError):
            with manager.trace_span("exception_span"):
                new_span = get_span_id()
                assert new_span != original_span
                raise RuntimeError("Test exception")

        # Should restore original span context
        assert get_span_id() == original_span

    def test_context_manager_with_env_override(self):
        """Test ContextManager with environment variable override"""
        with patch.dict(
            "os.environ",
            {"GENESIS_SERVICE": "test-service", "GENESIS_ENV": "test-environment"},
        ):
            manager = ContextManager()

            assert manager.service_name == "test-service"
            assert manager.environment == "test-environment"

    def test_user_context_role_permission_edge_cases(self):
        """Test UserContext role/permission methods with edge cases"""
        # Test with empty lists
        user_context = UserContext(user_id="edge-user", roles=[], permissions=[])

        assert user_context.has_role("any") is False
        assert user_context.has_permission("any") is False

        # Test with None values (different from empty lists)
        user_context_none = UserContext(
            user_id="none-user", roles=None, permissions=None
        )

        assert user_context_none.has_role("any") is False
        assert user_context_none.has_permission("any") is False


class TestContextIntegration:
    """Test integration scenarios and real-world usage patterns"""

    def setup_method(self):
        """Clear context before each test"""
        get_context_manager().clear_context()

    def teardown_method(self):
        """Clear context after each test"""
        get_context_manager().clear_context()

    @pytest.mark.asyncio
    async def test_web_request_simulation(self):
        """Test simulating a complete web request flow"""
        manager = ContextManager()

        # Simulate incoming request with headers
        incoming_headers = {
            "X-Correlation-ID": "web-req-123",
            "X-User-ID": "user-456",
            "traceparent": "00-1234567890abcdef1234567890abcdef-fedcba0987654321-01",
            "baggage": "service=frontend,version=1.2.3",
        }

        # Extract context from headers
        context_info = extract_headers(incoming_headers)

        # Set up request context
        async with manager.request_context(
            correlation_id=context_info["correlation_id"],
            user_id=context_info["user_id"],
            trace_id=context_info["trace_id"],
            span_id=generate_span_id(),  # New span for this service
            parent_span_id=context_info["parent_span_id"],
            metadata={"endpoint": "/api/users", "method": "GET"},
        ) as request_context:

            # Simulate business logic with nested spans
            with manager.trace_span("validate_user"):
                await asyncio.sleep(0.001)  # Simulate validation

                # Add user context after validation
                set_user_context(
                    user_id=context_info["user_id"],
                    roles=["user", "premium"],
                    permissions=["read", "write"],
                )

            with manager.trace_span("fetch_data"):
                await asyncio.sleep(0.002)  # Simulate data fetch
                add_metadata("records_found", 42)

            # Generate headers for downstream service call
            downstream_headers = propagate_headers()

            # Verify complete context
            final_context = manager.get_current_context()

            assert final_context.correlation_id == "web-req-123"
            assert final_context.user_context.user_id == "user-456"
            assert final_context.user_context.has_role("premium")
            assert (
                final_context.trace_context.trace_id
                == "1234567890abcdef1234567890abcdef"
            )
            assert final_context.metadata["endpoint"] == "/api/users"
            assert final_context.metadata["records_found"] == 42

            # Verify downstream headers
            assert downstream_headers["X-Correlation-ID"] == "web-req-123"
            assert downstream_headers["X-User-ID"] == "user-456"
            assert "traceparent" in downstream_headers

    @pytest.mark.asyncio
    async def test_microservice_chain_simulation(self):
        """Test simulating context propagation across microservices"""
        manager = ContextManager()

        # Service A: Initial request
        async with manager.request_context(
            correlation_id="microservice-chain",
            user_id="chain-user",
            trace_id=generate_trace_id(),
        ):

            # Service A processing
            with manager.trace_span("service_a_processing"):
                service_a_headers = propagate_headers()

            # Service B: Extract context from Service A headers
            service_b_context = extract_headers(service_a_headers)

            # Clear current context to simulate new service
            manager.clear_context()

            # Service B setup
            async with manager.request_context(
                correlation_id=service_b_context["correlation_id"],
                user_id=service_b_context["user_id"],
                trace_id=service_b_context["trace_id"],
                span_id=generate_span_id(),
                parent_span_id=service_b_context["parent_span_id"],
            ):

                with manager.trace_span("service_b_processing"):
                    service_b_headers = propagate_headers()

                # Service C: Extract from Service B
                service_c_context = extract_headers(service_b_headers)

                # Verify chain continuity
                assert service_c_context["correlation_id"] == "microservice-chain"
                assert service_c_context["user_id"] == "chain-user"
                assert service_c_context["trace_id"] == service_b_context["trace_id"]

                # Verify parent-child relationships
                current_trace = get_trace_context()
                assert current_trace.trace_id == service_b_context["trace_id"]
                assert (
                    current_trace.parent_span_id == service_b_context["parent_span_id"]
                )

    def test_background_task_context_propagation(self):
        """Test context propagation to background tasks"""
        manager = ContextManager()

        # Set up main request context
        set_correlation_id("background-main")
        set_user_id("background-user")
        set_trace_id("background-trace")
        add_metadata("source", "main_request")

        # Copy context for background task
        background_context = manager.copy_context()

        def background_task():
            # Verify context is available
            assert get_correlation_id() == "background-main"
            assert get_user_id() == "background-user"
            assert get_trace_id() == "background-trace"
            assert get_metadata()["source"] == "main_request"

            # Add background-specific metadata
            add_metadata("background_task", "completed")

            return {"correlation_id": get_correlation_id(), "metadata": get_metadata()}

        # Run background task with propagated context
        result = background_context.run(background_task)

        # Verify background task had correct context
        assert result["correlation_id"] == "background-main"
        assert result["metadata"]["source"] == "main_request"
        assert result["metadata"]["background_task"] == "completed"

        # Verify main context unchanged
        assert get_metadata().get("background_task") is None

    @pytest.mark.asyncio
    async def test_error_handling_with_context(self):
        """Test context preservation during error handling"""
        manager = ContextManager()

        async with manager.request_context(
            correlation_id="error-handling", user_id="error-user"
        ):

            try:
                with manager.trace_span("error_prone_operation"):
                    # Simulate operation that fails
                    add_metadata("operation", "risky_business")
                    raise ValueError("Something went wrong")

            except ValueError as e:
                # Context should still be available for error handling
                error_context = manager.get_current_context()

                assert error_context.correlation_id == "error-handling"
                assert error_context.user_context.user_id == "error-user"
                assert error_context.metadata["operation"] == "risky_business"

                # Add error information to context
                add_metadata("error", str(e))
                add_metadata("error_type", type(e).__name__)

                # Generate headers for error reporting service
                error_headers = propagate_headers()

                assert error_headers["X-Correlation-ID"] == "error-handling"
                assert error_headers["X-User-ID"] == "error-user"

    def test_multi_tenant_context_isolation(self):
        """Test context isolation in multi-tenant scenarios"""
        manager = ContextManager()
        results = {}

        def process_tenant_request(tenant_id, user_id):
            set_correlation_id(f"tenant-{tenant_id}-req")
            set_user_context(
                user_id=user_id, tenant_id=tenant_id, organization_id=f"org-{tenant_id}"
            )

            # Simulate processing
            time.sleep(0.001)

            user_context = get_user_context()
            results[tenant_id] = {
                "correlation_id": get_correlation_id(),
                "user_id": user_context.user_id,
                "tenant_id": user_context.tenant_id,
                "organization_id": user_context.organization_id,
            }

        # Process requests for different tenants concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for tenant_id in ["tenant1", "tenant2", "tenant3"]:
                future = executor.submit(
                    process_tenant_request, tenant_id, f"user-{tenant_id}"
                )
                futures.append(future)

            # Wait for completion
            for future in futures:
                future.result()

        # Verify tenant isolation
        for tenant_id in ["tenant1", "tenant2", "tenant3"]:
            result = results[tenant_id]
            assert result["correlation_id"] == f"tenant-{tenant_id}-req"
            assert result["user_id"] == f"user-{tenant_id}"
            assert result["tenant_id"] == tenant_id
            assert result["organization_id"] == f"org-{tenant_id}"
