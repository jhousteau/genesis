"""
Performance Service
Performance monitoring and optimization service following CRAFT methodology.
"""

import time
import asyncio
import threading
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data."""

    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class OperationTimer:
    """Operation timing context."""

    operation_name: str
    start_time: float
    tags: Dict[str, str] = field(default_factory=dict)


class PerformanceService:
    """
    Performance monitoring and optimization service implementing CRAFT principles.

    Create: Robust performance monitoring framework
    Refactor: Optimized for low overhead
    Authenticate: Secure metric collection
    Function: Reliable performance tracking
    Test: Comprehensive performance validation
    """

    def __init__(self, config_service):
        self.config_service = config_service
        self.perf_config = config_service.get_performance_config()

        # Performance targets
        self.target_response_time = self.perf_config.get("target_response_time", 2.0)
        self.response_timeout = self.perf_config.get("response_timeout", 120)

        # Metrics storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.operation_counts: Dict[str, int] = defaultdict(int)
        self.operation_times: Dict[str, List[float]] = defaultdict(list)

        # Performance state
        self._metrics_lock = threading.RLock()
        self._monitoring_enabled = self.perf_config.get("monitoring", {}).get(
            "enabled", True
        )
        self._sample_rate = self.perf_config.get("monitoring", {}).get(
            "sample_rate", 1.0
        )

        # Background monitoring
        self._start_background_monitoring()

    def start_timer(
        self, operation_name: str, tags: Optional[Dict[str, str]] = None
    ) -> OperationTimer:
        """Start timing an operation."""
        return OperationTimer(
            operation_name=operation_name,
            start_time=time.perf_counter(),
            tags=tags or {},
        )

    def end_timer(self, timer: OperationTimer) -> float:
        """End timing and record the operation."""
        elapsed_time = time.perf_counter() - timer.start_time

        if self._monitoring_enabled and self._should_sample():
            self.record_metric(
                name=f"{timer.operation_name}_duration",
                value=elapsed_time,
                unit="seconds",
                tags=timer.tags,
            )

            # Track operation statistics
            with self._metrics_lock:
                self.operation_counts[timer.operation_name] += 1
                self.operation_times[timer.operation_name].append(elapsed_time)

                # Keep only recent times (last 100 operations)
                if len(self.operation_times[timer.operation_name]) > 100:
                    self.operation_times[timer.operation_name] = self.operation_times[
                        timer.operation_name
                    ][-100:]

        return elapsed_time

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "count",
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a performance metric."""
        if not self._monitoring_enabled or not self._should_sample():
            return

        metric = PerformanceMetric(
            name=name, value=value, unit=unit, timestamp=datetime.now(), tags=tags or {}
        )

        with self._metrics_lock:
            self.metrics[name].append(metric)

    def time_operation(
        self, operation_name: str, tags: Optional[Dict[str, str]] = None
    ):
        """Decorator/context manager for timing operations."""

        class TimingContext:
            def __init__(self, perf_service: PerformanceService):
                self.perf_service = perf_service
                self.timer = None

            def __enter__(self):
                self.timer = self.perf_service.start_timer(operation_name, tags)
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.timer:
                    elapsed = self.perf_service.end_timer(self.timer)

                    # Log slow operations
                    if elapsed > self.perf_service.target_response_time:
                        logger.warning(
                            f"Slow operation: {operation_name} took {elapsed:.2f}s "
                            f"(target: {self.perf_service.target_response_time}s)"
                        )

        return TimingContext(self)

    def get_operation_stats(
        self, operation_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics for operations."""
        with self._metrics_lock:
            if operation_name:
                if operation_name not in self.operation_times:
                    return {"error": f"No data for operation: {operation_name}"}

                times = self.operation_times[operation_name]
                return self._calculate_stats(operation_name, times)
            else:
                # Return stats for all operations
                stats = {}
                for op_name, times in self.operation_times.items():
                    stats[op_name] = self._calculate_stats(op_name, times)
                return stats

    def _calculate_stats(
        self, operation_name: str, times: List[float]
    ) -> Dict[str, Any]:
        """Calculate statistics for operation times."""
        if not times:
            return {
                "operation": operation_name,
                "count": 0,
                "avg_duration": 0,
                "min_duration": 0,
                "max_duration": 0,
                "p95_duration": 0,
                "p99_duration": 0,
            }

        sorted_times = sorted(times)
        count = len(times)

        # Calculate percentiles
        p95_idx = int(count * 0.95)
        p99_idx = int(count * 0.99)

        return {
            "operation": operation_name,
            "count": self.operation_counts[operation_name],
            "recent_samples": count,
            "avg_duration": sum(times) / count,
            "min_duration": min(times),
            "max_duration": max(times),
            "p95_duration": (
                sorted_times[p95_idx] if p95_idx < count else sorted_times[-1]
            ),
            "p99_duration": (
                sorted_times[p99_idx] if p99_idx < count else sorted_times[-1]
            ),
            "target_compliance": sum(1 for t in times if t <= self.target_response_time)
            / count,
            "slow_operations": sum(1 for t in times if t > self.target_response_time),
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        with self._metrics_lock:
            total_operations = sum(self.operation_counts.values())

            if total_operations == 0:
                return {
                    "total_operations": 0,
                    "avg_response_time": 0,
                    "target_compliance": 1.0,
                    "slow_operations": 0,
                    "operations": {},
                }

            # Calculate overall metrics
            all_times = []
            for times in self.operation_times.values():
                all_times.extend(times)

            avg_response_time = sum(all_times) / len(all_times) if all_times else 0
            slow_operations = sum(1 for t in all_times if t > self.target_response_time)
            target_compliance = (
                (len(all_times) - slow_operations) / len(all_times)
                if all_times
                else 1.0
            )

            return {
                "total_operations": total_operations,
                "recent_samples": len(all_times),
                "avg_response_time": avg_response_time,
                "target_response_time": self.target_response_time,
                "target_compliance": target_compliance,
                "slow_operations": slow_operations,
                "operations": self.get_operation_stats(),
            }

    def check_performance_health(self) -> Dict[str, Any]:
        """Check if performance is meeting targets."""
        summary = self.get_performance_summary()

        health_status = "healthy"
        issues = []

        # Check overall compliance
        if summary["target_compliance"] < 0.95:  # 95% should meet target
            health_status = "degraded"
            issues.append(
                f"Only {summary['target_compliance']:.1%} of operations meet target response time"
            )

        # Check average response time
        if summary["avg_response_time"] > self.target_response_time * 1.5:
            health_status = "unhealthy"
            issues.append(
                f"Average response time {summary['avg_response_time']:.2f}s exceeds target by 50%"
            )

        # Check individual operations
        slow_operations = []
        for op_name, stats in summary["operations"].items():
            if stats["target_compliance"] < 0.90:
                slow_operations.append(op_name)

        if slow_operations:
            if health_status == "healthy":
                health_status = "degraded"
            issues.append(f"Slow operations detected: {', '.join(slow_operations)}")

        return {
            "status": health_status,
            "issues": issues,
            "summary": summary,
            "recommendations": self._get_performance_recommendations(summary),
        }

    def _get_performance_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Get performance improvement recommendations."""
        recommendations = []

        if summary["avg_response_time"] > self.target_response_time:
            recommendations.append(
                "Consider enabling caching for frequently accessed data"
            )
            recommendations.append("Review slow operations and optimize bottlenecks")

        if summary["slow_operations"] > summary["recent_samples"] * 0.1:
            recommendations.append("Investigate network connectivity issues")
            recommendations.append(
                "Consider increasing timeout values for long-running operations"
            )

        # Check specific operations
        for op_name, stats in summary["operations"].items():
            if stats["slow_operations"] > stats["recent_samples"] * 0.2:
                recommendations.append(
                    f"Optimize {op_name} operation - {stats['slow_operations']} slow executions"
                )

        return recommendations

    def export_metrics(
        self, operation_name: Optional[str] = None, since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Export metrics for analysis."""
        since = since or datetime.now() - timedelta(hours=1)

        with self._metrics_lock:
            if operation_name:
                metrics_to_export = {
                    operation_name: self.metrics.get(operation_name, deque())
                }
            else:
                metrics_to_export = dict(self.metrics)

            exported_metrics = {}

            for metric_name, metric_deque in metrics_to_export.items():
                filtered_metrics = [
                    {
                        "name": m.name,
                        "value": m.value,
                        "unit": m.unit,
                        "timestamp": m.timestamp.isoformat(),
                        "tags": m.tags,
                    }
                    for m in metric_deque
                    if m.timestamp >= since
                ]

                if filtered_metrics:
                    exported_metrics[metric_name] = filtered_metrics

            return {
                "export_timestamp": datetime.now().isoformat(),
                "since": since.isoformat(),
                "metrics": exported_metrics,
                "summary": self.get_performance_summary(),
            }

    def clear_metrics(self, operation_name: Optional[str] = None) -> None:
        """Clear performance metrics."""
        with self._metrics_lock:
            if operation_name:
                self.metrics.pop(operation_name, None)
                self.operation_counts.pop(operation_name, None)
                self.operation_times.pop(operation_name, None)
            else:
                self.metrics.clear()
                self.operation_counts.clear()
                self.operation_times.clear()

    def _should_sample(self) -> bool:
        """Determine if we should sample this metric."""
        import random

        return random.random() < self._sample_rate

    def _start_background_monitoring(self) -> None:
        """Start background performance monitoring."""
        if not self._monitoring_enabled:
            return

        def monitor():
            while self._monitoring_enabled:
                try:
                    time.sleep(60)  # Run every minute

                    # Record system metrics
                    self.record_metric("active_operations", len(self.operation_counts))
                    self.record_metric(
                        "total_metrics", sum(len(d) for d in self.metrics.values())
                    )

                    # Check for memory cleanup
                    with self._metrics_lock:
                        # Clean old metrics (older than 1 hour)
                        cutoff = datetime.now() - timedelta(hours=1)
                        for metric_name, metric_deque in self.metrics.items():
                            while metric_deque and metric_deque[0].timestamp < cutoff:
                                metric_deque.popleft()

                except Exception as e:
                    logger.error(f"Background monitoring error: {e}")

        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()

    # Async support

    async def async_time_operation(
        self, operation_name: str, coro, tags: Optional[Dict[str, str]] = None
    ):
        """Time an async operation."""
        timer = self.start_timer(operation_name, tags)
        try:
            result = await coro
            return result
        finally:
            self.end_timer(timer)

    def get_cache_performance(self) -> Dict[str, Any]:
        """Get cache performance metrics if available."""
        try:
            # Try to get cache stats if cache service is available
            if hasattr(self, "cache_service"):
                return self.cache_service.get_stats()
            return {"error": "Cache service not available"}
        except Exception as e:
            return {"error": f"Failed to get cache stats: {e}"}
