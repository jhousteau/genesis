"""
Metrics Module

Prometheus and OpenTelemetry integration for comprehensive application monitoring,
custom metrics collection, and performance tracking.
"""

import functools
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

try:
    from prometheus_client import (CollectorRegistry, Counter, Gauge,
                                   Histogram, Summary, generate_latest)
    from prometheus_client.exposition import start_http_server

    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

try:
    from opentelemetry import metrics as otel_metrics
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource

    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False

from ..logging import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricSample:
    """A single metric sample."""

    name: str
    value: float
    labels: Dict[str, str]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp,
        }


@dataclass
class MetricDefinition:
    """Metric definition with metadata."""

    name: str
    metric_type: MetricType
    description: str
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # For histograms

    def __post_init__(self):
        # Validate metric name
        if not self.name.replace("_", "").replace(":", "").isalnum():
            raise ValueError(f"Invalid metric name: {self.name}")


class MetricsCollector:
    """
    Base metrics collector interface.
    """

    def __init__(self, service_name: str = "whitehorse_service"):
        self.service_name = service_name
        self._metrics: Dict[str, Any] = {}
        self._definitions: Dict[str, MetricDefinition] = {}
        self._lock = threading.Lock()

    def define_metric(self, definition: MetricDefinition) -> None:
        """Define a new metric."""
        with self._lock:
            self._definitions[definition.name] = definition
            logger.debug(
                f"Defined metric: {definition.name} ({definition.metric_type.value})"
            )

    def increment_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric."""
        raise NotImplementedError

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge metric value."""
        raise NotImplementedError

    def observe_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Observe a value in a histogram."""
        raise NotImplementedError

    def observe_summary(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Observe a value in a summary."""
        raise NotImplementedError

    def get_metric_samples(self) -> List[MetricSample]:
        """Get all metric samples."""
        raise NotImplementedError


class PrometheusCollector(MetricsCollector):
    """Prometheus metrics collector."""

    def __init__(
        self,
        service_name: str = "whitehorse_service",
        registry: Optional[CollectorRegistry] = None,
    ):
        if not HAS_PROMETHEUS:
            raise ImportError("Prometheus client library not available")

        super().__init__(service_name)
        self.registry = registry or CollectorRegistry()
        self._prometheus_metrics: Dict[str, Any] = {}

        # Add default service info metric
        self._add_service_info()

        logger.info(f"Initialized Prometheus collector for service: {service_name}")

    def _add_service_info(self):
        """Add service info metric."""
        info_metric = Gauge(
            "service_info",
            "Service information",
            ["service_name", "version"],
            registry=self.registry,
        )
        info_metric.labels(service_name=self.service_name, version="1.0.0").set(1)

    def _get_or_create_metric(
        self, name: str, metric_type: MetricType, labels: List[str]
    ) -> Any:
        """Get or create Prometheus metric."""
        metric_key = f"{name}_{metric_type.value}"

        if metric_key not in self._prometheus_metrics:
            definition = self._definitions.get(name)
            description = definition.description if definition else f"{name} metric"

            if metric_type == MetricType.COUNTER:
                metric = Counter(name, description, labels, registry=self.registry)
            elif metric_type == MetricType.GAUGE:
                metric = Gauge(name, description, labels, registry=self.registry)
            elif metric_type == MetricType.HISTOGRAM:
                buckets = definition.buckets if definition else None
                metric = Histogram(
                    name, description, labels, registry=self.registry, buckets=buckets
                )
            elif metric_type == MetricType.SUMMARY:
                metric = Summary(name, description, labels, registry=self.registry)
            else:
                raise ValueError(f"Unsupported metric type: {metric_type}")

            self._prometheus_metrics[metric_key] = metric
            logger.debug(f"Created Prometheus metric: {name} ({metric_type.value})")

        return self._prometheus_metrics[metric_key]

    def increment_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment counter metric."""
        labels = labels or {}
        label_names = list(labels.keys())

        counter = self._get_or_create_metric(name, MetricType.COUNTER, label_names)

        if labels:
            counter.labels(**labels).inc(value)
        else:
            counter.inc(value)

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set gauge metric value."""
        labels = labels or {}
        label_names = list(labels.keys())

        gauge = self._get_or_create_metric(name, MetricType.GAUGE, label_names)

        if labels:
            gauge.labels(**labels).set(value)
        else:
            gauge.set(value)

    def observe_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Observe histogram value."""
        labels = labels or {}
        label_names = list(labels.keys())

        histogram = self._get_or_create_metric(name, MetricType.HISTOGRAM, label_names)

        if labels:
            histogram.labels(**labels).observe(value)
        else:
            histogram.observe(value)

    def observe_summary(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Observe summary value."""
        labels = labels or {}
        label_names = list(labels.keys())

        summary = self._get_or_create_metric(name, MetricType.SUMMARY, label_names)

        if labels:
            summary.labels(**labels).observe(value)
        else:
            summary.observe(value)

    def get_metric_samples(self) -> List[MetricSample]:
        """Get all metric samples (not directly available in Prometheus client)."""
        # This would require parsing the exposition format
        # For now, return empty list
        return []

    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus exposition format."""
        return generate_latest(self.registry).decode("utf-8")

    def start_http_server(self, port: int = 8000) -> None:
        """Start HTTP server for metrics exposition."""
        start_http_server(port, registry=self.registry)
        logger.info(f"Started Prometheus metrics server on port {port}")


class InMemoryCollector(MetricsCollector):
    """In-memory metrics collector for testing and development."""

    def __init__(
        self, service_name: str = "whitehorse_service", max_samples: int = 10000
    ):
        super().__init__(service_name)
        self.max_samples = max_samples
        self._samples: deque = deque(maxlen=max_samples)
        self._current_values: Dict[str, Dict[str, float]] = defaultdict(dict)

    def _record_sample(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a metric sample."""
        sample = MetricSample(
            name=name, value=value, labels=labels or {}, timestamp=time.time()
        )

        with self._lock:
            self._samples.append(sample)

            # Update current values for gauges
            label_key = str(sorted((labels or {}).items()))
            self._current_values[name][label_key] = value

    def increment_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment counter metric."""
        label_key = str(sorted((labels or {}).items()))

        with self._lock:
            current = self._current_values[name].get(label_key, 0)
            new_value = current + value
            self._current_values[name][label_key] = new_value

        self._record_sample(name, new_value, labels)

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set gauge metric value."""
        self._record_sample(name, value, labels)

    def observe_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Observe histogram value."""
        self._record_sample(f"{name}_bucket", value, labels)

    def observe_summary(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Observe summary value."""
        self._record_sample(f"{name}_summary", value, labels)

    def get_metric_samples(self) -> List[MetricSample]:
        """Get all metric samples."""
        with self._lock:
            return list(self._samples)

    def get_current_values(self) -> Dict[str, Dict[str, float]]:
        """Get current metric values."""
        with self._lock:
            return dict(self._current_values)

    def clear_samples(self) -> None:
        """Clear all stored samples."""
        with self._lock:
            self._samples.clear()
            self._current_values.clear()
            logger.info("Cleared all metric samples")


