"""
Genesis Context Implementation

Provides thread-safe context management for distributed applications.
Supports request tracking, user sessions, and distributed tracing.
"""

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

# Import Genesis core components
from ..logging.logger import GenesisLogger

# Thread-local storage for context
_context_var: ContextVar[Optional["Context"]] = ContextVar(
    "genesis_context", default=None
)

# Module logger
logger = GenesisLogger(__name__)


@dataclass
class TraceContext:
    """Distributed tracing context"""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    flags: int = 0
    baggage: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def new_trace(cls) -> "TraceContext":
        """Create a new trace context"""
        return cls(
            trace_id=str(uuid.uuid4()).replace("-", ""),
            span_id=str(uuid.uuid4()).replace("-", "")[:16],
        )

    def new_span(self) -> "TraceContext":
        """Create a new span within this trace"""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=str(uuid.uuid4()).replace("-", "")[:16],
            parent_span_id=self.span_id,
            flags=self.flags,
            baggage=self.baggage.copy(),
        )


@dataclass
class UserContext:
    """User session context"""

    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    roles: list = field(default_factory=list)
    permissions: list = field(default_factory=list)
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestContext:
    """HTTP request context"""

    request_id: str
    method: Optional[str] = None
    path: Optional[str] = None
    remote_addr: Optional[str] = None
    user_agent: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def new_request(cls) -> "RequestContext":
        """Create a new request context"""
        return cls(request_id=str(uuid.uuid4()))


@dataclass
class Context:
    """
    Root context containing all contextual information

    This is the main context object that holds request, user,
    and trace information for the current execution context.
    """

    correlation_id: str
    service: str
    environment: str
    version: str = "unknown"
    request: Optional[RequestContext] = None
    user: Optional[UserContext] = None
    trace: Optional[TraceContext] = None
    custom: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def new_context(
        cls,
        service: str,
        environment: str,
        version: str = "unknown",
        correlation_id: Optional[str] = None,
    ) -> "Context":
        """Create a new context"""
        return cls(
            correlation_id=correlation_id or str(uuid.uuid4()),
            service=service,
            environment=environment,
            version=version,
        )

    def with_request(self, request: RequestContext) -> "Context":
        """Create a copy with request context"""
        new_context = Context(
            correlation_id=self.correlation_id,
            service=self.service,
            environment=self.environment,
            version=self.version,
            request=request,
            user=self.user,
            trace=self.trace,
            custom=self.custom.copy(),
            created_at=self.created_at,
        )
        return new_context

    def with_user(self, user: UserContext) -> "Context":
        """Create a copy with user context"""
        new_context = Context(
            correlation_id=self.correlation_id,
            service=self.service,
            environment=self.environment,
            version=self.version,
            request=self.request,
            user=user,
            trace=self.trace,
            custom=self.custom.copy(),
            created_at=self.created_at,
        )
        return new_context

    def with_trace(self, trace: TraceContext) -> "Context":
        """Create a copy with trace context"""
        new_context = Context(
            correlation_id=self.correlation_id,
            service=self.service,
            environment=self.environment,
            version=self.version,
            request=self.request,
            user=self.user,
            trace=trace,
            custom=self.custom.copy(),
            created_at=self.created_at,
        )
        return new_context

    def set_custom(self, key: str, value: Any) -> "Context":
        """Create a copy with custom value set"""
        new_custom = self.custom.copy()
        new_custom[key] = value

        new_context = Context(
            correlation_id=self.correlation_id,
            service=self.service,
            environment=self.environment,
            version=self.version,
            request=self.request,
            user=self.user,
            trace=self.trace,
            custom=new_custom,
            created_at=self.created_at,
        )
        return new_context

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        result = {
            "correlation_id": self.correlation_id,
            "service": self.service,
            "environment": self.environment,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "custom": self.custom,
        }

        if self.request:
            result["request"] = {
                "request_id": self.request.request_id,
                "method": self.request.method,
                "path": self.request.path,
                "remote_addr": self.request.remote_addr,
                "user_agent": self.request.user_agent,
                "start_time": self.request.start_time.isoformat(),
            }

        if self.user:
            result["user"] = {
                "user_id": self.user.user_id,
                "username": self.user.username,
                "email": self.user.email,
                "roles": self.user.roles,
                "session_id": self.user.session_id,
                "tenant_id": self.user.tenant_id,
            }

        if self.trace:
            result["trace"] = {
                "trace_id": self.trace.trace_id,
                "span_id": self.trace.span_id,
                "parent_span_id": self.trace.parent_span_id,
                "flags": self.trace.flags,
            }

        return result


