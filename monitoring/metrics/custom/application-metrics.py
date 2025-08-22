"""
Universal Application Metrics Library
Provides standardized metrics collection for all applications in the platform.
"""

import functools
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

try:
    from opentelemetry import metrics
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import \
        OTLPMetricExporter
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.semconv.resource import ResourceAttributes

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    print("OpenTelemetry not available, metrics will be logged only")

try:
    import prometheus_client

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


@dataclass
class MetricConfig:
    """Configuration for metrics collection."""

    service_name: str
    service_version: str = "1.0.0"
    environment: str = "development"
    namespace: str = "universal_platform"
    enable_prometheus: bool = True
    enable_otel: bool = True
    prometheus_port: int = 8000
    otel_endpoint: str = "http://localhost:4317"
    custom_labels: Dict[str, str] = field(default_factory=dict)


class UniversalMetrics:
    """Universal metrics collection system for all platform applications."""

    def __init__(self, config: MetricConfig):
        self.config = config
        self.meters = {}
        self.counters = {}
        self.histograms = {}
        self.gauges = {}

        self._setup_providers()
        self._setup_standard_metrics()

    def _setup_providers(self):
        """Set up metrics providers based on configuration."""
        if not OTEL_AVAILABLE and not PROMETHEUS_AVAILABLE:
            print("Warning: No metrics libraries available")
            return

        # OpenTelemetry setup
        if self.config.enable_otel and OTEL_AVAILABLE:
            resource = Resource.create(
                {
                    ResourceAttributes.SERVICE_NAME: self.config.service_name,
                    ResourceAttributes.SERVICE_VERSION: self.config.service_version,
                    ResourceAttributes.DEPLOYMENT_ENVIRONMENT: self.config.environment,
                    **self.config.custom_labels,
                }
            )

            readers = []

            # Add Prometheus reader
            if self.config.enable_prometheus:
                readers.append(PrometheusMetricReader())

            # Add OTLP exporter
            otlp_exporter = OTLPMetricExporter(
                endpoint=self.config.otel_endpoint, insecure=True
            )
            readers.append(
                PeriodicExportingMetricReader(
                    otlp_exporter, export_interval_millis=15000
                )
            )

            provider = MeterProvider(resource=resource, metric_readers=readers)
            metrics.set_meter_provider(provider)

            self.meter = metrics.get_meter(
                self.config.service_name, version=self.config.service_version
            )

    def _setup_standard_metrics(self):
        """Set up standard metrics that all applications should have."""
        if not hasattr(self, "meter"):
            return

        # HTTP Request metrics
        self.http_request_counter = self.meter.create_counter(
            name="http_requests_total",
            description="Total number of HTTP requests",
            unit="1",
        )

        self.http_request_duration = self.meter.create_histogram(
            name="http_request_duration_seconds",
            description="Duration of HTTP requests in seconds",
            unit="s",
        )

        # Database metrics
        self.db_query_counter = self.meter.create_counter(
            name="db_queries_total",
            description="Total number of database queries",
            unit="1",
        )

        self.db_query_duration = self.meter.create_histogram(
            name="db_query_duration_seconds",
            description="Duration of database queries in seconds",
            unit="s",
        )

        # Background job metrics
        self.background_job_counter = self.meter.create_counter(
            name="background_jobs_total",
            description="Total number of background jobs",
            unit="1",
        )

        self.background_job_duration = self.meter.create_histogram(
            name="background_job_duration_seconds",
            description="Duration of background jobs in seconds",
            unit="s",
        )

        # Cache metrics
        self.cache_operations = self.meter.create_counter(
            name="cache_operations_total",
            description="Total number of cache operations",
            unit="1",
        )

        # External API metrics
        self.external_api_requests = self.meter.create_counter(
            name="external_api_requests_total",
            description="Total number of external API requests",
            unit="1",
        )

        # Business metrics
        self.user_registrations = self.meter.create_counter(
            name="user_registrations_total",
            description="Total number of user registrations",
            unit="1",
        )

        self.feature_usage = self.meter.create_counter(
            name="feature_usage_total",
            description="Total feature usage events",
            unit="1",
        )

    def record_http_request(
        self, method: str, endpoint: str, status_code: int, duration: float
    ):
        """Record HTTP request metrics."""
        if hasattr(self, "http_request_counter"):
            self.http_request_counter.add(
                1,
                attributes={
                    "method": method,
                    "endpoint": endpoint,
                    "code": str(status_code),
                    "environment": self.config.environment,
                },
            )

            self.http_request_duration.record(
                duration,
                attributes={
                    "method": method,
                    "endpoint": endpoint,
                    "code": str(status_code),
                    "environment": self.config.environment,
                },
            )

    def record_db_query(self, operation: str, table: str, status: str, duration: float):
        """Record database query metrics."""
        if hasattr(self, "db_query_counter"):
            self.db_query_counter.add(
                1,
                attributes={
                    "operation": operation,
                    "table": table,
                    "status": status,
                    "environment": self.config.environment,
                },
            )

            self.db_query_duration.record(
                duration,
                attributes={
                    "operation": operation,
                    "table": table,
                    "status": status,
                    "environment": self.config.environment,
                },
            )

    def record_background_job(self, job_type: str, status: str, duration: float):
        """Record background job metrics."""
        if hasattr(self, "background_job_counter"):
            self.background_job_counter.add(
                1,
                attributes={
                    "job_type": job_type,
                    "status": status,
                    "environment": self.config.environment,
                },
            )

            self.background_job_duration.record(
                duration,
                attributes={
                    "job_type": job_type,
                    "status": status,
                    "environment": self.config.environment,
                },
            )

    def record_cache_operation(self, operation: str, cache_type: str, hit: bool):
        """Record cache operation metrics."""
        if hasattr(self, "cache_operations"):
            self.cache_operations.add(
                1,
                attributes={
                    "operation": "hit" if hit else "miss",
                    "cache_type": cache_type,
                    "environment": self.config.environment,
                },
            )

    def record_external_api_request(
        self, service: str, endpoint: str, status_code: int, duration: float
    ):
        """Record external API request metrics."""
        if hasattr(self, "external_api_requests"):
            self.external_api_requests.add(
                1,
                attributes={
                    "external_service": service,
                    "endpoint": endpoint,
                    "code": str(status_code),
                    "environment": self.config.environment,
                },
            )

    def record_user_registration(self, method: str, status: str):
        """Record user registration metrics."""
        if hasattr(self, "user_registrations"):
            self.user_registrations.add(
                1,
                attributes={
                    "method": method,
                    "status": status,
                    "environment": self.config.environment,
                },
            )

    def record_feature_usage(self, feature: str, user_type: str = "unknown"):
        """Record feature usage metrics."""
        if hasattr(self, "feature_usage"):
            self.feature_usage.add(
                1,
                attributes={
                    "feature": feature,
                    "user_type": user_type,
                    "environment": self.config.environment,
                },
            )

    @contextmanager
    def time_operation(self, operation_type: str, **labels):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
            status = "success"
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            if operation_type == "http":
                self.record_http_request(duration=duration, **labels)
            elif operation_type == "db":
                self.record_db_query(duration=duration, status=status, **labels)
            elif operation_type == "job":
                self.record_background_job(duration=duration, status=status, **labels)