class MetricsManager:
    """
    Central metrics management with multiple collectors.
    """

    def __init__(self, service_name: str = "whitehorse_service"):
        self.service_name = service_name
        self.collectors: List[MetricsCollector] = []
        self._timers: Dict[str, float] = {}
        self._timer_lock = threading.Lock()

        # Default metrics definitions
        self._define_default_metrics()

        logger.info(f"Initialized metrics manager for service: {service_name}")

    def _define_default_metrics(self):
        """Define default application metrics."""
        default_metrics = [
            MetricDefinition(
                name="requests_total",
                metric_type=MetricType.COUNTER,
                description="Total number of requests",
                labels=["method", "endpoint", "status"],
            ),
            MetricDefinition(
                name="request_duration_seconds",
                metric_type=MetricType.HISTOGRAM,
                description="Request duration in seconds",
                labels=["method", "endpoint"],
                buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            ),
            MetricDefinition(
                name="errors_total",
                metric_type=MetricType.COUNTER,
                description="Total number of errors",
                labels=["error_type", "severity"],
            ),
            MetricDefinition(
                name="active_connections",
                metric_type=MetricType.GAUGE,
                description="Number of active connections",
                labels=["connection_type"],
            ),
            MetricDefinition(
                name="memory_usage_bytes",
                metric_type=MetricType.GAUGE,
                description="Memory usage in bytes",
                labels=["memory_type"],
            ),
            MetricDefinition(
                name="cpu_usage_percent",
                metric_type=MetricType.GAUGE,
                description="CPU usage percentage",
            ),
        ]

        for definition in default_metrics:
            self.define_metric(definition)

    def add_collector(self, collector: MetricsCollector) -> None:
        """Add metrics collector."""
        self.collectors.append(collector)

        # Apply existing metric definitions
        for definition in self._get_all_definitions():
            collector.define_metric(definition)

        logger.info(f"Added metrics collector: {collector.__class__.__name__}")

    def remove_collector(self, collector_class: type) -> None:
        """Remove metrics collector by class."""
        self.collectors = [
            c for c in self.collectors if not isinstance(c, collector_class)
        ]
        logger.info(f"Removed metrics collector: {collector_class.__name__}")

    def define_metric(self, definition: MetricDefinition) -> None:
        """Define metric across all collectors."""
        for collector in self.collectors:
            collector.define_metric(definition)

    def _get_all_definitions(self) -> List[MetricDefinition]:
        """Get all metric definitions."""
        definitions = []
        for collector in self.collectors:
            definitions.extend(collector._definitions.values())
        return definitions

    def increment(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment counter across all collectors."""
        for collector in self.collectors:
            collector.increment_counter(name, value, labels)

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set gauge across all collectors."""
        for collector in self.collectors:
            collector.set_gauge(name, value, labels)

    def observe_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Observe histogram across all collectors."""
        for collector in self.collectors:
            collector.observe_histogram(name, value, labels)

    def observe_summary(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Observe summary across all collectors."""
        for collector in self.collectors:
            collector.observe_summary(name, value, labels)

    def start_timer(self, name: str) -> str:
        """Start a timer and return timer ID."""
        timer_id = f"{name}_{time.time()}_{threading.current_thread().ident}"

        with self._timer_lock:
            self._timers[timer_id] = time.time()

        return timer_id

    def stop_timer(
        self, timer_id: str, labels: Optional[Dict[str, str]] = None
    ) -> float:
        """Stop timer and record duration."""
        with self._timer_lock:
            if timer_id not in self._timers:
                logger.warning(f"Timer not found: {timer_id}")
                return 0.0

            start_time = self._timers.pop(timer_id)

        duration = time.time() - start_time

        # Extract metric name from timer ID
        metric_name = timer_id.split("_")[0]
        self.observe_histogram(f"{metric_name}_duration_seconds", duration, labels)

        return duration

    def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: Optional[float] = None,
    ) -> None:
        """Record HTTP request metrics."""
        labels = {
            "method": method.upper(),
            "endpoint": endpoint,
            "status": str(status_code),
        }

        self.increment("requests_total", labels=labels)

        if duration is not None:
            duration_labels = {"method": method.upper(), "endpoint": endpoint}
            self.observe_histogram(
                "request_duration_seconds", duration, duration_labels
            )

    def record_error(self, error_type: str, severity: str = "error") -> None:
        """Record error metrics."""
        labels = {"error_type": error_type, "severity": severity}
        self.increment("errors_total", labels=labels)

    def update_system_metrics(self) -> None:
        """Update system resource metrics."""
        try:
            import psutil

            # Memory metrics
            memory = psutil.virtual_memory()
            self.set_gauge("memory_usage_bytes", memory.used, {"memory_type": "used"})
            self.set_gauge(
                "memory_usage_bytes", memory.available, {"memory_type": "available"}
            )

            # CPU metrics
            cpu_percent = psutil.cpu_percent()
            self.set_gauge("cpu_usage_percent", cpu_percent)

        except ImportError:
            logger.debug("psutil not available, skipping system metrics")
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")


