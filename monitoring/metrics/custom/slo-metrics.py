"""
SLO/SLA Metrics Collection and Monitoring
Provides automated SLO tracking and alerting for all platform services.
"""

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import Instrument

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class SLIType(Enum):
    """Types of Service Level Indicators."""

    AVAILABILITY = "availability"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    SATURATION = "saturation"


@dataclass
class SLOTarget:
    """SLO target configuration."""

    name: str
    sli_type: SLIType
    target: float  # Target percentage (e.g., 99.9 for 99.9%)
    measurement_window: timedelta = field(default_factory=lambda: timedelta(days=30))
    error_budget_burn_rate_threshold: float = 2.0  # Alert when burn rate exceeds this
    alerting_window: timedelta = field(default_factory=lambda: timedelta(hours=1))


@dataclass
class SLIMetric:
    """Service Level Indicator metric data point."""

    timestamp: datetime
    service: str
    sli_type: SLIType
    value: float
    total_requests: int = 0
    successful_requests: int = 0
    labels: Dict[str, str] = field(default_factory=dict)


class SLOMonitor:
    """Monitor and track SLO compliance for services."""

    def __init__(self, service_name: str, environment: str = "production"):
        self.service_name = service_name
        self.environment = environment
        self.slo_targets: Dict[str, SLOTarget] = {}
        self.metrics_history: List[SLIMetric] = []

        if OTEL_AVAILABLE:
            self.meter = metrics.get_meter(f"{service_name}_slo_monitor")
            self._setup_slo_metrics()

    def _setup_slo_metrics(self):
        """Set up OpenTelemetry metrics for SLO tracking."""
        if not hasattr(self, "meter"):
            return

        # SLO compliance gauge
        self.slo_compliance_gauge = self.meter.create_up_down_counter(
            name="slo_compliance_ratio",
            description="Current SLO compliance ratio",
            unit="1",
        )

        # Error budget remaining gauge
        self.error_budget_gauge = self.meter.create_up_down_counter(
            name="slo_error_budget_remaining",
            description="Remaining error budget as a ratio",
            unit="1",
        )

        # Error budget burn rate gauge
        self.burn_rate_gauge = self.meter.create_up_down_counter(
            name="slo_error_budget_burn_rate",
            description="Current error budget burn rate",
            unit="1",
        )

        # SLI value histogram
        self.sli_histogram = self.meter.create_histogram(
            name="sli_value", description="Service Level Indicator values", unit="1"
        )

        # SLO breach counter
        self.slo_breach_counter = self.meter.create_counter(
            name="slo_breaches_total",
            description="Total number of SLO breaches",
            unit="1",
        )

    def add_slo_target(self, target: SLOTarget):
        """Add an SLO target to monitor."""
        self.slo_targets[target.name] = target

    def record_sli_metric(self, metric: SLIMetric):
        """Record a Service Level Indicator metric."""
        self.metrics_history.append(metric)

        # Keep only metrics within the maximum window
        max_window = (
            max(target.measurement_window for target in self.slo_targets.values())
            if self.slo_targets
            else timedelta(days=30)
        )

        cutoff_time = datetime.now() - max_window
        self.metrics_history = [
            m for m in self.metrics_history if m.timestamp > cutoff_time
        ]

        # Record OpenTelemetry metrics
        if hasattr(self, "sli_histogram"):
            self.sli_histogram.record(
                metric.value,
                attributes={
                    "service": metric.service,
                    "sli_type": metric.sli_type.value,
                    "environment": self.environment,
                    **metric.labels,
                },
            )

    def calculate_slo_compliance(
        self, target_name: str
    ) -> Optional[Tuple[float, float, float]]:
        """
        Calculate SLO compliance for a target.
        Returns: (compliance_ratio, error_budget_remaining, burn_rate)
        """
        if target_name not in self.slo_targets:
            return None

        target = self.slo_targets[target_name]
        cutoff_time = datetime.now() - target.measurement_window

        # Get relevant metrics
        relevant_metrics = [
            m
            for m in self.metrics_history
            if (
                m.sli_type == target.sli_type
                and m.timestamp > cutoff_time
                and m.service == self.service_name
            )
        ]

        if not relevant_metrics:
            return None

        # Calculate compliance based on SLI type
        if target.sli_type == SLIType.AVAILABILITY:
            total_requests = sum(m.total_requests for m in relevant_metrics)
            successful_requests = sum(m.successful_requests for m in relevant_metrics)
            if total_requests == 0:
                return None
            compliance_ratio = successful_requests / total_requests

        elif target.sli_type == SLIType.ERROR_RATE:
            total_requests = sum(m.total_requests for m in relevant_metrics)
            error_requests = total_requests - sum(
                m.successful_requests for m in relevant_metrics
            )
            if total_requests == 0:
                return None
            error_rate = error_requests / total_requests
            compliance_ratio = 1.0 - error_rate

        elif target.sli_type == SLIType.LATENCY:
            # For latency, compliance is percentage of requests under threshold
            values = [m.value for m in relevant_metrics]
            if not values:
                return None
            compliance_ratio = len([v for v in values if v <= target.target]) / len(
                values
            )

        else:
            # For other metrics, use average value
            values = [m.value for m in relevant_metrics]
            if not values:
                return None
            avg_value = statistics.mean(values)
            compliance_ratio = min(avg_value / target.target, 1.0)

        # Calculate error budget
        target_ratio = target.target / 100.0
        allowed_error_ratio = 1.0 - target_ratio
        actual_error_ratio = 1.0 - compliance_ratio

        if allowed_error_ratio == 0:
            error_budget_remaining = 1.0 if actual_error_ratio == 0 else 0.0
        else:
            error_budget_remaining = max(
                0.0, 1.0 - (actual_error_ratio / allowed_error_ratio)
            )

        # Calculate burn rate (over alerting window)
        burn_rate = self._calculate_burn_rate(target)

        # Update OpenTelemetry metrics
        if hasattr(self, "slo_compliance_gauge"):
            attributes = {
                "service": self.service_name,
                "slo_target": target_name,
                "sli_type": target.sli_type.value,
                "environment": self.environment,
            }

            self.slo_compliance_gauge.add(compliance_ratio, attributes=attributes)
            self.error_budget_gauge.add(error_budget_remaining, attributes=attributes)
            self.burn_rate_gauge.add(burn_rate, attributes=attributes)

            # Record SLO breach if compliance is below target
            if compliance_ratio < target_ratio:
                self.slo_breach_counter.add(1, attributes=attributes)

        return compliance_ratio, error_budget_remaining, burn_rate

    def _calculate_burn_rate(self, target: SLOTarget) -> float:
        """Calculate the current error budget burn rate."""
        cutoff_time = datetime.now() - target.alerting_window

        recent_metrics = [
            m
            for m in self.metrics_history
            if (
                m.sli_type == target.sli_type
                and m.timestamp > cutoff_time
                and m.service == self.service_name
            )
        ]

        if not recent_metrics:
            return 0.0

        # Calculate error rate in alerting window
        if target.sli_type in [SLIType.AVAILABILITY, SLIType.ERROR_RATE]:
            total_requests = sum(m.total_requests for m in recent_metrics)
            successful_requests = sum(m.successful_requests for m in recent_metrics)
            if total_requests == 0:
                return 0.0
            actual_error_rate = 1.0 - (successful_requests / total_requests)
        else:
            # For other metrics, use deviation from target
            values = [m.value for m in recent_metrics]
            avg_value = statistics.mean(values)
            actual_error_rate = max(0.0, 1.0 - (avg_value / target.target))

        # Calculate allowed error rate
        target_ratio = target.target / 100.0
        allowed_error_rate = 1.0 - target_ratio

        if allowed_error_rate == 0:
            return float("inf") if actual_error_rate > 0 else 0.0

        # Calculate burn rate (how fast we're consuming error budget)
        window_fraction = (
            target.alerting_window.total_seconds()
            / target.measurement_window.total_seconds()
        )
        expected_error_rate_in_window = allowed_error_rate * window_fraction

        if expected_error_rate_in_window == 0:
            return float("inf") if actual_error_rate > 0 else 0.0

        return actual_error_rate / expected_error_rate_in_window

    def get_slo_status(self) -> Dict[str, Any]:
        """Get current SLO status for all targets."""
        status = {}

        for target_name, target in self.slo_targets.items():
            compliance_data = self.calculate_slo_compliance(target_name)
            if compliance_data:
                compliance_ratio, error_budget_remaining, burn_rate = compliance_data

                status[target_name] = {
                    "sli_type": target.sli_type.value,
                    "target": target.target,
                    "compliance_ratio": compliance_ratio,
                    "compliance_percentage": compliance_ratio * 100,
                    "error_budget_remaining": error_budget_remaining,
                    "error_budget_percentage": error_budget_remaining * 100,
                    "burn_rate": burn_rate,
                    "is_breached": compliance_ratio < (target.target / 100.0),
                    "is_burn_rate_high": burn_rate
                    > target.error_budget_burn_rate_threshold,
                    "measurement_window_hours": target.measurement_window.total_seconds()
                    / 3600,
                    "last_updated": datetime.now().isoformat(),
                }

        return status

    def should_alert(self, target_name: str) -> Tuple[bool, str]:
        """Check if we should alert for an SLO target."""
        if target_name not in self.slo_targets:
            return False, "Target not found"

        target = self.slo_targets[target_name]
        compliance_data = self.calculate_slo_compliance(target_name)

        if not compliance_data:
            return False, "No data available"

        compliance_ratio, error_budget_remaining, burn_rate = compliance_data
        target_ratio = target.target / 100.0

        # Alert conditions
        if compliance_ratio < target_ratio:
            return True, f"SLO breach: {compliance_ratio * 100:.2f}% < {target.target}%"

        if burn_rate > target.error_budget_burn_rate_threshold:
            return True, f"High error budget burn rate: {burn_rate:.2f}x"

        if error_budget_remaining < 0.1:  # Less than 10% error budget remaining
            return (
                True,
                f"Low error budget: {error_budget_remaining * 100:.1f}% remaining",
            )

        return False, "All metrics within SLO"