def timer(operation_type: str, **static_labels):
    """Decorator for timing function calls."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get metrics instance from global state or create one
            metrics_instance = getattr(wrapper, "_metrics_instance", None)
            if not metrics_instance:
                config = MetricConfig(
                    service_name=os.getenv("SERVICE_NAME", "unknown"),
                    environment=os.getenv("ENVIRONMENT", "development"),
                )
                metrics_instance = UniversalMetrics(config)
                wrapper._metrics_instance = metrics_instance

            with metrics_instance.time_operation(operation_type, **static_labels):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# Global metrics instance
_global_metrics = None


def get_metrics(config: Optional[MetricConfig] = None) -> UniversalMetrics:
    """Get the global metrics instance."""
    global _global_metrics
    if _global_metrics is None:
        if config is None:
            config = MetricConfig(
                service_name=os.getenv("SERVICE_NAME", "unknown-service"),
                service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
                environment=os.getenv("ENVIRONMENT", "development"),
                namespace=os.getenv("METRICS_NAMESPACE", "universal_platform"),
            )
        _global_metrics = UniversalMetrics(config)
    return _global_metrics


# Convenience functions for common metrics
def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """Convenience function to record HTTP request metrics."""
    metrics = get_metrics()
    metrics.record_http_request(method, endpoint, status_code, duration)


def record_db_query(operation: str, table: str, status: str, duration: float):
    """Convenience function to record database query metrics."""
    metrics = get_metrics()
    metrics.record_db_query(operation, table, status, duration)


def record_feature_usage(feature: str, user_type: str = "unknown"):
    """Convenience function to record feature usage metrics."""
    metrics = get_metrics()
    metrics.record_feature_usage(feature, user_type)
