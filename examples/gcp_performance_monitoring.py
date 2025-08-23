#!/usr/bin/env python3
"""
GCP Performance Monitoring Example
Demonstrates comprehensive performance monitoring with CRAFT methodology

This example shows how to use the Genesis performance monitoring system
with GCP-native integrations for optimal performance and cost efficiency.
"""

import asyncio
import json
import logging

from core.performance import (BenchmarkConfig, CostOptimizationMonitor,
                              OptimizedSecretManager, PerformanceBenchmarks,
                              PerformanceMonitor, PerformanceOptimizer,
                              PerformanceProfiler, ProfilerConfig,
                              RegressionDetector)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# Example application functions to benchmark
async def example_database_operation():
    """Simulate database operation."""
    await asyncio.sleep(0.1)  # Simulate 100ms DB query
    return {"status": "success", "records": 42}


async def example_api_call():
    """Simulate external API call."""
    await asyncio.sleep(0.05)  # Simulate 50ms API call
    return {"data": "example_response"}


def example_computation():
    """Simulate CPU-intensive computation."""
    result = sum(i**2 for i in range(1000))
    return result


class PerformanceMonitoringDemo:
    """Demonstration of comprehensive performance monitoring."""

    def __init__(self, gcp_project_id: str = "your-gcp-project"):
        self.gcp_project_id = gcp_project_id

        # Initialize performance monitoring components
        self.profiler = PerformanceProfiler(
            ProfilerConfig(
                enable_cpu_profiling=True,
                enable_memory_profiling=True,
                sampling_interval=0.1,
                profile_duration=60,
            )
        )

        self.benchmarks = PerformanceBenchmarks()
        self.regression_detector = RegressionDetector()

        self.monitor = PerformanceMonitor(
            gcp_project_id=gcp_project_id, metric_prefix="genesis.demo.performance"
        )

        self.optimizer = PerformanceOptimizer(gcp_project_id=gcp_project_id)
        self.cost_monitor = CostOptimizationMonitor(project_id=gcp_project_id)

        # Optimized Secret Manager for demo
        self.secret_manager = OptimizedSecretManager(gcp_project_id)

        logger.info("Performance monitoring demo initialized")

    async def demonstrate_profiling(self):
        """Demonstrate performance profiling capabilities."""
        logger.info("=== Performance Profiling Demo ===")

        # Start profiling session
        profile_id = self.profiler.start_profiling("demo_profile")

        # Simulate application operations
        with self.profiler.profile_context("database_operations"):
            for _ in range(5):
                await example_database_operation()

        with self.profiler.profile_context("api_calls"):
            for _ in range(10):
                await example_api_call()

        with self.profiler.profile_context("computations"):
            for _ in range(3):
                example_computation()

        # Stop profiling and get results
        profile_report = self.profiler.stop_profiling(profile_id)

        logger.info("Profiling completed:")
        logger.info(f"  - Total duration: {profile_report.total_duration_ms:.2f}ms")
        logger.info(f"  - Average CPU: {profile_report.avg_cpu_percent:.1f}%")
        logger.info(f"  - Peak memory: {profile_report.max_memory_mb:.2f}MB")
        logger.info(f"  - Performance issues: {len(profile_report.performance_issues)}")

        # Get performance summary
        summary = self.profiler.get_performance_summary()
        logger.info(f"Performance summary: {json.dumps(summary, indent=2)}")

    async def demonstrate_benchmarking(self):
        """Demonstrate performance benchmarking capabilities."""
        logger.info("=== Performance Benchmarking Demo ===")

        # Register benchmark configurations
        db_benchmark_config = BenchmarkConfig(
            benchmark_name="database_operations",
            target_function=example_database_operation,
            warmup_iterations=3,
            measurement_iterations=20,
            target_avg_ms=150.0,  # Target: < 150ms average
            target_p95_ms=200.0,  # Target: < 200ms P95
            gcp_project_id=self.gcp_project_id,
            environment="demo",
        )

        api_benchmark_config = BenchmarkConfig(
            benchmark_name="api_calls",
            target_function=example_api_call,
            warmup_iterations=3,
            measurement_iterations=15,
            target_avg_ms=75.0,  # Target: < 75ms average
            target_p95_ms=100.0,  # Target: < 100ms P95
            gcp_project_id=self.gcp_project_id,
            environment="demo",
        )

        self.benchmarks.register_benchmark(db_benchmark_config)
        self.benchmarks.register_benchmark(api_benchmark_config)

        # Run individual benchmarks
        db_result = await self.benchmarks.run_benchmark("database_operations")
        logger.info("Database benchmark result:")
        logger.info(f"  - Average: {db_result.avg_duration_ms:.2f}ms")
        logger.info(f"  - P95: {db_result.p95_duration_ms:.2f}ms")
        logger.info(f"  - Grade: {db_result.performance_grade}")
        logger.info(f"  - Meets targets: {db_result.meets_targets}")

        # Run benchmark suite
        suite_results = await self.benchmarks.run_benchmark_suite()
        logger.info(f"Benchmark suite completed with {len(suite_results)} benchmarks")

        # Create and update baselines
        if len(db_result.valid_samples) >= 10:
            # Create baseline for regression detection
            duration_samples = [db_result.avg_duration_ms] * db_result.valid_samples
            baseline = self.regression_detector.create_baseline(
                operation_name="database_operations",
                duration_samples=duration_samples,
                environment="demo",
                version="1.0.0",
            )
            logger.info(f"Created performance baseline: {baseline.baseline_id}")

    async def demonstrate_monitoring_and_alerting(self):
        """Demonstrate performance monitoring and alerting."""
        logger.info("=== Performance Monitoring & Alerting Demo ===")

        # Create performance alerts
        response_time_alert = self.monitor.create_response_time_alert(
            service_name="demo_service", threshold_ms=200.0, environment="demo"
        )
        logger.info(f"Created response time alert: {response_time_alert.alert_name}")

        error_rate_alert = self.monitor.create_error_rate_alert(
            service_name="demo_service", threshold_percent=2.0, environment="demo"
        )
        logger.info(f"Created error rate alert: {error_rate_alert.alert_name}")

        # Record performance metrics
        for i in range(10):
            # Simulate varying response times
            response_time = 100 + (i * 20)  # 100ms to 280ms
            self.monitor.record_performance_metric(
                "response_time",
                response_time,
                labels={
                    "service_name": "demo_service",
                    "environment": "demo",
                    "endpoint": "/api/test",
                },
            )

            # Simulate error rate
            error_rate = min(i * 0.5, 5.0)  # 0% to 5%
            self.monitor.record_performance_metric(
                "error_rate",
                error_rate,
                labels={"service_name": "demo_service", "environment": "demo"},
            )

        # Check for threshold breaches
        triggered_incidents = self.monitor.check_performance_thresholds()
        if triggered_incidents:
            logger.info(f"Triggered {len(triggered_incidents)} performance incidents:")
            for incident in triggered_incidents:
                logger.info(f"  - {incident.alert_name}: {incident.current_value}")

        # Generate performance summary
        summary = self.monitor.get_performance_summary("demo_service")
        logger.info(f"Performance summary: {json.dumps(summary, indent=2)}")

    async def demonstrate_optimization(self):
        """Demonstrate performance optimization recommendations."""
        logger.info("=== Performance Optimization Demo ===")

        # Simulate service performance metrics for optimization analysis
        simulated_metrics = {
            "response_times": [120, 150, 180, 200, 250, 300, 180, 160, 140, 190],
            "error_rates": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 2.0, 1.5, 1.0, 1.8],
            "cpu_utilization": [45, 55, 65, 75, 85, 90, 70, 60, 50, 65],
            "memory_utilization": [60, 65, 70, 75, 80, 85, 75, 70, 65, 72],
        }

        # Analyze service performance
        recommendations = await self.optimizer.analyze_service_performance(
            service_name="demo_service",
            service_type="cloud_run",
            metrics=simulated_metrics,
        )

        logger.info(f"Generated {len(recommendations)} optimization recommendations:")
        for rec in recommendations:
            logger.info(f"  - {rec.title} ({rec.category.value})")
            logger.info(f"    Priority: {rec.priority.value}")
            logger.info(f"    Potential improvement: {rec.potential_improvement}")
            logger.info(f"    Effort: {rec.estimated_effort_hours} hours")

        # Generate optimization plan
        plan = self.optimizer.generate_optimization_plan(
            max_recommendations=5,
            max_total_effort_hours=20.0,
            prioritize_quick_wins=True,
        )

        logger.info(f"Optimization plan: {json.dumps(plan['summary'], indent=2)}")

    async def demonstrate_cost_optimization(self):
        """Demonstrate cost optimization monitoring."""
        logger.info("=== Cost Optimization Demo ===")

        # Analyze monthly costs (simulated data)
        cost_analysis = await self.cost_monitor.analyze_monthly_costs()

        logger.info("Cost analysis results:")
        logger.info(f"  - Total cost: ${cost_analysis.total_cost:.2f}")
        logger.info(
            f"  - Potential savings: ${cost_analysis.total_potential_savings:.2f}"
        )
        logger.info(
            f"  - Top services: {[s['service'] for s in cost_analysis.top_services[:3]]}"
        )

        # Create budget alerts
        compute_alerts = self.cost_monitor.create_budget_alert(
            service_name="Compute Engine",
            monthly_budget=1000.0,
            threshold_percentages=[50.0, 80.0, 100.0],
        )
        logger.info(f"Created {len(compute_alerts)} budget alerts for Compute Engine")

        # Generate cost optimization plan
        cost_plan = self.cost_monitor.get_cost_optimization_plan(
            max_savings_target=500.0, max_implementation_hours=30.0
        )

        logger.info("Cost optimization plan:")
        logger.info(
            f"  - Total savings: ${cost_plan['summary']['total_monthly_savings']:.2f}/month"
        )
        logger.info(
            f"  - Implementation phases: {len(cost_plan['implementation_phases'])}"
        )

        # Get cost report
        cost_report = self.cost_monitor.generate_cost_report()
        logger.info(f"Cost report: {json.dumps(cost_report['summary'], indent=2)}")

    async def demonstrate_secret_optimization(self):
        """Demonstrate Secret Manager performance optimization."""
        logger.info("=== Secret Manager Optimization Demo ===")

        # Start optimization
        self.secret_manager.start_optimization()

        # Simulate secret access patterns
        secret_names = [
            "database-password",
            "api-key",
            "encryption-key",
            "oauth-secret",
            "service-account-key",
        ]

        # Preload frequently used secrets
        preload_results = self.secret_manager.preload_secrets(secret_names)
        logger.info(f"Preload results: {preload_results}")

        # Simulate multiple secret access
        try:
            # This will use cache for subsequent accesses
            for _ in range(3):
                results = await self.secret_manager.get_secrets(
                    secret_names[:3],  # Access first 3 secrets multiple times
                    use_cache=True,
                )
                logger.info(
                    f"Retrieved {sum(1 for v in results.values() if v is not None)} secrets"
                )

                await asyncio.sleep(0.1)  # Small delay between accesses

        except Exception as e:
            logger.warning(f"Secret access failed (expected in demo): {e}")

        # Get performance analysis
        performance_report = self.secret_manager.get_performance_report()
        logger.info("Secret Manager performance:")
        logger.info(
            f"  - Cache hit rate: {performance_report['performance_summary']['cache_hit_rate']:.1%}"
        )
        logger.info(
            f"  - Average access time: {performance_report['performance_summary']['avg_access_time_ms']:.2f}ms"
        )

        # Get cost optimization recommendations
        cost_recommendations = self.secret_manager.get_cost_recommendations()
        logger.info("Secret Manager cost recommendations:")
        for rec in cost_recommendations:
            logger.info(
                f"  - {rec['title']}: ${rec['estimated_monthly_savings']:.2f}/month"
            )

        # Stop optimization
        self.secret_manager.stop_optimization()

    async def run_complete_demo(self):
        """Run the complete performance monitoring demonstration."""
        logger.info("🚀 Starting Genesis GCP Performance Monitoring Demo")
        logger.info("=" * 60)

        try:
            # Run all demonstrations
            await self.demonstrate_profiling()
            await asyncio.sleep(1)

            await self.demonstrate_benchmarking()
            await asyncio.sleep(1)

            await self.demonstrate_monitoring_and_alerting()
            await asyncio.sleep(1)

            await self.demonstrate_optimization()
            await asyncio.sleep(1)

            await self.demonstrate_cost_optimization()
            await asyncio.sleep(1)

            await self.demonstrate_secret_optimization()

            logger.info("=" * 60)
            logger.info(
                "✅ Genesis GCP Performance Monitoring Demo completed successfully!"
            )

        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            raise


async def main():
    """Main entry point for the performance monitoring demo."""

    # Configuration
    gcp_project_id = "your-gcp-project"  # Replace with your GCP project ID

    # Create and run demo
    demo = PerformanceMonitoringDemo(gcp_project_id)
    await demo.run_complete_demo()


if __name__ == "__main__":
    asyncio.run(main())
