"""
GCP Cost Optimization Monitor - CRAFT Function Component
Comprehensive cost optimization monitoring and recommendations for GCP services

This module implements intelligent cost monitoring and optimization for GCP resources,
providing automated analysis and actionable cost-saving recommendations.
"""

import logging
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    from google.cloud import asset_v1, billing, monitoring_v3, recommender_v1

    GCP_COST_AVAILABLE = True
except ImportError:
    GCP_COST_AVAILABLE = False

logger = logging.getLogger(__name__)


class CostCategory(Enum):
    """Cost optimization categories."""

    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORKING = "networking"
    DATA_PROCESSING = "data_processing"
    DATABASES = "databases"
    MONITORING = "monitoring"
    SECURITY = "security"


class SavingsOpportunity(Enum):
    """Potential savings opportunity levels."""

    HIGH = "HIGH"  # > $500/month
    MEDIUM = "MEDIUM"  # $100-500/month
    LOW = "LOW"  # < $100/month


@dataclass
class CostAlert:
    """Cost alert configuration and status."""

    # Alert identification
    alert_id: str
    alert_name: str
    alert_type: str  # budget, anomaly, threshold

    # Cost thresholds
    monthly_budget: float
    threshold_percentage: float  # 80%, 90%, 100%
    current_spend: float = 0.0
    projected_spend: float = 0.0

    # Targeting
    services: List[str] = field(default_factory=list)
    projects: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)

    # Alert status
    status: str = "ACTIVE"  # ACTIVE, TRIGGERED, RESOLVED
    last_triggered: Optional[datetime] = None

    # Notification settings
    email_recipients: List[str] = field(default_factory=list)
    slack_webhook: Optional[str] = None
    enable_automatic_actions: bool = False

    def is_over_budget(self) -> bool:
        """Check if current spend is over budget."""
        return self.current_spend >= self.monthly_budget


@dataclass
class CostRecommendation:
    """Cost optimization recommendation."""

    # Identification
    recommendation_id: str
    title: str
    category: CostCategory
    opportunity_level: SavingsOpportunity

    # Cost analysis
    current_monthly_cost: float
    projected_monthly_savings: float
    annual_savings: float
    percentage_savings: float

    # Implementation details
    affected_resources: List[str]
    implementation_steps: List[str]
    estimated_implementation_hours: float
    risk_level: str  # LOW, MEDIUM, HIGH

    # Resource details
    gcp_service: str
    resource_type: str
    resource_ids: List[str] = field(default_factory=list)

    # Validation
    prerequisites: List[str] = field(default_factory=list)
    success_metrics: List[str] = field(default_factory=list)
    rollback_procedure: str = ""

    # Metadata
    confidence_score: float = 0.0  # 0.0 to 1.0
    data_collection_period: int = 30  # days
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    @property
    def roi_months(self) -> float:
        """Calculate ROI payback period in months."""
        if self.projected_monthly_savings <= 0:
            return float("inf")
        implementation_cost = self.estimated_implementation_hours * 150  # $150/hour
        return implementation_cost / self.projected_monthly_savings


@dataclass
class CostAnalysis:
    """Comprehensive cost analysis result."""

    # Analysis period
    analysis_period_start: date
    analysis_period_end: date

    # Cost summary
    total_cost: float
    cost_by_service: Dict[str, float]
    cost_by_project: Dict[str, float]
    cost_trend: str  # INCREASING, DECREASING, STABLE

    # Optimization opportunities
    total_potential_savings: float
    recommendations: List[CostRecommendation]

    # Top cost drivers
    top_services: List[Dict[str, Any]]
    top_projects: List[Dict[str, Any]]
    cost_anomalies: List[Dict[str, Any]]

    # Efficiency metrics
    compute_utilization: Dict[str, float]
    storage_utilization: Dict[str, float]
    cost_per_user: Optional[float] = None
    cost_per_transaction: Optional[float] = None