class ContextManager:
    """
    Thread-safe context manager

    Manages context lifecycle and provides utilities for
    context propagation and manipulation.
    """

    def __init__(self):
        self._logger = GenesisLogger(f"{__name__}.ContextManager")

    def get_current_context(self) -> Optional[Context]:
        """Get the current context"""
        return _context_var.get()

    def set_context(self, context: Context) -> None:
        """Set the current context"""
        _context_var.set(context)
        self._logger.debug(
            "Context set",
            extra={
                "correlation_id": context.correlation_id,
                "service": context.service,
                "environment": context.environment,
            },
        )

    def clear_context(self) -> None:
        """Clear the current context"""
        _context_var.set(None)
        self._logger.debug("Context cleared")

    @contextmanager
    def context_span(self, context: Context):
        """
        Context manager for temporary context

        Usage:
            with context_manager.context_span(new_context):
                # Code runs with new_context
                pass
            # Original context is restored
        """
        original_context = self.get_current_context()

        try:
            self.set_context(context)
            yield context
        finally:
            if original_context:
                self.set_context(original_context)
            else:
                self.clear_context()

    def fork_context(self, **updates) -> Optional[Context]:
        """
        Create a new context based on the current one

        Args:
            **updates: Fields to update in the new context

        Returns:
            New context with updates applied, or None if no current context
        """
        current = self.get_current_context()
        if not current:
            return None

        # Create new context with same base values
        new_context = Context(
            correlation_id=updates.get("correlation_id", current.correlation_id),
            service=updates.get("service", current.service),
            environment=updates.get("environment", current.environment),
            version=updates.get("version", current.version),
            request=updates.get("request", current.request),
            user=updates.get("user", current.user),
            trace=updates.get("trace", current.trace),
            custom=updates.get("custom", current.custom.copy()),
            created_at=current.created_at,
        )

        return new_context

    def ensure_context(
        self, service: str, environment: str, version: str = "unknown"
    ) -> Context:
        """
        Ensure there is a current context, creating one if needed

        Args:
            service: Service name for new context
            environment: Environment for new context
            version: Version for new context

        Returns:
            Current context or newly created context
        """
        current = self.get_current_context()
        if current:
            return current

        new_context = Context.new_context(
            service=service,
            environment=environment,
            version=version,
        )
        self.set_context(new_context)
        return new_context


# Global context manager instance
_context_manager = ContextManager()


# Convenience functions
def get_context() -> Optional[Context]:
    """Get the current context"""
    return _context_manager.get_current_context()


def set_context(context: Context) -> None:
    """Set the current context"""
    _context_manager.set_context(context)


def clear_context() -> None:
    """Clear the current context"""
    _context_manager.clear_context()


@contextmanager
def context_span(context: Context):
    """
    Context manager for temporary context

    Usage:
        with context_span(new_context):
            # Code runs with new_context
            pass
        # Original context is restored
    """
    with _context_manager.context_span(context):
        yield context


def current_context() -> Optional[Context]:
    """Alias for get_context() for convenience"""
    return get_context()


def ensure_context(service: str, environment: str, version: str = "unknown") -> Context:
    """
    Ensure there is a current context, creating one if needed

    Args:
        service: Service name for new context
        environment: Environment for new context
        version: Version for new context

    Returns:
        Current context or newly created context
    """
    return _context_manager.ensure_context(service, environment, version)
