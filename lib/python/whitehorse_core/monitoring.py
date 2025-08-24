"""
Monitoring Client Module

Provides comprehensive monitoring integration with GCP Cloud Operations,
metrics collection, alerting, and observability features.
"""

import json
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

try:
    from google.cloud import logging as cloud_logging
    from google.cloud import monitoring_v3
    from google.cloud.monitoring_v3 import query

    HAS_GCP_MONITORING = True
except ImportError:
    HAS_GCP_MONITORING = False

try:
    from prometheus_client import Counter, Gauge, Histogram, Summary, start_http_server
    from prometheus_client.core import CollectorRegistry

    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

from .config import get_config
from .errors import ExternalServiceError, ValidationError
from .logging import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Metric type enumeration."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricDefinition:
    """Metric definition configuration."""

    name: str
    metric_type: MetricType
    description: str
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # For histograms
    unit: Optional[str] = None


@dataclass
class Alert:
    """Alert information."""

    id: str
    name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class HealthCheck:
    """Health check definition."""

    name: str
    check_function: Callable[[], bool]
    description: str
    interval_seconds: int = 60
    timeout_seconds: int = 30
    enabled: bool = True


class MonitoringClient:
    """
    Central monitoring client for metrics collection, alerting, and health checks.
    Integrates with GCP Cloud Monitoring and Prometheus.
    """

    def __init__(self, service_name: str = "whitehorse-service"):
        """
        Initialize monitoring client.

        Args:
            service_name: Name of the service for monitoring identification
        """
        self.service_name = service_name
        self.config = get_config()
        self.metrics: Dict[str, Any] = {}
        self.health_checks: Dict[str, HealthCheck] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.monitoring_lock = threading.Lock()

        # Initialize clients
        self.gcp_client = None
        self.prometheus_registry = None

        self._initialize_gcp_monitoring()
        self._initialize_prometheus()
        self._setup_default_metrics()
        self._setup_default_health_checks()

    def _initialize_gcp_monitoring(self) -> None:
        """Initialize GCP Cloud Monitoring client."""
        if not HAS_GCP_MONITORING:
            logger.warning("GCP monitoring libraries not available")
            return

        try:
            project_id = getattr(self.config, "gcp_project", None) or os.environ.get(
                "GCP_PROJECT"
            )
            if project_id:
                self.gcp_client = monitoring_v3.MetricServiceClient()
                self.project_name = f"projects/{project_id}"
                logger.info("GCP Cloud Monitoring initialized", project=project_id)
            else:
                logger.warning("GCP project not configured, skipping GCP monitoring")
        except Exception as e:
            logger.error(f"Failed to initialize GCP monitoring: {e}")

    def _initialize_prometheus(self) -> None:
        """Initialize Prometheus metrics."""
        if not HAS_PROMETHEUS:
            logger.warning("Prometheus libraries not available")
            return

        try:
            self.prometheus_registry = CollectorRegistry()
            logger.info("Prometheus monitoring initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Prometheus: {e}")

    def _setup_default_metrics(self) -> None:
        """Setup default metrics for the service."""
        default_metrics = [
            MetricDefinition(
                name="requests_total",
                metric_type=MetricType.COUNTER,
                description="Total number of requests",
                labels=["method", "status", "endpoint"],
            ),
            MetricDefinition(
                name="request_duration_seconds",
                metric_type=MetricType.HISTOGRAM,
                description="Request duration in seconds",
                labels=["method", "endpoint"],
                buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            ),
            MetricDefinition(
                name="active_connections",
                metric_type=MetricType.GAUGE,
                description="Number of active connections",
                labels=["type"],
            ),
            MetricDefinition(
                name="errors_total",
                metric_type=MetricType.COUNTER,
                description="Total number of errors",
                labels=["type", "severity"],
            ),
            MetricDefinition(
                name="deployment_info",
                metric_type=MetricType.GAUGE,
                description="Deployment information",
                labels=["version", "environment", "service"],
            ),
        ]

        for metric_def in default_metrics:
            self.register_metric(metric_def)

    def _setup_default_health_checks(self) -> None:
        """Setup default health checks."""

        def check_memory_usage() -> bool:
            """Check if memory usage is within acceptable limits."""
            try:
                import psutil

                memory_percent = psutil.virtual_memory().percent
                return memory_percent < 90  # Alert if memory usage > 90%
            except ImportError:
                return True  # Assume healthy if psutil not available

        def check_disk_space() -> bool:
            """Check if disk space is within acceptable limits."""
            try:
                import psutil

                disk_usage = psutil.disk_usage("/").percent
                return disk_usage < 90  # Alert if disk usage > 90%
            except ImportError:
                return True  # Assume healthy if psutil not available

        def check_service_connectivity() -> bool:
            """Check basic service connectivity."""
            # This would check database, external APIs, etc.
            return True  # Placeholder

        default_health_checks = [
            HealthCheck(
                name="memory_usage",
                check_function=check_memory_usage,
                description="Check system memory usage",
                interval_seconds=60,
            ),
            HealthCheck(
                name="disk_space",
                check_function=check_disk_space,
                description="Check disk space usage",
                interval_seconds=300,  # 5 minutes
            ),
            HealthCheck(
                name="service_connectivity",
                check_function=check_service_connectivity,
                description="Check service connectivity",
                interval_seconds=30,
            ),
        ]

        for health_check in default_health_checks:
            self.register_health_check(health_check)

    def register_metric(self, metric_def: MetricDefinition) -> None:
        """
        Register a new metric.

        Args:
            metric_def: Metric definition
        """
        try:
            metric_name = f"{self.service_name}_{metric_def.name}"

            # Create Prometheus metric if available
            prometheus_metric = None
            if self.prometheus_registry:
                if metric_def.metric_type == MetricType.COUNTER:
                    prometheus_metric = Counter(
                        metric_name,
                        metric_def.description,
                        metric_def.labels,
                        registry=self.prometheus_registry,
                    )
                elif metric_def.metric_type == MetricType.GAUGE:
                    prometheus_metric = Gauge(
                        metric_name,
                        metric_def.description,
                        metric_def.labels,
                        registry=self.prometheus_registry,
                    )
                elif metric_def.metric_type == MetricType.HISTOGRAM:
                    prometheus_metric = Histogram(
                        metric_name,
                        metric_def.description,
                        metric_def.labels,
                        buckets=metric_def.buckets,
                        registry=self.prometheus_registry,
                    )
                elif metric_def.metric_type == MetricType.SUMMARY:
                    prometheus_metric = Summary(
                        metric_name,
                        metric_def.description,
                        metric_def.labels,
                        registry=self.prometheus_registry,
                    )

            self.metrics[metric_def.name] = {
                "definition": metric_def,
                "prometheus_metric": prometheus_metric,
                "gcp_metric_type": f"custom.googleapis.com/{metric_name}",
            }

            logger.info(f"Registered metric: {metric_def.name}")

        except Exception as e:
            logger.error(f"Failed to register metric {metric_def.name}: {e}")
            raise ValidationError(f"Failed to register metric: {e}")

    def record_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        labels: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record a metric value.

        Args:
            metric_name: Name of the metric
            value: Metric value
            labels: Metric labels
            timestamp: Optional timestamp (defaults to now)
        """
        if metric_name not in self.metrics:
            logger.warning(f"Unknown metric: {metric_name}")
            return

        labels = labels or {}
        timestamp = timestamp or datetime.utcnow()

        metric_info = self.metrics[metric_name]
        metric_def = metric_info["definition"]

        try:
            # Record to Prometheus if available
            prometheus_metric = metric_info.get("prometheus_metric")
            if prometheus_metric:
                if metric_def.metric_type == MetricType.COUNTER:
                    prometheus_metric.labels(**labels).inc(value)
                elif metric_def.metric_type == MetricType.GAUGE:
                    prometheus_metric.labels(**labels).set(value)
                elif metric_def.metric_type == MetricType.HISTOGRAM:
                    prometheus_metric.labels(**labels).observe(value)
                elif metric_def.metric_type == MetricType.SUMMARY:
                    prometheus_metric.labels(**labels).observe(value)

            # Record to GCP if available
            if self.gcp_client:
                self._record_gcp_metric(metric_info, value, labels, timestamp)

        except Exception as e:
            logger.error(f"Failed to record metric {metric_name}: {e}")

    def _record_gcp_metric(
        self,
        metric_info: Dict[str, Any],
        value: Union[int, float],
        labels: Dict[str, str],
        timestamp: datetime,
    ) -> None:
        """Record metric to GCP Cloud Monitoring."""
        try:
            from google.cloud.monitoring_v3 import Point, TimeSeries
            from google.protobuf.timestamp_pb2 import Timestamp

            # Create time series
            series = TimeSeries()
            series.metric.type = metric_info["gcp_metric_type"]
            series.resource.type = "generic_node"
            series.resource.labels["location"] = getattr(
                self.config, "gcp_region", "us-central1"
            )
            series.resource.labels["namespace"] = self.service_name
            series.resource.labels["node_id"] = "default"

            # Add labels
            for key, val in labels.items():
                series.metric.labels[key] = str(val)

            # Add point
            point = Point()
            point.value.double_value = float(value)

            # Set timestamp
            timestamp_pb = Timestamp()
            timestamp_pb.FromDatetime(timestamp)
            point.interval.end_time = timestamp_pb

            series.points = [point]

            # Write to GCP
            self.gcp_client.create_time_series(
                name=self.project_name, time_series=[series]
            )

        except Exception as e:
            logger.error(f"Failed to record GCP metric: {e}")

    @contextmanager
    def measure_time(self, metric_name: str, labels: Optional[Dict[str, str]] = None):
        """
        Context manager to measure execution time.

        Args:
            metric_name: Name of the histogram metric
            labels: Optional labels
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_metric(metric_name, duration, labels)

    def increment_counter(
        self,
        metric_name: str,
        value: Union[int, float] = 1,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Increment a counter metric.

        Args:
            metric_name: Name of the counter metric
            value: Value to increment by
            labels: Optional labels
        """
        self.record_metric(metric_name, value, labels)

    def set_gauge(
        self,
        metric_name: str,
        value: Union[int, float],
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Set a gauge metric value.

        Args:
            metric_name: Name of the gauge metric
            value: Value to set
            labels: Optional labels
        """
        self.record_metric(metric_name, value, labels)

    def register_health_check(self, health_check: HealthCheck) -> None:
        """
        Register a health check.

        Args:
            health_check: Health check definition
        """
        self.health_checks[health_check.name] = health_check
        logger.info(f"Registered health check: {health_check.name}")

    def run_health_check(self, check_name: str) -> Dict[str, Any]:
        """
        Run a specific health check.

        Args:
            check_name: Name of the health check

        Returns:
            Health check result
        """
        if check_name not in self.health_checks:
            return {
                "name": check_name,
                "status": "unknown",
                "error": "Health check not found",
            }

        health_check = self.health_checks[check_name]

        if not health_check.enabled:
            return {
                "name": check_name,
                "status": "disabled",
                "message": "Health check disabled",
            }

        start_time = time.time()

        try:
            # Run the health check with timeout
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("Health check timed out")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(health_check.timeout_seconds)

            try:
                result = health_check.check_function()
                signal.alarm(0)  # Cancel timeout

                duration = time.time() - start_time

                return {
                    "name": check_name,
                    "status": "healthy" if result else "unhealthy",
                    "duration_seconds": duration,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            except TimeoutError:
                return {
                    "name": check_name,
                    "status": "timeout",
                    "error": f"Health check timed out after {health_check.timeout_seconds} seconds",
                    "timestamp": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            duration = time.time() - start_time
            return {
                "name": check_name,
                "status": "error",
                "error": str(e),
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def run_all_health_checks(self) -> Dict[str, Any]:
        """
        Run all registered health checks.

        Returns:
            Comprehensive health check results
        """
        results = {
            "overall_status": "healthy",
            "checks": {},
            "summary": {
                "total": len(self.health_checks),
                "healthy": 0,
                "unhealthy": 0,
                "disabled": 0,
                "errors": 0,
                "timeouts": 0,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        for check_name in self.health_checks:
            check_result = self.run_health_check(check_name)
            results["checks"][check_name] = check_result

            status = check_result["status"]
            if status == "healthy":
                results["summary"]["healthy"] += 1
            elif status == "unhealthy":
                results["summary"]["unhealthy"] += 1
                results["overall_status"] = "degraded"
            elif status == "disabled":
                results["summary"]["disabled"] += 1
            elif status == "error":
                results["summary"]["errors"] += 1
                results["overall_status"] = "unhealthy"
            elif status == "timeout":
                results["summary"]["timeouts"] += 1
                results["overall_status"] = "unhealthy"

        # If we have any unhealthy checks and no errors/timeouts, status is degraded
        if (
            results["summary"]["unhealthy"] > 0
            and results["summary"]["errors"] == 0
            and results["summary"]["timeouts"] == 0
        ):
            results["overall_status"] = "degraded"

        return results

    def create_alert(
        self,
        name: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
        labels: Optional[Dict[str, str]] = None,
    ) -> Alert:
        """
        Create and register an alert.

        Args:
            name: Alert name
            message: Alert message
            severity: Alert severity
            labels: Optional labels

        Returns:
            Created Alert instance
        """
        import uuid

        alert = Alert(
            id=str(uuid.uuid4()),
            name=name,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            labels=labels or {},
        )

        with self.monitoring_lock:
            self.active_alerts[alert.id] = alert

        logger.warning(
            f"Alert created: {name}",
            alert_id=alert.id,
            severity=severity.value,
            message=message,
        )

        # Record alert metric
        self.increment_counter(
            "alerts_total", labels={"severity": severity.value, "name": name}
        )

        return alert

    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an active alert.

        Args:
            alert_id: ID of alert to resolve

        Returns:
            True if resolved, False if not found
        """
        with self.monitoring_lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()

                # Move to history
                self.alert_history.append(alert)
                del self.active_alerts[alert_id]

                logger.info(f"Alert resolved: {alert.name}", alert_id=alert_id)
                return True

        return False

    def get_active_alerts(
        self, severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """
        Get active alerts, optionally filtered by severity.

        Args:
            severity: Optional severity filter

        Returns:
            List of active alerts
        """
        alerts = list(self.active_alerts.values())

        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]

        # Sort by timestamp descending
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        return alerts

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of all registered metrics.

        Returns:
            Metrics summary
        """
        summary = {
            "total_metrics": len(self.metrics),
            "metrics_by_type": {},
            "prometheus_enabled": self.prometheus_registry is not None,
            "gcp_enabled": self.gcp_client is not None,
            "metrics": {},
        }

        for metric_name, metric_info in self.metrics.items():
            metric_def = metric_info["definition"]
            metric_type = metric_def.metric_type.value

            # Count by type
            summary["metrics_by_type"][metric_type] = (
                summary["metrics_by_type"].get(metric_type, 0) + 1
            )

            # Add metric details
            summary["metrics"][metric_name] = {
                "type": metric_type,
                "description": metric_def.description,
                "labels": metric_def.labels,
                "unit": metric_def.unit,
            }

        return summary

    def start_prometheus_server(self, port: int = 8000) -> bool:
        """
        Start Prometheus metrics server.

        Args:
            port: Port to serve metrics on

        Returns:
            True if started successfully
        """
        if not HAS_PROMETHEUS:
            logger.error("Prometheus not available")
            return False

        try:
            start_http_server(port, registry=self.prometheus_registry)
            logger.info(f"Prometheus metrics server started on port {port}")
            return True
        except Exception as e:
            logger.error(f"Failed to start Prometheus server: {e}")
            return False

    def export_metrics(self, format_type: str = "prometheus") -> str:
        """
        Export metrics in specified format.

        Args:
            format_type: Export format (prometheus, json)

        Returns:
            Formatted metrics string
        """
        if format_type == "prometheus" and HAS_PROMETHEUS:
            from prometheus_client import generate_latest

            return generate_latest(self.prometheus_registry).decode("utf-8")

        elif format_type == "json":
            metrics_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "service": self.service_name,
                "metrics": self.get_metrics_summary(),
            }
            return json.dumps(metrics_data, indent=2)

        else:
            raise ValidationError(f"Unsupported export format: {format_type}")

    def query_gcp_metrics(
        self,
        metric_filter: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query GCP Cloud Monitoring metrics.

        Args:
            metric_filter: Metric filter query
            start_time: Start time for query
            end_time: End time for query (defaults to now)

        Returns:
            List of metric data points
        """
        if not self.gcp_client:
            raise ExternalServiceError("GCP monitoring not available")

        end_time = end_time or datetime.utcnow()

        try:
            from google.cloud.monitoring_v3 import ListTimeSeriesRequest, TimeInterval
            from google.protobuf.timestamp_pb2 import Timestamp

            # Create time interval
            interval = TimeInterval()
            interval.end_time = Timestamp()
            interval.end_time.FromDatetime(end_time)
            interval.start_time = Timestamp()
            interval.start_time.FromDatetime(start_time)

            # Query metrics
            request = ListTimeSeriesRequest(
                name=self.project_name,
                filter=metric_filter,
                interval=interval,
                view=ListTimeSeriesRequest.TimeSeriesView.FULL,
            )

            results = []
            for time_series in self.gcp_client.list_time_series(request=request):
                for point in time_series.points:
                    results.append(
                        {
                            "metric_type": time_series.metric.type,
                            "labels": dict(time_series.metric.labels),
                            "value": point.value.double_value,
                            "timestamp": point.interval.end_time.ToDatetime().isoformat(),
                        }
                    )

            return results

        except Exception as e:
            logger.error(f"Failed to query GCP metrics: {e}")
            raise ExternalServiceError(f"GCP metrics query failed: {e}")

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on monitoring client.

        Returns:
            Health check results
        """
        try:
            health = {
                "status": "healthy",
                "service_name": self.service_name,
                "prometheus_available": HAS_PROMETHEUS,
                "gcp_monitoring_available": HAS_GCP_MONITORING,
                "prometheus_registry": self.prometheus_registry is not None,
                "gcp_client": self.gcp_client is not None,
                "registered_metrics": len(self.metrics),
                "registered_health_checks": len(self.health_checks),
                "active_alerts": len(self.active_alerts),
            }

            # Run a quick health check
            health_results = self.run_all_health_checks()
            if health_results["overall_status"] != "healthy":
                health["status"] = "degraded"
                health["health_check_issues"] = health_results["summary"]

            return health

        except Exception as e:
            logger.error(f"Monitoring client health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "service_name": self.service_name,
            }
