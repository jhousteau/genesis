"""
Performance Regression Detection - CRAFT Refactor Component
Automated detection of performance regressions with statistical analysis

This module implements comprehensive performance regression detection using
statistical methods to identify performance degradation over time.
"""

import json
import logging
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PerformanceBaseline:
    """Baseline performance metrics for regression detection."""

    # Identification
    operation_name: str
    baseline_id: str
    created_at: datetime

    # Performance metrics
    avg_duration_ms: float
    p50_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float

    # Resource metrics
    avg_cpu_percent: float
    avg_memory_mb: float

    # Statistical data
    sample_count: int
    std_deviation: float
    confidence_interval: Tuple[float, float]

    # Metadata
    environment: str = "unknown"
    version: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceBaseline":
        """Create from dictionary."""
        data = data.copy()
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


@dataclass
class RegressionResult:
    """Result of performance regression analysis."""

    # Test information
    operation_name: str
    test_timestamp: datetime
    baseline_id: str

    # Regression detection
    has_regression: bool
    regression_severity: str  # none, minor, major, critical
    confidence_score: float  # 0.0 to 1.0

    # Performance comparison
    current_avg_ms: float
    baseline_avg_ms: float
    performance_change_percent: float

    # Statistical analysis
    statistical_significance: float  # p-value
    effect_size: float  # Cohen's d

    # Details
    failing_metrics: List[str]
    recommendations: List[str]

    # Context
    sample_size: int
    test_duration_minutes: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class RegressionDetector:
    """
    Performance regression detector implementing CRAFT Refactor methodology.

    Uses statistical analysis to detect performance regressions:
    - Maintains performance baselines
    - Performs statistical significance tests
    - Provides confidence scoring
    - Generates actionable recommendations
    """

    def __init__(self, baseline_storage_path: Optional[str] = None):
        self.logger = logging.getLogger(f"{__name__}.RegressionDetector")

        # Storage configuration
        self.storage_path = Path(
            baseline_storage_path or ".genesis/performance/baselines"
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Detection configuration
        self.regression_thresholds = {
            "minor": 1.2,  # 20% performance degradation
            "major": 1.5,  # 50% performance degradation
            "critical": 2.0,  # 100% performance degradation
        }

        self.significance_threshold = 0.05  # p-value threshold
        self.min_effect_size = 0.5  # Cohen's d threshold
        self.min_sample_size = 10

        # Baseline cache
        self._baseline_cache: Dict[str, PerformanceBaseline] = {}

        self.logger.info("RegressionDetector initialized")

    def create_baseline(
        self,
        operation_name: str,
        duration_samples: List[float],
        cpu_samples: Optional[List[float]] = None,
        memory_samples: Optional[List[float]] = None,
        environment: str = "unknown",
        version: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PerformanceBaseline:
        """Create a performance baseline from sample data."""

        if len(duration_samples) < self.min_sample_size:
            raise ValueError(
                f"Insufficient samples: {len(duration_samples)} < {self.min_sample_size}"
            )

        # Calculate duration statistics
        avg_duration = statistics.mean(duration_samples)
        std_dev = (
            statistics.stdev(duration_samples) if len(duration_samples) > 1 else 0.0
        )

        # Calculate percentiles
        sorted_durations = sorted(duration_samples)
        n = len(sorted_durations)
        p50 = sorted_durations[int(0.5 * n)]
        p95 = sorted_durations[int(0.95 * n)]
        p99 = sorted_durations[int(0.99 * n)] if n >= 100 else sorted_durations[-1]

        # Calculate confidence interval (95%)
        margin_error = 1.96 * std_dev / (n**0.5)  # 95% confidence
        confidence_interval = (avg_duration - margin_error, avg_duration + margin_error)

        # Calculate resource averages
        avg_cpu = statistics.mean(cpu_samples) if cpu_samples else 0.0
        avg_memory = statistics.mean(memory_samples) if memory_samples else 0.0

        # Create baseline
        baseline_id = f"{operation_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        baseline = PerformanceBaseline(
            operation_name=operation_name,
            baseline_id=baseline_id,
            created_at=datetime.now(),
            avg_duration_ms=avg_duration,
            p50_duration_ms=p50,
            p95_duration_ms=p95,
            p99_duration_ms=p99,
            avg_cpu_percent=avg_cpu,
            avg_memory_mb=avg_memory,
            sample_count=len(duration_samples),
            std_deviation=std_dev,
            confidence_interval=confidence_interval,
            environment=environment,
            version=version,
            metadata=metadata or {},
        )

        # Save baseline
        self._save_baseline(baseline)
        self._baseline_cache[operation_name] = baseline

        self.logger.info(
            f"Created baseline for {operation_name}: {avg_duration:.2f}ms avg, {len(duration_samples)} samples"
        )
        return baseline

    def detect_regression(
        self,
        operation_name: str,
        current_samples: List[float],
        cpu_samples: Optional[List[float]] = None,
        memory_samples: Optional[List[float]] = None,
        baseline_id: Optional[str] = None,
    ) -> RegressionResult:
        """Detect performance regression against baseline."""

        if len(current_samples) < self.min_sample_size:
            raise ValueError(f"Insufficient current samples: {len(current_samples)}")

        # Get baseline
        baseline = self._get_baseline(operation_name, baseline_id)
        if not baseline:
            raise ValueError(f"No baseline found for operation: {operation_name}")

        # Calculate current statistics
        current_avg = statistics.mean(current_samples)
        current_std = (
            statistics.stdev(current_samples) if len(current_samples) > 1 else 0.0
        )

        # Perform statistical tests
        (
            has_regression,
            severity,
            confidence,
            p_value,
            effect_size,
        ) = self._analyze_regression(
            baseline, current_samples, current_avg, current_std
        )

        # Calculate performance change
        change_percent = (
            (current_avg - baseline.avg_duration_ms) / baseline.avg_duration_ms
        ) * 100

        # Identify failing metrics
        failing_metrics = self._identify_failing_metrics(
            baseline, current_samples, cpu_samples, memory_samples
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            severity, failing_metrics, change_percent
        )

        # Create result
        result = RegressionResult(
            operation_name=operation_name,
            test_timestamp=datetime.now(),
            baseline_id=baseline.baseline_id,
            has_regression=has_regression,
            regression_severity=severity,
            confidence_score=confidence,
            current_avg_ms=current_avg,
            baseline_avg_ms=baseline.avg_duration_ms,
            performance_change_percent=change_percent,
            statistical_significance=p_value,
            effect_size=effect_size,
            failing_metrics=failing_metrics,
            recommendations=recommendations,
            sample_size=len(current_samples),
            test_duration_minutes=0,  # Could be calculated from metadata
            metadata={
                "baseline_created": baseline.created_at.isoformat(),
                "baseline_samples": baseline.sample_count,
                "current_std_dev": current_std,
            },
        )

        # Log result
        if has_regression:
            self.logger.warning(
                f"REGRESSION_DETECTED: {operation_name} - {severity} regression "
                f"({change_percent:+.1f}%, confidence: {confidence:.2f})"
            )
        else:
            self.logger.info(
                f"No regression detected for {operation_name} ({change_percent:+.1f}%)"
            )

        return result

    def update_baseline(
        self, operation_name: str, new_samples: List[float]
    ) -> PerformanceBaseline:
        """Update existing baseline with new performance data."""
        existing_baseline = self._get_baseline(operation_name)

        if not existing_baseline:
            return self.create_baseline(operation_name, new_samples)

        # For simplicity, create new baseline (in production, might merge data)
        return self.create_baseline(
            operation_name,
            new_samples,
            environment=existing_baseline.environment,
            version=existing_baseline.version,
            metadata=existing_baseline.metadata,
        )

    def get_baseline(
        self, operation_name: str, baseline_id: Optional[str] = None
    ) -> Optional[PerformanceBaseline]:
        """Get baseline for operation."""
        return self._get_baseline(operation_name, baseline_id)

    def list_baselines(
        self, operation_name: Optional[str] = None
    ) -> List[PerformanceBaseline]:
        """List all baselines, optionally filtered by operation."""
        baselines = []

        for baseline_file in self.storage_path.glob("*.json"):
            try:
                with open(baseline_file, "r") as f:
                    data = json.load(f)
                    baseline = PerformanceBaseline.from_dict(data)

                    if (
                        operation_name is None
                        or baseline.operation_name == operation_name
                    ):
                        baselines.append(baseline)

            except Exception as e:
                self.logger.warning(
                    f"Failed to load baseline from {baseline_file}: {e}"
                )

        return sorted(baselines, key=lambda b: b.created_at, reverse=True)

    def _get_baseline(
        self, operation_name: str, baseline_id: Optional[str] = None
    ) -> Optional[PerformanceBaseline]:
        """Get baseline from cache or storage."""

        # Check cache first
        if baseline_id is None and operation_name in self._baseline_cache:
            return self._baseline_cache[operation_name]

        # Search storage
        for baseline_file in self.storage_path.glob("*.json"):
            try:
                with open(baseline_file, "r") as f:
                    data = json.load(f)
                    baseline = PerformanceBaseline.from_dict(data)

                    if baseline.operation_name == operation_name and (
                        baseline_id is None or baseline.baseline_id == baseline_id
                    ):
                        self._baseline_cache[operation_name] = baseline
                        return baseline

            except Exception as e:
                self.logger.warning(
                    f"Failed to load baseline from {baseline_file}: {e}"
                )

        return None

    def _save_baseline(self, baseline: PerformanceBaseline) -> None:
        """Save baseline to storage."""
        filename = f"{baseline.baseline_id}.json"
        filepath = self.storage_path / filename

        try:
            with open(filepath, "w") as f:
                json.dump(baseline.to_dict(), f, indent=2)

            self.logger.debug(f"Saved baseline to {filepath}")

        except Exception as e:
            self.logger.error(f"Failed to save baseline: {e}")

    def _analyze_regression(
        self,
        baseline: PerformanceBaseline,
        current_samples: List[float],
        current_avg: float,
        current_std: float,
    ) -> Tuple[bool, str, float, float, float]:
        """Perform comprehensive regression analysis."""

        # Calculate performance ratio
        performance_ratio = current_avg / baseline.avg_duration_ms

        # Determine severity based on ratio
        severity = "none"
        if performance_ratio >= self.regression_thresholds["critical"]:
            severity = "critical"
        elif performance_ratio >= self.regression_thresholds["major"]:
            severity = "major"
        elif performance_ratio >= self.regression_thresholds["minor"]:
            severity = "minor"

        # Calculate effect size (Cohen's d)
        pooled_std = ((baseline.std_deviation**2 + current_std**2) / 2) ** 0.5
        effect_size = (
            abs(current_avg - baseline.avg_duration_ms) / pooled_std
            if pooled_std > 0
            else 0
        )

        # Simple statistical significance test (would use proper t-test in production)
        # For now, use confidence interval check
        baseline_lower, baseline_upper = baseline.confidence_interval
        current_margin = 1.96 * current_std / (len(current_samples) ** 0.5)
        current_lower = current_avg - current_margin

        # Check if confidence intervals don't overlap (indicates significance)
        significant = current_lower > baseline_upper
        p_value = 0.01 if significant else 0.1  # Simplified

        # Calculate confidence score
        confidence = min(1.0, effect_size * 0.5 + (1 - p_value) * 0.5)

        # Determine if regression detected
        has_regression = (
            severity != "none"
            and significant
            and effect_size >= self.min_effect_size
            and p_value < self.significance_threshold
        )

        return has_regression, severity, confidence, p_value, effect_size

    def _identify_failing_metrics(
        self,
        baseline: PerformanceBaseline,
        duration_samples: List[float],
        cpu_samples: Optional[List[float]],
        memory_samples: Optional[List[float]],
    ) -> List[str]:
        """Identify which metrics are failing compared to baseline."""
        failing = []

        # Check duration metrics
        current_avg = statistics.mean(duration_samples)
        if current_avg > baseline.avg_duration_ms * 1.2:  # 20% threshold
            failing.append("average_duration")

        # Check percentiles
        sorted_durations = sorted(duration_samples)
        n = len(sorted_durations)
        current_p95 = sorted_durations[int(0.95 * n)]
        if current_p95 > baseline.p95_duration_ms * 1.2:
            failing.append("p95_duration")

        # Check CPU if available
        if cpu_samples and baseline.avg_cpu_percent > 0:
            current_avg_cpu = statistics.mean(cpu_samples)
            if current_avg_cpu > baseline.avg_cpu_percent * 1.5:  # 50% threshold
                failing.append("cpu_usage")

        # Check memory if available
        if memory_samples and baseline.avg_memory_mb > 0:
            current_avg_memory = statistics.mean(memory_samples)
            if current_avg_memory > baseline.avg_memory_mb * 1.3:  # 30% threshold
                failing.append("memory_usage")

        return failing

    def _generate_recommendations(
        self, severity: str, failing_metrics: List[str], change_percent: float
    ) -> List[str]:
        """Generate actionable recommendations based on regression analysis."""
        recommendations = []

        if severity == "none":
            return recommendations

        # General recommendations based on severity
        if severity == "critical":
            recommendations.extend(
                [
                    "URGENT: Critical performance regression detected - immediate investigation required",
                    "Consider rolling back recent changes if possible",
                    "Alert on-call team and escalate to senior developers",
                ]
            )
        elif severity == "major":
            recommendations.extend(
                [
                    "Major performance degradation - prioritize investigation",
                    "Review recent code changes and deployments",
                    "Consider implementing performance monitoring alerts",
                ]
            )
        elif severity == "minor":
            recommendations.extend(
                [
                    "Minor performance degradation detected",
                    "Schedule performance review in next sprint",
                    "Monitor trend to prevent further degradation",
                ]
            )

        # Specific recommendations based on failing metrics
        if "average_duration" in failing_metrics:
            recommendations.extend(
                [
                    "Profile slow operations to identify bottlenecks",
                    "Review algorithm efficiency and data structure usage",
                    "Consider implementing caching for frequently accessed data",
                ]
            )

        if "p95_duration" in failing_metrics:
            recommendations.extend(
                [
                    "Investigate outlier operations causing high percentile latency",
                    "Review error handling and timeout configurations",
                    "Consider implementing circuit breakers for external dependencies",
                ]
            )

        if "cpu_usage" in failing_metrics:
            recommendations.extend(
                [
                    "Profile CPU usage to identify compute-intensive operations",
                    "Consider async processing for CPU-bound tasks",
                    "Review loop efficiency and optimization opportunities",
                ]
            )

        if "memory_usage" in failing_metrics:
            recommendations.extend(
                [
                    "Check for memory leaks and unnecessary object retention",
                    "Review data structure choices and memory allocation patterns",
                    "Consider implementing object pooling for frequently used objects",
                ]
            )

        # Add change magnitude context
        if abs(change_percent) > 100:
            recommendations.append(
                f"Performance changed by {change_percent:+.1f}% - requires immediate attention"
            )
        elif abs(change_percent) > 50:
            recommendations.append(
                f"Significant performance change: {change_percent:+.1f}%"
            )

        return recommendations

    def cleanup_old_baselines(self, retention_days: int = 30) -> int:
        """Clean up old baseline files beyond retention period."""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        removed_count = 0

        for baseline_file in self.storage_path.glob("*.json"):
            try:
                # Check file modification time
                file_time = datetime.fromtimestamp(baseline_file.stat().st_mtime)

                if file_time < cutoff_date:
                    baseline_file.unlink()
                    removed_count += 1
                    self.logger.debug(f"Removed old baseline: {baseline_file.name}")

            except Exception as e:
                self.logger.warning(
                    f"Failed to process baseline file {baseline_file}: {e}"
                )

        if removed_count > 0:
            self.logger.info(f"Cleaned up {removed_count} old baseline files")

        return removed_count
