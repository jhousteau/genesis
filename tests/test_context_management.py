"""
Comprehensive tests for Genesis context management.
"""

import pytest
import threading
import asyncio
from datetime import datetime
from unittest.mock import patch

from genesis.core.context import (
    RequestContext,
    TraceContext,
    ContextManager,
    get_context,
    set_context,
    clear_context,
    context_span,
    get_correlation_id,
    set_correlation_id,
    generate_correlation_id,
    generate_request_id,
)


@pytest.fixture(autouse=True)
def clear_context_before_test():
    """Ensure clean context state before each test."""
    clear_context()
    yield
    clear_context()


class TestTraceContext:
    """Test TraceContext functionality."""

    def test_trace_context_creation(self):
        """Test creating trace context."""
        trace = TraceContext(
            trace_id="trace123",
            span_id="span456",
            parent_span_id="parent789",
            baggage={"key": "value"}
        )
        
        assert trace.trace_id == "trace123"
        assert trace.span_id == "span456"
        assert trace.parent_span_id == "parent789"
        assert trace.baggage == {"key": "value"}

    def test_trace_context_to_dict(self):
        """Test trace context serialization."""
        trace = TraceContext(
            trace_id="trace123",
            span_id="span456"
        )
        
        trace_dict = trace.to_dict()
        
        assert trace_dict['trace_id'] == "trace123"
        assert trace_dict['span_id'] == "span456"
        assert trace_dict['parent_span_id'] is None
        assert trace_dict['baggage'] == {}

    def test_create_child_span(self):
        """Test creating child span from trace context."""
        parent_trace = TraceContext(
            trace_id="trace123",
            span_id="span456",
            baggage={"key": "value"}
        )
        
        child_trace = parent_trace.create_child_span()
        
        assert child_trace.trace_id == "trace123"  # Same trace
        assert child_trace.span_id != "span456"   # New span ID
        assert child_trace.parent_span_id == "span456"  # Parent span set
        assert child_trace.baggage == {"key": "value"}  # Baggage copied


class TestRequestContext:
    """Test RequestContext functionality."""

    def test_request_context_creation(self):
        """Test creating request context."""
        with patch.dict('os.environ', {'GENESIS_SERVICE': 'test-service', 'GENESIS_ENV': 'test'}):
            context = RequestContext(
                correlation_id="corr123",
                request_id="req456",
                user_id="user789"
            )
            
            assert context.correlation_id == "corr123"
            assert context.request_id == "req456"
            assert context.user_id == "user789"
            assert context.service == "test-service"
            assert context.environment == "test"
            assert isinstance(context.timestamp, datetime)
            assert context.metadata == {}

    def test_request_context_to_dict(self):
        """Test request context serialization."""
        trace = TraceContext(trace_id="trace123", span_id="span456")
        context = RequestContext(
            correlation_id="corr123",
            request_id="req456",
            user_id="user789",
            trace_context=trace,
            metadata={"key": "value"}
        )
        
        context_dict = context.to_dict()
        
        assert context_dict['correlation_id'] == "corr123"
        assert context_dict['request_id'] == "req456"
        assert context_dict['user_id'] == "user789"
        assert 'trace' in context_dict
        assert context_dict['trace']['trace_id'] == "trace123"
        assert context_dict['metadata'] == {"key": "value"}

    def test_request_context_logger_context(self):
        """Test request context logger formatting."""
        trace = TraceContext(
            trace_id="trace123",
            span_id="span456",
            parent_span_id="parent789"
        )
        context = RequestContext(
            correlation_id="corr123",
            request_id="req456",
            user_id="user789",
            trace_context=trace
        )
        
        logger_context = context.get_logger_context()
        
        assert logger_context['correlation_id'] == "corr123"
        assert logger_context['request_id'] == "req456"
        assert logger_context['user_id'] == "user789"
        assert logger_context['trace_id'] == "trace123"
        assert logger_context['span_id'] == "span456"
        assert logger_context['parent_span_id'] == "parent789"

    def test_create_new_context(self):
        """Test creating new request context with generated IDs."""
        context = RequestContext.create_new(
            user_id="user123",
            metadata={"key": "value"}
        )
        
        assert context.correlation_id is not None
        assert context.request_id is not None
        assert context.user_id == "user123"
        assert context.metadata == {"key": "value"}
        assert len(context.correlation_id) == 36  # UUID format
        assert context.request_id.startswith("req_")

    def test_context_with_trace(self):
        """Test adding trace context to request context."""
        original_context = RequestContext.create_new()
        trace = TraceContext(trace_id="trace123", span_id="span456")
        
        context_with_trace = original_context.with_trace(trace)
        
        assert context_with_trace.correlation_id == original_context.correlation_id
        assert context_with_trace.trace_context == trace
        assert context_with_trace is not original_context  # New instance

    def test_context_with_user(self):
        """Test adding user to request context."""
        original_context = RequestContext.create_new()
        
        context_with_user = original_context.with_user("user123")
        
        assert context_with_user.correlation_id == original_context.correlation_id
        assert context_with_user.user_id == "user123"
        assert context_with_user is not original_context  # New instance