# Decorators for automatic metrics collection


def measure_time(metric_name: str = None, labels: Optional[Dict[str, str]] = None):
    """Decorator to measure function execution time."""

    def decorator(func: Callable) -> Callable:
        nonlocal metric_name
        if metric_name is None:
            metric_name = f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                success = True
                error_type = None
            except Exception as e:
                success = False
                error_type = e.__class__.__name__
                raise
            finally:
                duration = time.time() - start_time

                # Record timing
                timing_labels = labels.copy() if labels else {}
                timing_labels.update(
                    {"function": func.__name__, "success": str(success)}
                )

                if hasattr(wrapper, "_metrics_manager"):
                    wrapper._metrics_manager.observe_histogram(
                        f"{metric_name}_duration_seconds", duration, timing_labels
                    )

                    # Record error if occurred
                    if not success:
                        error_labels = {
                            "error_type": error_type,
                            "function": func.__name__,
                        }
                        wrapper._metrics_manager.record_error(error_type)

            return result

        return wrapper

    return decorator


def count_calls(metric_name: str = None, labels: Optional[Dict[str, str]] = None):
    """Decorator to count function calls."""

    def decorator(func: Callable) -> Callable:
        nonlocal metric_name
        if metric_name is None:
            metric_name = f"{func.__module__}.{func.__name__}_calls_total"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            call_labels = labels.copy() if labels else {}
            call_labels["function"] = func.__name__

            if hasattr(wrapper, "_metrics_manager"):
                wrapper._metrics_manager.increment(metric_name, labels=call_labels)

            return func(*args, **kwargs)

        return wrapper

    return decorator


# Global metrics manager instance
_global_metrics_manager = None


def get_metrics_manager() -> MetricsManager:
    """Get global metrics manager instance."""
    global _global_metrics_manager
    if _global_metrics_manager is None:
        _global_metrics_manager = MetricsManager()

        # Add default collector
        if HAS_PROMETHEUS:
            _global_metrics_manager.add_collector(PrometheusCollector())
        else:
            _global_metrics_manager.add_collector(InMemoryCollector())

    return _global_metrics_manager


def setup_metrics(
    service_name: str = "whitehorse_service",
    enable_prometheus: bool = True,
    prometheus_port: Optional[int] = None,
) -> MetricsManager:
    """
    Setup global metrics with common configuration.

    Args:
        service_name: Service name for metrics
        enable_prometheus: Whether to enable Prometheus collector
        prometheus_port: Port for Prometheus HTTP server

    Returns:
        Configured MetricsManager instance
    """
    global _global_metrics_manager
    _global_metrics_manager = MetricsManager(service_name)

    if enable_prometheus and HAS_PROMETHEUS:
        prometheus_collector = PrometheusCollector(service_name)
        _global_metrics_manager.add_collector(prometheus_collector)

        if prometheus_port:
            prometheus_collector.start_http_server(prometheus_port)
    else:
        _global_metrics_manager.add_collector(InMemoryCollector())

    logger.info(f"Setup metrics for service: {service_name}")
    return _global_metrics_manager
