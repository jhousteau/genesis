"""Genesis Context Management - Python Implementation

Thread-safe context management for distributed applications using contextvars.
Provides correlation ID tracking, request context, and distributed tracing support.
"""

import os
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass
class TraceContext:
    """Distributed tracing context"""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    baggage: dict[str, str] | None = None


@dataclass
class RequestContext:
    """Request context with correlation tracking"""

    correlation_id: str
    request_id: str
    timestamp: datetime
    service: str
    environment: str
    metadata: dict[str, Any] = field(default_factory=dict)
    user_id: str | None = None
    trace_context: TraceContext | None = None


# Context variable for storing request context
_request_context: ContextVar[RequestContext | None] = ContextVar(
    "request_context", default=None
)


class ContextManager:
    """Thread-safe context manager using contextvars"""

    def __init__(self, service_name: str = "genesis", environment: str = "development"):
        self.service_name = service_name
        self.environment = environment

    def get_current_context(self) -> RequestContext | None:
        """Get current request context"""
        return _request_context.get()

    def set_current_context(self, context: RequestContext) -> None:
        """Set current request context"""
        _request_context.set(context)

    def clear_current_context(self) -> None:
        """Clear current request context"""
        _request_context.set(None)

    def context_scope(self, context: RequestContext, fn: Callable[[], T]) -> T:
        """Execute function within context scope"""
        token = _request_context.set(context)
        try:
            return fn()
        finally:
            _request_context.reset(token)

    async def context_scope_async(
        self, context: RequestContext, fn: Callable[[], T]
    ) -> T:
        """Execute async function within context scope"""
        token = _request_context.set(context)
        try:
            return await fn()
        finally:
            _request_context.reset(token)


# Global context manager instance
_global_context_manager: ContextManager | None = None


def get_context_manager() -> ContextManager:
    """Get global context manager instance"""
    global _global_context_manager
    if _global_context_manager is None:
        _global_context_manager = ContextManager(
            service_name=os.environ.get("SERVICE", "genesis"),
            environment=os.environ.get("ENV", "development"),
        )
    return _global_context_manager


# Convenience functions for direct context access
def get_context() -> RequestContext | None:
    """Get current request context"""
    return get_context_manager().get_current_context()


def set_context(context: RequestContext) -> None:
    """Set current request context"""
    get_context_manager().set_current_context(context)


def clear_context() -> None:
    """Clear current request context"""
    get_context_manager().clear_current_context()


def context_span(context: RequestContext, fn: Callable[[], T]) -> T:
    """Execute function within context scope"""
    return get_context_manager().context_scope(context, fn)


async def context_span_async(context: RequestContext, fn: Callable[[], T]) -> T:
    """Execute async function within context scope"""
    return await get_context_manager().context_scope_async(context, fn)


# Individual context variable accessors
def get_correlation_id() -> str | None:
    """Get correlation ID from current context"""
    context = get_context()
    return context.correlation_id if context else None


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in current context"""
    context = get_context()
    if context:
        context.correlation_id = correlation_id


def get_request_id() -> str | None:
    """Get request ID from current context"""
    context = get_context()
    return context.request_id if context else None


def get_trace_id() -> str | None:
    """Get trace ID from current context"""
    context = get_context()
    return context.trace_context.trace_id if context and context.trace_context else None


def get_user_id() -> str | None:
    """Get user ID from current context"""
    context = get_context()
    return context.user_id if context else None


def get_metadata() -> dict[str, Any]:
    """Get metadata from current context"""
    context = get_context()
    return context.metadata if context else {}


# Context generation utilities
def generate_correlation_id() -> str:
    """Generate new correlation ID"""
    return str(uuid.uuid4())


def generate_request_id() -> str:
    """Generate new request ID"""
    return str(uuid.uuid4())


def generate_trace_id() -> str:
    """Generate new trace ID"""
    return str(uuid.uuid4())


def generate_span_id() -> str:
    """Generate new span ID"""
    return str(uuid.uuid4())


def create_request_context(
    correlation_id: str | None = None,
    request_id: str | None = None,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    trace_context: TraceContext | None = None,
) -> RequestContext:
    """Create new request context with generated IDs"""
    manager = get_context_manager()

    return RequestContext(
        correlation_id=correlation_id or generate_correlation_id(),
        request_id=request_id or generate_request_id(),
        timestamp=datetime.utcnow(),
        service=manager.service_name,
        environment=manager.environment,
        metadata=metadata or {},
        user_id=user_id,
        trace_context=trace_context,
    )


def create_trace_context(
    trace_id: str | None = None,
    parent_span_id: str | None = None,
    baggage: dict[str, str] | None = None,
) -> TraceContext:
    """Create new trace context"""
    return TraceContext(
        trace_id=trace_id or generate_trace_id(),
        span_id=generate_span_id(),
        parent_span_id=parent_span_id,
        baggage=baggage,
    )


def enrich_context(**kwargs: Any) -> None:
    """Add metadata to current context"""
    context = get_context()
    if context:
        context.metadata.update(kwargs)


def context_to_dict() -> dict[str, Any] | None:
    """Convert current context to dictionary"""
    context = get_context()
    if not context:
        return None

    result = {
        "correlation_id": context.correlation_id,
        "request_id": context.request_id,
        "timestamp": context.timestamp.isoformat(),
        "service": context.service,
        "environment": context.environment,
        "metadata": context.metadata,
    }

    if context.user_id:
        result["user_id"] = context.user_id

    if context.trace_context:
        result["trace_context"] = {
            "trace_id": context.trace_context.trace_id,
            "span_id": context.trace_context.span_id,
            "parent_span_id": context.trace_context.parent_span_id,
            "baggage": context.trace_context.baggage,
        }

    return result


def get_logger_context() -> dict[str, Any]:
    """Get context for logging purposes"""
    context = get_context()
    if not context:
        return {}

    logger_context = {
        "correlation_id": context.correlation_id,
        "request_id": context.request_id,
        "service": context.service,
        "environment": context.environment,
    }

    if context.user_id:
        logger_context["user_id"] = context.user_id

    if context.trace_context:
        logger_context["trace_id"] = context.trace_context.trace_id
        logger_context["span_id"] = context.trace_context.span_id

    return logger_context
