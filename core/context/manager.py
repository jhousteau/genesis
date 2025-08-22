"""
Genesis Context Management Implementation

Following CRAFT methodology:
- Create: Clean architecture with contextvars for thread/async safety
- Refactor: Modular design with clear separation of concerns
- Authenticate: Secure context handling with proper isolation
- Function: High-performance context operations with minimal overhead
- Test: Comprehensive integration with existing Genesis systems

Provides production-ready context propagation for distributed systems.
"""

import os
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar, copy_context
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from core.errors.handler import ErrorCategory, GenesisError
from core.logging.logger import get_logger

# Context variables for thread-safe and async-safe storage
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_session_id: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_span_id: ContextVar[Optional[str]] = ContextVar("span_id", default=None)
_parent_span_id: ContextVar[Optional[str]] = ContextVar("parent_span_id", default=None)
_baggage: ContextVar[Dict[str, str]] = ContextVar("baggage", default_factory=dict)
_metadata: ContextVar[Dict[str, Any]] = ContextVar("metadata", default_factory=dict)


@dataclass
class CorrelationID:
    """
    Correlation ID with metadata

    Tracks request flow across services and provides
    debugging information for distributed tracing.
    """

    id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    service: str = field(
        default_factory=lambda: os.environ.get("GENESIS_SERVICE", "genesis")
    )
    environment: str = field(
        default_factory=lambda: os.environ.get("GENESIS_ENV", "development")
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() + "Z",
            "service": self.service,
            "environment": self.environment,
        }


@dataclass
class UserContext:
    """
    User context information

    Stores user-related context that needs to be
    propagated across service boundaries.
    """

    user_id: str
    session_id: Optional[str] = None
    roles: Optional[list] = None
    permissions: Optional[list] = None
    tenant_id: Optional[str] = None
    organization_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "roles": self.roles or [],
            "permissions": self.permissions or [],
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "metadata": self.metadata,
        }

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return self.roles is not None and role in self.roles

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        return self.permissions is not None and permission in self.permissions


@dataclass
class TraceContext:
    """
    Distributed tracing context

    Compatible with OpenTelemetry and other tracing systems.
    Provides trace and span IDs for request correlation.
    """

    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: int = 0
    trace_state: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "trace_flags": self.trace_flags,
            "trace_state": self.trace_state,
            "baggage": self.baggage,
        }

    def create_child_span(self) -> "TraceContext":
        """Create a child span context"""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=generate_span_id(),
            parent_span_id=self.span_id,
            trace_flags=self.trace_flags,
            trace_state=self.trace_state,
            baggage=self.baggage.copy(),
        )


