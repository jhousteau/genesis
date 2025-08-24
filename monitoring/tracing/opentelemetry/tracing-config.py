"""
Universal Distributed Tracing Configuration
Provides comprehensive tracing setup for all platform applications.
"""

import logging
import os
from contextlib import contextmanager
from functools import wraps
from typing import Any, Dict

try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.auto_instrumentation import sitecustomize
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.b3 import B3MultiFormat
    from opentelemetry.propagators.composite import CompositeHTTPPropagator
    from opentelemetry.propagators.jaeger import JaegerPropagator
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
    from opentelemetry.sdk.trace.sampling import (
        AlwaysOff,
        AlwaysOn,
        ParentBased,
        TraceIdRatioBased,
    )
    from opentelemetry.semconv.resource import ResourceAttributes
    from opentelemetry.semconv.trace import SpanAttributes

    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    print("OpenTelemetry not available, tracing will be disabled")

try:
    from google.cloud.trace_v1 import TraceServiceClient
    from google.cloud.trace_v1.types import Trace, TraceSpan

    GCP_TRACE_AVAILABLE = True
except ImportError:
    GCP_TRACE_AVAILABLE = False


class TracingConfig:
    """Configuration for distributed tracing."""

    def __init__(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        environment: str = "development",
        project_id: str = None,
        sampling_rate: float = 0.1,
        jaeger_endpoint: str = None,
        otlp_endpoint: str = None,
        enable_gcp_trace: bool = True,
        enable_console_export: bool = False,
        custom_attributes: Dict[str, str] = None,
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.project_id = project_id or os.getenv("GCP_PROJECT", "unknown")
        self.sampling_rate = sampling_rate
        self.jaeger_endpoint = jaeger_endpoint or os.getenv(
            "JAEGER_ENDPOINT", "http://localhost:14268/api/traces"
        )
        self.otlp_endpoint = otlp_endpoint or os.getenv(
            "OTLP_ENDPOINT", "http://localhost:4317"
        )
        self.enable_gcp_trace = enable_gcp_trace
        self.enable_console_export = enable_console_export
        self.custom_attributes = custom_attributes or {}


class UniversalTracer:
    """Universal distributed tracer for all platform applications."""

    def __init__(self, config: TracingConfig):
        self.config = config
        self.tracer = None
        self.trace_provider = None

        if TRACING_AVAILABLE:
            self._setup_tracing()
        else:
            logging.warning("Tracing not available, operations will not be traced")

    def _setup_tracing(self):
        """Set up OpenTelemetry tracing with multiple exporters."""
        # Create resource with service information
        resource = Resource.create(
            {
                ResourceAttributes.SERVICE_NAME: self.config.service_name,
                ResourceAttributes.SERVICE_VERSION: self.config.service_version,
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: self.config.environment,
                ResourceAttributes.CLOUD_PROVIDER: "gcp",
                ResourceAttributes.CLOUD_PLATFORM: "gcp_compute_engine",
                **self.config.custom_attributes,
            }
        )

        # Set up sampling strategy
        sampler = self._create_sampler()

        # Create tracer provider
        self.trace_provider = TracerProvider(resource=resource, sampler=sampler)

        # Set up exporters
        self._setup_exporters()

        # Set global tracer provider
        trace.set_tracer_provider(self.trace_provider)

        # Set up propagators
        self._setup_propagators()

        # Get tracer instance
        self.tracer = trace.get_tracer(
            self.config.service_name, version=self.config.service_version
        )

        # Set up automatic instrumentation
        self._setup_auto_instrumentation()

    def _create_sampler(self):
        """Create intelligent sampling strategy."""
        if self.config.environment == "development":
            # Always sample in development
            return AlwaysOn()
        elif self.config.environment == "production":
            # Use parent-based sampling with rate limiting in production
            return ParentBased(
                root=TraceIdRatioBased(self.config.sampling_rate),
                remote_parent_sampled=AlwaysOn(),
                remote_parent_not_sampled=TraceIdRatioBased(
                    0.01
                ),  # Still sample 1% of child spans
                local_parent_sampled=AlwaysOn(),
                local_parent_not_sampled=AlwaysOff(),
            )
        else:
            # Default rate-based sampling for other environments
            return TraceIdRatioBased(self.config.sampling_rate)

    def _setup_exporters(self):
        """Set up trace exporters for various backends."""
        exporters = []

        # Jaeger exporter
        if self.config.jaeger_endpoint:
            try:
                jaeger_exporter = JaegerExporter(
                    agent_host_name="localhost",
                    agent_port=6831,
                    collector_endpoint=self.config.jaeger_endpoint,
                )
                exporters.append(jaeger_exporter)
            except Exception as e:
                logging.warning(f"Failed to setup Jaeger exporter: {e}")

        # OTLP exporter (for Google Cloud Trace or other OTLP-compatible backends)
        if self.config.otlp_endpoint:
            try:
                otlp_exporter = OTLPSpanExporter(
                    endpoint=self.config.otlp_endpoint, insecure=True
                )
                exporters.append(otlp_exporter)
            except Exception as e:
                logging.warning(f"Failed to setup OTLP exporter: {e}")

        # Console exporter for debugging
        if self.config.enable_console_export:
            from opentelemetry.exporter.console import ConsoleSpanExporter

            exporters.append(ConsoleSpanExporter())

        # Add batch span processors for each exporter
        for exporter in exporters:
            processor = BatchSpanProcessor(
                exporter,
                max_export_batch_size=512,
                max_queue_size=2048,
                export_timeout_millis=30000,
                schedule_delay_millis=5000,
            )
            self.trace_provider.add_span_processor(processor)

    def _setup_propagators(self):
        """Set up trace context propagation."""
        # Support multiple propagation formats
        composite_propagator = CompositeHTTPPropagator(
            [
                JaegerPropagator(),  # Jaeger format
                B3MultiFormat(),  # B3 format (Zipkin)
            ]
        )
        set_global_textmap(composite_propagator)

    def _setup_auto_instrumentation(self):
        """Set up automatic instrumentation for common libraries."""
        try:
            # HTTP libraries
            RequestsInstrumentor().instrument()

            # Database libraries
            Psycopg2Instrumentor().instrument()
            RedisInstrumentor().instrument()

            # Background job libraries
            CeleryInstrumentor().instrument()

            # Web frameworks (conditional based on availability)
            try:
                import django

                DjangoInstrumentor().instrument()
            except ImportError:
                pass

            try:
                import flask

                FlaskInstrumentor().instrument()
            except ImportError:
                pass

            try:
                import fastapi

                FastAPIInstrumentor().instrument()
            except ImportError:
                pass

        except Exception as e:
            logging.warning(f"Some auto-instrumentation failed: {e}")

    def start_span(
        self,
        name: str,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL,
        attributes: Dict[str, Any] = None,
    ) -> trace.Span:
        """Start a new span with optional attributes."""
        if not self.tracer:
            return trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)

        span = self.tracer.start_span(name=name, kind=kind, attributes=attributes or {})
        return span

    @contextmanager
    def trace_operation(
        self,
        name: str,
        operation_type: str = "internal",
        attributes: Dict[str, Any] = None,
    ):
        """Context manager for tracing operations."""
        if not self.tracer:
            yield None
            return

        # Determine span kind based on operation type
        kind_map = {
            "http_client": trace.SpanKind.CLIENT,
            "http_server": trace.SpanKind.SERVER,
            "database": trace.SpanKind.CLIENT,
            "queue_producer": trace.SpanKind.PRODUCER,
            "queue_consumer": trace.SpanKind.CONSUMER,
            "internal": trace.SpanKind.INTERNAL,
        }
        kind = kind_map.get(operation_type, trace.SpanKind.INTERNAL)

        with self.tracer.start_as_current_span(
            name=name, kind=kind, attributes=attributes or {}
        ) as span:
            try:
                yield span
                span.set_status(trace.Status(trace.StatusCode.OK))
            except Exception as e:
                span.set_status(
                    trace.Status(trace.StatusCode.ERROR, description=str(e))
                )
                span.record_exception(e)
                raise

    def trace_http_request(
        self,
        method: str,
        url: str,
        status_code: int,
        duration: float,
        user_id: str = None,
    ):
        """Trace HTTP request with standard attributes."""
        attributes = {
            SpanAttributes.HTTP_METHOD: method,
            SpanAttributes.HTTP_URL: url,
            SpanAttributes.HTTP_STATUS_CODE: status_code,
            "http.duration_ms": duration * 1000,
        }
        if user_id:
            attributes["user.id"] = user_id

        with self.trace_operation(
            f"{method} {url}", operation_type="http_server", attributes=attributes
        ) as span:
            if span and status_code >= 400:
                span.set_status(
                    trace.Status(
                        trace.StatusCode.ERROR, description=f"HTTP {status_code}"
                    )
                )

    def trace_database_query(
        self, operation: str, table: str, query: str = None, duration: float = None
    ):
        """Trace database query with standard attributes."""
        attributes = {
            SpanAttributes.DB_OPERATION: operation,
            SpanAttributes.DB_SQL_TABLE: table,
        }
        if query:
            attributes[SpanAttributes.DB_STATEMENT] = query
        if duration:
            attributes["db.duration_ms"] = duration * 1000

        return self.trace_operation(
            f"DB {operation} {table}", operation_type="database", attributes=attributes
        )

    def trace_external_api(self, service_name: str, endpoint: str, method: str = "GET"):
        """Trace external API call."""
        attributes = {
            SpanAttributes.HTTP_METHOD: method,
            SpanAttributes.HTTP_URL: endpoint,
            "external.service": service_name,
        }

        return self.trace_operation(
            f"{service_name} {method} {endpoint}",
            operation_type="http_client",
            attributes=attributes,
        )

    def trace_background_job(self, job_type: str, job_id: str = None):
        """Trace background job execution."""
        attributes = {
            "job.type": job_type,
        }
        if job_id:
            attributes["job.id"] = job_id

        return self.trace_operation(
            f"Job {job_type}", operation_type="internal", attributes=attributes
        )

    def add_business_context(
        self,
        span: trace.Span,
        event: str,
        value: float = None,
        user_id: str = None,
        **kwargs,
    ):
        """Add business context to a span."""
        if not span or not span.is_recording():
            return

        attributes = {
            "business.event": event,
        }
        if value is not None:
            attributes["business.value"] = value
        if user_id:
            attributes["business.user_id"] = user_id

        for key, val in kwargs.items():
            attributes[f"business.{key}"] = val

        span.set_attributes(attributes)


