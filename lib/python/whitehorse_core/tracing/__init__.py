"""
Tracing Module

Distributed tracing implementation with OpenTelemetry integration,
span management, and correlation tracking across service boundaries.
"""

import functools
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.zipkin.json import ZipkinExporter
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (BatchSpanProcessor,
                                                ConsoleSpanExporter)

    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False

from ..logging import get_correlation_id, get_logger, set_correlation_id

logger = get_logger(__name__)


class SpanKind(Enum):
    """Span kinds for categorizing traces."""

    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class SpanData:
    """Span data for tracing."""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    kind: SpanKind = SpanKind.INTERNAL

    def __post_init__(self):
        if self.end_time and self.start_time:
            self.duration = self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "tags": self.tags,
            "logs": self.logs,
            "status": self.status,
            "kind": self.kind.value,
        }


class Span:
    """
    Span implementation for distributed tracing.
    """

    def __init__(
        self,
        operation_name: str,
        tracer: "Tracer",
        parent_span: Optional["Span"] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        tags: Optional[Dict[str, Any]] = None,
    ):
        self.operation_name = operation_name
        self.tracer = tracer
        self.parent_span = parent_span
        self.kind = kind

        # Generate IDs
        self.trace_id = parent_span.trace_id if parent_span else str(uuid.uuid4())
        self.span_id = str(uuid.uuid4())
        self.parent_span_id = parent_span.span_id if parent_span else None

        # Timing
        self.start_time = time.time()
        self.end_time: Optional[float] = None

        # Data
        self.tags: Dict[str, Any] = tags or {}
        self.logs: List[Dict[str, Any]] = []
        self.status = "ok"
        self.finished = False

        # OpenTelemetry span if available
        self.otel_span = None

        logger.debug(
            f"Started span: {operation_name}",
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
        )

    def set_tag(self, key: str, value: Any) -> "Span":
        """Set a tag on the span."""
        self.tags[key] = value

        if self.otel_span:
            self.otel_span.set_attribute(key, value)

        return self

    def set_tags(self, tags: Dict[str, Any]) -> "Span":
        """Set multiple tags on the span."""
        for key, value in tags.items():
            self.set_tag(key, value)
        return self

    def log(self, message: str, **kwargs) -> "Span":
        """Add a log entry to the span."""
        log_entry = {"timestamp": time.time(), "message": message, **kwargs}
        self.logs.append(log_entry)

        if self.otel_span:
            self.otel_span.add_event(message, kwargs)

        logger.debug(f"Span log: {message}", span_id=self.span_id, **kwargs)
        return self

    def set_status(self, status: str, description: Optional[str] = None) -> "Span":
        """Set span status."""
        self.status = status

        if description:
            self.set_tag("status.description", description)

        if self.otel_span:
            if status == "error":
                from opentelemetry.trace import Status, StatusCode

                self.otel_span.set_status(Status(StatusCode.ERROR, description))

        return self

    def record_exception(self, exception: Exception) -> "Span":
        """Record an exception in the span."""
        self.set_status("error", str(exception))
        self.set_tag("error", True)
        self.set_tag("error.type", exception.__class__.__name__)
        self.set_tag("error.message", str(exception))

        self.log(
            "exception",
            exception_type=exception.__class__.__name__,
            exception_message=str(exception),
        )

        if self.otel_span:
            self.otel_span.record_exception(exception)

        return self

    def finish(self) -> None:
        """Finish the span."""
        if self.finished:
            return

        self.end_time = time.time()
        self.finished = True

        # Create span data
        span_data = SpanData(
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            operation_name=self.operation_name,
            start_time=self.start_time,
            end_time=self.end_time,
            tags=self.tags,
            logs=self.logs,
            status=self.status,
            kind=self.kind,
        )

        # Report to tracer
        self.tracer._report_span(span_data)

        if self.otel_span:
            self.otel_span.end()

        logger.debug(
            f"Finished span: {self.operation_name}",
            trace_id=self.trace_id,
            span_id=self.span_id,
            duration=span_data.duration,
        )

    def __enter__(self) -> "Span":
        """Context manager entry."""
        self.tracer._set_active_span(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type:
            self.record_exception(exc_val)

        self.finish()
        self.tracer._clear_active_span()


class Tracer:
    """
    Tracer for creating and managing spans.
    """

    def __init__(self, service_name: str = "whitehorse_service"):
        self.service_name = service_name
        self._active_spans: Dict[int, Span] = {}  # Thread ID -> Span
        self._span_storage: List[SpanData] = []
        self._lock = threading.Lock()

        # OpenTelemetry tracer if available
        self.otel_tracer = None

        logger.info(f"Initialized tracer for service: {service_name}")

    def _get_thread_id(self) -> int:
        """Get current thread ID."""
        return threading.current_thread().ident

    def _set_active_span(self, span: Span) -> None:
        """Set active span for current thread."""
        thread_id = self._get_thread_id()
        with self._lock:
            self._active_spans[thread_id] = span

    def _clear_active_span(self) -> None:
        """Clear active span for current thread."""
        thread_id = self._get_thread_id()
        with self._lock:
            if thread_id in self._active_spans:
                del self._active_spans[thread_id]

    def get_active_span(self) -> Optional[Span]:
        """Get active span for current thread."""
        thread_id = self._get_thread_id()
        with self._lock:
            return self._active_spans.get(thread_id)

    def start_span(
        self,
        operation_name: str,
        parent_span: Optional[Span] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        tags: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a new span."""
        if parent_span is None:
            parent_span = self.get_active_span()

        span = Span(
            operation_name=operation_name,
            tracer=self,
            parent_span=parent_span,
            kind=kind,
            tags=tags,
        )

        # Create OpenTelemetry span if available
        if self.otel_tracer:
            otel_span = self.otel_tracer.start_span(operation_name)
            span.otel_span = otel_span

            # Set tags
            if tags:
                for key, value in tags.items():
                    otel_span.set_attribute(key, value)

        return span

    def _report_span(self, span_data: SpanData) -> None:
        """Report completed span."""
        with self._lock:
            self._span_storage.append(span_data)

            # Keep only last 1000 spans to prevent memory growth
            if len(self._span_storage) > 1000:
                self._span_storage = self._span_storage[-1000:]

        logger.debug(f"Reported span: {span_data.operation_name}")

    def get_spans(self, trace_id: Optional[str] = None) -> List[SpanData]:
        """Get stored spans, optionally filtered by trace ID."""
        with self._lock:
            if trace_id:
                return [
                    span for span in self._span_storage if span.trace_id == trace_id
                ]
            return list(self._span_storage)

    def clear_spans(self) -> None:
        """Clear stored spans."""
        with self._lock:
            self._span_storage.clear()
        logger.info("Cleared span storage")


class TracingManager:
    """
    Central tracing management with OpenTelemetry integration.
    """

    def __init__(
        self,
        service_name: str = "whitehorse_service",
        service_version: str = "1.0.0",
        enable_opentelemetry: bool = True,
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.tracer = Tracer(service_name)

        # Initialize OpenTelemetry if available and enabled
        if enable_opentelemetry and HAS_OPENTELEMETRY:
            self._setup_opentelemetry()

        logger.info(f"Initialized tracing manager for service: {service_name}")

    def _setup_opentelemetry(self) -> None:
        """Setup OpenTelemetry tracing."""
        try:
            # Create resource
            resource = Resource.create(
                {
                    "service.name": self.service_name,
                    "service.version": self.service_version,
                }
            )

            # Create tracer provider
            tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(tracer_provider)

            # Add console exporter for development
            console_exporter = ConsoleSpanExporter()
            tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))

            # Create tracer
            self.tracer.otel_tracer = trace.get_tracer(
                self.service_name, self.service_version
            )

            logger.info("OpenTelemetry tracing initialized")
        except Exception as e:
            logger.error(f"Failed to setup OpenTelemetry: {e}")

    def add_jaeger_exporter(
        self, agent_host_name: str = "localhost", agent_port: int = 6831
    ) -> None:
        """Add Jaeger exporter for tracing."""
        if not HAS_OPENTELEMETRY:
            logger.warning("OpenTelemetry not available, cannot add Jaeger exporter")
            return

        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name=agent_host_name, agent_port=agent_port
            )

            tracer_provider = trace.get_tracer_provider()
            tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

            logger.info(f"Added Jaeger exporter: {agent_host_name}:{agent_port}")
        except Exception as e:
            logger.error(f"Failed to add Jaeger exporter: {e}")

    def add_zipkin_exporter(
        self, endpoint: str = "http://localhost:9411/api/v2/spans"
    ) -> None:
        """Add Zipkin exporter for tracing."""
        if not HAS_OPENTELEMETRY:
            logger.warning("OpenTelemetry not available, cannot add Zipkin exporter")
            return

        try:
            zipkin_exporter = ZipkinExporter(endpoint=endpoint)

            tracer_provider = trace.get_tracer_provider()
            tracer_provider.add_span_processor(BatchSpanProcessor(zipkin_exporter))

            logger.info(f"Added Zipkin exporter: {endpoint}")
        except Exception as e:
            logger.error(f"Failed to add Zipkin exporter: {e}")

    def start_span(
        self,
        operation_name: str,
        parent_span: Optional[Span] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        tags: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a new span."""
        return self.tracer.start_span(operation_name, parent_span, kind, tags)

    def get_active_span(self) -> Optional[Span]:
        """Get active span."""
        return self.tracer.get_active_span()

    @contextmanager
    def trace(
        self,
        operation_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        tags: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for tracing an operation."""
        span = self.start_span(operation_name, kind=kind, tags=tags)

        # Set correlation ID from span
        old_correlation_id = get_correlation_id()
        set_correlation_id(span.trace_id)

        try:
            with span:
                yield span
        finally:
            set_correlation_id(old_correlation_id)

    def instrument_requests(self) -> None:
        """Instrument HTTP requests with tracing."""
        if HAS_OPENTELEMETRY:
            try:
                RequestsInstrumentor().instrument()
                logger.info("Instrumented HTTP requests with tracing")
            except Exception as e:
                logger.error(f"Failed to instrument requests: {e}")

    def instrument_sqlalchemy(self, engine=None) -> None:
        """Instrument SQLAlchemy with tracing."""
        if HAS_OPENTELEMETRY:
            try:
                if engine:
                    SQLAlchemyInstrumentor().instrument(engine=engine)
                else:
                    SQLAlchemyInstrumentor().instrument()
                logger.info("Instrumented SQLAlchemy with tracing")
            except Exception as e:
                logger.error(f"Failed to instrument SQLAlchemy: {e}")

    def get_trace_context(self) -> Dict[str, str]:
        """Get current trace context for propagation."""
        active_span = self.get_active_span()
        if not active_span:
            return {}

        return {
            "trace-id": active_span.trace_id,
            "span-id": active_span.span_id,
            "parent-span-id": active_span.parent_span_id or "",
        }

    def inject_trace_context(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Inject trace context into headers."""
        context = self.get_trace_context()
        headers_copy = headers.copy()

        for key, value in context.items():
            headers_copy[f"x-{key}"] = value

        return headers_copy

    def extract_trace_context(
        self, headers: Dict[str, str]
    ) -> Optional[Dict[str, str]]:
        """Extract trace context from headers."""
        context = {}

        for key in ["trace-id", "span-id", "parent-span-id"]:
            header_key = f"x-{key}"
            if header_key in headers:
                context[key] = headers[header_key]

        return context if context else None


# Decorators for automatic tracing


def trace_function(
    operation_name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    tags: Optional[Dict[str, Any]] = None,
):
    """Decorator to trace function execution."""

    def decorator(func: Callable) -> Callable:
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracing_manager = get_tracing_manager()

            function_tags = {
                "function.name": func.__name__,
                "function.module": func.__module__,
                **(tags or {}),
            }

            with tracing_manager.trace(
                operation_name, kind=kind, tags=function_tags
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_tag("function.success", True)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_tag("function.success", False)
                    raise

        return wrapper

    return decorator


def trace_class_methods(cls):
    """Class decorator to trace all methods."""
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if callable(attr) and not attr_name.startswith("_"):
            traced_method = trace_function(
                operation_name=f"{cls.__name__}.{attr_name}", kind=SpanKind.INTERNAL
            )(attr)
            setattr(cls, attr_name, traced_method)

    return cls


# Global tracing manager instance
_global_tracing_manager = None


def get_tracing_manager() -> TracingManager:
    """Get global tracing manager instance."""
    global _global_tracing_manager
    if _global_tracing_manager is None:
        _global_tracing_manager = TracingManager()
    return _global_tracing_manager


def setup_tracing(
    service_name: str = "whitehorse_service",
    service_version: str = "1.0.0",
    jaeger_endpoint: Optional[str] = None,
    zipkin_endpoint: Optional[str] = None,
    instrument_requests: bool = True,
    instrument_sqlalchemy: bool = True,
) -> TracingManager:
    """
    Setup global tracing with common configuration.

    Args:
        service_name: Service name for tracing
        service_version: Service version
        jaeger_endpoint: Jaeger endpoint for trace export
        zipkin_endpoint: Zipkin endpoint for trace export
        instrument_requests: Whether to instrument HTTP requests
        instrument_sqlalchemy: Whether to instrument SQLAlchemy

    Returns:
        Configured TracingManager instance
    """
    global _global_tracing_manager
    _global_tracing_manager = TracingManager(service_name, service_version)

    # Add exporters
    if jaeger_endpoint:
        if jaeger_endpoint.startswith("http://") or jaeger_endpoint.startswith(
            "https://"
        ):
            # HTTP endpoint format - extract host and port
            from urllib.parse import urlparse

            parsed = urlparse(jaeger_endpoint)
            host = parsed.hostname or "localhost"
            port = parsed.port or 6831
        else:
            # Assume host:port format
            host, port = jaeger_endpoint.split(":")
            port = int(port)

        _global_tracing_manager.add_jaeger_exporter(host, port)

    if zipkin_endpoint:
        _global_tracing_manager.add_zipkin_exporter(zipkin_endpoint)

    # Instrument libraries
    if instrument_requests:
        _global_tracing_manager.instrument_requests()

    if instrument_sqlalchemy:
        _global_tracing_manager.instrument_sqlalchemy()

    logger.info(f"Setup tracing for service: {service_name}")
    return _global_tracing_manager


# Convenience functions
def start_span(operation_name: str, **kwargs) -> Span:
    """Start a new span using global tracing manager."""
    return get_tracing_manager().start_span(operation_name, **kwargs)


def get_active_span() -> Optional[Span]:
    """Get active span using global tracing manager."""
    return get_tracing_manager().get_active_span()


@contextmanager
def trace(operation_name: str, **kwargs):
    """Trace an operation using global tracing manager."""
    with get_tracing_manager().trace(operation_name, **kwargs) as span:
        yield span
