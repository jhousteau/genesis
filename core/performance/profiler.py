"""
Performance Profiler - CRAFT Create Component
Automated performance profiling with comprehensive metrics collection

This module implements automated performance profiling for the Genesis platform,
capturing detailed performance metrics across all system components.
"""

import asyncio
import cProfile
import io
import logging
import pstats
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class ProfilerConfig:
    """Configuration for performance profiling."""

    # Profiling settings
    enable_cpu_profiling: bool = True
    enable_memory_profiling: bool = True
    enable_io_profiling: bool = True
    enable_network_profiling: bool = True

    # Sampling settings
    sampling_interval: float = 0.1  # seconds
    profile_duration: int = 60  # seconds
    max_profile_history: int = 100

    # Thresholds for performance alerts
    cpu_threshold_percent: float = 80.0
    memory_threshold_percent: float = 85.0
    response_time_threshold_ms: float = 500.0

    # Storage settings
    profile_storage_path: str = ".genesis/profiles"
    enable_persistent_storage: bool = True
    retention_days: int = 30


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    # Timing metrics
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0

    # Resource metrics
    cpu_percent: float = 0.0
    memory_usage_mb: float = 0.0
    memory_percent: float = 0.0

    # IO metrics
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0

    # Function-level metrics
    function_calls: int = 0
    function_name: str = ""

    # Additional context
    thread_id: str = ""
    process_id: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def finalize(self) -> None:
        """Finalize metrics calculation."""
        if self.end_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000


@dataclass
class ProfileReport:
    """Comprehensive performance profile report."""

    profile_id: str
    start_time: datetime
    end_time: datetime
    total_duration_ms: float

    # Aggregated metrics
    avg_cpu_percent: float
    max_cpu_percent: float
    avg_memory_mb: float
    max_memory_mb: float

    # Function-level performance
    top_functions: List[Dict[str, Any]]
    slow_functions: List[Dict[str, Any]]

    # Resource utilization
    resource_usage: Dict[str, float]

    # Performance issues detected
    performance_issues: List[str]

    # Recommendations
    optimization_recommendations: List[str]