def trace_function(operation_name: str = None, operation_type: str = "internal"):
    """Decorator for tracing function calls."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if not tracer or not tracer.tracer:
                return func(*args, **kwargs)

            name = operation_name or f"{func.__module__}.{func.__name__}"
            with tracer.trace_operation(name, operation_type) as span:
                try:
                    result = func(*args, **kwargs)
                    if span and hasattr(result, "__dict__"):
                        # Add result metadata if available
                        if hasattr(result, "id"):
                            span.set_attribute("result.id", str(result.id))
                    return result
                except Exception as e:
                    if span:
                        span.set_attribute("error.type", type(e).__name__)
                        span.set_attribute("error.message", str(e))
                    raise

        return wrapper

    return decorator


# Global tracer instance
_global_tracer = None


def get_tracer(config: TracingConfig = None) -> UniversalTracer:
    """Get the global tracer instance."""
    global _global_tracer
    if _global_tracer is None:
        if config is None:
            config = TracingConfig(
                service_name=os.getenv("SERVICE_NAME", "unknown-service"),
                service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
                environment=os.getenv("ENVIRONMENT", "development"),
                project_id=os.getenv("GCP_PROJECT", "unknown"),
                sampling_rate=float(os.getenv("TRACE_SAMPLING_RATE", "0.1")),
            )
        _global_tracer = UniversalTracer(config)
    return _global_tracer


# Convenience functions
def trace_http_request(
    method: str, url: str, status_code: int, duration: float, user_id: str = None
):
    """Convenience function for tracing HTTP requests."""
    tracer = get_tracer()
    tracer.trace_http_request(method, url, status_code, duration, user_id)


def trace_operation(
    name: str, operation_type: str = "internal", attributes: Dict[str, Any] = None
):
    """Convenience function for tracing operations."""
    tracer = get_tracer()
    return tracer.trace_operation(name, operation_type, attributes)