class TestContextManager:
    """Test ContextManager functionality."""

    def test_context_manager_creation(self):
        """Test creating context manager."""
        manager = ContextManager(service_name="test-service", environment="test")
        
        assert manager.service_name == "test-service"
        assert manager.environment == "test"

    def test_get_set_clear_context(self):
        """Test basic context operations."""
        manager = ContextManager()
        context = RequestContext.create_new()
        
        # Initially no context
        assert manager.get_current_context() is None
        
        # Set context
        manager.set_current_context(context)
        current = manager.get_current_context()
        assert current == context
        
        # Clear context
        manager.clear_current_context()
        assert manager.get_current_context() is None

    def test_create_context(self):
        """Test creating context through manager."""
        manager = ContextManager(service_name="test-service", environment="test")
        
        context = manager.create_context(
            correlation_id="corr123",
            user_id="user456",
            metadata={"key": "value"}
        )
        
        assert context.correlation_id == "corr123"
        assert context.user_id == "user456"
        assert context.service == "test-service"
        assert context.environment == "test"
        assert context.metadata == {"key": "value"}

    def test_context_scope(self):
        """Test context scope manager."""
        manager = ContextManager()
        outer_context = RequestContext.create_new(user_id="outer_user")
        inner_context = RequestContext.create_new(user_id="inner_user")
        
        # Set outer context
        manager.set_current_context(outer_context)
        
        # Use inner context in scope
        with manager.context_scope(inner_context) as scoped_context:
            assert scoped_context == inner_context
            assert manager.get_current_context() == inner_context
        
        # Should restore outer context
        assert manager.get_current_context() == outer_context

    def test_context_scope_nesting(self):
        """Test nested context scopes."""
        manager = ContextManager()
        
        ctx1 = RequestContext.create_new(user_id="user1")
        ctx2 = RequestContext.create_new(user_id="user2")
        ctx3 = RequestContext.create_new(user_id="user3")
        
        with manager.context_scope(ctx1):
            assert manager.get_current_context().user_id == "user1"
            
            with manager.context_scope(ctx2):
                assert manager.get_current_context().user_id == "user2"
                
                with manager.context_scope(ctx3):
                    assert manager.get_current_context().user_id == "user3"
                
                assert manager.get_current_context().user_id == "user2"
            
            assert manager.get_current_context().user_id == "user1"
        
        assert manager.get_current_context() is None


class TestConvenienceFunctions:
    """Test convenience functions for context access."""

    def test_global_context_functions(self):
        """Test global get/set/clear context functions."""
        context = RequestContext.create_new(user_id="test_user")
        
        # Initially no context
        assert get_context() is None
        
        # Set context
        set_context(context)
        current = get_context()
        assert current == context
        assert current.user_id == "test_user"
        
        # Clear context
        clear_context()
        assert get_context() is None

    def test_context_span_function(self):
        """Test context_span convenience function."""
        context = RequestContext.create_new(user_id="span_user")
        
        assert get_context() is None
        
        with context_span(context) as span_context:
            assert span_context == context
            assert get_context() == context
        
        assert get_context() is None

    def test_correlation_id_functions(self):
        """Test correlation ID convenience functions."""
        # Test without context
        assert get_correlation_id() is None
        
        set_correlation_id("corr123")
        assert get_correlation_id() == "corr123"
        
        # Test with context
        context = RequestContext.create_new()
        set_context(context)
        
        # Should get correlation ID from context
        assert get_correlation_id() == context.correlation_id
        
        clear_context()


