"""
Performance Optimizer - CRAFT Function Component
GCP-specific performance optimization with automated recommendations

This module implements intelligent performance optimization for GCP services,
providing automated analysis and actionable recommendations for improvement.
"""

import logging
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from google.cloud import billing, monitoring_v3, resource_manager

    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False

logger = logging.getLogger(__name__)


class OptimizationCategory(Enum):
    """Performance optimization categories."""

    RESPONSE_TIME = "response_time"
    RESOURCE_UTILIZATION = "resource_utilization"
    COST_EFFICIENCY = "cost_efficiency"
    SCALABILITY = "scalability"
    RELIABILITY = "reliability"


class OptimizationPriority(Enum):
    """Optimization priority levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation."""

    # Identification
    recommendation_id: str
    title: str
    category: OptimizationCategory
    priority: OptimizationPriority

    # Analysis
    current_state: Dict[str, Any]
    target_state: Dict[str, Any]
    potential_improvement: Dict[str, float]  # metrics -> improvement %

    # Implementation
    implementation_steps: List[str]
    estimated_effort_hours: float
    risk_level: str  # LOW, MEDIUM, HIGH
    prerequisites: List[str] = field(default_factory=list)

    # Impact assessment
    performance_impact: str = ""
    cost_impact: str = ""
    user_impact: str = ""

    # GCP-specific
    affected_services: List[str] = field(default_factory=list)
    gcp_resources: List[str] = field(default_factory=list)
    terraform_changes: List[str] = field(default_factory=list)

    # Validation
    success_criteria: List[str] = field(default_factory=list)
    rollback_plan: str = ""

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    confidence_score: float = 0.0  # 0.0 to 1.0
    data_sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["category"] = self.category.value
        data["priority"] = self.priority.value
        data["created_at"] = self.created_at.isoformat()
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        return data