# Predefined SLO targets for common service types
STANDARD_SLO_TARGETS = {
    "web_service_availability": SLOTarget(
        name="web_service_availability",
        sli_type=SLIType.AVAILABILITY,
        target=99.9,
        measurement_window=timedelta(days=30),
    ),
    "web_service_latency_p95": SLOTarget(
        name="web_service_latency_p95",
        sli_type=SLIType.LATENCY,
        target=500,  # 500ms
        measurement_window=timedelta(days=7),
    ),
    "api_error_rate": SLOTarget(
        name="api_error_rate",
        sli_type=SLIType.ERROR_RATE,
        target=99.0,  # 99% success rate (1% error rate)
        measurement_window=timedelta(days=30),
    ),
    "critical_service_availability": SLOTarget(
        name="critical_service_availability",
        sli_type=SLIType.AVAILABILITY,
        target=99.95,
        measurement_window=timedelta(days=30),
        error_budget_burn_rate_threshold=1.5,
    ),
}


def create_standard_slo_monitor(
    service_name: str, environment: str = "production"
) -> SLOMonitor:
    """Create an SLO monitor with standard targets."""
    monitor = SLOMonitor(service_name, environment)

    # Add appropriate targets based on service type
    if "web" in service_name.lower() or "api" in service_name.lower():
        monitor.add_slo_target(STANDARD_SLO_TARGETS["web_service_availability"])
        monitor.add_slo_target(STANDARD_SLO_TARGETS["web_service_latency_p95"])
        monitor.add_slo_target(STANDARD_SLO_TARGETS["api_error_rate"])

    if "critical" in service_name.lower():
        monitor.add_slo_target(STANDARD_SLO_TARGETS["critical_service_availability"])

    return monitor


# Convenience functions for recording common SLI metrics
def record_http_request_sli(
    monitor: SLOMonitor,
    success: bool,
    latency_ms: float,
    labels: Optional[Dict[str, str]] = None,
):
    """Record SLI metrics for HTTP requests."""
    timestamp = datetime.now()
    labels = labels or {}

    # Availability metric
    availability_metric = SLIMetric(
        timestamp=timestamp,
        service=monitor.service_name,
        sli_type=SLIType.AVAILABILITY,
        value=1.0 if success else 0.0,
        total_requests=1,
        successful_requests=1 if success else 0,
        labels=labels,
    )
    monitor.record_sli_metric(availability_metric)

    # Latency metric
    latency_metric = SLIMetric(
        timestamp=timestamp,
        service=monitor.service_name,
        sli_type=SLIType.LATENCY,
        value=latency_ms,
        total_requests=1,
        successful_requests=1 if success else 0,
        labels=labels,
    )
    monitor.record_sli_metric(latency_metric)


def export_slo_status_to_json(monitor: SLOMonitor, file_path: str):
    """Export SLO status to JSON file for external consumption."""
    status = monitor.get_slo_status()
    with open(file_path, "w") as f:
        json.dump(status, f, indent=2)