class PerformanceProfiler:
    """
    Automated performance profiler implementing CRAFT Create methodology.

    Provides comprehensive performance monitoring with:
    - Continuous resource monitoring
    - Function-level profiling
    - Automated issue detection
    - Performance optimization recommendations
    """

    def __init__(self, config: Optional[ProfilerConfig] = None):
        self.config = config or ProfilerConfig()
        self.logger = logging.getLogger(f"{__name__}.PerformanceProfiler")

        # Profiling state
        self._profiling_active = False
        self._profiler: Optional[cProfile.Profile] = None
        self._monitoring_thread: Optional[threading.Thread] = None

        # Metrics storage
        self._metrics_history: deque = deque(maxlen=self.config.max_profile_history)
        self._current_metrics: Dict[str, PerformanceMetrics] = {}

        # Resource monitoring
        self._resource_monitor = ResourceMonitor(self.config.sampling_interval)

        # Performance baselines
        self._baselines: Dict[str, float] = {}

        # Thread safety
        self._lock = threading.RLock()

        self.logger.info("PerformanceProfiler initialized")

    def start_profiling(self, profile_id: Optional[str] = None) -> str:
        """Start performance profiling session."""
        with self._lock:
            if self._profiling_active:
                raise RuntimeError("Profiling already active")

            profile_id = profile_id or f"profile_{int(time.time())}"

            # Initialize profiler
            self._profiler = cProfile.Profile()
            self._profiler.enable()

            # Start resource monitoring
            self._resource_monitor.start()

            # Start monitoring thread
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_worker, args=(profile_id,), daemon=True
            )
            self._monitoring_thread.start()

            self._profiling_active = True

            self.logger.info(f"Started profiling session: {profile_id}")
            return profile_id

    def stop_profiling(self, profile_id: str) -> ProfileReport:
        """Stop profiling session and generate report."""
        with self._lock:
            if not self._profiling_active:
                raise RuntimeError("No active profiling session")

            # Stop profiler
            if self._profiler:
                self._profiler.disable()

            # Stop resource monitoring
            self._resource_monitor.stop()

            self._profiling_active = False

            # Generate report
            report = self._generate_profile_report(profile_id)

            # Store in history
            self._metrics_history.append(report)

            self.logger.info(f"Stopped profiling session: {profile_id}")
            return report

    @contextmanager
    def profile_context(self, operation_name: str):
        """Context manager for profiling specific operations."""
        metrics = PerformanceMetrics(
            start_time=datetime.now(),
            function_name=operation_name,
            thread_id=str(threading.get_ident()),
            process_id=psutil.Process().pid,
        )

        # Capture initial resource state
        process = psutil.Process()
        initial_cpu_times = process.cpu_times()
        initial_memory = process.memory_info()
        initial_io = process.io_counters() if hasattr(process, "io_counters") else None

        try:
            yield metrics
        finally:
            # Capture final state
            metrics.end_time = datetime.now()

            # Calculate resource usage
            final_cpu_times = process.cpu_times()
            final_memory = process.memory_info()
            final_io = (
                process.io_counters() if hasattr(process, "io_counters") else None
            )

            metrics.cpu_percent = process.cpu_percent()
            metrics.memory_usage_mb = final_memory.rss / (1024 * 1024)
            metrics.memory_percent = process.memory_percent()

            if initial_io and final_io:
                metrics.disk_read_mb = (final_io.read_bytes - initial_io.read_bytes) / (
                    1024 * 1024
                )
                metrics.disk_write_mb = (
                    final_io.write_bytes - initial_io.write_bytes
                ) / (1024 * 1024)

            metrics.finalize()

            # Store metrics
            with self._lock:
                self._current_metrics[operation_name] = metrics

            # Check for performance issues
            self._check_performance_thresholds(metrics)

    def profile_function(self, func: Callable) -> Callable:
        """Decorator for profiling individual functions."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.profile_context(func.__name__):
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with self.profile_context(func.__name__):
                return await func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper

    def get_performance_metrics(
        self, operation_name: Optional[str] = None
    ) -> Dict[str, PerformanceMetrics]:
        """Get current performance metrics."""
        with self._lock:
            if operation_name:
                return {operation_name: self._current_metrics.get(operation_name)}
            return dict(self._current_metrics)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        with self._lock:
            if not self._current_metrics:
                return {}

            metrics_list = list(self._current_metrics.values())

            return {
                "total_operations": len(metrics_list),
                "avg_duration_ms": sum(m.duration_ms for m in metrics_list)
                / len(metrics_list),
                "max_duration_ms": max(m.duration_ms for m in metrics_list),
                "avg_cpu_percent": sum(m.cpu_percent for m in metrics_list)
                / len(metrics_list),
                "max_cpu_percent": max(m.cpu_percent for m in metrics_list),
                "avg_memory_mb": sum(m.memory_usage_mb for m in metrics_list)
                / len(metrics_list),
                "max_memory_mb": max(m.memory_usage_mb for m in metrics_list),
                "performance_issues": self._detect_performance_issues(metrics_list),
            }

    def _monitoring_worker(self, profile_id: str) -> None:
        """Background worker for continuous monitoring."""
        start_time = time.time()

        while (
            self._profiling_active
            and (time.time() - start_time) < self.config.profile_duration
        ):
            try:
                # Sample system metrics
                self._sample_system_metrics()

                # Check for performance issues
                self._check_system_thresholds()

                time.sleep(self.config.sampling_interval)

            except Exception as e:
                self.logger.error(f"Error in monitoring worker: {e}")

    def _sample_system_metrics(self) -> None:
        """Sample current system performance metrics."""
        try:
            process = psutil.Process()

            # CPU and memory
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            # Store in resource monitor
            self._resource_monitor.add_sample(
                {
                    "timestamp": datetime.now(),
                    "cpu_percent": cpu_percent,
                    "memory_mb": memory_info.rss / (1024 * 1024),
                    "memory_percent": memory_percent,
                }
            )

        except Exception as e:
            self.logger.warning(f"Failed to sample system metrics: {e}")

    def _check_performance_thresholds(self, metrics: PerformanceMetrics) -> None:
        """Check if metrics exceed performance thresholds."""
        issues = []

        if metrics.duration_ms > self.config.response_time_threshold_ms:
            issues.append(
                f"Slow operation: {metrics.function_name} took {metrics.duration_ms:.1f}ms"
            )

        if metrics.cpu_percent > self.config.cpu_threshold_percent:
            issues.append(
                f"High CPU usage: {metrics.cpu_percent:.1f}% in {metrics.function_name}"
            )

        if metrics.memory_percent > self.config.memory_threshold_percent:
            issues.append(
                f"High memory usage: {metrics.memory_percent:.1f}% in {metrics.function_name}"
            )

        for issue in issues:
            self.logger.warning(f"PERFORMANCE_ISSUE: {issue}")

    def _check_system_thresholds(self) -> None:
        """Check system-wide performance thresholds."""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()

            if cpu_percent > self.config.cpu_threshold_percent:
                self.logger.warning(
                    f"SYSTEM_PERFORMANCE: High CPU usage: {cpu_percent:.1f}%"
                )

            if memory.percent > self.config.memory_threshold_percent:
                self.logger.warning(
                    f"SYSTEM_PERFORMANCE: High memory usage: {memory.percent:.1f}%"
                )

        except Exception as e:
            self.logger.warning(f"Failed to check system thresholds: {e}")

    def _generate_profile_report(self, profile_id: str) -> ProfileReport:
        """Generate comprehensive profile report."""
        end_time = datetime.now()
        start_time = end_time - timedelta(seconds=self.config.profile_duration)

        # Analyze profiler data
        stats_io = io.StringIO()
        if self._profiler:
            stats = pstats.Stats(self._profiler, stream=stats_io)
            stats.sort_stats("cumulative")

        # Get resource usage summary
        resource_summary = self._resource_monitor.get_summary()

        # Identify top functions and performance issues
        top_functions = self._analyze_top_functions()
        slow_functions = self._analyze_slow_functions()
        performance_issues = self._detect_current_issues()

        report = ProfileReport(
            profile_id=profile_id,
            start_time=start_time,
            end_time=end_time,
            total_duration_ms=(end_time - start_time).total_seconds() * 1000,
            avg_cpu_percent=resource_summary.get("avg_cpu_percent", 0.0),
            max_cpu_percent=resource_summary.get("max_cpu_percent", 0.0),
            avg_memory_mb=resource_summary.get("avg_memory_mb", 0.0),
            max_memory_mb=resource_summary.get("max_memory_mb", 0.0),
            top_functions=top_functions,
            slow_functions=slow_functions,
            resource_usage=resource_summary,
            performance_issues=performance_issues,
            optimization_recommendations=self._generate_recommendations(
                performance_issues
            ),
        )

        return report

    def _analyze_top_functions(self) -> List[Dict[str, Any]]:
        """Analyze top functions by various metrics."""
        with self._lock:
            metrics_list = list(self._current_metrics.values())

        # Sort by duration
        top_by_duration = sorted(
            metrics_list, key=lambda m: m.duration_ms, reverse=True
        )[:10]

        return [
            {
                "function_name": m.function_name,
                "duration_ms": m.duration_ms,
                "cpu_percent": m.cpu_percent,
                "memory_mb": m.memory_usage_mb,
                "calls": m.function_calls,
            }
            for m in top_by_duration
        ]

    def _analyze_slow_functions(self) -> List[Dict[str, Any]]:
        """Identify slow functions that exceed thresholds."""
        with self._lock:
            metrics_list = list(self._current_metrics.values())

        slow_functions = [
            m
            for m in metrics_list
            if m.duration_ms > self.config.response_time_threshold_ms
        ]

        return [
            {
                "function_name": m.function_name,
                "duration_ms": m.duration_ms,
                "threshold_ms": self.config.response_time_threshold_ms,
                "slowness_ratio": m.duration_ms
                / self.config.response_time_threshold_ms,
            }
            for m in slow_functions
        ]

    def _detect_performance_issues(
        self, metrics_list: List[PerformanceMetrics]
    ) -> List[str]:
        """Detect performance issues from metrics."""
        issues = []

        # Check for consistently slow operations
        slow_ops = [
            m
            for m in metrics_list
            if m.duration_ms > self.config.response_time_threshold_ms
        ]
        if slow_ops:
            issues.append(
                f"{len(slow_ops)} operations exceeded response time threshold"
            )

        # Check for high resource usage
        high_cpu_ops = [
            m for m in metrics_list if m.cpu_percent > self.config.cpu_threshold_percent
        ]
        if high_cpu_ops:
            issues.append(f"{len(high_cpu_ops)} operations had high CPU usage")

        high_memory_ops = [
            m
            for m in metrics_list
            if m.memory_percent > self.config.memory_threshold_percent
        ]
        if high_memory_ops:
            issues.append(f"{len(high_memory_ops)} operations had high memory usage")

        return issues

    def _detect_current_issues(self) -> List[str]:
        """Detect current performance issues."""
        with self._lock:
            metrics_list = list(self._current_metrics.values())

        return self._detect_performance_issues(metrics_list)

    def _generate_recommendations(self, performance_issues: List[str]) -> List[str]:
        """Generate optimization recommendations based on detected issues."""
        recommendations = []

        for issue in performance_issues:
            if "response time" in issue.lower():
                recommendations.extend(
                    [
                        "Consider implementing caching for frequently accessed data",
                        "Review database query performance and add indexes where needed",
                        "Optimize algorithm complexity in slow functions",
                    ]
                )

            if "cpu usage" in issue.lower():
                recommendations.extend(
                    [
                        "Profile CPU-intensive operations and optimize algorithms",
                        "Consider implementing async processing for CPU-bound tasks",
                        "Review loop efficiency and data structure usage",
                    ]
                )

            if "memory usage" in issue.lower():
                recommendations.extend(
                    [
                        "Review memory allocation patterns and implement object pooling",
                        "Check for memory leaks in long-running operations",
                        "Optimize data structures and reduce memory footprint",
                    ]
                )

        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)

        return unique_recommendations


class ResourceMonitor:
    """Monitors system resource usage over time."""

    def __init__(self, sampling_interval: float = 0.1):
        self.sampling_interval = sampling_interval
        self._samples: deque = deque(maxlen=1000)
        self._monitoring = False

    def start(self) -> None:
        """Start resource monitoring."""
        self._monitoring = True

    def stop(self) -> None:
        """Stop resource monitoring."""
        self._monitoring = False

    def add_sample(self, sample: Dict[str, Any]) -> None:
        """Add a resource usage sample."""
        if self._monitoring:
            self._samples.append(sample)

    def get_summary(self) -> Dict[str, float]:
        """Get summary statistics of resource usage."""
        if not self._samples:
            return {}

        samples = list(self._samples)

        cpu_values = [s.get("cpu_percent", 0) for s in samples]
        memory_values = [s.get("memory_mb", 0) for s in samples]
        memory_percent_values = [s.get("memory_percent", 0) for s in samples]

        return {
            "avg_cpu_percent": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            "max_cpu_percent": max(cpu_values) if cpu_values else 0,
            "avg_memory_mb": (
                sum(memory_values) / len(memory_values) if memory_values else 0
            ),
            "max_memory_mb": max(memory_values) if memory_values else 0,
            "avg_memory_percent": (
                sum(memory_percent_values) / len(memory_percent_values)
                if memory_percent_values
                else 0
            ),
            "max_memory_percent": (
                max(memory_percent_values) if memory_percent_values else 0
            ),
            "sample_count": len(samples),
        }