class TestIDGeneration:
    """Test ID generation functions."""

    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        corr_id = generate_correlation_id()
        
        assert corr_id is not None
        assert len(corr_id) == 36  # UUID format
        assert '-' in corr_id  # UUID contains hyphens
        
        # Should generate unique IDs
        corr_id2 = generate_correlation_id()
        assert corr_id != corr_id2

    def test_generate_request_id(self):
        """Test request ID generation."""
        req_id = generate_request_id()
        
        assert req_id is not None
        assert req_id.startswith("req_")
        assert len(req_id) == 16  # req_ + 12 hex chars
        
        # Should generate unique IDs
        req_id2 = generate_request_id()
        assert req_id != req_id2


class TestThreadSafety:
    """Test thread safety of context management."""

    def test_context_isolation_between_threads(self):
        """Test that contexts are isolated between threads."""
        results = {}
        
        def thread_function(thread_id: str):
            context = RequestContext.create_new(user_id=f"user_{thread_id}")
            set_context(context)
            
            # Store the context for verification
            results[thread_id] = get_context()
        
        threads = []
        for i in range(3):
            thread = threading.Thread(target=thread_function, args=[str(i)])
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Each thread should have its own context
        assert len(results) == 3
        for i in range(3):
            context = results[str(i)]
            assert context.user_id == f"user_{i}"
        
        # All contexts should be different
        contexts = list(results.values())
        assert contexts[0] != contexts[1]
        assert contexts[1] != contexts[2]

    def test_correlation_id_thread_safety(self):
        """Test correlation ID thread safety."""
        results = {}
        
        def thread_function(thread_id: str):
            correlation_id = f"corr_{thread_id}"
            set_correlation_id(correlation_id)
            results[thread_id] = get_correlation_id()
        
        threads = []
        for i in range(3):
            thread = threading.Thread(target=thread_function, args=[str(i)])
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Each thread should have its own correlation ID
        for i in range(3):
            assert results[str(i)] == f"corr_{i}"


class TestAsyncSupport:
    """Test async support for context management."""

    @pytest.mark.asyncio
    async def test_async_context_isolation(self):
        """Test that contexts work properly with async/await."""
        async def async_function(user_id: str) -> str:
            context = RequestContext.create_new(user_id=user_id)
            set_context(context)
            
            # Simulate async operation
            await asyncio.sleep(0.01)
            
            current_context = get_context()
            return current_context.user_id if current_context else None
        
        # Run multiple async operations concurrently
        tasks = [
            async_function("user1"),
            async_function("user2"),
            async_function("user3")
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Each async operation should maintain its own context
        assert "user1" in results
        assert "user2" in results
        assert "user3" in results
        assert len(set(results)) == 3  # All different

    @pytest.mark.asyncio
    async def test_async_context_span(self):
        """Test context span with async operations."""
        context = RequestContext.create_new(user_id="async_user")
        
        with context_span(context):
            # Simulate async work
            await asyncio.sleep(0.01)
            
            current = get_context()
            assert current == context
            assert current.user_id == "async_user"
        
        assert get_context() is None


class TestContextIntegration:
    """Test context integration with other systems."""

    def test_context_with_error_framework_integration(self):
        """Test that context can be used with error framework."""
        # This is a basic integration test
        # Full integration will be tested in the integration tests
        from genesis.core.errors import ErrorContext, handle_error
        
        # Create request context
        request_context = RequestContext.create_new(user_id="test_user")
        set_context(request_context)
        
        # Create error context from request context
        error_context = ErrorContext.create_default()
        error_context.correlation_id = request_context.correlation_id
        error_context.user_id = request_context.user_id
        
        # Handle error with context
        error = ValueError("Test error")
        handled = handle_error(error, error_context)
        
        assert handled.context.correlation_id == request_context.correlation_id
        assert handled.context.user_id == request_context.user_id

    def test_context_metadata_handling(self):
        """Test context metadata functionality."""
        context = RequestContext.create_new(metadata={"initial": "value"})
        set_context(context)
        
        # Add metadata
        context.metadata["runtime"] = "added"
        context.metadata["count"] = 42
        
        retrieved_context = get_context()
        assert retrieved_context.metadata["initial"] == "value"
        assert retrieved_context.metadata["runtime"] == "added"
        assert retrieved_context.metadata["count"] == 42