class GCPCostAnalyzer:
    """Analyzer for GCP service costs and optimization opportunities."""

    def __init__(self, project_id: str, billing_account_id: Optional[str] = None):
        self.project_id = project_id
        self.billing_account_id = billing_account_id
        self.logger = logging.getLogger(f"{__name__}.GCPCostAnalyzer")

        # Initialize GCP clients
        self.billing_client = None
        self.recommender_client = None

        if GCP_COST_AVAILABLE:
            try:
                self.billing_client = billing.CloudBillingClient()
                self.recommender_client = recommender_v1.RecommenderClient()
                self.logger.info("GCP Cost clients initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize GCP cost clients: {e}")

    async def analyze_compute_costs(
        self, cost_data: Dict[str, Any]
    ) -> List[CostRecommendation]:
        """Analyze compute costs and generate optimization recommendations."""
        recommendations = []

        if "compute_engine" in cost_data:
            compute_costs = cost_data["compute_engine"]

            # Analyze idle instances
            idle_instances = [
                instance
                for instance in compute_costs.get("instances", [])
                if instance.get("cpu_utilization_avg", 0) < 10.0  # < 10% CPU
            ]

            if idle_instances:
                total_idle_cost = sum(
                    instance.get("monthly_cost", 0) for instance in idle_instances
                )

                recommendations.append(
                    CostRecommendation(
                        recommendation_id=f"compute_idle_instances_{self.project_id}",
                        title="Remove or downsize idle Compute Engine instances",
                        category=CostCategory.COMPUTE,
                        opportunity_level=self._categorize_savings(total_idle_cost),
                        current_monthly_cost=total_idle_cost,
                        projected_monthly_savings=total_idle_cost * 0.8,  # 80% savings
                        annual_savings=total_idle_cost * 0.8 * 12,
                        percentage_savings=80.0,
                        affected_resources=[
                            f"Instance: {i['name']}" for i in idle_instances
                        ],
                        implementation_steps=[
                            "Identify instances with < 10% CPU utilization over 7 days",
                            "Verify instances are not needed for development/testing",
                            "Create snapshots of persistent disks if needed",
                            "Stop or delete idle instances",
                            "Set up monitoring alerts to prevent future idle instances",
                        ],
                        estimated_implementation_hours=2.0,
                        risk_level="LOW",
                        gcp_service="Compute Engine",
                        resource_type="Instance",
                        resource_ids=[i["name"] for i in idle_instances],
                        confidence_score=0.95,
                    )
                )

            # Analyze oversized instances
            oversized_instances = [
                instance
                for instance in compute_costs.get("instances", [])
                if instance.get("cpu_utilization_avg", 0) < 30.0
                and instance.get("memory_utilization_avg", 0) < 30.0
                and instance.get("machine_type", "").startswith(
                    "n1-standard-"
                )  # Can be downsized
            ]

            if oversized_instances:
                total_current_cost = sum(
                    instance.get("monthly_cost", 0) for instance in oversized_instances
                )
                estimated_savings = (
                    total_current_cost * 0.4
                )  # 40% savings from downsizing

                recommendations.append(
                    CostRecommendation(
                        recommendation_id=f"compute_downsize_instances_{self.project_id}",
                        title="Downsize over-provisioned Compute Engine instances",
                        category=CostCategory.COMPUTE,
                        opportunity_level=self._categorize_savings(estimated_savings),
                        current_monthly_cost=total_current_cost,
                        projected_monthly_savings=estimated_savings,
                        annual_savings=estimated_savings * 12,
                        percentage_savings=40.0,
                        affected_resources=[
                            f"Instance: {i['name']}" for i in oversized_instances
                        ],
                        implementation_steps=[
                            "Analyze historical resource usage patterns",
                            "Plan maintenance window for resizing",
                            "Create instance snapshots for rollback",
                            "Resize instances to appropriate machine types",
                            "Monitor performance after resizing",
                            "Rollback if performance issues occur",
                        ],
                        estimated_implementation_hours=4.0,
                        risk_level="MEDIUM",
                        gcp_service="Compute Engine",
                        resource_type="Instance",
                        prerequisites=[
                            "Verify application performance requirements",
                            "Plan maintenance window",
                            "Get approval from application owners",
                        ],
                        confidence_score=0.80,
                    )
                )

        # Analyze Cloud Run costs
        if "cloud_run" in cost_data:
            cloud_run_costs = cost_data["cloud_run"]

            # Analyze over-provisioned Cloud Run services
            overprovisioned_services = [
                service
                for service in cloud_run_costs.get("services", [])
                if service.get("cpu_utilization_avg", 0) < 20.0
                and service.get("memory_utilization_avg", 0) < 50.0
            ]

            if overprovisioned_services:
                total_current_cost = sum(
                    s.get("monthly_cost", 0) for s in overprovisioned_services
                )
                estimated_savings = total_current_cost * 0.25  # 25% savings

                recommendations.append(
                    CostRecommendation(
                        recommendation_id=f"cloud_run_optimize_{self.project_id}",
                        title="Optimize Cloud Run resource allocation",
                        category=CostCategory.COMPUTE,
                        opportunity_level=self._categorize_savings(estimated_savings),
                        current_monthly_cost=total_current_cost,
                        projected_monthly_savings=estimated_savings,
                        annual_savings=estimated_savings * 12,
                        percentage_savings=25.0,
                        affected_resources=[
                            f"Service: {s['name']}" for s in overprovisioned_services
                        ],
                        implementation_steps=[
                            "Reduce CPU allocation from 1.0 to 0.5 vCPU",
                            "Adjust memory allocation based on usage patterns",
                            "Update concurrency settings for better efficiency",
                            "Monitor performance and adjust if needed",
                        ],
                        estimated_implementation_hours=3.0,
                        risk_level="LOW",
                        gcp_service="Cloud Run",
                        resource_type="Service",
                        confidence_score=0.85,
                    )
                )

        return recommendations

    async def analyze_storage_costs(
        self, cost_data: Dict[str, Any]
    ) -> List[CostRecommendation]:
        """Analyze storage costs and generate optimization recommendations."""
        recommendations = []

        if "cloud_storage" in cost_data:
            storage_costs = cost_data["cloud_storage"]

            # Analyze storage class optimization opportunities
            standard_storage = [
                bucket
                for bucket in storage_costs.get("buckets", [])
                if bucket.get("storage_class") == "STANDARD"
                and bucket.get("access_frequency_30d", 0) < 5  # Low access frequency
            ]

            if standard_storage:
                total_current_cost = sum(
                    bucket.get("monthly_cost", 0) for bucket in standard_storage
                )
                estimated_savings = total_current_cost * 0.5  # 50% savings

                recommendations.append(
                    CostRecommendation(
                        recommendation_id=f"storage_class_optimization_{self.project_id}",
                        title="Optimize Cloud Storage classes for infrequently accessed data",
                        category=CostCategory.STORAGE,
                        opportunity_level=self._categorize_savings(estimated_savings),
                        current_monthly_cost=total_current_cost,
                        projected_monthly_savings=estimated_savings,
                        annual_savings=estimated_savings * 12,
                        percentage_savings=50.0,
                        affected_resources=[
                            f"Bucket: {b['name']}" for b in standard_storage
                        ],
                        implementation_steps=[
                            "Set up lifecycle policies for buckets with low access patterns",
                            "Transition objects > 30 days old to Nearline storage",
                            "Transition objects > 90 days old to Coldline storage",
                            "Monitor access patterns to validate optimization",
                            "Adjust policies based on actual usage",
                        ],
                        estimated_implementation_hours=3.0,
                        risk_level="LOW",
                        gcp_service="Cloud Storage",
                        resource_type="Bucket",
                        confidence_score=0.90,
                    )
                )

            # Analyze unused persistent disks
            if "persistent_disks" in storage_costs:
                unused_disks = [
                    disk
                    for disk in storage_costs["persistent_disks"]
                    if disk.get("status") == "READY"
                    and not disk.get("attached_instances")
                ]

                if unused_disks:
                    total_unused_cost = sum(
                        disk.get("monthly_cost", 0) for disk in unused_disks
                    )

                    recommendations.append(
                        CostRecommendation(
                            recommendation_id=f"unused_disks_cleanup_{self.project_id}",
                            title="Remove unused persistent disks",
                            category=CostCategory.STORAGE,
                            opportunity_level=self._categorize_savings(
                                total_unused_cost
                            ),
                            current_monthly_cost=total_unused_cost,
                            projected_monthly_savings=total_unused_cost
                            * 0.95,  # 95% savings
                            annual_savings=total_unused_cost * 0.95 * 12,
                            percentage_savings=95.0,
                            affected_resources=[
                                f"Disk: {d['name']}" for d in unused_disks
                            ],
                            implementation_steps=[
                                "Identify persistent disks not attached to any instances",
                                "Verify disks are not needed for backups or snapshots",
                                "Create snapshots of important disks before deletion",
                                "Delete unused persistent disks",
                                "Set up monitoring to prevent future unused disks",
                            ],
                            estimated_implementation_hours=2.0,
                            risk_level="LOW",
                            gcp_service="Compute Engine",
                            resource_type="Persistent Disk",
                            prerequisites=[
                                "Verify disk data is not needed",
                                "Create snapshots if data might be needed later",
                            ],
                            confidence_score=0.95,
                        )
                    )

        return recommendations

    async def analyze_bigquery_costs(
        self, cost_data: Dict[str, Any]
    ) -> List[CostRecommendation]:
        """Analyze BigQuery costs and generate optimization recommendations."""
        recommendations = []

        if "bigquery" in cost_data:
            bq_costs = cost_data["bigquery"]

            # Analyze expensive queries
            expensive_queries = [
                query
                for query in bq_costs.get("queries", [])
                if query.get("bytes_processed", 0) > 1_000_000_000_000  # > 1TB
            ]

            if expensive_queries:
                total_query_cost = sum(
                    query.get("cost_usd", 0) for query in expensive_queries
                )
                estimated_savings = (
                    total_query_cost * 0.4
                )  # 40% savings through optimization

                recommendations.append(
                    CostRecommendation(
                        recommendation_id=f"bigquery_query_optimization_{self.project_id}",
                        title="Optimize expensive BigQuery queries",
                        category=CostCategory.DATA_PROCESSING,
                        opportunity_level=self._categorize_savings(
                            estimated_savings * 30
                        ),  # Monthly
                        current_monthly_cost=total_query_cost * 30,  # Assume daily cost
                        projected_monthly_savings=estimated_savings * 30,
                        annual_savings=estimated_savings * 365,
                        percentage_savings=40.0,
                        affected_resources=[
                            f"Query: {q.get('query_id', 'unknown')}"
                            for q in expensive_queries[:5]
                        ],
                        implementation_steps=[
                            "Identify queries processing > 1TB of data",
                            "Add partitioning to large tables based on date columns",
                            "Implement clustering for frequently filtered columns",
                            "Rewrite queries to use partition pruning",
                            "Add query result caching for repeated queries",
                            "Use approximate aggregation functions where appropriate",
                        ],
                        estimated_implementation_hours=12.0,
                        risk_level="LOW",
                        gcp_service="BigQuery",
                        resource_type="Query",
                        confidence_score=0.85,
                    )
                )

            # Analyze table storage optimization
            large_tables = [
                table
                for table in bq_costs.get("tables", [])
                if table.get("size_gb", 0) > 100 and not table.get("partitioned", False)
            ]

            if large_tables:
                storage_cost = sum(
                    table.get("storage_cost_monthly", 0) for table in large_tables
                )
                estimated_savings = storage_cost * 0.3  # 30% savings

                recommendations.append(
                    CostRecommendation(
                        recommendation_id=f"bigquery_table_optimization_{self.project_id}",
                        title="Optimize BigQuery table storage with partitioning",
                        category=CostCategory.STORAGE,
                        opportunity_level=self._categorize_savings(estimated_savings),
                        current_monthly_cost=storage_cost,
                        projected_monthly_savings=estimated_savings,
                        annual_savings=estimated_savings * 12,
                        percentage_savings=30.0,
                        affected_resources=[
                            f"Table: {t['table_id']}" for t in large_tables
                        ],
                        implementation_steps=[
                            "Identify large unpartitioned tables",
                            "Create partitioned versions of tables using date/timestamp columns",
                            "Migrate data to partitioned tables",
                            "Update queries to use new partitioned tables",
                            "Validate query performance improvements",
                            "Remove old unpartitioned tables",
                        ],
                        estimated_implementation_hours=8.0,
                        risk_level="MEDIUM",
                        gcp_service="BigQuery",
                        resource_type="Table",
                        confidence_score=0.80,
                    )
                )

        return recommendations

    async def analyze_networking_costs(
        self, cost_data: Dict[str, Any]
    ) -> List[CostRecommendation]:
        """Analyze networking costs and generate optimization recommendations."""
        recommendations = []

        if "networking" in cost_data:
            net_costs = cost_data["networking"]

            # Analyze NAT Gateway costs
            if "nat_gateways" in net_costs:
                high_nat_costs = [
                    nat
                    for nat in net_costs["nat_gateways"]
                    if nat.get("monthly_cost", 0) > 200  # > $200/month
                ]

                if high_nat_costs:
                    total_nat_cost = sum(
                        nat.get("monthly_cost", 0) for nat in high_nat_costs
                    )
                    estimated_savings = total_nat_cost * 0.3  # 30% savings

                    recommendations.append(
                        CostRecommendation(
                            recommendation_id=f"nat_gateway_optimization_{self.project_id}",
                            title="Optimize NAT Gateway usage and costs",
                            category=CostCategory.NETWORKING,
                            opportunity_level=self._categorize_savings(
                                estimated_savings
                            ),
                            current_monthly_cost=total_nat_cost,
                            projected_monthly_savings=estimated_savings,
                            annual_savings=estimated_savings * 12,
                            percentage_savings=30.0,
                            affected_resources=[
                                f"NAT Gateway: {n['name']}" for n in high_nat_costs
                            ],
                            implementation_steps=[
                                "Analyze NAT Gateway data processing patterns",
                                "Consolidate NAT Gateways where possible",
                                "Optimize outbound traffic routing",
                                "Consider Private Google Access for GCP services",
                                "Review firewall rules to minimize unnecessary traffic",
                            ],
                            estimated_implementation_hours=6.0,
                            risk_level="MEDIUM",
                            gcp_service="VPC Network",
                            resource_type="NAT Gateway",
                            confidence_score=0.75,
                        )
                    )

            # Analyze load balancer costs
            if "load_balancers" in net_costs:
                underutilized_lbs = [
                    lb
                    for lb in net_costs["load_balancers"]
                    if lb.get("rps_avg", 0) < 10  # < 10 requests per second
                ]

                if underutilized_lbs:
                    total_lb_cost = sum(
                        lb.get("monthly_cost", 0) for lb in underutilized_lbs
                    )
                    estimated_savings = (
                        total_lb_cost * 0.8
                    )  # 80% savings by consolidation

                    recommendations.append(
                        CostRecommendation(
                            recommendation_id=f"load_balancer_consolidation_{self.project_id}",
                            title="Consolidate underutilized load balancers",
                            category=CostCategory.NETWORKING,
                            opportunity_level=self._categorize_savings(
                                estimated_savings
                            ),
                            current_monthly_cost=total_lb_cost,
                            projected_monthly_savings=estimated_savings,
                            annual_savings=estimated_savings * 12,
                            percentage_savings=80.0,
                            affected_resources=[
                                f"Load Balancer: {lb['name']}"
                                for lb in underutilized_lbs
                            ],
                            implementation_steps=[
                                "Identify load balancers with < 10 RPS",
                                "Analyze traffic patterns and routing requirements",
                                "Consolidate multiple low-traffic services behind single LB",
                                "Update DNS records and application configurations",
                                "Monitor consolidated load balancer performance",
                            ],
                            estimated_implementation_hours=8.0,
                            risk_level="MEDIUM",
                            gcp_service="Load Balancing",
                            resource_type="Load Balancer",
                            confidence_score=0.70,
                        )
                    )

        return recommendations

    def _categorize_savings(self, monthly_savings: float) -> SavingsOpportunity:
        """Categorize savings opportunity level."""
        if monthly_savings >= 500:
            return SavingsOpportunity.HIGH
        elif monthly_savings >= 100:
            return SavingsOpportunity.MEDIUM
        else:
            return SavingsOpportunity.LOW


