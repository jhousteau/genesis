"""
Cost Metrics Collection and Analysis
Tracks infrastructure and operational costs across all platform services.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Tuple

try:
    from google.cloud import billing, monitoring
    from opentelemetry import metrics

    OTEL_AVAILABLE = True
    GCP_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    GCP_AVAILABLE = False


class CostCategory(Enum):
    """Categories for cost tracking."""

    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORKING = "networking"
    DATABASE = "database"
    MONITORING = "monitoring"
    SECURITY = "security"
    DATA_PROCESSING = "data_processing"
    EXTERNAL_SERVICES = "external_services"
    LICENSING = "licensing"


@dataclass
class CostMetric:
    """Cost metric data point."""

    timestamp: datetime
    service_name: str
    category: CostCategory
    cost: float  # Cost in base currency (USD)
    currency: str = "USD"
    project_id: str = ""
    environment: str = "production"
    resource_id: str = ""
    tags: Dict[str, str] = field(default_factory=dict)


class CostTracker:
    """Track and analyze costs across all platform services."""

    def __init__(self, project_id: str, billing_account_id: str = None):
        self.project_id = project_id
        self.billing_account_id = billing_account_id
        self.cost_history: List[CostMetric] = []

        if OTEL_AVAILABLE:
            self.meter = metrics.get_meter("cost_tracker")
            self._setup_cost_metrics()

        if GCP_AVAILABLE:
            self._setup_gcp_clients()

    def _setup_cost_metrics(self):
        """Set up OpenTelemetry metrics for cost tracking."""
        if not hasattr(self, "meter"):
            return

        # Current cost gauge
        self.cost_gauge = self.meter.create_up_down_counter(
            name="infrastructure_cost_total",
            description="Total infrastructure cost",
            unit="USD",
        )

        # Cost per category
        self.cost_by_category = self.meter.create_up_down_counter(
            name="infrastructure_cost_by_category",
            description="Infrastructure cost by category",
            unit="USD",
        )

        # Cost efficiency metrics
        self.cost_per_request = self.meter.create_histogram(
            name="cost_per_request",
            description="Cost per request processed",
            unit="USD",
        )

        self.cost_per_user = self.meter.create_histogram(
            name="cost_per_user", description="Cost per active user", unit="USD"
        )

        # Budget utilization
        self.budget_utilization = self.meter.create_up_down_counter(
            name="budget_utilization_ratio",
            description="Budget utilization as a ratio",
            unit="1",
        )

        # Cost anomaly detection
        self.cost_anomaly_score = self.meter.create_histogram(
            name="cost_anomaly_score",
            description="Cost anomaly detection score",
            unit="1",
        )

    def _setup_gcp_clients(self):
        """Set up GCP clients for cost data collection."""
        try:
            self.billing_client = billing.CloudBillingClient()
            self.monitoring_client = monitoring.MetricServiceClient()
        except Exception as e:
            print(f"Failed to setup GCP clients: {e}")

    def record_cost_metric(self, metric: CostMetric):
        """Record a cost metric."""
        self.cost_history.append(metric)

        # Keep only the last 90 days of data
        cutoff_time = datetime.now() - timedelta(days=90)
        self.cost_history = [m for m in self.cost_history if m.timestamp > cutoff_time]

        # Update OpenTelemetry metrics
        if hasattr(self, "cost_gauge"):
            attributes = {
                "service": metric.service_name,
                "category": metric.category.value,
                "environment": metric.environment,
                "project_id": metric.project_id,
                **metric.tags,
            }

            self.cost_gauge.add(metric.cost, attributes=attributes)
            self.cost_by_category.add(metric.cost, attributes=attributes)

    def get_daily_costs(
        self, days: int = 30
    ) -> Dict[str, List[Tuple[datetime, float]]]:
        """Get daily cost breakdown for the last N days."""
        cutoff_time = datetime.now() - timedelta(days=days)

        # Group costs by category and day
        daily_costs = {}
        for metric in self.cost_history:
            if metric.timestamp < cutoff_time:
                continue

            date_key = metric.timestamp.date()
            category = metric.category.value

            if category not in daily_costs:
                daily_costs[category] = {}

            if date_key not in daily_costs[category]:
                daily_costs[category][date_key] = 0.0

            daily_costs[category][date_key] += metric.cost

        # Convert to sorted lists
        result = {}
        for category, daily_data in daily_costs.items():
            sorted_data = sorted(daily_data.items())
            result[category] = [
                (datetime.combine(date, datetime.min.time()), cost)
                for date, cost in sorted_data
            ]

        return result

    def calculate_cost_efficiency_metrics(
        self,
        total_requests: int = None,
        active_users: int = None,
        time_period_hours: int = 24,
    ) -> Dict[str, float]:
        """Calculate cost efficiency metrics."""
        cutoff_time = datetime.now() - timedelta(hours=time_period_hours)

        # Calculate total cost in time period
        total_cost = sum(
            metric.cost
            for metric in self.cost_history
            if metric.timestamp > cutoff_time
        )

        efficiency_metrics = {
            "total_cost": total_cost,
            "cost_per_hour": total_cost / time_period_hours,
        }

        if total_requests and total_requests > 0:
            cost_per_request = total_cost / total_requests
            efficiency_metrics["cost_per_request"] = cost_per_request

            # Update OpenTelemetry metric
            if hasattr(self, "cost_per_request"):
                self.cost_per_request.record(
                    cost_per_request, attributes={"project_id": self.project_id}
                )

        if active_users and active_users > 0:
            cost_per_user = total_cost / active_users
            efficiency_metrics["cost_per_user"] = cost_per_user

            # Update OpenTelemetry metric
            if hasattr(self, "cost_per_user"):
                self.cost_per_user.record(
                    cost_per_user, attributes={"project_id": self.project_id}
                )

        return efficiency_metrics

    def detect_cost_anomalies(
        self, threshold_multiplier: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Detect cost anomalies using statistical analysis."""
        if len(self.cost_history) < 14:  # Need at least 2 weeks of data
            return []

        # Calculate daily costs for the last 30 days
        daily_costs = self.get_daily_costs(30)
        anomalies = []

        for category, daily_data in daily_costs.items():
            if len(daily_data) < 7:  # Need at least a week of data
                continue

            costs = [cost for _, cost in daily_data]

            # Calculate baseline (median of all but last 3 days)
            baseline_costs = costs[:-3] if len(costs) > 3 else costs[:-1]
            baseline_median = sorted(baseline_costs)[len(baseline_costs) // 2]

            # Check recent days for anomalies
            recent_costs = costs[-3:]
            for i, cost in enumerate(recent_costs):
                if cost > baseline_median * threshold_multiplier:
                    anomaly_score = cost / baseline_median
                    anomalies.append(
                        {
                            "category": category,
                            "date": daily_data[-(3 - i)][0],
                            "cost": cost,
                            "baseline_cost": baseline_median,
                            "anomaly_score": anomaly_score,
                            "severity": "high" if anomaly_score > 3.0 else "medium",
                        }
                    )

                    # Update OpenTelemetry metric
                    if hasattr(self, "cost_anomaly_score"):
                        self.cost_anomaly_score.record(
                            anomaly_score,
                            attributes={
                                "category": category,
                                "project_id": self.project_id,
                            },
                        )

        return anomalies

    def track_budget_utilization(
        self, budget_amount: float, budget_period_days: int = 30
    ):
        """Track budget utilization."""
        cutoff_time = datetime.now() - timedelta(days=budget_period_days)

        # Calculate total cost in budget period
        period_cost = sum(
            metric.cost
            for metric in self.cost_history
            if metric.timestamp > cutoff_time
        )

        utilization_ratio = period_cost / budget_amount if budget_amount > 0 else 0.0

        # Update OpenTelemetry metric
        if hasattr(self, "budget_utilization"):
            self.budget_utilization.add(
                utilization_ratio,
                attributes={
                    "project_id": self.project_id,
                    "budget_period_days": str(budget_period_days),
                },
            )

        return {
            "budget_amount": budget_amount,
            "period_cost": period_cost,
            "utilization_ratio": utilization_ratio,
            "utilization_percentage": utilization_ratio * 100,
            "remaining_budget": max(0, budget_amount - period_cost),
            "days_remaining": budget_period_days - (datetime.now() - cutoff_time).days,
            "projected_overspend": max(0, period_cost - budget_amount),
        }

    def get_cost_breakdown_by_service(
        self, days: int = 30
    ) -> Dict[str, Dict[str, float]]:
        """Get cost breakdown by service and category."""
        cutoff_time = datetime.now() - timedelta(days=days)

        breakdown = {}
        for metric in self.cost_history:
            if metric.timestamp < cutoff_time:
                continue

            if metric.service_name not in breakdown:
                breakdown[metric.service_name] = {}

            category = metric.category.value
            if category not in breakdown[metric.service_name]:
                breakdown[metric.service_name][category] = 0.0

            breakdown[metric.service_name][category] += metric.cost

        return breakdown

    def generate_cost_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive cost report."""
        cutoff_time = datetime.now() - timedelta(days=days)
        period_costs = [
            metric for metric in self.cost_history if metric.timestamp > cutoff_time
        ]

        if not period_costs:
            return {"error": "No cost data available for the specified period"}

        # Calculate totals
        total_cost = sum(metric.cost for metric in period_costs)
        avg_daily_cost = total_cost / days

        # Cost by category
        category_costs = {}
        for metric in period_costs:
            category = metric.category.value
            category_costs[category] = category_costs.get(category, 0.0) + metric.cost

        # Cost by service
        service_costs = {}
        for metric in period_costs:
            service = metric.service_name
            service_costs[service] = service_costs.get(service, 0.0) + metric.cost

        # Top cost contributors
        top_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]
        top_categories = sorted(
            category_costs.items(), key=lambda x: x[1], reverse=True
        )

        # Cost trend (compare with previous period)
        prev_cutoff = cutoff_time - timedelta(days=days)
        prev_period_costs = [
            metric
            for metric in self.cost_history
            if prev_cutoff <= metric.timestamp < cutoff_time
        ]
        prev_total_cost = sum(metric.cost for metric in prev_period_costs)

        cost_change = total_cost - prev_total_cost
        cost_change_percentage = (
            (cost_change / prev_total_cost * 100) if prev_total_cost > 0 else 0
        )

        return {
            "report_period_days": days,
            "total_cost": total_cost,
            "average_daily_cost": avg_daily_cost,
            "cost_change_from_previous_period": cost_change,
            "cost_change_percentage": cost_change_percentage,
            "cost_by_category": category_costs,
            "cost_by_service": service_costs,
            "top_services": dict(top_services),
            "top_categories": dict(top_categories),
            "generated_at": datetime.now().isoformat(),
        }


# GCP-specific cost collection functions
def collect_gcp_billing_data(project_id: str, days: int = 1) -> List[CostMetric]:
    """Collect billing data from GCP."""
    if not GCP_AVAILABLE:
        return []

    try:
        billing_client = billing.CloudBillingClient()

        # This is a simplified example - actual implementation would use
        # the Cloud Billing API to fetch detailed billing data
        # The real implementation requires proper authentication and
        # access to billing export data in BigQuery

        cost_metrics = []

        # Placeholder for actual GCP billing data collection
        # In practice, you would:
        # 1. Query billing export data from BigQuery
        # 2. Parse the results into CostMetric objects
        # 3. Categorize services into appropriate cost categories

        return cost_metrics

    except Exception as e:
        print(f"Failed to collect GCP billing data: {e}")
        return []


# Convenience functions
def create_cost_tracker(project_id: str) -> CostTracker:
    """Create a cost tracker with standard configuration."""
    billing_account_id = os.getenv("GCP_BILLING_ACCOUNT_ID")
    return CostTracker(project_id, billing_account_id)


def record_compute_cost(
    tracker: CostTracker,
    service_name: str,
    cost: float,
    resource_id: str = "",
    environment: str = "production",
):
    """Convenience function to record compute costs."""
    metric = CostMetric(
        timestamp=datetime.now(),
        service_name=service_name,
        category=CostCategory.COMPUTE,
        cost=cost,
        resource_id=resource_id,
        environment=environment,
        project_id=tracker.project_id,
    )
    tracker.record_cost_metric(metric)


def record_storage_cost(
    tracker: CostTracker,
    service_name: str,
    cost: float,
    storage_type: str = "standard",
    environment: str = "production",
):
    """Convenience function to record storage costs."""
    metric = CostMetric(
        timestamp=datetime.now(),
        service_name=service_name,
        category=CostCategory.STORAGE,
        cost=cost,
        environment=environment,
        project_id=tracker.project_id,
        tags={"storage_type": storage_type},
    )
    tracker.record_cost_metric(metric)


def export_cost_report_to_json(tracker: CostTracker, file_path: str, days: int = 30):
    """Export cost report to JSON file."""
    report = tracker.generate_cost_report(days)
    with open(file_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
