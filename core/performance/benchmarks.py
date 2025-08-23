"""
Performance Benchmarking - CRAFT Create Component
Automated performance benchmarking with GCP Cloud Operations integration

This module implements continuous performance benchmarking for the Genesis platform,
integrating with GCP Cloud Monitoring for comprehensive performance tracking.
"""

import asyncio
import json
import logging
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from google.api_core import exceptions as gcp_exceptions
    from google.cloud import monitoring_v3
    from google.cloud.monitoring_v3 import TimeSeries

    GCP_MONITORING_AVAILABLE = True
except ImportError:
    GCP_MONITORING_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfig:
    """Configuration for performance benchmarking."""

    # Benchmark settings
    benchmark_name: str
    target_function: Optional[Callable] = None
    warmup_iterations: int = 5
    measurement_iterations: int = 50
    max_duration_seconds: int = 300

    # Statistical analysis
    confidence_level: float = 0.95
    outlier_threshold_std: float = 2.0
    min_valid_samples: int = 10

    # Performance targets
    target_avg_ms: Optional[float] = None
    target_p95_ms: Optional[float] = None
    target_p99_ms: Optional[float] = None

    # GCP Integration
    gcp_project_id: Optional[str] = None
    gcp_metric_prefix: str = "genesis.performance"
    enable_cloud_monitoring: bool = True

    # Storage
    results_storage_path: str = ".genesis/benchmarks"
    enable_persistent_storage: bool = True

    # Metadata
    environment: str = "unknown"
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Comprehensive benchmark result."""

    # Identification
    benchmark_name: str
    run_id: str
    timestamp: datetime

    # Performance metrics
    avg_duration_ms: float
    median_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    std_deviation_ms: float

    # Statistical analysis
    sample_count: int
    valid_samples: int
    outliers_removed: int
    confidence_interval: Tuple[float, float]

    # Performance evaluation
    meets_targets: bool
    performance_grade: str  # A, B, C, D, F

    # Comparison with previous runs
    trend_direction: str  # improving, degrading, stable
    change_percent: Optional[float] = None

    # Resource usage
    avg_cpu_percent: float = 0.0
    avg_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0

    # Context
    environment: str = "unknown"
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkResult":
        """Create from dictionary."""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class PerformanceBenchmarks:
    """
    Performance benchmarking system implementing CRAFT Create methodology.

    Provides comprehensive performance benchmarking with:
    - Automated benchmark execution
    - Statistical analysis and outlier detection
    - GCP Cloud Monitoring integration
    - Performance trend analysis
    - Automated alerting for regressions
    """

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.logger = logging.getLogger(f"{__name__}.PerformanceBenchmarks")

        # Default configuration
        self.default_config = BenchmarkConfig(
            benchmark_name="default", gcp_project_id=self._get_gcp_project_id()
        )

        # Storage setup
        self.storage_path = Path(self.default_config.results_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # GCP Monitoring client
        self.monitoring_client = None
        if GCP_MONITORING_AVAILABLE and self.default_config.gcp_project_id:
            try:
                self.monitoring_client = monitoring_v3.MetricServiceClient()
                self.logger.info("GCP Cloud Monitoring client initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize GCP monitoring: {e}")

        # Benchmark registry
        self.registered_benchmarks: Dict[str, BenchmarkConfig] = {}
        self.benchmark_history: Dict[str, List[BenchmarkResult]] = {}

        self.logger.info("PerformanceBenchmarks initialized")

    def register_benchmark(self, config: BenchmarkConfig) -> None:
        """Register a benchmark for automated execution."""
        self.registered_benchmarks[config.benchmark_name] = config
        self.logger.info(f"Registered benchmark: {config.benchmark_name}")

    async def run_benchmark(
        self,
        benchmark_name: str,
        target_function: Optional[Callable] = None,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> BenchmarkResult:
        """Run a single benchmark with comprehensive analysis."""

        # Get benchmark configuration
        if benchmark_name in self.registered_benchmarks:
            config = self.registered_benchmarks[benchmark_name]
        else:
            config = BenchmarkConfig(benchmark_name=benchmark_name)

        # Apply overrides
        if config_override:
            for key, value in config_override.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        # Use provided function or registered function
        function_to_benchmark = target_function or config.target_function
        if not function_to_benchmark:
            raise ValueError(
                f"No target function provided for benchmark: {benchmark_name}"
            )

        self.logger.info(f"Starting benchmark: {benchmark_name}")
        start_time = time.time()

        # Warmup phase
        self.logger.debug(f"Warming up with {config.warmup_iterations} iterations")
        for _ in range(config.warmup_iterations):
            try:
                if asyncio.iscoroutinefunction(function_to_benchmark):
                    await function_to_benchmark()
                else:
                    function_to_benchmark()
            except Exception as e:
                self.logger.warning(f"Warmup iteration failed: {e}")

        # Measurement phase
        self.logger.debug(
            f"Running {config.measurement_iterations} measurement iterations"
        )
        raw_durations = []
        cpu_samples = []
        memory_samples = []

        for iteration in range(config.measurement_iterations):
            # Check timeout
            if time.time() - start_time > config.max_duration_seconds:
                self.logger.warning(
                    f"Benchmark timeout reached after {iteration} iterations"
                )
                break

            # Measure single iteration
            try:
                (
                    duration_ms,
                    cpu_percent,
                    memory_mb,
                ) = await self._measure_single_iteration(function_to_benchmark)
                raw_durations.append(duration_ms)
                cpu_samples.append(cpu_percent)
                memory_samples.append(memory_mb)

            except Exception as e:
                self.logger.warning(f"Measurement iteration {iteration} failed: {e}")

        if len(raw_durations) < config.min_valid_samples:
            raise RuntimeError(
                f"Insufficient valid samples: {len(raw_durations)} < {config.min_valid_samples}"
            )

        # Statistical analysis
        result = self._analyze_benchmark_results(
            config, raw_durations, cpu_samples, memory_samples
        )

        # Store result
        if config.enable_persistent_storage:
            await self._store_benchmark_result(result)

        # Send to GCP Monitoring
        if config.enable_cloud_monitoring and self.monitoring_client:
            await self._send_metrics_to_gcp(result)

        # Update history for trend analysis
        if benchmark_name not in self.benchmark_history:
            self.benchmark_history[benchmark_name] = []
        self.benchmark_history[benchmark_name].append(result)

        # Keep only recent history (last 100 results)
        if len(self.benchmark_history[benchmark_name]) > 100:
            self.benchmark_history[benchmark_name] = self.benchmark_history[
                benchmark_name
            ][-100:]

        self.logger.info(
            f"Benchmark completed: {benchmark_name} - "
            f"{result.avg_duration_ms:.2f}ms avg, grade: {result.performance_grade}"
        )

        return result

    async def run_benchmark_suite(
        self, benchmark_names: Optional[List[str]] = None
    ) -> Dict[str, BenchmarkResult]:
        """Run multiple benchmarks in parallel."""

        if benchmark_names is None:
            benchmark_names = list(self.registered_benchmarks.keys())

        if not benchmark_names:
            self.logger.warning("No benchmarks to run")
            return {}

        self.logger.info(
            f"Running benchmark suite with {len(benchmark_names)} benchmarks"
        )

        # Run benchmarks in parallel (with limited concurrency)
        results = {}
        max_concurrent = min(4, len(benchmark_names))  # Limit concurrent benchmarks

        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_single_benchmark(name: str) -> Tuple[str, BenchmarkResult]:
            async with semaphore:
                result = await self.run_benchmark(name)
                return name, result

        # Execute all benchmarks
        tasks = [run_single_benchmark(name) for name in benchmark_names]

        for completed_task in asyncio.as_completed(tasks):
            try:
                benchmark_name, result = await completed_task
                results[benchmark_name] = result
                self.logger.info(f"Completed benchmark: {benchmark_name}")
            except Exception as e:
                self.logger.error(f"Benchmark failed: {e}")

        # Generate suite summary
        await self._generate_suite_summary(results)

        return results

    def get_benchmark_history(
        self, benchmark_name: str, days: int = 30
    ) -> List[BenchmarkResult]:
        """Get historical benchmark results."""
        if benchmark_name not in self.benchmark_history:
            # Load from storage if available
            self._load_benchmark_history(benchmark_name)

        history = self.benchmark_history.get(benchmark_name, [])

        # Filter by date range
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_history = [
            result for result in history if result.timestamp >= cutoff_date
        ]

        return sorted(filtered_history, key=lambda x: x.timestamp, reverse=True)

    def analyze_performance_trends(
        self, benchmark_name: str, days: int = 30
    ) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        history = self.get_benchmark_history(benchmark_name, days)

        if len(history) < 2:
            return {"trend": "insufficient_data"}

        # Sort by timestamp
        history.sort(key=lambda x: x.timestamp)

        # Calculate trend metrics
        recent_results = history[-10:]  # Last 10 results
        older_results = (
            history[:-10] if len(history) > 10 else history[: len(history) // 2]
        )

        recent_avg = statistics.mean([r.avg_duration_ms for r in recent_results])
        older_avg = statistics.mean([r.avg_duration_ms for r in older_results])

        trend_change_percent = ((recent_avg - older_avg) / older_avg) * 100

        # Determine trend direction
        if abs(trend_change_percent) < 5:
            trend = "stable"
        elif trend_change_percent > 0:
            trend = "degrading"
        else:
            trend = "improving"

        return {
            "trend": trend,
            "change_percent": trend_change_percent,
            "recent_avg_ms": recent_avg,
            "historical_avg_ms": older_avg,
            "sample_count": len(history),
            "analysis_period_days": days,
            "performance_grades": [r.performance_grade for r in recent_results],
            "meets_targets_rate": sum(1 for r in recent_results if r.meets_targets)
            / len(recent_results),
        }

    async def _measure_single_iteration(
        self, function: Callable
    ) -> Tuple[float, float, float]:
        """Measure a single function execution."""
        import psutil

        process = psutil.Process()

        # Capture initial state
        initial_memory = process.memory_info().rss
        initial_time = time.perf_counter()

        # Execute function
        if asyncio.iscoroutinefunction(function):
            await function()
        else:
            function()

        # Capture final state
        end_time = time.perf_counter()
        final_memory = process.memory_info().rss
        cpu_percent = process.cpu_percent()

        # Calculate metrics
        duration_ms = (end_time - initial_time) * 1000
        memory_mb = max(initial_memory, final_memory) / (1024 * 1024)

        return duration_ms, cpu_percent, memory_mb

    def _analyze_benchmark_results(
        self,
        config: BenchmarkConfig,
        raw_durations: List[float],
        cpu_samples: List[float],
        memory_samples: List[float],
    ) -> BenchmarkResult:
        """Perform comprehensive statistical analysis of benchmark results."""

        # Remove outliers
        durations = self._remove_outliers(raw_durations, config.outlier_threshold_std)
        outliers_removed = len(raw_durations) - len(durations)

        # Calculate statistics
        avg_duration = statistics.mean(durations)
        median_duration = statistics.median(durations)
        std_dev = statistics.stdev(durations) if len(durations) > 1 else 0.0

        # Calculate percentiles
        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        p95 = sorted_durations[int(0.95 * n)] if n >= 20 else sorted_durations[-1]
        p99 = sorted_durations[int(0.99 * n)] if n >= 100 else sorted_durations[-1]

        # Calculate confidence interval
        margin_error = 1.96 * std_dev / (n**0.5)  # 95% confidence
        confidence_interval = (avg_duration - margin_error, avg_duration + margin_error)

        # Resource usage
        avg_cpu = statistics.mean(cpu_samples) if cpu_samples else 0.0
        avg_memory = statistics.mean(memory_samples) if memory_samples else 0.0
        peak_memory = max(memory_samples) if memory_samples else 0.0

        # Performance evaluation
        meets_targets = self._evaluate_performance_targets(
            config, avg_duration, p95, p99
        )
        performance_grade = self._calculate_performance_grade(
            config, avg_duration, p95, p99
        )

        # Trend analysis (if previous results exist)
        trend_direction = "unknown"
        change_percent = None

        if config.benchmark_name in self.benchmark_history:
            previous_results = self.benchmark_history[config.benchmark_name]
            if previous_results:
                previous_avg = previous_results[-1].avg_duration_ms
                change_percent = ((avg_duration - previous_avg) / previous_avg) * 100

                if abs(change_percent) < 5:
                    trend_direction = "stable"
                elif change_percent > 0:
                    trend_direction = "degrading"
                else:
                    trend_direction = "improving"

        # Create result
        run_id = f"{config.benchmark_name}_{int(time.time())}"
        result = BenchmarkResult(
            benchmark_name=config.benchmark_name,
            run_id=run_id,
            timestamp=datetime.now(),
            avg_duration_ms=avg_duration,
            median_duration_ms=median_duration,
            p95_duration_ms=p95,
            p99_duration_ms=p99,
            min_duration_ms=min(durations),
            max_duration_ms=max(durations),
            std_deviation_ms=std_dev,
            sample_count=len(raw_durations),
            valid_samples=len(durations),
            outliers_removed=outliers_removed,
            confidence_interval=confidence_interval,
            meets_targets=meets_targets,
            performance_grade=performance_grade,
            trend_direction=trend_direction,
            change_percent=change_percent,
            avg_cpu_percent=avg_cpu,
            avg_memory_mb=avg_memory,
            peak_memory_mb=peak_memory,
            environment=config.environment,
            version=config.version,
            metadata=config.metadata,
        )

        return result

    def _remove_outliers(self, data: List[float], threshold_std: float) -> List[float]:
        """Remove statistical outliers from data."""
        if len(data) < 3:
            return data

        mean = statistics.mean(data)
        std_dev = statistics.stdev(data)

        filtered_data = [x for x in data if abs(x - mean) <= threshold_std * std_dev]

        # Ensure we keep at least 50% of the data
        if len(filtered_data) < len(data) * 0.5:
            return data

        return filtered_data

    def _evaluate_performance_targets(
        self, config: BenchmarkConfig, avg_ms: float, p95_ms: float, p99_ms: float
    ) -> bool:
        """Evaluate if performance meets configured targets."""
        targets_met = []

        if config.target_avg_ms:
            targets_met.append(avg_ms <= config.target_avg_ms)

        if config.target_p95_ms:
            targets_met.append(p95_ms <= config.target_p95_ms)

        if config.target_p99_ms:
            targets_met.append(p99_ms <= config.target_p99_ms)

        return all(targets_met) if targets_met else True

    def _calculate_performance_grade(
        self, config: BenchmarkConfig, avg_ms: float, p95_ms: float, p99_ms: float
    ) -> str:
        """Calculate performance grade based on targets."""

        if not any([config.target_avg_ms, config.target_p95_ms, config.target_p99_ms]):
            return "N/A"

        scores = []

        # Average duration score
        if config.target_avg_ms:
            ratio = avg_ms / config.target_avg_ms
            if ratio <= 1.0:
                scores.append(100)  # A
            elif ratio <= 1.2:
                scores.append(80)  # B
            elif ratio <= 1.5:
                scores.append(60)  # C
            elif ratio <= 2.0:
                scores.append(40)  # D
            else:
                scores.append(20)  # F

        # P95 duration score
        if config.target_p95_ms:
            ratio = p95_ms / config.target_p95_ms
            if ratio <= 1.0:
                scores.append(100)
            elif ratio <= 1.2:
                scores.append(80)
            elif ratio <= 1.5:
                scores.append(60)
            elif ratio <= 2.0:
                scores.append(40)
            else:
                scores.append(20)

        # P99 duration score
        if config.target_p99_ms:
            ratio = p99_ms / config.target_p99_ms
            if ratio <= 1.0:
                scores.append(100)
            elif ratio <= 1.2:
                scores.append(80)
            elif ratio <= 1.5:
                scores.append(60)
            elif ratio <= 2.0:
                scores.append(40)
            else:
                scores.append(20)

        # Calculate overall grade
        if not scores:
            return "N/A"

        avg_score = sum(scores) / len(scores)

        if avg_score >= 90:
            return "A"
        elif avg_score >= 80:
            return "B"
        elif avg_score >= 70:
            return "C"
        elif avg_score >= 60:
            return "D"
        else:
            return "F"

    async def _store_benchmark_result(self, result: BenchmarkResult) -> None:
        """Store benchmark result to persistent storage."""
        try:
            filename = f"{result.benchmark_name}_{result.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.storage_path / filename

            with open(filepath, "w") as f:
                json.dump(result.to_dict(), f, indent=2)

            self.logger.debug(f"Stored benchmark result: {filepath}")

        except Exception as e:
            self.logger.error(f"Failed to store benchmark result: {e}")

    async def _send_metrics_to_gcp(self, result: BenchmarkResult) -> None:
        """Send benchmark metrics to GCP Cloud Monitoring."""
        if not self.monitoring_client or not self.default_config.gcp_project_id:
            return

        try:
            project_name = f"projects/{self.default_config.gcp_project_id}"

            # Create time series for different metrics
            series = []

            # Average duration
            series.append(
                self._create_time_series(
                    f"{self.default_config.gcp_metric_prefix}/benchmark/avg_duration_ms",
                    result.avg_duration_ms,
                    {
                        "benchmark_name": result.benchmark_name,
                        "environment": result.environment,
                        "version": result.version,
                        "grade": result.performance_grade,
                    },
                )
            )

            # P95 duration
            series.append(
                self._create_time_series(
                    f"{self.default_config.gcp_metric_prefix}/benchmark/p95_duration_ms",
                    result.p95_duration_ms,
                    {
                        "benchmark_name": result.benchmark_name,
                        "environment": result.environment,
                        "version": result.version,
                    },
                )
            )

            # Performance targets met (0/1)
            series.append(
                self._create_time_series(
                    f"{self.default_config.gcp_metric_prefix}/benchmark/targets_met",
                    1 if result.meets_targets else 0,
                    {
                        "benchmark_name": result.benchmark_name,
                        "environment": result.environment,
                        "version": result.version,
                    },
                )
            )

            # Send to GCP
            self.monitoring_client.create_time_series(
                name=project_name, time_series=series
            )

            self.logger.debug(f"Sent {len(series)} metrics to GCP Monitoring")

        except Exception as e:
            self.logger.error(f"Failed to send metrics to GCP: {e}")

    def _create_time_series(
        self, metric_type: str, value: float, labels: Dict[str, str]
    ) -> TimeSeries:
        """Create a GCP Monitoring TimeSeries object."""
        series = TimeSeries()
        series.metric.type = f"custom.googleapis.com/{metric_type}"

        # Add labels
        for key, val in labels.items():
            series.metric.labels[key] = str(val)

        # Add resource labels
        series.resource.type = "generic_node"
        series.resource.labels["location"] = "global"
        series.resource.labels["namespace"] = self.default_config.gcp_metric_prefix
        series.resource.labels["node_id"] = "benchmark-runner"

        # Add data point
        point = series.points.add()
        point.value.double_value = value

        # Set timestamp to now
        now = time.time()
        point.interval.end_time.seconds = int(now)
        point.interval.end_time.nanos = int((now - int(now)) * 10**9)

        return series

    def _load_benchmark_history(self, benchmark_name: str) -> None:
        """Load benchmark history from storage."""
        try:
            history = []
            pattern = f"{benchmark_name}_*.json"

            for filepath in self.storage_path.glob(pattern):
                with open(filepath, "r") as f:
                    data = json.load(f)
                    result = BenchmarkResult.from_dict(data)
                    history.append(result)

            # Sort by timestamp and keep recent results
            history.sort(key=lambda x: x.timestamp, reverse=True)
            self.benchmark_history[benchmark_name] = history[:100]  # Keep last 100

            self.logger.debug(
                f"Loaded {len(history)} historical results for {benchmark_name}"
            )

        except Exception as e:
            self.logger.warning(f"Failed to load benchmark history: {e}")

    async def _generate_suite_summary(
        self, results: Dict[str, BenchmarkResult]
    ) -> None:
        """Generate summary report for benchmark suite."""
        if not results:
            return

        summary = {
            "suite_timestamp": datetime.now().isoformat(),
            "total_benchmarks": len(results),
            "successful_benchmarks": sum(
                1 for r in results.values() if r.meets_targets
            ),
            "average_grade": self._calculate_average_grade(results),
            "performance_summary": {
                name: {
                    "avg_ms": result.avg_duration_ms,
                    "grade": result.performance_grade,
                    "meets_targets": result.meets_targets,
                    "trend": result.trend_direction,
                }
                for name, result in results.items()
            },
        }

        # Store suite summary
        summary_path = self.storage_path / f"suite_summary_{int(time.time())}.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        self.logger.info(
            f"Benchmark suite completed: {summary['successful_benchmarks']}/{summary['total_benchmarks']} passed"
        )

    def _calculate_average_grade(self, results: Dict[str, BenchmarkResult]) -> str:
        """Calculate average grade across all benchmarks."""
        grade_values = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0, "N/A": 0}
        grade_names = ["F", "D", "C", "B", "A"]

        if not results:
            return "N/A"

        total_points = sum(
            grade_values.get(r.performance_grade, 0) for r in results.values()
        )
        avg_points = total_points / len(results)

        return grade_names[min(int(avg_points), 4)]

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


class BenchmarkRunner:
    """
    Automated benchmark runner for continuous performance monitoring.

    Provides scheduled benchmark execution and integration with CI/CD pipelines.
    """

    def __init__(self, benchmarks: PerformanceBenchmarks):
        self.benchmarks = benchmarks
        self.logger = logging.getLogger(f"{__name__}.BenchmarkRunner")
        self._running = False

    async def run_continuous_benchmarks(
        self, interval_minutes: int = 60, benchmark_names: Optional[List[str]] = None
    ) -> None:
        """Run benchmarks continuously at specified intervals."""
        self.logger.info(
            f"Starting continuous benchmarks every {interval_minutes} minutes"
        )
        self._running = True

        while self._running:
            try:
                await self.benchmarks.run_benchmark_suite(benchmark_names)

                # Wait for next run
                await asyncio.sleep(interval_minutes * 60)

            except Exception as e:
                self.logger.error(f"Error in continuous benchmarking: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry

    def stop_continuous_benchmarks(self) -> None:
        """Stop continuous benchmark execution."""
        self._running = False
        self.logger.info("Stopped continuous benchmarks")

    async def run_performance_regression_check(
        self, benchmark_names: Optional[List[str]] = None
    ) -> bool:
        """Run benchmarks and check for performance regressions."""
        results = await self.benchmarks.run_benchmark_suite(benchmark_names)

        # Check for regressions
        regressions_found = False
        for name, result in results.items():
            if not result.meets_targets or result.performance_grade in ["D", "F"]:
                self.logger.warning(
                    f"Performance regression detected in {name}: grade {result.performance_grade}"
                )
                regressions_found = True

            if (
                result.trend_direction == "degrading"
                and result.change_percent
                and result.change_percent > 20
            ):
                self.logger.warning(
                    f"Performance degradation in {name}: {result.change_percent:.1f}% slower"
                )
                regressions_found = True

        return not regressions_found  # Return True if no regressions found