class CostOptimizationMonitor:
    """
    Comprehensive GCP cost optimization monitor implementing CRAFT Function methodology.

    Provides intelligent cost monitoring with:
    - Real-time cost tracking and alerting
    - Automated cost anomaly detection
    - Service-specific cost optimization recommendations
    - Budget management and forecasting
    - ROI analysis for optimization efforts
    """

    def __init__(
        self, project_id: Optional[str] = None, billing_account_id: Optional[str] = None
    ):
        self.logger = logging.getLogger(f"{__name__}.CostOptimizationMonitor")

        self.project_id = project_id or self._get_gcp_project_id()
        self.billing_account_id = billing_account_id

        # Initialize cost analyzer
        self.cost_analyzer = GCPCostAnalyzer(self.project_id, self.billing_account_id)

        # Cost tracking
        self.cost_alerts: List[CostAlert] = []
        self.cost_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self.optimization_recommendations: List[CostRecommendation] = []

        # Budget tracking
        self.monthly_budgets: Dict[str, float] = {}  # service -> budget
        self.cost_forecasts: Dict[str, float] = {}  # service -> projected cost

        self.logger.info("CostOptimizationMonitor initialized")

    async def analyze_monthly_costs(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> CostAnalysis:
        """Perform comprehensive monthly cost analysis."""

        # Default to current month if no dates provided
        if not start_date:
            today = date.today()
            start_date = date(today.year, today.month, 1)

        if not end_date:
            end_date = date.today()

        self.logger.info(f"Analyzing costs from {start_date} to {end_date}")

        # Collect cost data (simulated - in practice would call GCP APIs)
        cost_data = await self._collect_cost_data(start_date, end_date)

        # Generate optimization recommendations
        all_recommendations = []

        # Analyze different cost categories
        compute_recs = await self.cost_analyzer.analyze_compute_costs(cost_data)
        storage_recs = await self.cost_analyzer.analyze_storage_costs(cost_data)
        bigquery_recs = await self.cost_analyzer.analyze_bigquery_costs(cost_data)
        networking_recs = await self.cost_analyzer.analyze_networking_costs(cost_data)

        all_recommendations.extend(compute_recs)
        all_recommendations.extend(storage_recs)
        all_recommendations.extend(bigquery_recs)
        all_recommendations.extend(networking_recs)

        # Store recommendations
        self.optimization_recommendations.extend(all_recommendations)

        # Calculate cost summary
        total_cost = sum(cost_data.get("cost_by_service", {}).values())
        total_potential_savings = sum(
            rec.projected_monthly_savings for rec in all_recommendations
        )

        # Identify top cost drivers
        cost_by_service = cost_data.get("cost_by_service", {})
        top_services = [
            {"service": service, "cost": cost, "percentage": (cost / total_cost) * 100}
            for service, cost in sorted(
                cost_by_service.items(), key=lambda x: x[1], reverse=True
            )[:5]
        ]

        # Create analysis result
        analysis = CostAnalysis(
            analysis_period_start=start_date,
            analysis_period_end=end_date,
            total_cost=total_cost,
            cost_by_service=cost_by_service,
            cost_by_project=cost_data.get("cost_by_project", {}),
            cost_trend=self._determine_cost_trend(start_date),
            total_potential_savings=total_potential_savings,
            recommendations=all_recommendations,
            top_services=top_services,
            top_projects=cost_data.get("top_projects", []),
            cost_anomalies=cost_data.get("anomalies", []),
            compute_utilization=cost_data.get("compute_utilization", {}),
            storage_utilization=cost_data.get("storage_utilization", {}),
        )

        return analysis

    def create_budget_alert(
        self,
        service_name: str,
        monthly_budget: float,
        threshold_percentages: List[float] = None,
    ) -> List[CostAlert]:
        """Create budget alerts for a service."""

        if threshold_percentages is None:
            threshold_percentages = [50.0, 80.0, 100.0]

        alerts = []
        for threshold in threshold_percentages:
            alert = CostAlert(
                alert_id=f"budget_alert_{service_name}_{int(threshold)}",
                alert_name=f"Budget Alert - {service_name} ({threshold}%)",
                alert_type="budget",
                monthly_budget=monthly_budget,
                threshold_percentage=threshold,
                services=[service_name],
                projects=[self.project_id],
            )
            alerts.append(alert)
            self.cost_alerts.append(alert)

        self.monthly_budgets[service_name] = monthly_budget
        self.logger.info(f"Created {len(alerts)} budget alerts for {service_name}")

        return alerts

    def check_cost_alerts(self) -> List[CostAlert]:
        """Check all cost alerts and return triggered alerts."""
        triggered_alerts = []

        for alert in self.cost_alerts:
            if alert.status == "TRIGGERED":
                continue  # Already triggered

            # Get current cost for alert services
            current_cost = 0.0
            for service in alert.services:
                service_cost = self._get_current_service_cost(service)
                current_cost += service_cost

            alert.current_spend = current_cost

            # Check if threshold is exceeded
            threshold_amount = alert.monthly_budget * (alert.threshold_percentage / 100)

            if current_cost >= threshold_amount:
                alert.status = "TRIGGERED"
                alert.last_triggered = datetime.now()
                triggered_alerts.append(alert)

                self.logger.warning(
                    f"COST_ALERT_TRIGGERED: {alert.alert_name} - "
                    f"Current: ${current_cost:.2f}, Threshold: ${threshold_amount:.2f}"
                )

        return triggered_alerts

    def get_cost_optimization_plan(
        self,
        max_savings_target: float = 1000.0,
        max_implementation_hours: float = 40.0,
        prioritize_high_roi: bool = True,
    ) -> Dict[str, Any]:
        """Generate a comprehensive cost optimization plan."""

        plan = {
            "plan_id": f"cost_optimization_{int(datetime.now().timestamp())}",
            "created_at": datetime.now().isoformat(),
            "target_monthly_savings": max_savings_target,
            "max_implementation_effort": max_implementation_hours,
            "selected_recommendations": [],
            "summary": {},
            "implementation_phases": [],
        }

        # Filter and sort recommendations
        valid_recommendations = [
            rec
            for rec in self.optimization_recommendations
            if rec.expires_at is None or rec.expires_at > datetime.now()
        ]

        if prioritize_high_roi:
            # Sort by ROI (lower ROI months = higher priority)
            valid_recommendations.sort(key=lambda x: x.roi_months)
        else:
            # Sort by absolute savings
            valid_recommendations.sort(
                key=lambda x: x.projected_monthly_savings, reverse=True
            )

        # Select recommendations within constraints
        selected_recommendations = []
        total_savings = 0.0
        total_effort = 0.0

        for rec in valid_recommendations:
            if (
                total_savings + rec.projected_monthly_savings <= max_savings_target
                and total_effort + rec.estimated_implementation_hours
                <= max_implementation_hours
            ):
                selected_recommendations.append(rec)
                total_savings += rec.projected_monthly_savings
                total_effort += rec.estimated_implementation_hours

        plan["selected_recommendations"] = [
            rec.recommendation_id for rec in selected_recommendations
        ]

        # Generate summary
        plan["summary"] = {
            "total_recommendations": len(selected_recommendations),
            "total_monthly_savings": total_savings,
            "total_annual_savings": total_savings * 12,
            "total_implementation_hours": total_effort,
            "average_roi_months": statistics.mean(
                [
                    rec.roi_months
                    for rec in selected_recommendations
                    if rec.roi_months != float("inf")
                ]
            ),
            "savings_by_category": self._calculate_savings_by_category(
                selected_recommendations
            ),
            "risk_assessment": self._assess_plan_risk(selected_recommendations),
        }

        # Generate implementation phases
        plan["implementation_phases"] = self._create_implementation_phases(
            selected_recommendations
        )

        return plan

    def track_cost_trend(self, service_name: str, days: int = 30) -> Dict[str, Any]:
        """Track cost trends for a service over time."""

        if service_name not in self.cost_history:
            return {"error": "No cost history available for service"}

        # Get recent cost data
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_costs = [
            (timestamp, cost)
            for timestamp, cost in self.cost_history[service_name]
            if timestamp >= cutoff_date
        ]

        if len(recent_costs) < 2:
            return {"error": "Insufficient cost data for trend analysis"}

        # Calculate trend
        costs = [cost for _, cost in recent_costs]
        recent_avg = statistics.mean(costs[-7:])  # Last 7 days
        older_avg = statistics.mean(costs[:-7])  # Earlier period

        trend_change = ((recent_avg - older_avg) / older_avg) * 100

        # Determine trend direction
        if abs(trend_change) < 5:
            trend = "STABLE"
        elif trend_change > 0:
            trend = "INCREASING"
        else:
            trend = "DECREASING"

        # Project future costs
        daily_costs = [cost for _, cost in recent_costs[-7:]]
        daily_avg = statistics.mean(daily_costs)
        projected_monthly = daily_avg * 30

        return {
            "service_name": service_name,
            "trend_direction": trend,
            "trend_change_percent": trend_change,
            "recent_daily_average": daily_avg,
            "projected_monthly_cost": projected_monthly,
            "analysis_period_days": days,
            "data_points": len(recent_costs),
        }

    def generate_cost_report(self) -> Dict[str, Any]:
        """Generate a comprehensive cost optimization report."""

        report = {
            "report_id": f"cost_report_{int(datetime.now().timestamp())}",
            "generated_at": datetime.now().isoformat(),
            "project_id": self.project_id,
            "summary": {
                "total_active_alerts": len(
                    [a for a in self.cost_alerts if a.status == "ACTIVE"]
                ),
                "triggered_alerts": len(
                    [a for a in self.cost_alerts if a.status == "TRIGGERED"]
                ),
                "total_recommendations": len(self.optimization_recommendations),
                "total_potential_monthly_savings": sum(
                    r.projected_monthly_savings
                    for r in self.optimization_recommendations
                ),
                "high_priority_recommendations": len(
                    [
                        r
                        for r in self.optimization_recommendations
                        if r.opportunity_level == SavingsOpportunity.HIGH
                    ]
                ),
            },
            "cost_alerts": [
                {
                    "alert_name": alert.alert_name,
                    "status": alert.status,
                    "current_spend": alert.current_spend,
                    "budget": alert.monthly_budget,
                    "utilization_percent": (
                        (alert.current_spend / alert.monthly_budget) * 100
                        if alert.monthly_budget > 0
                        else 0
                    ),
                }
                for alert in self.cost_alerts
            ],
            "top_recommendations": [
                {
                    "title": rec.title,
                    "category": rec.category.value,
                    "monthly_savings": rec.projected_monthly_savings,
                    "annual_savings": rec.annual_savings,
                    "roi_months": rec.roi_months,
                    "confidence_score": rec.confidence_score,
                }
                for rec in sorted(
                    self.optimization_recommendations,
                    key=lambda x: x.projected_monthly_savings,
                    reverse=True,
                )[:10]
            ],
        }

        return report

    async def _collect_cost_data(
        self, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Collect cost data from GCP APIs (simulated for this implementation)."""

        # In a real implementation, this would call GCP Billing APIs
        # For now, return simulated cost data

        return {
            "cost_by_service": {
                "Compute Engine": 850.0,
                "Cloud Storage": 120.0,
                "BigQuery": 450.0,
                "Cloud Run": 75.0,
                "Load Balancing": 35.0,
                "VPC Network": 25.0,
            },
            "cost_by_project": {self.project_id: 1555.0},
            "compute_engine": {
                "instances": [
                    {
                        "name": "instance-1",
                        "machine_type": "n1-standard-4",
                        "cpu_utilization_avg": 8.5,
                        "memory_utilization_avg": 15.2,
                        "monthly_cost": 120.0,
                    },
                    {
                        "name": "instance-2",
                        "machine_type": "n1-standard-2",
                        "cpu_utilization_avg": 65.3,
                        "memory_utilization_avg": 72.1,
                        "monthly_cost": 60.0,
                    },
                ]
            },
            "cloud_storage": {
                "buckets": [
                    {
                        "name": "data-archive",
                        "storage_class": "STANDARD",
                        "access_frequency_30d": 2,
                        "monthly_cost": 80.0,
                    }
                ],
                "persistent_disks": [
                    {
                        "name": "disk-unused-1",
                        "status": "READY",
                        "attached_instances": [],
                        "monthly_cost": 25.0,
                    }
                ],
            },
            "bigquery": {
                "queries": [
                    {
                        "query_id": "expensive-query-1",
                        "bytes_processed": 2_500_000_000_000,  # 2.5 TB
                        "cost_usd": 12.50,
                    }
                ],
                "tables": [
                    {
                        "table_id": "large-table-1",
                        "size_gb": 500,
                        "partitioned": False,
                        "storage_cost_monthly": 10.0,
                    }
                ],
            },
            "networking": {
                "nat_gateways": [
                    {
                        "name": "nat-gateway-1",
                        "monthly_cost": 250.0,
                        "data_processed_gb": 5000,
                    }
                ],
                "load_balancers": [
                    {"name": "lb-underutilized", "rps_avg": 3.2, "monthly_cost": 18.0}
                ],
            },
            "compute_utilization": {
                "average_cpu_utilization": 35.2,
                "average_memory_utilization": 42.8,
            },
            "storage_utilization": {
                "total_provisioned_gb": 2500,
                "total_used_gb": 1800,
            },
            "anomalies": [],
        }

    def _get_current_service_cost(self, service_name: str) -> float:
        """Get current cost for a service (simulated)."""
        # In practice, this would query GCP Billing APIs
        service_costs = {
            "Compute Engine": 850.0,
            "Cloud Storage": 120.0,
            "BigQuery": 450.0,
            "Cloud Run": 75.0,
        }
        return service_costs.get(service_name, 0.0)

    def _determine_cost_trend(self, start_date: date) -> str:
        """Determine cost trend direction."""
        # Simplified implementation - would analyze historical data
        return "STABLE"

    def _calculate_savings_by_category(
        self, recommendations: List[CostRecommendation]
    ) -> Dict[str, float]:
        """Calculate total savings by category."""
        savings_by_category = {}
        for rec in recommendations:
            category = rec.category.value
            if category not in savings_by_category:
                savings_by_category[category] = 0.0
            savings_by_category[category] += rec.projected_monthly_savings
        return savings_by_category

    def _assess_plan_risk(
        self, recommendations: List[CostRecommendation]
    ) -> Dict[str, int]:
        """Assess overall risk of the implementation plan."""
        risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for rec in recommendations:
            risk_counts[rec.risk_level] += 1
        return risk_counts

    def _create_implementation_phases(
        self, recommendations: List[CostRecommendation]
    ) -> List[Dict[str, Any]]:
        """Create implementation phases for recommendations."""

        # Phase 1: Low risk, high ROI
        phase1 = [
            r for r in recommendations if r.risk_level == "LOW" and r.roi_months <= 3
        ]

        # Phase 2: Medium risk or longer ROI
        phase2 = [
            r
            for r in recommendations
            if r not in phase1 and r.risk_level in ["LOW", "MEDIUM"]
        ]

        # Phase 3: High risk implementations
        phase3 = [r for r in recommendations if r not in phase1 + phase2]

        phases = []

        if phase1:
            phases.append(
                {
                    "phase": 1,
                    "name": "Quick Wins - Low Risk",
                    "duration_weeks": 2,
                    "recommendations": [r.recommendation_id for r in phase1],
                    "total_savings": sum(r.projected_monthly_savings for r in phase1),
                    "total_effort_hours": sum(
                        r.estimated_implementation_hours for r in phase1
                    ),
                }
            )

        if phase2:
            phases.append(
                {
                    "phase": 2,
                    "name": "Medium Impact Optimizations",
                    "duration_weeks": 4,
                    "recommendations": [r.recommendation_id for r in phase2],
                    "total_savings": sum(r.projected_monthly_savings for r in phase2),
                    "total_effort_hours": sum(
                        r.estimated_implementation_hours for r in phase2
                    ),
                }
            )

        if phase3:
            phases.append(
                {
                    "phase": 3,
                    "name": "High Impact, Careful Planning",
                    "duration_weeks": 6,
                    "recommendations": [r.recommendation_id for r in phase3],
                    "total_savings": sum(r.projected_monthly_savings for r in phase3),
                    "total_effort_hours": sum(
                        r.estimated_implementation_hours for r in phase3
                    ),
                }
            )

        return phases

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