class GCPServiceAnalyzer:
    """Analyzer for specific GCP services performance."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.GCPServiceAnalyzer")

    def analyze_cloud_run_performance(
        self, service_name: str, metrics: Dict[str, List[float]]
    ) -> List[OptimizationRecommendation]:
        """Analyze Cloud Run service performance."""
        recommendations = []

        # Analyze CPU utilization
        if "cpu_utilization" in metrics:
            cpu_values = metrics["cpu_utilization"]
            avg_cpu = statistics.mean(cpu_values)
            max_cpu = max(cpu_values)

            # Over-provisioned CPU
            if avg_cpu < 0.2 and max_cpu < 0.5:  # Less than 20% average, 50% peak
                recommendations.append(
                    OptimizationRecommendation(
                        recommendation_id=f"cloud_run_cpu_downsize_{service_name}",
                        title=f"Reduce CPU allocation for {service_name}",
                        category=OptimizationCategory.COST_EFFICIENCY,
                        priority=OptimizationPriority.MEDIUM,
                        current_state={
                            "avg_cpu_utilization": avg_cpu,
                            "max_cpu_utilization": max_cpu,
                            "current_cpu_limit": metrics.get("cpu_limit", ["unknown"])[
                                0
                            ],
                        },
                        target_state={
                            "recommended_cpu_utilization": "40-60%",
                            "suggested_cpu_limit": "0.5 vCPU",
                        },
                        potential_improvement={
                            "cost_reduction": 25.0,
                            "efficiency_gain": 15.0,
                        },
                        implementation_steps=[
                            "Update Cloud Run service CPU limit from 1.0 to 0.5 vCPU",
                            "Monitor performance for 24 hours",
                            "Verify response times remain within SLA",
                            "Adjust if needed based on load patterns",
                        ],
                        estimated_effort_hours=2.0,
                        risk_level="LOW",
                        affected_services=[service_name],
                        gcp_resources=[f"Cloud Run service: {service_name}"],
                        terraform_changes=[
                            f'resource "google_cloud_run_service" "{service_name}" {{\n'
                            "  template {\n"
                            "    spec {\n"
                            "      containers {\n"
                            "        resources {\n"
                            "          limits = {\n"
                            '            cpu = "500m"\n'
                            "          }\n"
                            "        }\n"
                            "      }\n"
                            "    }\n"
                            "  }\n"
                            "}"
                        ],
                        success_criteria=[
                            "CPU utilization increases to 40-60% average",
                            "Response times remain < 500ms",
                            "No increase in error rate",
                            "Cost reduction visible in billing",
                        ],
                        rollback_plan="Increase CPU limit back to original value if performance degrades",
                        confidence_score=0.85,
                    )
                )

            # Under-provisioned CPU
            elif avg_cpu > 0.8 or max_cpu > 0.95:  # High utilization
                recommendations.append(
                    OptimizationRecommendation(
                        recommendation_id=f"cloud_run_cpu_upsize_{service_name}",
                        title=f"Increase CPU allocation for {service_name}",
                        category=OptimizationCategory.RESPONSE_TIME,
                        priority=OptimizationPriority.HIGH,
                        current_state={
                            "avg_cpu_utilization": avg_cpu,
                            "max_cpu_utilization": max_cpu,
                            "current_cpu_limit": metrics.get("cpu_limit", ["unknown"])[
                                0
                            ],
                        },
                        target_state={
                            "recommended_cpu_utilization": "60-70%",
                            "suggested_cpu_limit": "2.0 vCPU",
                        },
                        potential_improvement={
                            "response_time_improvement": 30.0,
                            "throughput_increase": 40.0,
                        },
                        implementation_steps=[
                            "Update Cloud Run service CPU limit to 2.0 vCPU",
                            "Monitor performance improvements",
                            "Validate response time improvements",
                            "Check for any cold start improvements",
                        ],
                        estimated_effort_hours=1.5,
                        risk_level="LOW",
                        affected_services=[service_name],
                        gcp_resources=[f"Cloud Run service: {service_name}"],
                        success_criteria=[
                            "CPU utilization decreases to 60-70% average",
                            "Response times improve by 20%+",
                            "Throughput increases",
                            "Reduced request queuing",
                        ],
                        confidence_score=0.90,
                    )
                )

        # Analyze memory utilization
        if "memory_utilization" in metrics:
            memory_values = metrics["memory_utilization"]
            avg_memory = statistics.mean(memory_values)
            max_memory = max(memory_values)

            if avg_memory > 0.85 or max_memory > 0.95:
                recommendations.append(
                    OptimizationRecommendation(
                        recommendation_id=f"cloud_run_memory_upsize_{service_name}",
                        title=f"Increase memory allocation for {service_name}",
                        category=OptimizationCategory.RELIABILITY,
                        priority=OptimizationPriority.HIGH,
                        current_state={
                            "avg_memory_utilization": avg_memory,
                            "max_memory_utilization": max_memory,
                        },
                        target_state={
                            "recommended_memory_utilization": "70-80%",
                            "suggested_memory_limit": "2Gi",
                        },
                        potential_improvement={
                            "stability_improvement": 25.0,
                            "oom_reduction": 90.0,
                        },
                        implementation_steps=[
                            "Increase Cloud Run memory limit to 2Gi",
                            "Monitor for OOM errors reduction",
                            "Verify memory usage patterns",
                            "Optimize memory usage in application code if needed",
                        ],
                        estimated_effort_hours=2.0,
                        risk_level="LOW",
                        confidence_score=0.88,
                    )
                )

        # Analyze concurrency settings
        if "concurrent_requests" in metrics:
            concurrent_values = metrics["concurrent_requests"]
            avg_concurrent = statistics.mean(concurrent_values)
            max_concurrent = max(concurrent_values)

            if max_concurrent > 80:  # Default Cloud Run concurrency is 100
                recommendations.append(
                    OptimizationRecommendation(
                        recommendation_id=f"cloud_run_concurrency_optimize_{service_name}",
                        title=f"Optimize concurrency settings for {service_name}",
                        category=OptimizationCategory.SCALABILITY,
                        priority=OptimizationPriority.MEDIUM,
                        current_state={
                            "avg_concurrent_requests": avg_concurrent,
                            "max_concurrent_requests": max_concurrent,
                            "current_concurrency_limit": 100,
                        },
                        target_state={
                            "recommended_concurrency_limit": "50-60",
                            "reason": "Better resource utilization and response times",
                        },
                        potential_improvement={
                            "response_time_consistency": 20.0,
                            "resource_efficiency": 15.0,
                        },
                        implementation_steps=[
                            "Set Cloud Run concurrency to 50 requests per instance",
                            "Monitor instance scaling behavior",
                            "Verify response time consistency",
                            "Adjust based on load testing results",
                        ],
                        estimated_effort_hours=3.0,
                        risk_level="MEDIUM",
                        confidence_score=0.75,
                    )
                )

        return recommendations

    def analyze_gke_performance(
        self, cluster_name: str, metrics: Dict[str, List[float]]
    ) -> List[OptimizationRecommendation]:
        """Analyze GKE cluster performance."""
        recommendations = []

        # Node utilization analysis
        if "node_cpu_utilization" in metrics:
            node_cpu_values = metrics["node_cpu_utilization"]
            avg_node_cpu = statistics.mean(node_cpu_values)

            if avg_node_cpu < 0.3:  # Under-utilized nodes
                recommendations.append(
                    OptimizationRecommendation(
                        recommendation_id=f"gke_node_downsize_{cluster_name}",
                        title=f"Right-size GKE nodes for {cluster_name}",
                        category=OptimizationCategory.COST_EFFICIENCY,
                        priority=OptimizationPriority.MEDIUM,
                        current_state={
                            "avg_node_cpu_utilization": avg_node_cpu,
                            "current_node_type": "e2-standard-4",  # Example
                        },
                        target_state={
                            "recommended_node_type": "e2-standard-2",
                            "expected_utilization": "50-70%",
                        },
                        potential_improvement={
                            "cost_reduction": 50.0,
                            "efficiency_gain": 25.0,
                        },
                        implementation_steps=[
                            "Create new node pool with smaller instance types",
                            "Migrate workloads to new node pool",
                            "Monitor resource usage and performance",
                            "Remove old node pool once migration is complete",
                        ],
                        estimated_effort_hours=8.0,
                        risk_level="MEDIUM",
                        prerequisites=[
                            "Backup cluster configuration",
                            "Plan maintenance window",
                            "Verify workload resource requirements",
                        ],
                        confidence_score=0.80,
                    )
                )

        # HPA analysis
        if "pod_cpu_utilization" in metrics and "replica_count" in metrics:
            pod_cpu_values = metrics["pod_cpu_utilization"]
            replica_values = metrics["replica_count"]

            avg_pod_cpu = statistics.mean(pod_cpu_values)
            max_replicas = max(replica_values)
            min_replicas = min(replica_values)

            if avg_pod_cpu < 0.5 and max_replicas > min_replicas * 3:
                recommendations.append(
                    OptimizationRecommendation(
                        recommendation_id=f"gke_hpa_tune_{cluster_name}",
                        title=f"Optimize HPA settings for {cluster_name}",
                        category=OptimizationCategory.SCALABILITY,
                        priority=OptimizationPriority.MEDIUM,
                        current_state={
                            "avg_pod_cpu_utilization": avg_pod_cpu,
                            "max_replicas": max_replicas,
                            "min_replicas": min_replicas,
                            "current_hpa_target": 70,
                        },
                        target_state={
                            "recommended_hpa_target": 60,
                            "adjusted_min_replicas": min_replicas,
                            "adjusted_max_replicas": int(max_replicas * 0.8),
                        },
                        potential_improvement={
                            "resource_efficiency": 20.0,
                            "cost_reduction": 15.0,
                        },
                        implementation_steps=[
                            "Update HPA target CPU utilization to 60%",
                            "Adjust max replicas based on actual usage patterns",
                            "Monitor scaling behavior",
                            "Fine-tune based on performance metrics",
                        ],
                        estimated_effort_hours=4.0,
                        risk_level="LOW",
                        confidence_score=0.75,
                    )
                )

        return recommendations

    def analyze_bigquery_performance(
        self, dataset_name: str, metrics: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Analyze BigQuery performance and costs."""
        recommendations = []

        # Query cost analysis
        if "query_costs" in metrics:
            query_costs = metrics["query_costs"]
            expensive_queries = [q for q in query_costs if q["cost_usd"] > 10.0]

            if expensive_queries:
                recommendations.append(
                    OptimizationRecommendation(
                        recommendation_id=f"bigquery_cost_optimize_{dataset_name}",
                        title=f"Optimize expensive BigQuery queries in {dataset_name}",
                        category=OptimizationCategory.COST_EFFICIENCY,
                        priority=OptimizationPriority.HIGH,
                        current_state={
                            "expensive_query_count": len(expensive_queries),
                            "total_monthly_cost": sum(
                                q["cost_usd"] for q in expensive_queries
                            ),
                            "most_expensive_query_cost": max(
                                q["cost_usd"] for q in expensive_queries
                            ),
                        },
                        target_state={
                            "optimized_query_cost_reduction": "30-50%",
                            "query_optimization_techniques": [
                                "partitioning",
                                "clustering",
                                "query_rewriting",
                            ],
                        },
                        potential_improvement={
                            "cost_reduction": 40.0,
                            "query_performance": 25.0,
                        },
                        implementation_steps=[
                            "Identify queries scanning > 1TB of data",
                            "Implement table partitioning by date/timestamp",
                            "Add clustering keys for frequently filtered columns",
                            "Rewrite queries to use partition pruning",
                            "Add query result caching where appropriate",
                        ],
                        estimated_effort_hours=12.0,
                        risk_level="LOW",
                        affected_services=[dataset_name],
                        gcp_resources=[f"BigQuery dataset: {dataset_name}"],
                        success_criteria=[
                            "Query costs reduced by 30%+",
                            "Query execution times improved",
                            "No degradation in result accuracy",
                            "Partition pruning working effectively",
                        ],
                        confidence_score=0.85,
                    )
                )

        # Storage optimization
        if "table_sizes" in metrics:
            table_sizes = metrics["table_sizes"]
            large_tables = [t for t in table_sizes if t["size_gb"] > 100]

            for table in large_tables:
                if not table.get("partitioned", False):
                    recommendations.append(
                        OptimizationRecommendation(
                            recommendation_id=f"bigquery_partition_{table['name']}",
                            title=f"Add partitioning to large table {table['name']}",
                            category=OptimizationCategory.RESPONSE_TIME,
                            priority=OptimizationPriority.HIGH,
                            current_state={
                                "table_size_gb": table["size_gb"],
                                "partitioned": False,
                                "clustered": table.get("clustered", False),
                            },
                            target_state={
                                "partitioned": True,
                                "partition_type": "DATE",
                                "expected_performance_improvement": "60-80%",
                            },
                            potential_improvement={
                                "query_performance": 70.0,
                                "cost_reduction": 60.0,
                            },
                            implementation_steps=[
                                f"Create partitioned version of {table['name']}",
                                "Copy data to partitioned table using date column",
                                "Update all queries to use new partitioned table",
                                "Verify query performance improvements",
                                "Drop original table after validation",
                            ],
                            estimated_effort_hours=6.0,
                            risk_level="MEDIUM",
                            prerequisites=[
                                "Identify appropriate partition column",
                                "Plan data migration strategy",
                                "Update application queries",
                            ],
                            confidence_score=0.90,
                        )
                    )

        return recommendations

    def analyze_cloud_storage_performance(
        self, bucket_name: str, metrics: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Analyze Cloud Storage performance and costs."""
        recommendations = []

        # Storage class optimization
        if "object_access_patterns" in metrics:
            access_patterns = metrics["object_access_patterns"]

            # Find objects with low access frequency but in Standard storage
            infrequent_objects = [
                obj
                for obj in access_patterns
                if obj.get("access_count_30d", 0) < 5
                and obj.get("storage_class") == "STANDARD"
            ]

            if infrequent_objects:
                total_size_gb = sum(obj.get("size_gb", 0) for obj in infrequent_objects)

                recommendations.append(
                    OptimizationRecommendation(
                        recommendation_id=f"storage_class_optimize_{bucket_name}",
                        title=f"Optimize storage classes for {bucket_name}",
                        category=OptimizationCategory.COST_EFFICIENCY,
                        priority=OptimizationPriority.MEDIUM,
                        current_state={
                            "infrequent_objects_count": len(infrequent_objects),
                            "infrequent_objects_size_gb": total_size_gb,
                            "current_storage_class": "STANDARD",
                            "monthly_cost_standard": total_size_gb
                            * 0.020,  # $0.020/GB/month
                        },
                        target_state={
                            "recommended_storage_class": "NEARLINE",
                            "expected_monthly_cost": total_size_gb
                            * 0.010,  # $0.010/GB/month
                            "cost_savings_monthly": total_size_gb * 0.010,
                        },
                        potential_improvement={
                            "cost_reduction": 50.0,
                            "storage_efficiency": 100.0,
                        },
                        implementation_steps=[
                            "Set up lifecycle policy for objects > 30 days old",
                            "Transition infrequently accessed objects to Nearline",
                            "Monitor access patterns for validation",
                            "Consider Coldline for objects > 90 days old",
                        ],
                        estimated_effort_hours=4.0,
                        risk_level="LOW",
                        affected_services=[bucket_name],
                        gcp_resources=[f"Cloud Storage bucket: {bucket_name}"],
                        terraform_changes=[
                            f'resource "google_storage_bucket" "{bucket_name}" {{\n'
                            "  lifecycle_rule {\n"
                            "    condition {\n"
                            "      age = 30\n"
                            "    }\n"
                            "    action {\n"
                            '      type = "SetStorageClass"\n'
                            '      storage_class = "NEARLINE"\n'
                            "    }\n"
                            "  }\n"
                            "}"
                        ],
                        confidence_score=0.95,
                    )
                )

        return recommendations


class PerformanceOptimizer:
    """
    Performance optimizer implementing CRAFT Function methodology.

    Provides intelligent performance optimization with:
    - Automated performance analysis
    - GCP-specific optimization recommendations
    - Cost efficiency improvements
    - Scalability enhancements
    - Implementation guidance
    """

    def __init__(self, gcp_project_id: Optional[str] = None):
        self.logger = logging.getLogger(f"{__name__}.PerformanceOptimizer")
        self.gcp_project_id = gcp_project_id or self._get_gcp_project_id()

        # Initialize analyzers
        self.gcp_analyzer = (
            GCPServiceAnalyzer(self.gcp_project_id) if self.gcp_project_id else None
        )

        # Recommendation storage
        self.recommendations: List[OptimizationRecommendation] = []
        self.implemented_recommendations: List[str] = []

        # Performance baselines
        self.performance_baselines: Dict[str, Dict[str, float]] = {}

        self.logger.info("PerformanceOptimizer initialized")

    async def analyze_service_performance(
        self,
        service_name: str,
        service_type: str,
        metrics: Dict[str, Any],
        time_range_hours: int = 24,
    ) -> List[OptimizationRecommendation]:
        """Analyze service performance and generate recommendations."""

        if not self.gcp_analyzer:
            self.logger.warning("GCP analyzer not available")
            return []

        recommendations = []

        try:
            # Analyze based on service type
            if service_type.lower() == "cloud_run":
                recommendations.extend(
                    self.gcp_analyzer.analyze_cloud_run_performance(
                        service_name, metrics
                    )
                )
            elif service_type.lower() == "gke":
                recommendations.extend(
                    self.gcp_analyzer.analyze_gke_performance(service_name, metrics)
                )
            elif service_type.lower() == "bigquery":
                recommendations.extend(
                    self.gcp_analyzer.analyze_bigquery_performance(
                        service_name, metrics
                    )
                )
            elif service_type.lower() == "cloud_storage":
                recommendations.extend(
                    self.gcp_analyzer.analyze_cloud_storage_performance(
                        service_name, metrics
                    )
                )
            else:
                self.logger.warning(f"Unknown service type: {service_type}")

            # Add generic performance recommendations
            generic_recommendations = self._generate_generic_recommendations(
                service_name, metrics
            )
            recommendations.extend(generic_recommendations)

            # Store recommendations
            self.recommendations.extend(recommendations)

            # Set expiration dates for recommendations
            for rec in recommendations:
                rec.expires_at = datetime.now() + timedelta(days=30)

            self.logger.info(
                f"Generated {len(recommendations)} recommendations for {service_name}"
            )

        except Exception as e:
            self.logger.error(f"Error analyzing service performance: {e}")

        return recommendations

    def get_recommendations_by_priority(
        self,
        priority: OptimizationPriority,
        category: Optional[OptimizationCategory] = None,
        service_name: Optional[str] = None,
    ) -> List[OptimizationRecommendation]:
        """Get recommendations filtered by priority and other criteria."""

        filtered_recommendations = [
            rec
            for rec in self.recommendations
            if rec.priority == priority
            and (category is None or rec.category == category)
            and (service_name is None or service_name in rec.affected_services)
            and (rec.expires_at is None or rec.expires_at > datetime.now())
            and rec.recommendation_id not in self.implemented_recommendations
        ]

        # Sort by confidence score descending
        filtered_recommendations.sort(key=lambda x: x.confidence_score, reverse=True)

        return filtered_recommendations

    def get_cost_optimization_recommendations(
        self, max_effort_hours: Optional[float] = None
    ) -> List[OptimizationRecommendation]:
        """Get cost optimization recommendations."""

        cost_recommendations = [
            rec
            for rec in self.recommendations
            if rec.category == OptimizationCategory.COST_EFFICIENCY
            and rec.recommendation_id not in self.implemented_recommendations
            and (rec.expires_at is None or rec.expires_at > datetime.now())
        ]

        # Filter by effort if specified
        if max_effort_hours:
            cost_recommendations = [
                rec
                for rec in cost_recommendations
                if rec.estimated_effort_hours <= max_effort_hours
            ]

        # Sort by potential cost reduction
        def get_cost_reduction(rec):
            return rec.potential_improvement.get("cost_reduction", 0.0)

        cost_recommendations.sort(key=get_cost_reduction, reverse=True)

        return cost_recommendations

    def generate_optimization_plan(
        self,
        max_recommendations: int = 10,
        max_total_effort_hours: float = 40.0,
        prioritize_quick_wins: bool = True,
    ) -> Dict[str, Any]:
        """Generate a comprehensive optimization plan."""

        plan = {
            "plan_id": f"optimization_plan_{int(datetime.now().timestamp())}",
            "created_at": datetime.now().isoformat(),
            "parameters": {
                "max_recommendations": max_recommendations,
                "max_total_effort_hours": max_total_effort_hours,
                "prioritize_quick_wins": prioritize_quick_wins,
            },
            "recommendations": [],
            "summary": {},
            "implementation_timeline": [],
        }

        # Get all valid recommendations
        valid_recommendations = [
            rec
            for rec in self.recommendations
            if rec.recommendation_id not in self.implemented_recommendations
            and (rec.expires_at is None or rec.expires_at > datetime.now())
        ]

        if prioritize_quick_wins:
            # Sort by effort/impact ratio (lower is better)
            def effort_impact_ratio(rec):
                max_improvement = (
                    max(rec.potential_improvement.values())
                    if rec.potential_improvement
                    else 1.0
                )
                return rec.estimated_effort_hours / max(max_improvement, 1.0)

            valid_recommendations.sort(key=effort_impact_ratio)
        else:
            # Sort by priority and confidence
            priority_order = {
                OptimizationPriority.CRITICAL: 4,
                OptimizationPriority.HIGH: 3,
                OptimizationPriority.MEDIUM: 2,
                OptimizationPriority.LOW: 1,
            }

            valid_recommendations.sort(
                key=lambda x: (priority_order.get(x.priority, 0), x.confidence_score),
                reverse=True,
            )

        # Select recommendations within constraints
        selected_recommendations = []
        total_effort = 0.0

        for rec in valid_recommendations:
            if len(selected_recommendations) >= max_recommendations:
                break

            if total_effort + rec.estimated_effort_hours <= max_total_effort_hours:
                selected_recommendations.append(rec)
                total_effort += rec.estimated_effort_hours

        plan["recommendations"] = [rec.to_dict() for rec in selected_recommendations]

        # Generate summary
        plan["summary"] = self._generate_plan_summary(selected_recommendations)

        # Generate implementation timeline
        plan["implementation_timeline"] = self._generate_implementation_timeline(
            selected_recommendations
        )

        return plan

    def mark_recommendation_implemented(
        self,
        recommendation_id: str,
        implementation_notes: str = "",
        actual_effort_hours: Optional[float] = None,
    ) -> bool:
        """Mark a recommendation as implemented."""

        if recommendation_id in self.implemented_recommendations:
            return False

        self.implemented_recommendations.append(recommendation_id)

        # Find the recommendation and update it
        for rec in self.recommendations:
            if rec.recommendation_id == recommendation_id:
                rec.metadata = rec.metadata if hasattr(rec, "metadata") else {}
                rec.metadata["implemented_at"] = datetime.now().isoformat()
                rec.metadata["implementation_notes"] = implementation_notes
                if actual_effort_hours:
                    rec.metadata["actual_effort_hours"] = actual_effort_hours
                break

        self.logger.info(f"Marked recommendation as implemented: {recommendation_id}")
        return True

    def _generate_generic_recommendations(
        self, service_name: str, metrics: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Generate generic performance recommendations applicable to any service."""
        recommendations = []

        # Response time analysis
        if "response_times" in metrics:
            response_times = metrics["response_times"]
            if response_times:
                avg_response_time = statistics.mean(response_times)
                p95_response_time = sorted(response_times)[
                    int(0.95 * len(response_times))
                ]

                if avg_response_time > 1000:  # > 1 second average
                    recommendations.append(
                        OptimizationRecommendation(
                            recommendation_id=f"response_time_optimization_{service_name}",
                            title=f"Improve response times for {service_name}",
                            category=OptimizationCategory.RESPONSE_TIME,
                            priority=OptimizationPriority.HIGH,
                            current_state={
                                "avg_response_time_ms": avg_response_time,
                                "p95_response_time_ms": p95_response_time,
                            },
                            target_state={
                                "target_avg_response_time_ms": 500,
                                "target_p95_response_time_ms": 1000,
                            },
                            potential_improvement={
                                "response_time_improvement": 50.0,
                                "user_satisfaction": 25.0,
                            },
                            implementation_steps=[
                                "Profile application to identify bottlenecks",
                                "Implement caching for frequently accessed data",
                                "Optimize database queries and add indexes",
                                "Consider using CDN for static content",
                                "Implement connection pooling",
                                "Review and optimize business logic",
                            ],
                            estimated_effort_hours=16.0,
                            risk_level="MEDIUM",
                            confidence_score=0.80,
                        )
                    )

        # Error rate analysis
        if "error_rates" in metrics:
            error_rates = metrics["error_rates"]
            if error_rates:
                avg_error_rate = statistics.mean(error_rates)

                if avg_error_rate > 2.0:  # > 2% error rate
                    recommendations.append(
                        OptimizationRecommendation(
                            recommendation_id=f"error_rate_reduction_{service_name}",
                            title=f"Reduce error rate for {service_name}",
                            category=OptimizationCategory.RELIABILITY,
                            priority=OptimizationPriority.CRITICAL,
                            current_state={"avg_error_rate_percent": avg_error_rate},
                            target_state={"target_error_rate_percent": 1.0},
                            potential_improvement={
                                "reliability_improvement": 60.0,
                                "user_experience": 40.0,
                            },
                            implementation_steps=[
                                "Analyze error logs to identify common failure patterns",
                                "Implement proper error handling and retry logic",
                                "Add input validation and sanitization",
                                "Implement circuit breakers for external dependencies",
                                "Add health checks and monitoring",
                                "Review and fix application logic bugs",
                            ],
                            estimated_effort_hours=20.0,
                            risk_level="LOW",
                            confidence_score=0.85,
                        )
                    )

        return recommendations

    def _generate_plan_summary(
        self, recommendations: List[OptimizationRecommendation]
    ) -> Dict[str, Any]:
        """Generate a summary of the optimization plan."""

        if not recommendations:
            return {}

        summary = {
            "total_recommendations": len(recommendations),
            "total_estimated_effort_hours": sum(
                rec.estimated_effort_hours for rec in recommendations
            ),
            "priority_breakdown": {},
            "category_breakdown": {},
            "potential_improvements": {},
            "risk_assessment": {},
            "affected_services": list(
                set(
                    service
                    for rec in recommendations
                    for service in rec.affected_services
                )
            ),
        }

        # Priority breakdown
        for priority in OptimizationPriority:
            count = sum(1 for rec in recommendations if rec.priority == priority)
            summary["priority_breakdown"][priority.value] = count

        # Category breakdown
        for category in OptimizationCategory:
            count = sum(1 for rec in recommendations if rec.category == category)
            summary["category_breakdown"][category.value] = count

        # Aggregate potential improvements
        all_improvements = {}
        for rec in recommendations:
            for metric, improvement in rec.potential_improvement.items():
                if metric not in all_improvements:
                    all_improvements[metric] = []
                all_improvements[metric].append(improvement)

        for metric, improvements in all_improvements.items():
            summary["potential_improvements"][metric] = {
                "average": statistics.mean(improvements),
                "maximum": max(improvements),
                "total_opportunities": len(improvements),
            }

        # Risk assessment
        risk_levels = [rec.risk_level for rec in recommendations]
        summary["risk_assessment"] = {
            "LOW": risk_levels.count("LOW"),
            "MEDIUM": risk_levels.count("MEDIUM"),
            "HIGH": risk_levels.count("HIGH"),
            "overall_risk": "MEDIUM" if "HIGH" in risk_levels else "LOW",
        }

        return summary

    def _generate_implementation_timeline(
        self, recommendations: List[OptimizationRecommendation]
    ) -> List[Dict[str, Any]]:
        """Generate an implementation timeline for recommendations."""

        # Group by priority and effort
        timeline = []

        # Phase 1: Critical and high priority, low effort
        phase1 = [
            rec
            for rec in recommendations
            if rec.priority
            in [OptimizationPriority.CRITICAL, OptimizationPriority.HIGH]
            and rec.estimated_effort_hours <= 8.0
        ]

        if phase1:
            timeline.append(
                {
                    "phase": 1,
                    "name": "Quick Critical Fixes",
                    "duration_weeks": 1,
                    "recommendations": [rec.recommendation_id for rec in phase1],
                    "total_effort_hours": sum(
                        rec.estimated_effort_hours for rec in phase1
                    ),
                    "expected_impact": "High impact, low effort improvements",
                }
            )

        # Phase 2: High priority, medium effort
        phase2 = [
            rec
            for rec in recommendations
            if rec.priority == OptimizationPriority.HIGH
            and rec.estimated_effort_hours > 8.0
            and rec not in phase1
        ]

        if phase2:
            timeline.append(
                {
                    "phase": 2,
                    "name": "Major Performance Improvements",
                    "duration_weeks": 2,
                    "recommendations": [rec.recommendation_id for rec in phase2],
                    "total_effort_hours": sum(
                        rec.estimated_effort_hours for rec in phase2
                    ),
                    "expected_impact": "Significant performance and reliability improvements",
                }
            )

        # Phase 3: Medium priority optimizations
        phase3 = [
            rec
            for rec in recommendations
            if rec.priority == OptimizationPriority.MEDIUM
            and rec not in phase1 + phase2
        ]

        if phase3:
            timeline.append(
                {
                    "phase": 3,
                    "name": "Efficiency and Cost Optimizations",
                    "duration_weeks": 3,
                    "recommendations": [rec.recommendation_id for rec in phase3],
                    "total_effort_hours": sum(
                        rec.estimated_effort_hours for rec in phase3
                    ),
                    "expected_impact": "Cost reduction and efficiency improvements",
                }
            )

        # Phase 4: Low priority, long-term improvements
        phase4 = [rec for rec in recommendations if rec not in phase1 + phase2 + phase3]

        if phase4:
            timeline.append(
                {
                    "phase": 4,
                    "name": "Long-term Optimizations",
                    "duration_weeks": 4,
                    "recommendations": [rec.recommendation_id for rec in phase4],
                    "total_effort_hours": sum(
                        rec.estimated_effort_hours for rec in phase4
                    ),
                    "expected_impact": "Long-term maintainability and performance",
                }
            )

        return timeline

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