@dataclass
class RequestContext:
    """
    Complete request context

    Aggregates all context information for a request,
    providing a comprehensive view of the execution context.
    """

    correlation_id: str
    request_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_context: Optional[UserContext] = None
    trace_context: Optional[TraceContext] = None
    service: str = field(
        default_factory=lambda: os.environ.get("GENESIS_SERVICE", "genesis")
    )
    environment: str = field(
        default_factory=lambda: os.environ.get("GENESIS_ENV", "development")
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        context_dict = {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat() + "Z",
            "service": self.service,
            "environment": self.environment,
            "metadata": self.metadata,
        }

        if self.user_context:
            context_dict["user"] = self.user_context.to_dict()

        if self.trace_context:
            context_dict["trace"] = self.trace_context.to_dict()

        return context_dict

    def get_logger_context(self) -> Dict[str, Any]:
        """Get context data formatted for logger"""
        logger_context = {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
        }

        if self.user_context:
            logger_context["user_id"] = self.user_context.user_id
            if self.user_context.session_id:
                logger_context["session_id"] = self.user_context.session_id

        if self.trace_context:
            logger_context["trace_id"] = self.trace_context.trace_id
            logger_context["span_id"] = self.trace_context.span_id
            if self.trace_context.parent_span_id:
                logger_context["parent_span_id"] = self.trace_context.parent_span_id

        return logger_context


class ContextManager:
    """
    Central context manager for Genesis platform

    Provides thread-safe and async-safe context management using
    Python's contextvars. Integrates with logging and error handling.
    """

    def __init__(
        self,
        service_name: str = None,
        environment: str = None,
        auto_generate_ids: bool = True,
    ):
        """
        Initialize context manager

        Args:
            service_name: Name of the service
            environment: Environment (development, staging, production)
            auto_generate_ids: Whether to auto-generate missing IDs
        """
        self.service_name = service_name or os.environ.get("GENESIS_SERVICE", "genesis")
        self.environment = environment or os.environ.get("GENESIS_ENV", "development")
        self.auto_generate_ids = auto_generate_ids
        self.logger = get_logger(f"ContextManager.{self.service_name}")

    @asynccontextmanager
    async def request_context(
        self,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Async context manager for request context

        Sets up complete request context and ensures proper cleanup.
        All operations within this context will have access to the context data.

        Args:
            correlation_id: Unique correlation ID for request tracking
            request_id: Unique request ID
            user_id: User ID if authenticated
            session_id: Session ID if applicable
            trace_id: Distributed trace ID
            span_id: Current span ID
            parent_span_id: Parent span ID for hierarchical tracing
            metadata: Additional context metadata

        Usage:
            async with context_manager.request_context(correlation_id="abc-123"):
                # All operations here will have the context
                logger.info("Processing request")
        """
        # Generate missing IDs if enabled
        if self.auto_generate_ids:
            correlation_id = correlation_id or generate_correlation_id()
            request_id = request_id or generate_correlation_id()
            if trace_id and not span_id:
                span_id = generate_span_id()

        # Store previous context values
        previous_values = {
            "correlation_id": _correlation_id.get(None),
            "request_id": _request_id.get(None),
            "user_id": _user_id.get(None),
            "session_id": _session_id.get(None),
            "trace_id": _trace_id.get(None),
            "span_id": _span_id.get(None),
            "parent_span_id": _parent_span_id.get(None),
            "metadata": _metadata.get({}).copy(),
        }

        try:
            # Set context variables
            if correlation_id:
                _correlation_id.set(correlation_id)
            if request_id:
                _request_id.set(request_id)
            if user_id:
                _user_id.set(user_id)
            if session_id:
                _session_id.set(session_id)
            if trace_id:
                _trace_id.set(trace_id)
            if span_id:
                _span_id.set(span_id)
            if parent_span_id:
                _parent_span_id.set(parent_span_id)
            if metadata:
                current_metadata = _metadata.get({}).copy()
                current_metadata.update(metadata)
                _metadata.set(current_metadata)

            self.logger.debug(
                "Request context initialized",
                correlation_id=correlation_id,
                request_id=request_id,
                user_id=user_id,
                trace_id=trace_id,
            )

            yield self.get_current_context()

        finally:
            # Restore previous context values
            for var_name, previous_value in previous_values.items():
                context_var = globals()[f"_{var_name}"]
                if previous_value is not None:
                    context_var.set(previous_value)
                else:
                    # Reset to default
                    try:
                        context_var.delete()
                    except LookupError:
                        pass

            self.logger.debug("Request context cleaned up")

    @contextmanager
    def trace_span(
        self,
        span_name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for creating trace spans

        Creates a new span within the current trace context.
        Useful for tracking operations within a request.

        Args:
            span_name: Name of the span operation
            trace_id: Trace ID (uses current if not provided)
            parent_span_id: Parent span ID (uses current span as parent)
            metadata: Additional span metadata

        Usage:
            with context_manager.trace_span("database_query"):
                # Database operation here
                result = await db.query("SELECT * FROM users")
        """
        # Get or generate trace context
        current_trace_id = trace_id or get_trace_id()
        if not current_trace_id:
            if self.auto_generate_ids:
                current_trace_id = generate_trace_id()
                _trace_id.set(current_trace_id)
            else:
                raise GenesisError(
                    "No trace ID available and auto-generation disabled",
                    code="TRACE_CONTEXT_MISSING",
                    category=ErrorCategory.CONFIGURATION,
                )

        # Create new span
        new_span_id = generate_span_id()
        current_span_id = parent_span_id or get_span_id()

        # Store previous span context
        previous_span_id = _span_id.get(None)
        previous_parent_span_id = _parent_span_id.get(None)

        try:
            # Set new span context
            _span_id.set(new_span_id)
            if current_span_id:
                _parent_span_id.set(current_span_id)

            # Add span metadata
            if metadata:
                current_metadata = _metadata.get({}).copy()
                span_metadata = {
                    f"span.{key}": value for key, value in metadata.items()
                }
                current_metadata.update(span_metadata)
                _metadata.set(current_metadata)

            self.logger.debug(
                f"Started trace span: {span_name}",
                trace_id=current_trace_id,
                span_id=new_span_id,
                parent_span_id=current_span_id,
            )

            span_start_time = time.time()

            try:
                yield TraceContext(
                    trace_id=current_trace_id,
                    span_id=new_span_id,
                    parent_span_id=current_span_id,
                )
            finally:
                span_duration_ms = (time.time() - span_start_time) * 1000
                self.logger.debug(
                    f"Completed trace span: {span_name}",
                    trace_id=current_trace_id,
                    span_id=new_span_id,
                    duration_ms=round(span_duration_ms, 2),
                )

        finally:
            # Restore previous span context
            if previous_span_id is not None:
                _span_id.set(previous_span_id)
            else:
                try:
                    _span_id.delete()
                except LookupError:
                    pass

            if previous_parent_span_id is not None:
                _parent_span_id.set(previous_parent_span_id)
            else:
                try:
                    _parent_span_id.delete()
                except LookupError:
                    pass

    def get_current_context(self) -> Optional[RequestContext]:
        """
        Get the current request context

        Returns:
            RequestContext if context is set, None otherwise
        """
        correlation_id = get_correlation_id()
        request_id = get_request_id()

        if not correlation_id:
            return None

        # Build user context if available
        user_context = None
        user_id = get_user_id()
        if user_id:
            user_context = UserContext(
                user_id=user_id,
                session_id=get_session_id(),
            )

        # Build trace context if available
        trace_context = None
        trace_id = get_trace_id()
        if trace_id:
            trace_context = TraceContext(
                trace_id=trace_id,
                span_id=get_span_id() or generate_span_id(),
                parent_span_id=get_parent_span_id(),
                baggage=_baggage.get({}).copy(),
            )

        return RequestContext(
            correlation_id=correlation_id,
            request_id=request_id or correlation_id,
            user_context=user_context,
            trace_context=trace_context,
            service=self.service_name,
            environment=self.environment,
            metadata=_metadata.get({}).copy(),
        )

    def copy_context(self):
        """
        Copy the current context for use in other threads or tasks

        Returns:
            Context copy that can be used with contextvars.copy_context().run()
        """
        return copy_context()

    def clear_context(self):
        """Clear all context variables"""
        context_vars = [
            _correlation_id,
            _request_id,
            _user_id,
            _session_id,
            _trace_id,
            _span_id,
            _parent_span_id,
            _baggage,
            _metadata,
        ]

        for var in context_vars:
            try:
                var.delete()
            except LookupError:
                pass

        self.logger.debug("Context cleared")


# ID Generation Functions
def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID

    Uses UUID4 with timestamp prefix for better readability
    and uniqueness guarantees.

    Returns:
        Unique correlation ID string
    """
    timestamp = int(time.time() * 1000)  # milliseconds
    uuid_part = str(uuid.uuid4()).replace("-", "")[:16]
    return f"req_{timestamp}_{uuid_part}"


def generate_trace_id() -> str:
    """
    Generate a trace ID compatible with OpenTelemetry

    Returns:
        32-character hexadecimal trace ID
    """
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """
    Generate a span ID compatible with OpenTelemetry

    Returns:
        16-character hexadecimal span ID
    """
    return uuid.uuid4().hex[:16]


# Context Access Functions
def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID"""
    return _correlation_id.get(None)


def set_correlation_id(correlation_id: str):
    """Set the correlation ID"""
    _correlation_id.set(correlation_id)


def get_request_id() -> Optional[str]:
    """Get the current request ID"""
    return _request_id.get(None)


def set_request_id(request_id: str):
    """Set the request ID"""
    _request_id.set(request_id)


def get_user_id() -> Optional[str]:
    """Get the current user ID"""
    return _user_id.get(None)


def set_user_id(user_id: str):
    """Set the user ID"""
    _user_id.set(user_id)


def get_session_id() -> Optional[str]:
    """Get the current session ID"""
    return _session_id.get(None)


def set_session_id(session_id: str):
    """Set the session ID"""
    _session_id.set(session_id)


def get_trace_id() -> Optional[str]:
    """Get the current trace ID"""
    return _trace_id.get(None)


def set_trace_id(trace_id: str):
    """Set the trace ID"""
    _trace_id.set(trace_id)


def get_span_id() -> Optional[str]:
    """Get the current span ID"""
    return _span_id.get(None)


def set_span_id(span_id: str):
    """Set the span ID"""
    _span_id.set(span_id)


def get_parent_span_id() -> Optional[str]:
    """Get the current parent span ID"""
    return _parent_span_id.get(None)


def set_parent_span_id(parent_span_id: str):
    """Set the parent span ID"""
    _parent_span_id.set(parent_span_id)


def get_baggage() -> Dict[str, str]:
    """Get the current baggage"""
    return _baggage.get({}).copy()


def set_baggage(baggage: Dict[str, str]):
    """Set the baggage"""
    _baggage.set(baggage.copy())


def add_baggage(key: str, value: str):
    """Add an item to baggage"""
    current_baggage = _baggage.get({}).copy()
    current_baggage[key] = value
    _baggage.set(current_baggage)


def get_metadata() -> Dict[str, Any]:
    """Get the current metadata"""
    return _metadata.get({}).copy()


def set_metadata(metadata: Dict[str, Any]):
    """Set the metadata"""
    _metadata.set(metadata.copy())


def add_metadata(key: str, value: Any):
    """Add an item to metadata"""
    current_metadata = _metadata.get({}).copy()
    current_metadata[key] = value
    _metadata.set(current_metadata)


# Convenience Functions
def get_current_context() -> Optional[RequestContext]:
    """Get the current request context"""
    return _global_context_manager.get_current_context()


def set_user_context(
    user_id: str,
    session_id: Optional[str] = None,
    roles: Optional[list] = None,
    permissions: Optional[list] = None,
    tenant_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    **metadata,
):
    """
    Set user context information

    Args:
        user_id: User identifier
        session_id: Session identifier
        roles: List of user roles
        permissions: List of user permissions
        tenant_id: Tenant identifier for multi-tenancy
        organization_id: Organization identifier
        **metadata: Additional user metadata
    """
    set_user_id(user_id)
    if session_id:
        set_session_id(session_id)

    # Store additional user context in metadata
    user_metadata = {
        "user.roles": roles or [],
        "user.permissions": permissions or [],
        "user.tenant_id": tenant_id,
        "user.organization_id": organization_id,
    }
    user_metadata.update({f"user.{k}": v for k, v in metadata.items()})

    current_metadata = get_metadata()
    current_metadata.update(user_metadata)
    set_metadata(current_metadata)


def get_user_context() -> Optional[UserContext]:
    """Get the current user context"""
    user_id = get_user_id()
    if not user_id:
        return None

    metadata = get_metadata()

    return UserContext(
        user_id=user_id,
        session_id=get_session_id(),
        roles=metadata.get("user.roles"),
        permissions=metadata.get("user.permissions"),
        tenant_id=metadata.get("user.tenant_id"),
        organization_id=metadata.get("user.organization_id"),
        metadata={
            k.replace("user.", ""): v
            for k, v in metadata.items()
            if k.startswith("user.") and "." in k[5:]
        },
    )


def set_trace_context(
    trace_id: str,
    span_id: str,
    parent_span_id: Optional[str] = None,
    baggage: Optional[Dict[str, str]] = None,
):
    """
    Set trace context information

    Args:
        trace_id: Distributed trace identifier
        span_id: Current span identifier
        parent_span_id: Parent span identifier
        baggage: Trace baggage key-value pairs
    """
    set_trace_id(trace_id)
    set_span_id(span_id)
    if parent_span_id:
        set_parent_span_id(parent_span_id)
    if baggage:
        set_baggage(baggage)


def get_trace_context() -> Optional[TraceContext]:
    """Get the current trace context"""
    trace_id = get_trace_id()
    if not trace_id:
        return None

    return TraceContext(
        trace_id=trace_id,
        span_id=get_span_id() or generate_span_id(),
        parent_span_id=get_parent_span_id(),
        baggage=get_baggage(),
    )


# Header Propagation Functions
def propagate_headers() -> Dict[str, str]:
    """
    Generate headers for context propagation

    Creates HTTP headers that can be used to propagate context
    across service boundaries.

    Returns:
        Dictionary of headers for context propagation
    """
    headers = {}

    # Correlation headers
    correlation_id = get_correlation_id()
    if correlation_id:
        headers["X-Correlation-ID"] = correlation_id
        headers["X-Request-ID"] = get_request_id() or correlation_id

    # User headers
    user_id = get_user_id()
    if user_id:
        headers["X-User-ID"] = user_id

    session_id = get_session_id()
    if session_id:
        headers["X-Session-ID"] = session_id

    # Tracing headers (OpenTelemetry compatible)
    trace_id = get_trace_id()
    span_id = get_span_id()
    if trace_id and span_id:
        headers["traceparent"] = f"00-{trace_id}-{span_id}-01"

        baggage = get_baggage()
        if baggage:
            baggage_header = ",".join([f"{k}={v}" for k, v in baggage.items()])
            headers["baggage"] = baggage_header

    return headers


def extract_headers(headers: Dict[str, str]) -> Dict[str, Optional[str]]:
    """
    Extract context information from HTTP headers

    Args:
        headers: HTTP headers dictionary

    Returns:
        Dictionary with extracted context information
    """
    # Normalize header keys (case-insensitive)
    normalized_headers = {k.lower(): v for k, v in headers.items()}

    context_info = {
        "correlation_id": None,
        "request_id": None,
        "user_id": None,
        "session_id": None,
        "trace_id": None,
        "span_id": None,
        "parent_span_id": None,
        "baggage": {},
    }

    # Extract correlation headers
    for header in ["x-correlation-id", "x-request-id"]:
        if header in normalized_headers:
            context_info["correlation_id"] = normalized_headers[header]
            break

    # Extract request ID
    if "x-request-id" in normalized_headers:
        context_info["request_id"] = normalized_headers["x-request-id"]

    # Extract user headers
    if "x-user-id" in normalized_headers:
        context_info["user_id"] = normalized_headers["x-user-id"]

    if "x-session-id" in normalized_headers:
        context_info["session_id"] = normalized_headers["x-session-id"]

    # Extract tracing headers (OpenTelemetry format)
    if "traceparent" in normalized_headers:
        traceparent = normalized_headers["traceparent"]
        parts = traceparent.split("-")
        if len(parts) >= 4:
            context_info["trace_id"] = parts[1]
            context_info["span_id"] = parts[2]
            # The span_id from traceparent becomes parent_span_id for the next span
            context_info["parent_span_id"] = parts[2]

    # Extract baggage
    if "baggage" in normalized_headers:
        baggage_header = normalized_headers["baggage"]
        baggage = {}
        for item in baggage_header.split(","):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                baggage[key] = value
        context_info["baggage"] = baggage

    return context_info


# Global context manager instance
_global_context_manager = ContextManager()


def get_context_manager() -> ContextManager:
    """Get the global context manager instance"""
    return _global_context_manager


# Example usage and integration patterns
def example_usage():
    """
    Example usage patterns for the context management system

    This function demonstrates how to use the context manager
    in various scenarios.
    """

    # Example 1: Basic request context
    async def handle_request():
        async with get_context_manager().request_context(
            correlation_id="req_123", user_id="user_456"
        ):
            # All operations within this context will have access
            # to correlation_id and user_id
            logger = get_logger(__name__)
            logger.info("Processing user request")  # Will include correlation_id

    # Example 2: Trace spans within a request
    async def process_data():
        with get_context_manager().trace_span("data_processing"):
            # Simulate data processing
            with get_context_manager().trace_span("database_query"):
                # Database operation
                pass

            with get_context_manager().trace_span("data_transformation"):
                # Data transformation
                pass

    # Example 3: Header propagation for service-to-service calls
    async def call_external_service():
        headers = propagate_headers()
        # Use headers in HTTP client request to propagate context
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(url, headers=headers) as response:
        #         pass

    # Example 4: Extract context from incoming request
    def handle_incoming_request(request_headers):
        context_info = extract_headers(request_headers)

        # Set up context based on extracted information
        if context_info["correlation_id"]:
            set_correlation_id(context_info["correlation_id"])

        if context_info["trace_id"]:
            set_trace_context(
                trace_id=context_info["trace_id"],
                span_id=generate_span_id(),  # New span for this service
                parent_span_id=context_info["parent_span_id"],
                baggage=context_info["baggage"],
            )
