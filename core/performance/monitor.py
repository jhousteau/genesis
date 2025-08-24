"""
Performance Monitor - CRAFT Authenticate Component
GCP Cloud Monitoring integration for performance alerting and monitoring

This module implements comprehensive performance monitoring with GCP Cloud Operations,
providing real-time alerting and automated performance issue detection.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from google.api_core import exceptions as gcp_exceptions
    from google.cloud import monitoring_v3
    from google.cloud.monitoring_v3 import AlertPolicy, TimeSeries

    GCP_MONITORING_AVAILABLE = True
except ImportError:
    GCP_MONITORING_AVAILABLE = False

try:
    from google.cloud import logging as cloud_logging

    GCP_LOGGING_AVAILABLE = True
except ImportError:
    GCP_LOGGING_AVAILABLE = False

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""

    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class PerformanceThreshold(Enum):
    """Performance threshold types."""

    RESPONSE_TIME = "response_time"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


@dataclass
class PerformanceAlert:
    """Performance alert definition."""

    # Alert identification
    alert_id: str
    alert_name: str
    severity: AlertSeverity

    # Threshold configuration
    threshold_type: PerformanceThreshold
    threshold_value: float
    comparison_operator: str  # GREATER_THAN, LESS_THAN, EQUAL
    duration_minutes: int = 5

    # Targeting
    service_filters: Dict[str, str] = field(default_factory=dict)
    environment_filters: List[str] = field(default_factory=list)

    # Notification
    notification_channels: List[str] = field(default_factory=list)
    enable_email: bool = True
    enable_slack: bool = False
    enable_pagerduty: bool = False

    # Metadata
    description: str = ""
    documentation_url: str = ""
    created_at: Optional[datetime] = None
    enabled: bool = True


@dataclass
class PerformanceIncident:
    """Performance incident record."""

    # Incident identification
    incident_id: str
    alert_id: str
    alert_name: str
    severity: AlertSeverity

    # Incident details
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    current_value: float = 0.0
    threshold_value: float = 0.0

    # Context
    service_name: str = ""
    environment: str = ""
    affected_resources: List[str] = field(default_factory=list)

    # Resolution
    status: str = "OPEN"  # OPEN, ACKNOWLEDGED, RESOLVED
    assigned_to: str = ""
    resolution_notes: str = ""

    # Impact assessment
    estimated_impact: str = ""
    user_impact_count: int = 0
    duration_minutes: int = 0

    @property
    def is_resolved(self) -> bool:
        return self.resolved_at is not None


class PerformanceMonitor:
    """
    Performance monitoring system implementing CRAFT Authenticate methodology.

    Provides comprehensive performance monitoring with:
    - GCP Cloud Monitoring integration
    - Real-time performance alerting
    - Automated incident management
    - Performance SLI/SLO tracking
    - Custom dashboard creation
    """

    def __init__(
        self,
        gcp_project_id: Optional[str] = None,
        metric_prefix: str = "genesis.performance",
    ):
        self.logger = logging.getLogger(f"{__name__}.PerformanceMonitor")

        # GCP Configuration
        self.gcp_project_id = gcp_project_id or self._get_gcp_project_id()
        self.metric_prefix = metric_prefix

        # Initialize GCP clients
        self.monitoring_client = None
        self.logging_client = None

        if GCP_MONITORING_AVAILABLE and self.gcp_project_id:
            try:
                self.monitoring_client = monitoring_v3.MetricServiceClient()
                self.alert_policy_client = monitoring_v3.AlertPolicyServiceClient()
                self.notification_client = (
                    monitoring_v3.NotificationChannelServiceClient()
                )
                self.logger.info("GCP Cloud Monitoring clients initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize GCP monitoring: {e}")

        if GCP_LOGGING_AVAILABLE and self.gcp_project_id:
            try:
                self.logging_client = cloud_logging.Client(project=self.gcp_project_id)
                self.logger.info("GCP Cloud Logging client initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize GCP logging: {e}")

        # Alert management
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.active_incidents: Dict[str, PerformanceIncident] = {}
        self.alert_history: List[PerformanceIncident] = []

        # Performance tracking
        self.performance_metrics: Dict[str, List[float]] = {}
        self.metric_timestamps: Dict[str, List[datetime]] = {}

        self.logger.info("PerformanceMonitor initialized")

    def create_performance_alert(self, alert: PerformanceAlert) -> bool:
        """Create a performance alert in GCP Cloud Monitoring."""
        if not self.alert_policy_client or not self.gcp_project_id:
            self.logger.warning("GCP Alert Policy client not available")
            return False

        try:
            project_name = f"projects/{self.gcp_project_id}"

            # Create alert policy
            policy = self._build_alert_policy(alert)

            created_policy = self.alert_policy_client.create_alert_policy(
                name=project_name, alert_policy=policy
            )

            # Update alert with GCP policy ID
            alert.alert_id = created_policy.name
            alert.created_at = datetime.now()

            # Register alert locally
            self.active_alerts[alert.alert_id] = alert

            self.logger.info(f"Created performance alert: {alert.alert_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create performance alert: {e}")
            return False

    def delete_performance_alert(self, alert_id: str) -> bool:
        """Delete a performance alert."""
        if not self.alert_policy_client:
            return False

        try:
            self.alert_policy_client.delete_alert_policy(name=alert_id)

            # Remove from local registry
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]

            self.logger.info(f"Deleted performance alert: {alert_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete alert: {e}")
            return False

    def create_response_time_alert(
        self,
        service_name: str,
        threshold_ms: float = 500,
        severity: AlertSeverity = AlertSeverity.WARNING,
        environment: str = "production",
    ) -> PerformanceAlert:
        """Create a response time alert for a service."""
        alert = PerformanceAlert(
            alert_id="",  # Will be set when created in GCP
            alert_name=f"High Response Time - {service_name}",
            severity=severity,
            threshold_type=PerformanceThreshold.RESPONSE_TIME,
            threshold_value=threshold_ms,
            comparison_operator="GREATER_THAN",
            duration_minutes=5,
            service_filters={"service_name": service_name},
            environment_filters=[environment],
            description=f"Response time for {service_name} exceeds {threshold_ms}ms",
            enabled=True,
        )

        if self.create_performance_alert(alert):
            return alert
        else:
            raise RuntimeError(
                f"Failed to create response time alert for {service_name}"
            )

    def create_error_rate_alert(
        self,
        service_name: str,
        threshold_percent: float = 5.0,
        severity: AlertSeverity = AlertSeverity.CRITICAL,
        environment: str = "production",
    ) -> PerformanceAlert:
        """Create an error rate alert for a service."""
        alert = PerformanceAlert(
            alert_id="",
            alert_name=f"High Error Rate - {service_name}",
            severity=severity,
            threshold_type=PerformanceThreshold.ERROR_RATE,
            threshold_value=threshold_percent,
            comparison_operator="GREATER_THAN",
            duration_minutes=2,
            service_filters={"service_name": service_name},
            environment_filters=[environment],
            description=f"Error rate for {service_name} exceeds {threshold_percent}%",
            enabled=True,
        )

        if self.create_performance_alert(alert):
            return alert
        else:
            raise RuntimeError(f"Failed to create error rate alert for {service_name}")

    def record_performance_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record a performance metric."""
        timestamp = timestamp or datetime.now()
        labels = labels or {}

        # Store locally for trend analysis
        metric_key = f"{metric_name}:{':'.join(f'{k}={v}' for k, v in labels.items())}"

        if metric_key not in self.performance_metrics:
            self.performance_metrics[metric_key] = []
            self.metric_timestamps[metric_key] = []

        self.performance_metrics[metric_key].append(value)
        self.metric_timestamps[metric_key].append(timestamp)

        # Keep only recent metrics (last 1000 points)
        if len(self.performance_metrics[metric_key]) > 1000:
            self.performance_metrics[metric_key] = self.performance_metrics[metric_key][
                -1000:
            ]
            self.metric_timestamps[metric_key] = self.metric_timestamps[metric_key][
                -1000:
            ]

        # Send to GCP Monitoring
        if self.monitoring_client:
            asyncio.create_task(
                self._send_metric_to_gcp(metric_name, value, labels, timestamp)
            )

    def check_performance_thresholds(self) -> List[PerformanceIncident]:
        """Check current metrics against defined thresholds."""
        incidents = []

        for alert_id, alert in self.active_alerts.items():
            if not alert.enabled:
                continue

            # Get relevant metrics
            metric_values = self._get_recent_metrics_for_alert(alert)

            if not metric_values:
                continue

            # Check threshold
            current_value = metric_values[-1]  # Most recent value
            threshold_breached = self._evaluate_threshold(
                current_value, alert.threshold_value, alert.comparison_operator
            )

            if threshold_breached:
                # Check if this is a new incident
                existing_incident = self._find_active_incident(alert_id)

                if not existing_incident:
                    # Create new incident
                    incident = self._create_incident(alert, current_value)
                    incidents.append(incident)
                    self.active_incidents[incident.incident_id] = incident

                    # Log the incident
                    self._log_performance_incident(incident)
                else:
                    # Update existing incident
                    existing_incident.current_value = current_value
                    existing_incident.duration_minutes = int(
                        (
                            datetime.now() - existing_incident.triggered_at
                        ).total_seconds()
                        / 60
                    )

        return incidents

    def resolve_incident(
        self, incident_id: str, resolution_notes: str = "", assigned_to: str = ""
    ) -> bool:
        """Resolve a performance incident."""
        if incident_id not in self.active_incidents:
            return False

        incident = self.active_incidents[incident_id]
        incident.resolved_at = datetime.now()
        incident.status = "RESOLVED"
        incident.resolution_notes = resolution_notes
        incident.assigned_to = assigned_to
        incident.duration_minutes = int(
            (incident.resolved_at - incident.triggered_at).total_seconds() / 60
        )

        # Move to history
        self.alert_history.append(incident)
        del self.active_incidents[incident_id]

        self.logger.info(
            f"Resolved incident {incident_id} after {incident.duration_minutes} minutes"
        )
        return True

    def get_performance_summary(
        self, service_name: Optional[str] = None, hours: int = 24
    ) -> Dict[str, Any]:
        """Get performance summary for services."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        summary = {
            "summary_period_hours": hours,
            "active_incidents": len(self.active_incidents),
            "resolved_incidents_period": 0,
            "average_resolution_time_minutes": 0,
            "top_performance_issues": [],
            "service_performance": {},
            "alert_statistics": {
                "total_alerts": len(self.active_alerts),
                "enabled_alerts": sum(
                    1 for a in self.active_alerts.values() if a.enabled
                ),
                "critical_alerts": sum(
                    1
                    for a in self.active_alerts.values()
                    if a.severity == AlertSeverity.CRITICAL
                ),
            },
        }

        # Calculate resolved incidents in period
        recent_resolved = [
            i
            for i in self.alert_history
            if i.resolved_at and i.resolved_at >= cutoff_time
        ]
        summary["resolved_incidents_period"] = len(recent_resolved)

        # Calculate average resolution time
        if recent_resolved:
            avg_resolution = sum(i.duration_minutes for i in recent_resolved) / len(
                recent_resolved
            )
            summary["average_resolution_time_minutes"] = avg_resolution

        # Get service-specific metrics
        service_metrics = self._calculate_service_metrics(service_name, cutoff_time)
        summary["service_performance"] = service_metrics

        # Identify top performance issues
        summary["top_performance_issues"] = self._identify_top_issues(cutoff_time)

        return summary

    def create_performance_dashboard(
        self, dashboard_name: str, services: List[str], environment: str = "production"
    ) -> Dict[str, Any]:
        """Create a performance monitoring dashboard configuration."""
        dashboard_config = {
            "dashboard_name": dashboard_name,
            "environment": environment,
            "services": services,
            "widgets": [],
        }

        # Response time widget
        dashboard_config["widgets"].append(
            {
                "type": "line_chart",
                "title": "Response Time",
                "metrics": [
                    {
                        "metric": f"custom.googleapis.com/{self.metric_prefix}/response_time",
                        "filters": {
                            "environment": environment,
                            "service_name": services,
                        },
                        "aggregation": "ALIGN_MEAN",
                    }
                ],
                "thresholds": [
                    {"value": 200, "label": "Good", "color": "green"},
                    {"value": 500, "label": "Warning", "color": "yellow"},
                    {"value": 1000, "label": "Critical", "color": "red"},
                ],
            }
        )

        # Error rate widget
        dashboard_config["widgets"].append(
            {
                "type": "line_chart",
                "title": "Error Rate",
                "metrics": [
                    {
                        "metric": f"custom.googleapis.com/{self.metric_prefix}/error_rate",
                        "filters": {
                            "environment": environment,
                            "service_name": services,
                        },
                        "aggregation": "ALIGN_MEAN",
                    }
                ],
                "thresholds": [
                    {"value": 1, "label": "Good", "color": "green"},
                    {"value": 5, "label": "Warning", "color": "yellow"},
                    {"value": 10, "label": "Critical", "color": "red"},
                ],
            }
        )

        # Throughput widget
        dashboard_config["widgets"].append(
            {
                "type": "line_chart",
                "title": "Requests per Second",
                "metrics": [
                    {
                        "metric": f"custom.googleapis.com/{self.metric_prefix}/throughput",
                        "filters": {
                            "environment": environment,
                            "service_name": services,
                        },
                        "aggregation": "ALIGN_RATE",
                    }
                ],
            }
        )

        # Resource utilization widget
        dashboard_config["widgets"].append(
            {
                "type": "stacked_area",
                "title": "Resource Utilization",
                "metrics": [
                    {
                        "metric": f"custom.googleapis.com/{self.metric_prefix}/cpu_usage",
                        "label": "CPU %",
                        "filters": {
                            "environment": environment,
                            "service_name": services,
                        },
                        "aggregation": "ALIGN_MEAN",
                    },
                    {
                        "metric": f"custom.googleapis.com/{self.metric_prefix}/memory_usage",
                        "label": "Memory %",
                        "filters": {
                            "environment": environment,
                            "service_name": services,
                        },
                        "aggregation": "ALIGN_MEAN",
                    },
                ],
            }
        )

        self.logger.info(f"Created dashboard configuration: {dashboard_name}")
        return dashboard_config

    async def _send_metric_to_gcp(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, str],
        timestamp: datetime,
    ) -> None:
        """Send metric to GCP Cloud Monitoring."""
        if not self.monitoring_client or not self.gcp_project_id:
            return

        try:
            project_name = f"projects/{self.gcp_project_id}"

            series = TimeSeries()
            series.metric.type = (
                f"custom.googleapis.com/{self.metric_prefix}/{metric_name}"
            )

            # Add labels
            for key, val in labels.items():
                series.metric.labels[key] = str(val)

            # Add resource labels
            series.resource.type = "generic_node"
            series.resource.labels["location"] = "global"
            series.resource.labels["namespace"] = self.metric_prefix
            series.resource.labels["node_id"] = "performance-monitor"

            # Add data point
            point = series.points.add()
            point.value.double_value = value

            # Set timestamp
            timestamp_seconds = timestamp.timestamp()
            point.interval.end_time.seconds = int(timestamp_seconds)
            point.interval.end_time.nanos = int(
                (timestamp_seconds - int(timestamp_seconds)) * 10**9
            )

            self.monitoring_client.create_time_series(
                name=project_name, time_series=[series]
            )

        except Exception as e:
            self.logger.error(f"Failed to send metric to GCP: {e}")

    def _build_alert_policy(self, alert: PerformanceAlert) -> AlertPolicy:
        """Build GCP AlertPolicy from PerformanceAlert."""
        policy = AlertPolicy()
        policy.display_name = alert.alert_name
        policy.documentation.content = alert.description

        if alert.documentation_url:
            policy.documentation.mime_type = "text/markdown"
            policy.documentation.content += (
                f"\n\nDocumentation: {alert.documentation_url}"
            )

        # Create condition
        condition = policy.conditions.add()
        condition.display_name = f"{alert.alert_name} Condition"

        # Set metric threshold
        threshold = condition.condition_threshold
        threshold.comparison = self._get_gcp_comparison_operator(
            alert.comparison_operator
        )
        threshold.threshold_value.double_value = alert.threshold_value

        # Set duration
        duration = threshold.duration
        duration.seconds = alert.duration_minutes * 60

        # Set metric filter
        metric_filter = threshold.filter
        metric_type = self._get_metric_type_for_threshold(alert.threshold_type)
        metric_filter = f'metric.type="{metric_type}"'

        # Add service filters
        if alert.service_filters:
            for key, value in alert.service_filters.items():
                metric_filter += f' AND metric.label.{key}="{value}"'

        # Add environment filters
        if alert.environment_filters:
            env_filter = " OR ".join(
                f'metric.label.environment="{env}"' for env in alert.environment_filters
            )
            metric_filter += f" AND ({env_filter})"

        threshold.filter = metric_filter

        # Set aggregation
        aggregation = threshold.aggregations.add()
        aggregation.alignment_period.seconds = 60  # 1 minute
        aggregation.per_series_aligner = monitoring_v3.Aggregation.Aligner.ALIGN_MEAN
        aggregation.cross_series_reducer = monitoring_v3.Aggregation.Reducer.REDUCE_MEAN

        # Set notification channels (if configured)
        if alert.notification_channels:
            for channel in alert.notification_channels:
                policy.notification_channels.append(channel)

        # Set enabled state
        policy.enabled.value = alert.enabled

        return policy

    def _get_gcp_comparison_operator(
        self, operator: str
    ) -> monitoring_v3.ComparisonType:
        """Convert string comparison operator to GCP enum."""
        operator_map = {
            "GREATER_THAN": monitoring_v3.ComparisonType.COMPARISON_GREATER_THAN,
            "LESS_THAN": monitoring_v3.ComparisonType.COMPARISON_LESS_THAN,
            "EQUAL": monitoring_v3.ComparisonType.COMPARISON_EQUAL,
            "GREATER_THAN_OR_EQUAL": monitoring_v3.ComparisonType.COMPARISON_GREATER_THAN_OR_EQUAL,
            "LESS_THAN_OR_EQUAL": monitoring_v3.ComparisonType.COMPARISON_LESS_THAN_OR_EQUAL,
        }
        return operator_map.get(
            operator, monitoring_v3.ComparisonType.COMPARISON_GREATER_THAN
        )

    def _get_metric_type_for_threshold(
        self, threshold_type: PerformanceThreshold
    ) -> str:
        """Get GCP metric type for threshold type."""
        type_map = {
            PerformanceThreshold.RESPONSE_TIME: f"custom.googleapis.com/{self.metric_prefix}/response_time",
            PerformanceThreshold.CPU_USAGE: f"custom.googleapis.com/{self.metric_prefix}/cpu_usage",
            PerformanceThreshold.MEMORY_USAGE: f"custom.googleapis.com/{self.metric_prefix}/memory_usage",
            PerformanceThreshold.ERROR_RATE: f"custom.googleapis.com/{self.metric_prefix}/error_rate",
            PerformanceThreshold.THROUGHPUT: f"custom.googleapis.com/{self.metric_prefix}/throughput",
        }
        return type_map.get(
            threshold_type, f"custom.googleapis.com/{self.metric_prefix}/generic"
        )

    def _get_recent_metrics_for_alert(self, alert: PerformanceAlert) -> List[float]:
        """Get recent metric values relevant to an alert."""
        # This is a simplified implementation
        # In practice, you'd query the specific metrics based on alert configuration

        metric_type = alert.threshold_type.value
        service_filters = alert.service_filters

        # Find matching metrics
        matching_metrics = []
        for metric_key, values in self.performance_metrics.items():
            if metric_type in metric_key:
                # Check service filters
                if service_filters:
                    matches_filter = all(
                        f"{k}={v}" in metric_key for k, v in service_filters.items()
                    )
                    if not matches_filter:
                        continue

                # Get recent values (last 10 minutes)
                timestamps = self.metric_timestamps[metric_key]
                cutoff = datetime.now() - timedelta(minutes=10)
                recent_indices = [i for i, ts in enumerate(timestamps) if ts >= cutoff]

                if recent_indices:
                    matching_metrics.extend([values[i] for i in recent_indices])

        return matching_metrics

    def _evaluate_threshold(
        self, current_value: float, threshold: float, operator: str
    ) -> bool:
        """Evaluate if current value breaches threshold."""
        if operator == "GREATER_THAN":
            return current_value > threshold
        elif operator == "LESS_THAN":
            return current_value < threshold
        elif operator == "EQUAL":
            return abs(current_value - threshold) < 0.001  # Float comparison
        elif operator == "GREATER_THAN_OR_EQUAL":
            return current_value >= threshold
        elif operator == "LESS_THAN_OR_EQUAL":
            return current_value <= threshold

        return False

    def _find_active_incident(self, alert_id: str) -> Optional[PerformanceIncident]:
        """Find active incident for an alert."""
        for incident in self.active_incidents.values():
            if incident.alert_id == alert_id and not incident.is_resolved:
                return incident
        return None

    def _create_incident(
        self, alert: PerformanceAlert, current_value: float
    ) -> PerformanceIncident:
        """Create a new performance incident."""
        incident_id = (
            f"incident_{int(time.time())}_{alert.alert_name.replace(' ', '_')}"
        )

        # Extract service name from filters
        service_name = alert.service_filters.get("service_name", "unknown")
        environment = (
            alert.environment_filters[0] if alert.environment_filters else "unknown"
        )

        incident = PerformanceIncident(
            incident_id=incident_id,
            alert_id=alert.alert_id,
            alert_name=alert.alert_name,
            severity=alert.severity,
            triggered_at=datetime.now(),
            current_value=current_value,
            threshold_value=alert.threshold_value,
            service_name=service_name,
            environment=environment,
            status="OPEN",
        )

        return incident

    def _log_performance_incident(self, incident: PerformanceIncident) -> None:
        """Log performance incident."""
        self.logger.warning(
            f"PERFORMANCE_INCIDENT: {incident.alert_name} - "
            f"Current: {incident.current_value}, Threshold: {incident.threshold_value}, "
            f"Service: {incident.service_name}, Environment: {incident.environment}"
        )

        # Send to GCP Cloud Logging if available
        if self.logging_client:
            try:
                cloud_logger = self.logging_client.logger("performance-incidents")
                cloud_logger.log_struct(
                    {
                        "incident_id": incident.incident_id,
                        "alert_name": incident.alert_name,
                        "severity": incident.severity.value,
                        "service_name": incident.service_name,
                        "environment": incident.environment,
                        "current_value": incident.current_value,
                        "threshold_value": incident.threshold_value,
                        "triggered_at": incident.triggered_at.isoformat(),
                    },
                    severity=(
                        "WARNING"
                        if incident.severity == AlertSeverity.WARNING
                        else "ERROR"
                    ),
                )
            except Exception as e:
                self.logger.error(f"Failed to send incident to Cloud Logging: {e}")

    def _calculate_service_metrics(
        self, service_name: Optional[str], cutoff_time: datetime
    ) -> Dict[str, Any]:
        """Calculate service-specific performance metrics."""
        metrics = {}

        # Filter metrics by service if specified
        relevant_metrics = {}
        for metric_key, values in self.performance_metrics.items():
            if service_name and f"service_name={service_name}" not in metric_key:
                continue

            timestamps = self.metric_timestamps[metric_key]
            recent_indices = [i for i, ts in enumerate(timestamps) if ts >= cutoff_time]

            if recent_indices:
                relevant_metrics[metric_key] = [values[i] for i in recent_indices]

        # Calculate aggregated metrics
        if relevant_metrics:
            all_response_times = []
            all_error_rates = []
            all_cpu_usage = []
            all_memory_usage = []

            for metric_key, values in relevant_metrics.items():
                if "response_time" in metric_key:
                    all_response_times.extend(values)
                elif "error_rate" in metric_key:
                    all_error_rates.extend(values)
                elif "cpu_usage" in metric_key:
                    all_cpu_usage.extend(values)
                elif "memory_usage" in metric_key:
                    all_memory_usage.extend(values)

            if all_response_times:
                import statistics

                metrics["avg_response_time_ms"] = statistics.mean(all_response_times)
                metrics["p95_response_time_ms"] = sorted(all_response_times)[
                    int(0.95 * len(all_response_times))
                ]

            if all_error_rates:
                metrics["avg_error_rate_percent"] = statistics.mean(all_error_rates)

            if all_cpu_usage:
                metrics["avg_cpu_usage_percent"] = statistics.mean(all_cpu_usage)

            if all_memory_usage:
                metrics["avg_memory_usage_percent"] = statistics.mean(all_memory_usage)

        return metrics

    def _identify_top_issues(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Identify top performance issues in the time period."""
        issues = []

        # Recent resolved incidents
        recent_incidents = [
            i for i in self.alert_history if i.triggered_at >= cutoff_time
        ]

        # Group by alert name and count frequency
        issue_counts = {}
        for incident in recent_incidents:
            if incident.alert_name not in issue_counts:
                issue_counts[incident.alert_name] = {
                    "count": 0,
                    "total_duration_minutes": 0,
                    "avg_severity": [],
                    "affected_services": set(),
                }

            issue_counts[incident.alert_name]["count"] += 1
            issue_counts[incident.alert_name][
                "total_duration_minutes"
            ] += incident.duration_minutes
            issue_counts[incident.alert_name]["avg_severity"].append(
                incident.severity.value
            )
            issue_counts[incident.alert_name]["affected_services"].add(
                incident.service_name
            )

        # Convert to list and sort by frequency
        for alert_name, data in issue_counts.items():
            issues.append(
                {
                    "alert_name": alert_name,
                    "frequency": data["count"],
                    "total_duration_minutes": data["total_duration_minutes"],
                    "avg_duration_minutes": data["total_duration_minutes"]
                    / data["count"],
                    "most_common_severity": max(
                        set(data["avg_severity"]), key=data["avg_severity"].count
                    ),
                    "affected_services": list(data["affected_services"]),
                }
            )

        # Sort by frequency descending
        issues.sort(key=lambda x: x["frequency"], reverse=True)

        return issues[:10]  # Top 10 issues

    def _get_gcp_project_id(self) -> Optional[str]:
        """Get GCP project ID from environment or metadata."""
        import os

        # Try environment variable first
        project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        if project_id:
            return project_id

        # Try to get from GCP metadata service
        try:
            import requests

            response = requests.get(
                "http://metadata.google.internal/computeMetadata/v1/project/project-id",
                headers={"Metadata-Flavor": "Google"},
                timeout=1,
            )
            if response.status_code == 200:
                return response.text
        except:
            pass

        return None
