"""
Genesis Context Management - Simplified

Thread-safe context management for distributed applications using contextvars.
Provides correlation ID tracking, request context, and distributed tracing support.
"""

import uuid
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from genesis.core.constants import get_environment, get_service_name

# Context variables for thread-safe and async-safe storage
_current_context: ContextVar[Optional["RequestContext"]] = ContextVar(
    "current_context", default=None
)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_span_id: ContextVar[str | None] = ContextVar("span_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("user_id", default=None)
_metadata: ContextVar[dict[str, Any] | None] = ContextVar("metadata", default=None)


@dataclass
class TraceContext:
    """Distributed tracing context information."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    baggage: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "baggage": self.baggage,
        }

    def create_child_span(self) -> "TraceContext":
        """Create a child span context."""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=generate_span_id(),
            parent_span_id=self.span_id,
            baggage=self.baggage.copy(),
        )


@dataclass
class RequestContext:
    """Complete request context for distributed operations."""

    correlation_id: str
    request_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: str | None = None
    trace_context: TraceContext | None = None
    service: str = field(default_factory=lambda: get_service_name())
    environment: str = field(default_factory=lambda: get_environment())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        context_dict = {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "service": self.service,
            "environment": self.environment,
            "user_id": self.user_id,
            "metadata": self.metadata,
        }

        if self.trace_context:
            context_dict["trace"] = self.trace_context.to_dict()

        return context_dict

    def get_logger_context(self) -> dict[str, Any]:
        """Get context data formatted for logger."""
        logger_context = {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
        }

        if self.user_id:
            logger_context["user_id"] = self.user_id

        if self.trace_context:
            logger_context["trace_id"] = self.trace_context.trace_id
            logger_context["span_id"] = self.trace_context.span_id
            if self.trace_context.parent_span_id:
                logger_context["parent_span_id"] = self.trace_context.parent_span_id

        return logger_context

    @classmethod
    def create_new(
        cls,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "RequestContext":
        """Create a new request context with generated IDs."""
        return cls(
            correlation_id=generate_correlation_id(),
            request_id=generate_request_id(),
            user_id=user_id,
            metadata=metadata or {},
        )

    def with_trace(self, trace_context: TraceContext) -> "RequestContext":
        """Create a copy with trace context."""
        return RequestContext(
            correlation_id=self.correlation_id,
            request_id=self.request_id,
            timestamp=self.timestamp,
            user_id=self.user_id,
            trace_context=trace_context,
            service=self.service,
            environment=self.environment,
            metadata=self.metadata.copy(),
        )

    def with_user(self, user_id: str) -> "RequestContext":
        """Create a copy with user ID."""
        return RequestContext(
            correlation_id=self.correlation_id,
            request_id=self.request_id,
            timestamp=self.timestamp,
            user_id=user_id,
            trace_context=self.trace_context,
            service=self.service,
            environment=self.environment,
            metadata=self.metadata.copy(),
        )


class ContextManager:
    """
    Central context manager for handling request contexts.

    Provides thread-safe context storage and retrieval using contextvars.
    """

    def __init__(self, service_name: str, environment: str):
        if not service_name or not service_name.strip():
            raise ValueError("service_name is required and cannot be empty")
        if not environment or not environment.strip():
            raise ValueError("environment is required and cannot be empty")

        self.service_name = service_name.strip()
        self.environment = environment.strip()

    @classmethod
    def default(cls) -> "ContextManager":
        """Create ContextManager with values from environment variables."""
        from genesis.core.constants import get_environment, get_service_name

        return cls(
            service_name=get_service_name(),
            environment=get_environment(),
        )

    def get_current_context(self) -> RequestContext | None:
        """Get the current request context."""
        return _current_context.get()

    def set_current_context(self, context: RequestContext) -> None:
        """Set the current request context."""
        _current_context.set(context)
        # Also set individual context variables for backwards compatibility
        _correlation_id.set(context.correlation_id)
        _request_id.set(context.request_id)
        if context.user_id:
            _user_id.set(context.user_id)
        if context.trace_context:
            _trace_id.set(context.trace_context.trace_id)
            _span_id.set(context.trace_context.span_id)
        _metadata.set(context.metadata)

    def clear_current_context(self) -> None:
        """Clear the current request context."""
        _current_context.set(None)
        _correlation_id.set(None)
        _request_id.set(None)
        _trace_id.set(None)
        _span_id.set(None)
        _user_id.set(None)
        _metadata.set(None)

    def create_context(
        self,
        correlation_id: str | None = None,
        request_id: str | None = None,
        user_id: str | None = None,
        trace_context: TraceContext | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RequestContext:
        """Create a new request context."""
        return RequestContext(
            correlation_id=correlation_id or generate_correlation_id(),
            request_id=request_id or generate_request_id(),
            user_id=user_id,
            trace_context=trace_context,
            service=self.service_name,
            environment=self.environment,
            metadata=metadata or {},
        )

    @contextmanager
    def context_scope(
        self, context: RequestContext
    ) -> Generator[RequestContext, None, None]:
        """Context manager for scoped context execution."""
        # Save current context
        previous_context = self.get_current_context()

        try:
            # Set new context
            self.set_current_context(context)
            yield context
        finally:
            # Restore previous context
            if previous_context:
                self.set_current_context(previous_context)
            else:
                self.clear_current_context()


# Global context manager instance
_context_manager: ContextManager | None = None


def get_context_manager() -> ContextManager:
    """Get the global context manager instance."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager(
            service_name=get_service_name(),
            environment=get_environment(),
        )
    return _context_manager


# Convenience functions for direct context access
def get_context() -> RequestContext | None:
    """Get the current request context."""
    return get_context_manager().get_current_context()


def set_context(context: RequestContext) -> None:
    """Set the current request context."""
    get_context_manager().set_current_context(context)


def clear_context() -> None:
    """Clear the current request context."""
    get_context_manager().clear_current_context()


@contextmanager
def context_span(context: RequestContext) -> Generator[RequestContext, None, None]:
    """Context manager for scoped context execution."""
    with get_context_manager().context_scope(context) as ctx:
        yield ctx


# Individual context variable accessors
def get_correlation_id() -> str | None:
    """Get current correlation ID."""
    context = get_context()
    if context:
        return context.correlation_id
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set current correlation ID."""
    _correlation_id.set(correlation_id)
    # If we have a context, update it too
    context = get_context()
    if context:
        context.correlation_id = correlation_id


def get_request_id() -> str | None:
    """Get current request ID."""
    context = get_context()
    if context:
        return context.request_id
    return _request_id.get()


def get_trace_id() -> str | None:
    """Get current trace ID."""
    context = get_context()
    if context and context.trace_context:
        return context.trace_context.trace_id
    return _trace_id.get()


def get_user_id() -> str | None:
    """Get current user ID."""
    context = get_context()
    if context:
        return context.user_id
    return _user_id.get()


def get_metadata() -> dict[str, Any]:
    """Get current metadata."""
    context = get_context()
    if context:
        return context.metadata
    return _metadata.get() or {}


# ID generation functions
def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def generate_request_id() -> str:
    """Generate a new request ID."""
    return f"req_{uuid.uuid4().hex[:12]}"


def generate_trace_id() -> str:
    """Generate a new trace ID."""
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """Generate a new span ID."""
    return uuid.uuid4().hex[:16]
